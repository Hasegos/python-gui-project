import logging
import sys


# ─────────────────────────────────────
# 1. 공용 로거 설정
# ─────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거를 반환한다.

    처음 호출될 때만 StreamHandler 를 붙이고, 이후에는 같은 로거를 재사용한다.

    Args:
        name: 로거 이름 (보통 모듈명)
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(name)s | %(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.propagate = False

    return logger
