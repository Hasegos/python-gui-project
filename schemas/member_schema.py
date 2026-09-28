import re
from dataclasses import dataclass

from core.exceptions import ValidationError
from schemas.common_schema import clean_text

STUDENT_NO_PATTERN = re.compile(r"[0-9A-Za-z]+")
PHONE_PATTERN      = re.compile(r"\d{2,3}-?\d{3,4}-?\d{4}")   # 010-1234-5678 / 01012345678
EMAIL_PATTERN      = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


# ─────────────────────────────────────
# 1. 대출자 등록/수정 요청 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class MemberRequest:
    """
    대출자 등록/수정 요청 스키마. 검증을 통과한 값만 담는다.

    Args:
        student_no: 학번 (필수, 영문/숫자)
        name      : 이름 (필수, 50자 이하)
        department: 학과
        phone     : 연락처 (010-1234-5678 형식)
        email     : 이메일
    """
    student_no : str
    name       : str
    department : str | None = None
    phone      : str | None = None
    email      : str | None = None

    @classmethod
    def from_form(cls, form: dict) -> "MemberRequest":
        """
        화면 입력값(문자열 dict)을 검증하여 요청 스키마로 변환한다.

        Args:
            form: 화면 입력값 dict
        Returns:
            MemberRequest 객체
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

        return cls(
            student_no=student_no,
            name=clean_text(form.get("name"), "이름", 50, required=True),
            department=clean_text(form.get("department"), "학과", 100),
            phone=phone,
            email=email,
        )
