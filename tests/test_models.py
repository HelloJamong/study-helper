"""models.py 단위 테스트."""

from src.scraper.models import Course, CourseDetail, LectureItem, LectureType, Week


def test_lecture_item_is_video():
    """VIDEO_LECTURE_TYPES에 해당하면 is_video=True."""
    movie = LectureItem(title="t", item_url="/a", lecture_type=LectureType.MOVIE)
    assert movie.is_video is True

    assign = LectureItem(title="t", item_url="/a", lecture_type=LectureType.ASSIGNMENT)
    assert assign.is_video is False


def test_lecture_item_needs_watch():
    """미완료 비디오 강의만 needs_watch=True."""
    lec = LectureItem(title="t", item_url="/a", lecture_type=LectureType.MOVIE, completion="incomplete")
    assert lec.needs_watch is True

    lec_done = LectureItem(title="t", item_url="/a", lecture_type=LectureType.MOVIE, completion="completed")
    assert lec_done.needs_watch is False

    lec_upcoming = LectureItem(
        title="t", item_url="/a", lecture_type=LectureType.MOVIE, completion="incomplete", is_upcoming=True
    )
    assert lec_upcoming.needs_watch is False


def test_lecture_item_full_url():
    """상대/절대 URL 처리 정확성."""
    lec_rel = LectureItem(title="t", item_url="/courses/123", lecture_type=LectureType.MOVIE)
    assert lec_rel.full_url == "https://canvas.ssu.ac.kr/courses/123"

    lec_abs = LectureItem(title="t", item_url="https://example.com/v", lecture_type=LectureType.MOVIE)
    assert lec_abs.full_url == "https://example.com/v"


def test_course_detail_counts():
    """과목 상세 비디오/미시청 카운트."""
    lecs = [
        LectureItem(title="v1", item_url="/a", lecture_type=LectureType.MOVIE, completion="incomplete"),
        LectureItem(title="v2", item_url="/b", lecture_type=LectureType.MOVIE, completion="completed"),
        LectureItem(title="a1", item_url="/c", lecture_type=LectureType.ASSIGNMENT),
    ]
    week = Week(title="1주차", week_number=1, lectures=lecs)
    course = Course(id="1", long_name="Test", href="/c/1", term="2026-1")
    detail = CourseDetail(course=course, course_name="Test", professors="Prof", weeks=[week])
    assert detail.total_video_count == 2
    assert detail.pending_video_count == 1


def test_week_pending_count():
    """Week의 미시청 강의 카운트."""
    lecs = [
        LectureItem(title="v1", item_url="/a", lecture_type=LectureType.MOVIE, completion="incomplete"),
        LectureItem(title="v2", item_url="/b", lecture_type=LectureType.READYSTREAM, completion="incomplete"),
        LectureItem(title="v3", item_url="/c", lecture_type=LectureType.MOVIE, completion="completed"),
    ]
    week = Week(title="2주차", week_number=2, lectures=lecs)
    assert week.pending_count == 2


def test_course_urls():
    """Course URL 프로퍼티."""
    course = Course(id="42", long_name="Test", href="/courses/42", term="2026-1")
    assert course.full_url == "https://canvas.ssu.ac.kr/courses/42"
    assert course.lectures_url == "https://canvas.ssu.ac.kr/courses/42/external_tools/71"


def test_all_video_lecture_types():
    """모든 비디오 타입이 is_video=True."""
    for lt in (
        LectureType.MOVIE,
        LectureType.READYSTREAM,
        LectureType.SCREENLECTURE,
        LectureType.EVERLEC,
        LectureType.MP4,
    ):
        lec = LectureItem(title="t", item_url="/a", lecture_type=lt)
        assert lec.is_video is True, f"{lt} should be video"

    for lt in (LectureType.ASSIGNMENT, LectureType.QUIZ, LectureType.DISCUSSION, LectureType.FILE, LectureType.OTHER):
        lec = LectureItem(title="t", item_url="/a", lecture_type=lt)
        assert lec.is_video is False, f"{lt} should not be video"
