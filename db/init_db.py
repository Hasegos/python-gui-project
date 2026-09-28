import argparse
import sys
from pathlib import Path

import psycopg2

from core.config import settings
from core.logger import get_logger
from db.session import close_pool, transaction

logger = get_logger("db.init_db")

DB_DIR      = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"
SAMPLE_PATH = DB_DIR / "sample_data.sql"


# ─────────────────────────────────────
# 1. 스키마 생성
# ─────────────────────────────────────
def init_schema() -> None:
    """
    schema.sql 을 실행해 테이블과 인덱스를 생성한다.

    IF NOT EXISTS 로 작성되어 있어 여러 번 실행해도 안전하다.
    """
    with transaction() as cur:
        cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    logger.info("스키마 생성 완료")


# ─────────────────────────────────────
# 2. 샘플 데이터 입력
# ─────────────────────────────────────
def load_sample_data() -> None:
    """
    sample_data.sql 을 실행해 시연용 데이터를 입력한다.

    이미 데이터가 있으면 중복 삽입하지 않는다.
    """
    with transaction() as cur:
        cur.execute(SAMPLE_PATH.read_text(encoding="utf-8"))
    logger.info("샘플 데이터 입력 완료")


# ─────────────────────────────────────
# 3. 빈 DB 여부 확인
# ─────────────────────────────────────
def is_empty() -> bool:
    """
    도서와 대출자가 한 건도 없는지 확인한다.

    Returns:
        book, member 테이블이 모두 비어 있으면 True
    """
    with transaction() as cur:
        cur.execute(
            "SELECT NOT EXISTS (SELECT 1 FROM book) AND NOT EXISTS (SELECT 1 FROM member) AS empty"
        )
        return cur.fetchone()["empty"]


# ─────────────────────────────────────
# 4. 프로그램 시작 시 자동 초기화
# ─────────────────────────────────────
def init_database() -> None:
    """
    테이블을 자동 생성하고, DB 가 비어 있으면 샘플 데이터를 입력한다.

    샘플 자동 입력은 settings.AUTO_LOAD_SAMPLE(LIBRARY_AUTO_SAMPLE)로 끌 수 있다.
    """
    init_schema()
    if settings.AUTO_LOAD_SAMPLE and is_empty():
        load_sample_data()


# ─────────────────────────────────────
# 5. 명령행 실행
# ─────────────────────────────────────
def main() -> int:
    """
    스키마를 생성하고, --sample 옵션이 있으면 샘플 데이터를 입력한다.

    사용법:
        python -m db.init_db            # 테이블/인덱스 생성
        python -m db.init_db --sample   # 생성 후 샘플 데이터 입력
    Returns:
        종료 코드 (성공 0, 실패 1)
    """
    parser = argparse.ArgumentParser(description="도서 대출 관리 시스템 DB 초기화")
    parser.add_argument("--sample", action="store_true", help="샘플 데이터 입력")
    args = parser.parse_args()

    try:
        init_schema()
        if args.sample:
            load_sample_data()
    except psycopg2.Error as e:
        logger.error("DB 초기화 실패: %s", e)
        return 1
    finally:
        close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
