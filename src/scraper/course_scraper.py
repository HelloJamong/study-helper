import asyncio
import re
from collections.abc import Callable

from playwright.async_api import Frame, async_playwright

from src.auth.login import ensure_logged_in
from src.scraper.models import (
    Course,
    CourseDetail,
    LectureItem,
    LectureType,
    Week,
)

_BASE_URL = "https://canvas.ssu.ac.kr"
_DASHBOARD_URL = f"{_BASE_URL}/"

_TYPE_CLASS_MAP = {
    "movie": LectureType.MOVIE,
    "readystream": LectureType.READYSTREAM,
    "screenlecture": LectureType.SCREENLECTURE,
    "everlec": LectureType.EVERLEC,
    "zoom": LectureType.ZOOM,
    "mp4": LectureType.MP4,
    "assignment": LectureType.ASSIGNMENT,
    "wiki_page": LectureType.WIKI_PAGE,
    "quiz": LectureType.QUIZ,
    "discussion": LectureType.DISCUSSION,
    "file": LectureType.FILE,
    "attachment": LectureType.FILE,
}


class CourseScraper:
    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        log_callback: Callable[[str], None] | None = None,
    ):
        self.username = username
        self.password = password
        self.headless = headless
        self._log = log_callback or (lambda msg: None)
        self._pw = None
        self._browser = None
        self._page = None

    async def _setup_browser(self):
        _args = [
            "--disable-blink-features=AutomationControlled",
            "--enable-proprietary-codecs",
            "--disable-web-security",
            "--use-fake-ui-for-media-stream",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--window-size=1280,720",
            "--password-store=basic",
        ]
        # Chrome(H.264 포함) 우선 시도 — ARM64 등 미지원 환경에서는 Chromium으로 fallback
        try:
            browser = await self._pw.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=_args,
            )
        except Exception:
            browser = await self._pw.chromium.launch(
                headless=self.headless,
                args=_args,
            )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            permissions=["camera", "microphone", "geolocation"],
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        await page.add_init_script("""
            // webdriver 속성 제거
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // chrome 런타임 위장
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // plugins 위장 (headless에서는 빈 배열)
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // languages 위장
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en'],
            });

            // permissions 위장
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );
        """)
        return page, browser

    async def start(self):
        self._pw = await async_playwright().start()
        self._page, self._browser = await self._setup_browser()
        self._log("LMS 접속 중...")
        await self._page.goto(_DASHBOARD_URL, wait_until="networkidle")
        if "login" in self._page.url:
            self._log("로그인 진행 중...")
            ok = await ensure_logged_in(self._page, self.username, self.password)
            if not ok:
                raise RuntimeError("로그인 실패. 학번/비밀번호를 확인하세요.")
            self._log("로그인 완료")

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def fetch_courses(self) -> list[Course]:
        """대시보드에서 수강 과목 목록 추출"""
        if "canvas.ssu.ac.kr" not in self._page.url or "/courses/" in self._page.url:
            await self._page.goto(_DASHBOARD_URL, wait_until="networkidle")

        # 세션 만료 시 자동 재로그인
        if "login" in self._page.url:
            await self._ensure_session()
            await self._page.goto(_DASHBOARD_URL, wait_until="networkidle")

        raw = await self._page.evaluate("() => window.ENV && window.ENV.STUDENT_PLANNER_COURSES")
        if not raw:
            raise RuntimeError("과목 목록을 불러올 수 없습니다.")

        courses = []
        for item in raw:
            # 학기 정보가 없는 비교과(안내 등) 과목 제외
            term = item.get("term", "")
            if not term:
                continue

            long_name = item.get("longName", "")
            # LMS API가 "과목명 - 과목명" 형태로 중복 반환하는 경우 앞쪽만 사용
            if " - " in long_name:
                first, _, second = long_name.partition(" - ")
                if first.strip() == second.strip():
                    long_name = first.strip()
            courses.append(
                Course(
                    id=str(item["id"]),
                    long_name=long_name,
                    href=item.get("href", f"/courses/{item['id']}"),
                    term=term,
                    is_favorited=item.get("isFavorited", False),
                )
            )
        return courses

    async def _ensure_session(self) -> None:
        """세션 만료 시 자동 재로그인을 시도한다."""
        if "login" in self._page.url:
            self._log("세션 만료 감지 — 자동 재로그인 중...")
            ok = await ensure_logged_in(self._page, self.username, self.password)
            if not ok:
                raise RuntimeError("자동 재로그인 실패. 학번/비밀번호를 확인하세요.")
            self._log("재로그인 완료")

    async def fetch_lectures(self, course: Course) -> CourseDetail:
        """과목의 주차별 강의 목록 스크래핑"""
        self._log(f"강의 목록 로딩: {course.long_name}")
        await self._page.goto(course.lectures_url, wait_until="networkidle")

        # 세션 만료로 로그인 페이지로 리디렉트된 경우 재로그인 후 재시도
        if "login" in self._page.url:
            await self._ensure_session()
            await self._page.goto(course.lectures_url, wait_until="networkidle")

        iframe_el = await self._page.wait_for_selector("iframe#tool_content", timeout=15000)
        iframe = await iframe_el.content_frame()
        if not iframe:
            raise RuntimeError("iframe을 찾을 수 없습니다.")

        await iframe.wait_for_selector("#root", timeout=15000)
        await asyncio.sleep(0.5)

        root = await iframe.query_selector("#root")
        course_name = await root.get_attribute("data-course_name") or course.long_name
        professors = await root.get_attribute("data-professors") or ""

        expand_btn = await iframe.query_selector(".xnmb-all_fold-btn")
        if expand_btn:
            btn_text = await expand_btn.text_content()
            if btn_text and "펼치기" in btn_text:
                await expand_btn.click()
                await asyncio.sleep(0.5)

        weeks = await self._parse_weeks(iframe)
        return CourseDetail(course=course, course_name=course_name, professors=professors, weeks=weeks)

    async def _parse_weeks(self, iframe: Frame) -> list[Week]:
        module_list = await iframe.query_selector(".xnmb-module-list")
        if not module_list:
            self._log("강의 목록을 찾을 수 없습니다 (.xnmb-module-list). LMS 구조가 변경되었을 수 있습니다.")
            return []

        top_divs = await module_list.query_selector_all(":scope > div")
        weeks = []
        for div in top_divs:
            header = await div.query_selector(".xnmb-module-outer-wrapper")
            if not header:
                continue

            title_el = await header.query_selector(".xnmb-module-title")
            title = (await title_el.text_content()).strip() if title_el else ""

            week_num = len(weeks) + 1
            match = re.search(r"(\d+)주차", title)
            if match:
                week_num = int(match.group(1))

            items = await div.query_selector_all(".xnmb-module_item-outer-wrapper")
            lectures = []
            for item_el in items:
                lecture = await self._parse_item(item_el)
                if lecture:
                    lectures.append(lecture)

            weeks.append(Week(title=title, week_number=week_num, lectures=lectures))
        return weeks

    async def _parse_item(self, el) -> LectureItem | None:
        icon_el = await el.query_selector("i.xnmb-module_item-icon")
        lecture_type = LectureType.OTHER
        if icon_el:
            classes = await icon_el.get_attribute("class") or ""
            for cls_name, lt in _TYPE_CLASS_MAP.items():
                if cls_name in classes.split():
                    lecture_type = lt
                    break

        title_el = await el.query_selector("a.xnmb-module_item-left-title")
        if not title_el:
            title_el = await el.query_selector(".xnmb-module_item-left-title")
            if not title_el:
                return None
            title = (await title_el.text_content() or "").strip()
            item_url = ""
        else:
            title = (await title_el.text_content() or "").strip()
            item_url = await title_el.get_attribute("href") or ""
            if "?" in item_url:
                item_url = item_url.split("?")[0]

        if not title:
            return None

        duration = None
        periods_el = await el.query_selector("[class*='lecture_periods']")
        if periods_el:
            spans = await periods_el.query_selector_all("span")
            for span in reversed(spans):
                text = (await span.text_content() or "").strip()
                if re.match(r"^\d+:\d+$", text):
                    duration = text
                    break

        week_label = ""
        lesson_label = ""
        start_date = None
        end_date = None

        week_span = await el.query_selector("[class*='lesson_periods-week']")
        if week_span:
            week_label = (await week_span.text_content() or "").strip()
        lesson_span = await el.query_selector("[class*='lesson_periods-lesson']")
        if lesson_span:
            lesson_label = (await lesson_span.text_content() or "").strip()

        # 시작/마감 날짜 추출 (예: "3월 10일 오전 00:00")
        unlock_el = await el.query_selector("[class*='lecture_periods-unlock_at'] span")
        if unlock_el:
            start_date = (await unlock_el.text_content() or "").strip() or None
        due_el = await el.query_selector("[class*='lecture_periods-due_at'] span")
        if due_el:
            end_date = (await due_el.text_content() or "").strip() or None

        attendance = "none"
        att_el = await el.query_selector("[class*='attendance_status']")
        if att_el:
            att_classes = await att_el.get_attribute("class") or ""
            for status in ("attendance", "late", "absent", "excused"):
                if status in att_classes:
                    attendance = status
                    break

        completion = "incomplete"
        comp_el = await el.query_selector("[class*='module_item-completed']")
        if comp_el:
            comp_classes = await comp_el.get_attribute("class") or ""
            if "completed" in comp_classes and "incomplete" not in comp_classes:
                completion = "completed"

        is_upcoming = False
        dday_el = await el.query_selector(".xncb-component-sub-d_day")
        if dday_el:
            dday_classes = await dday_el.get_attribute("class") or ""
            if "upcoming" in dday_classes:
                is_upcoming = True

        return LectureItem(
            title=title,
            item_url=item_url,
            lecture_type=lecture_type,
            week_label=week_label,
            lesson_label=lesson_label,
            duration=duration,
            attendance=attendance,
            completion=completion,
            is_upcoming=is_upcoming,
            start_date=start_date,
            end_date=end_date,
        )

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()
