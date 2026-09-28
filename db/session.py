from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from core.config import settings
from core.logger import get_logger

logger = get_logger("db.session")

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
        try:
            _pool = SimpleConnectionPool(
                minconn=settings.POOL_MIN_CONN,
                maxconn=settings.POOL_MAX_CONN,
                **settings.DB_CONNECT_ARGS,
            )
        except UnicodeDecodeError as e:
            # 한글 Windows 용 PostgreSQL 은 접속 실패 메시지(비밀번호 오류 등)를 CP949 로 보내
            # psycopg2 가 UTF-8 로 해석하다 실패한다. 원문을 CP949 로 다시 읽어 접속 오류로 바꿔 던진다.
            raise psycopg2.OperationalError(_decode_server_message(e)) from None
        logger.info("커넥션 풀 생성: %s", settings.DB_DISPLAY)
    return _pool


# ─────────────────────────────────────
# 1-1. 서버 오류 메시지 복원
# ─────────────────────────────────────
def _decode_server_message(error: UnicodeDecodeError) -> str:
    """
    UTF-8 해석에 실패한 서버 메시지를 CP949 로 다시 디코딩한다.

    Args:
        error: psycopg2 접속 중 발생한 UnicodeDecodeError
    Returns:
        복원한 서버 오류 메시지. 복원할 수 없으면 기본 안내 문구.
    """
    raw = error.object if isinstance(error.object, (bytes, bytearray)) else b""
    for encoding in ("cp949", "utf-8"):
        try:
            message = bytes(raw).decode(encoding).strip()
            if message:
                return message
        except UnicodeDecodeError:
            continue
    return "DB 접속에 실패했습니다. 비밀번호, 포트, DB 이름을 확인해 주세요."


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
        logger.info("커넥션 풀 종료")


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
# 4. 접속 확인
# ─────────────────────────────────────
def check_connection() -> None:
    """
    DB 접속 가능 여부를 확인한다.

    Raises:
        psycopg2.OperationalError: 접속 실패 시
    """
    with transaction() as cur:
        cur.execute("SELECT 1")
