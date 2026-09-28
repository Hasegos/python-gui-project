import argparse
import sys
from pathlib import Path

import psycopg2

from library import db

SAMPLE_PATH = Path(__file__).parent / "library" / "sample_data.sql"


# ─────────────────────────────────────
# 1. DB 초기화 실행
# ─────────────────────────────────────
def main() -> int:
    """
    스키마를 생성하고, --sample 옵션이 있으면 샘플 데이터를 입력한다.

    사용법:
        python init_db.py            # 테이블/인덱스 생성
        python init_db.py --sample   # 생성 후 샘플 데이터 입력
    Returns:
        종료 코드 (성공 0, 실패 1)
    """
    parser = argparse.ArgumentParser(description="도서 대출 관리 시스템 DB 초기화")
    parser.add_argument("--sample", action="store_true", help="샘플 데이터 입력")
    args = parser.parse_args()

    try:
        db.init_schema()
        print("스키마 생성 완료")
        if args.sample:
            with db.transaction() as cur:
                cur.execute(SAMPLE_PATH.read_text(encoding="utf-8"))
            print("샘플 데이터 입력 완료")
    except psycopg2.Error as e:
        print(f"DB 초기화 실패: {e}", file=sys.stderr)
        return 1
    finally:
        db.close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
