"""deadline_checker.py 단위 테스트."""

from datetime import datetime, timedelta, timezone

from src.notifier.deadline_checker import _parse_lms_date, find_approaching_deadlines
from src.scraper.models import Course, CourseDetail, LectureItem, LectureType, Week

KST = timezone(timedelta(hours=9))


def _course(id: str = "1") -> Course:
    return Course(id=id, long_name="테스트과목", href=f"/courses/{id}", term="2026-1")


def _detail(course: Course, lectures: list[LectureItem]) -> CourseDetail:
    week = Week(title="1주차", week_number=1, lectures=lectures)
    return CourseDetail(course=course, course_name=course.long_name, professors="교수", weeks=[week])


def _now() -> datetime:
    return datetime(2026, 5, 19, 10, 0, 0, tzinfo=KST)


def _lec(
    lecture_type: LectureType,
    end_date: str = "5월 19일 오후 11:59",
    attendance: str = "none",
    completion: str = "incomplete",
    **kwargs,
) -> LectureItem:
    return LectureItem(
        title="테스트항목",
        item_url="/courses/1/modules/items/999",
        lecture_type=lecture_type,
        end_date=end_date,
        attendance=attendance,
        completion=completion,
        **kwargs,
    )


class TestFindApproachingDeadlines:
    def test_file_type_excluded(self):
        """PDF 파일 열람 항목(FILE)은 마감 알림 대상에서 제외된다."""
        course = _course()
        lec = _lec(LectureType.FILE)
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert items == [], "FILE 타입은 알림 대상이 아니어야 함"

    def test_quiz_included(self):
        """퀴즈는 마감 알림 대상이다."""
        course = _course()
        lec = _lec(LectureType.QUIZ)
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert len(items) == 1
        assert items[0].type_label == "퀴즈"

    def test_assignment_included(self):
        """과제는 마감 알림 대상이다."""
        course = _course()
        lec = _lec(LectureType.ASSIGNMENT)
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert len(items) == 1
        assert items[0].type_label == "과제"

    def test_discussion_included(self):
        """토론은 마감 알림 대상이다."""
        course = _course()
        lec = _lec(LectureType.DISCUSSION)
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert len(items) == 1
        assert items[0].type_label == "토론"

    def test_video_types_excluded(self):
        """영상 강의 타입은 마감 알림 대상에서 제외된다."""
        course = _course()
        for lt in (
            LectureType.MOVIE,
            LectureType.READYSTREAM,
            LectureType.SCREENLECTURE,
            LectureType.EVERLEC,
            LectureType.MP4,
        ):
            lec = _lec(lt)
            detail = _detail(course, [lec])
            items = find_approaching_deadlines([course], [detail], now=_now())
            assert items == [], f"{lt} 타입은 알림 대상이 아니어야 함"

    def test_completed_item_excluded(self):
        """완료된 항목은 알림 대상에서 제외된다."""
        course = _course()
        lec = _lec(LectureType.QUIZ, completion="completed")
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert items == []

    def test_attended_item_excluded(self):
        """출석 처리된 항목은 알림 대상에서 제외된다."""
        course = _course()
        for status in ("attendance", "late", "excused"):
            lec = _lec(LectureType.QUIZ, attendance=status)
            detail = _detail(course, [lec])
            items = find_approaching_deadlines([course], [detail], now=_now())
            assert items == [], f"attendance={status}인 항목은 알림 대상이 아니어야 함"

    def test_dedup_skips_already_notified(self):
        """이미 전송된 알림은 재전송하지 않는다."""
        from src.notifier.deadline_checker import _make_dedup_key

        course = _course()
        lec = _lec(LectureType.QUIZ)
        detail = _detail(course, [lec])

        key = _make_dedup_key(course, lec, 24)
        items = find_approaching_deadlines([course], [detail], notified={key}, now=_now())

        # 24h 키가 이미 notified에 있으므로 해당 threshold는 건너뜀
        assert all(item.threshold != 24 for item in items)

    def test_no_end_date_excluded(self):
        """마감일 없는 항목은 알림 대상에서 제외된다."""
        course = _course()
        lec = LectureItem(
            title="t",
            item_url="/a",
            lecture_type=LectureType.QUIZ,
            end_date=None,
            attendance="none",
            completion="incomplete",
        )
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert items == []

    def test_past_deadline_excluded(self):
        """이미 지난 마감일은 알림 대상에서 제외된다."""
        course = _course()
        lec = _lec(LectureType.QUIZ, end_date="5월 18일 오후 11:59")  # now보다 하루 전
        detail = _detail(course, [lec])

        items = find_approaching_deadlines([course], [detail], now=_now())

        assert items == []


class TestParseLmsDate:
    def test_basic_parsing(self):
        now = datetime(2026, 5, 19, 10, 0, tzinfo=KST)
        result = _parse_lms_date("5월 19일 오후 11:59", now=now)
        assert result == datetime(2026, 5, 19, 23, 59, tzinfo=KST)

    def test_noon_pm(self):
        now = datetime(2026, 5, 1, tzinfo=KST)
        result = _parse_lms_date("5월 1일 오후 12:00", now=now)
        assert result == datetime(2026, 5, 1, 12, 0, tzinfo=KST)

    def test_midnight_am(self):
        now = datetime(2026, 5, 1, tzinfo=KST)
        result = _parse_lms_date("5월 1일 오전 12:00", now=now)
        assert result == datetime(2026, 5, 1, 0, 0, tzinfo=KST)

    def test_empty_string_returns_none(self):
        assert _parse_lms_date("") is None

    def test_invalid_format_returns_none(self):
        assert _parse_lms_date("invalid") is None
