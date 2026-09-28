import re

from psycopg2 import errors

from library.db import transaction
from library.exceptions import LibraryError, NotFoundError, ValidationError
from library.repository import member_repository
from library.service import clean_text

STUDENT_NO_PATTERN = re.compile(r"[0-9A-Za-z]+")
PHONE_PATTERN      = re.compile(r"\d{2,3}-?\d{3,4}-?\d{4}")   # 010-1234-5678 / 01012345678
EMAIL_PATTERN      = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


# ─────────────────────────────────────
# 1. 대출자 검색
# ─────────────────────────────────────
def search_members(keyword: str = "", field: str = "all") -> list[dict]:
    """
    대출자 목록을 검색한다.

    Args:
        keyword: 검색어
        field  : 검색 기준 (student_no, name, department, phone, all)
    Returns:
        대출자 dict 리스트
    """
    with transaction() as cur:
        return member_repository.find_all(cur, keyword.strip(), field)


# ─────────────────────────────────────
# 2. 학과 목록 조회
# ─────────────────────────────────────
def get_departments() -> list[str]:
    """
    입력 폼 Combobox 에 표시할 학과 목록을 조회한다.

    Returns:
        학과 문자열 리스트
    """
    with transaction() as cur:
        return member_repository.find_departments(cur)


# ─────────────────────────────────────
# 3. 대출자 등록
# ─────────────────────────────────────
def create_member(form: dict) -> int:
    """
    입력값을 검증한 뒤 대출자를 등록한다.

    Args:
        form: 화면 입력값 dict (문자열)
    Returns:
        생성된 member_id
    Raises:
        ValidationError: 입력값 오류 또는 학번 중복 시
    """
    data = _validate(form)
    try:
        with transaction() as cur:
            return member_repository.insert(cur, data)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 학번입니다. ({data['student_no']})") from None


# ─────────────────────────────────────
# 4. 대출자 수정
# ─────────────────────────────────────
def update_member(member_id: int, form: dict) -> None:
    """
    입력값을 검증한 뒤 대출자 정보를 수정한다.

    Args:
        member_id: 수정할 대출자 PK
        form     : 화면 입력값 dict (문자열)
    Raises:
        ValidationError: 입력값 오류 또는 학번 중복 시
    """
    data = _validate(form)
    try:
        with transaction() as cur:
            _lock_member(cur, member_id)
            member_repository.update(cur, member_id, data)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 학번입니다. ({data['student_no']})") from None


# ─────────────────────────────────────
# 5. 대출자 삭제
# ─────────────────────────────────────
def delete_member(member_id: int) -> None:
    """
    대출자를 삭제한다. 반납하지 않은 도서가 있으면 삭제하지 않는다.

    Args:
        member_id: 삭제할 대출자 PK
    Raises:
        LibraryError: 미반납 도서가 있을 때
    """
    with transaction() as cur:
        member = _lock_member(cur, member_id)
        on_loan = member_repository.count_on_loan(cur, member_id)
        if on_loan:
            raise LibraryError(
                f"{member['name']}({member['student_no']}) 님은 반납하지 않은 도서가 {on_loan}권 있어 "
                "삭제할 수 없습니다.\n반납 처리 후 다시 시도해 주세요."
            )
        member_repository.delete(cur, member_id)


# ─────────────────────────────────────
# 6. 대출자 잠금 + 존재 확인
# ─────────────────────────────────────
def _lock_member(cur, member_id: int) -> dict:
    """
    대출자 행을 잠그고, 없으면 NotFoundError 를 던진다.

    Args:
        cur      : DB 커서
        member_id: 대출자 PK
    Returns:
        잠근 대출자 dict
    """
    member = member_repository.lock_by_id(cur, member_id)
    if member is None:
        raise NotFoundError("존재하지 않는 대출자입니다. 목록을 새로고침해 주세요.")
    return member


# ─────────────────────────────────────
# 7. 입력값 검증
# ─────────────────────────────────────
def _validate(form: dict) -> dict:
    """
    화면 입력값을 검증하고 DB 에 저장할 형태로 변환한다.

    Args:
        form: 화면 입력값 dict (문자열)
    Returns:
        검증된 대출자 정보 dict
    Raises:
        ValidationError: 입력값 오류 시
    """
    student_no = clean_text(form.get("student_no"), "학번", 20, required=True)
    if not STUDENT_NO_PATTERN.fullmatch(student_no):
        raise ValidationError("학번은 영문/숫자만 입력해 주세요.")

    phone = clean_text(form.get("phone"), "연락처", 20)
    if phone and not PHONE_PATTERN.fullmatch(phone):
        raise ValidationError("연락처 형식이 올바르지 않습니다. (예: 010-1234-5678)")

    email = clean_text(form.get("email"), "이메일", 100)
    if email and not EMAIL_PATTERN.fullmatch(email):
        raise ValidationError("이메일 형식이 올바르지 않습니다. (예: user@example.com)")

    return {
        "student_no": student_no,
        "name": clean_text(form.get("name"), "이름", 50, required=True),
        "department": clean_text(form.get("department"), "학과", 100),
        "phone": phone,
        "email": email,
    }
