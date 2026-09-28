from contextlib import contextmanager
from pathlib import Path

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from library import config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# 프로그램 전체에서 공유하는 커넥션 풀 (최초 사용 시 생성)
_pool = None


# ─────────────────────────────────────
# 1. 커넥션 풀 생성
# ─────────────────────────────────────
def get_pool() -> SimpleConnectionPool:
    """
    커넥션 풀을 반환한다. 없으면 새로 생성한다.

    Returns:
        SimpleConnectionPool 객체
    """
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(minconn=1, maxconn=5, **config.DB.as_dict())
    return _pool


# ─────────────────────────────────────
# 2. 커넥션 풀 종료
# ─────────────────────────────────────
def close_pool() -> None:
    """
    풀에 있는 모든 커넥션을 닫는다. 프로그램 종료 시 호출한다.
    """
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


# ─────────────────────────────────────
# 3. 트랜잭션 범위
# ─────────────────────────────────────
@contextmanager
def transaction():
    """
    하나의 트랜잭션 범위를 제공한다.

    블록이 정상 종료되면 commit, 예외가 발생하면 rollback 후 예외를 다시 던진다.
    커서는 RealDictCursor 로 조회 결과를 dict 로 돌려준다.

    Returns:
        (yield) RealDictCursor 커서
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # 커넥션을 닫지 않고 풀에 반납해 재사용한다.
        pool.putconn(conn)


# ─────────────────────────────────────
# 4. 스키마 생성
# ─────────────────────────────────────
def init_schema() -> None:
    """
    schema.sql 을 실행해 테이블과 인덱스를 생성한다.

    IF NOT EXISTS 로 작성되어 있어 여러 번 실행해도 안전하다.
    """
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with transaction() as cur:
        cur.execute(sql)


# ─────────────────────────────────────
# 5. 접속 확인
# ─────────────────────────────────────
def check_connection() -> None:
    """
    DB 접속 가능 여부를 확인한다.

    Raises:
        psycopg2.OperationalError: 접속 실패 시
    """
    with transaction() as cur:
        cur.execute("SELECT 1")
