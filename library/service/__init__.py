# Service 계층: 입력값 검증, 업무 규칙 확인, 트랜잭션 경계를 담당한다.
from library.exceptions import ValidationError


# ─────────────────────────────────────
# 1. 문자열 입력값 정리/검증
# ─────────────────────────────────────
def clean_text(value, label: str, max_length: int, required: bool = False) -> str | None:
    """
    앞뒤 공백을 제거하고 필수 여부와 길이를 검증한다.

    Args:
        value     : 입력값
        label     : 오류 메시지에 표시할 항목명
        max_length: 최대 길이
        required  : 필수 입력 여부
    Returns:
        정리된 문자열. 빈 값이면 None.
    Raises:
        ValidationError: 필수값 누락 또는 길이 초과 시
    """
    text = (value or "").strip()
    if not text:
        if required:
            raise ValidationError(f"{label} 항목을 입력해 주세요.")
        return None
    if len(text) > max_length:
        raise ValidationError(f"{label} 항목은 {max_length}자 이하로 입력해 주세요.")
    return text


# ─────────────────────────────────────
# 2. 정수 입력값 변환/검증
# ─────────────────────────────────────
def parse_int(value, label: str, minimum: int | None = None, maximum: int | None = None) -> int | None:
    """
    정수 문자열을 변환하고 범위를 검증한다.

    Args:
        value  : 입력값
        label  : 오류 메시지에 표시할 항목명
        minimum: 최소값 (None 이면 검사 안 함)
        maximum: 최대값 (None 이면 검사 안 함)
    Returns:
        변환된 정수. 빈 값이면 None.
    Raises:
        ValidationError: 숫자가 아니거나 범위를 벗어날 때
    """
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        number = int(text)
    except ValueError:
        raise ValidationError(f"{label} 항목은 숫자로 입력해 주세요.") from None
    if minimum is not None and number < minimum:
        raise ValidationError(f"{label} 항목은 {minimum} 이상이어야 합니다.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{label} 항목은 {maximum} 이하여야 합니다.")
    return number
