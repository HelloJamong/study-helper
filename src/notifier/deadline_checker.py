"""
마감 임박 알림 모듈.

비디오가 아닌 강의 항목(퀴즈, 과제 등)의 마감이 임박할 때
텔레그램으로 알림을 전송한다.
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime

from src.config import KST, get_data_path
from src.scraper.models import VIDEO_LECTURE_TYPES, Course, CourseDetail, LectureItem, LectureType

_DEADLINE_FILE = get_data_path("deadline_notified.json")

# 알림 기준 시간 (시간 단위)
_THRESHOLDS = [24, 12]

_TYPE_LABELS = {
    LectureType.QUIZ: "퀴즈",
    LectureType.ASSIGNMENT: "과제",
    LectureType.DISCUSSION: "토론",
    LectureType.WIKI_PAGE: "위키",
    LectureType.FILE: "파일",
    LectureType.ZOOM: "Zoom",
    LectureType.OTHER: "기타",
}


@dataclass
class DeadlineItem:
    """마감 임박 항목."""

    course: Course
    lecture: LectureItem
    type_label: str
    remaining_hours: float
    threshold: int
    dedup_key: str


def _parse_lms_date(date_str: str, now: datetime | None = None) -> datetime | None:
    """LMS 날짜 문자열을 파싱한다. (예: '3월 19일 오후 11:59')

    연도 전환기(12월→1월, 1월→12월) 보정:
    - 현재 11~12월인데 파싱 월이 1~2월이면 다음 해
    - 현재 1~2월인데 파싱 월이 11~12월이면 전년도
    """
    if not date_str:
        return None
    match = re.match(r"(\d+)월\s*(\d+)일(?:\s*(오전|오후)\s*(\d+):(\d+))?", date_str.strip())
    if not match:
        return None
    month = int(match.group(1))
    day = int(match.group(2))
    ampm = match.group(3)
    hour = int(match.group(4)) if match.group(4) else 23
    minute = int(match.group(5)) if match.group(5) else 59

    if ampm == "오후" and hour != 12:
        hour += 12
    elif ampm == "오전" and hour == 12:
        hour = 0

    if now is None:
        now = datetime.now(KST)
    year = now.year

    # 연도 전환기 보정
    if now.month >= 11 and month <= 2:
        year += 1
    elif now.month <= 2 and month >= 11:
        year -= 1

    try:
        return datetime(year, month, day, hour, minute, tzinfo=KST)
    except ValueError:
        return None


def _make_dedup_key(course: Course, lecture: LectureItem, threshold: int) -> str:
    """과목 ID + 강의 제목 해시 기반의 안정적인 dedup 키를 생성한다."""
    stable_id = hashlib.sha256(f"{course.id}:{lecture.title}".encode()).hexdigest()[:16]
    return f"{stable_id}:{threshold}"


def _load_notified() -> set[str]:
    try:
        if _DEADLINE_FILE.exists():
            return set(json.loads(_DEADLINE_FILE.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        print("  [경고] deadline_notified.json 파싱 실패 — 초기화합니다.", file=sys.stderr)
    except Exception:
        pass
    return set()


def _save_notified(notified: set[str]) -> None:
    try:
        _DEADLINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DEADLINE_FILE.write_text(json.dumps(sorted(notified)), encoding="utf-8")
    except Exception as e:
        print(f"  [경고] deadline_notified.json 저장 실패: {e}", file=sys.stderr)


def find_approaching_deadlines(
    courses: list[Course],
    details: list[CourseDetail | None],
    notified: set[str] | None = None,
    now: datetime | None = None,
) -> list[DeadlineItem]:
    """마감 임박 항목을 검색한다 (순수 로직, 알림 전송 없음).

    Args:
        courses:  과목 목록
        details:  과목별 강의 상세 (courses와 동일 순서)
        notified: 이미 알림 전송된 키 집합 (None이면 빈 set)
        now:      현재 시각 (테스트 시 주입 가능)

    Returns:
        마감 임박 DeadlineItem 목록
    """
    if now is None:
        now = datetime.now(KST)
    if notified is None:
        notified = set()

    items: list[DeadlineItem] = []

    for course, detail in zip(courses, details, strict=False):
        if detail is None:
            continue
        for week in detail.weeks:
            for lec in week.lectures:
                if lec.lecture_type in VIDEO_LECTURE_TYPES:
                    continue
                # 완료 판별: completion 또는 attendance 둘 중 하나라도 완료면 건너뜀
                if lec.completion == "completed":
                    continue
                if lec.attendance in ("attendance", "late", "excused"):
                    continue
                if lec.is_upcoming:
                    continue
                if not lec.end_date:
                    continue

                deadline = _parse_lms_date(lec.end_date, now=now)
                if deadline is None:
                    continue

                remaining_hours = (deadline - now).total_seconds() / 3600
                if remaining_hours <= 0:
                    continue

                type_label = _TYPE_LABELS.get(lec.lecture_type, lec.lecture_type.value)

                for threshold in _THRESHOLDS:
                    key = _make_dedup_key(course, lec, threshold)
                    if key in notified:
                        continue
                    if remaining_hours <= threshold:
                        items.append(
                            DeadlineItem(
                                course=course,
                                lecture=lec,
                                type_label=type_label,
                                remaining_hours=remaining_hours,
                                threshold=threshold,
                                dedup_key=key,
                            )
                        )

    return items


def check_and_notify_deadlines(
    courses: list[Course],
    details: list[CourseDetail | None],
    token: str = "",
    chat_id: str = "",
) -> int:
    """마감 임박 항목을 확인하고 텔레그램으로 알림을 전송한다.

    Args:
        courses:  과목 목록
        details:  과목별 강의 상세
        token:    텔레그램 봇 토큰 (빈 문자열이면 전송 건너뜀)
        chat_id:  텔레그램 Chat ID

    Returns:
        전송된 알림 수
    """
    if not token or not chat_id:
        return 0

    from src.notifier.telegram_notifier import notify_deadline_warning

    notified = _load_notified()
    items = find_approaching_deadlines(courses, details, notified=notified)

    if not items:
        return 0

    sent_count = 0
    for item in items:
        ok = notify_deadline_warning(
            bot_token=token,
            chat_id=chat_id,
            course_name=item.course.long_name,
            week_label=item.lecture.week_label,
            lecture_title=item.lecture.title,
            type_label=item.type_label,
            end_date=item.lecture.end_date or "",
            remaining_hours=item.remaining_hours,
        )
        if ok:
            notified.add(item.dedup_key)
            sent_count += 1

    if sent_count > 0:
        _save_notified(notified)

    return sent_count
