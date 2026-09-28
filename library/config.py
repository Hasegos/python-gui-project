import os
from dataclasses import dataclass


# ─────────────────────────────────────
# 1. 데이터베이스 (PostgreSQL)
# ─────────────────────────────────────
@dataclass(frozen=True)
class DatabaseConfig:
    """
    PostgreSQL 접속 정보.

    환경 변수(LIBRARY_DB_*)가 있으면 그 값을, 없으면 기본값을 사용한다.
    """
    host    : str = os.getenv("LIBRARY_DB_HOST", "localhost")
    port    : int = int(os.getenv("LIBRARY_DB_PORT", "5432"))
    dbname  : str = os.getenv("LIBRARY_DB_NAME", "library")
    user    : str = os.getenv("LIBRARY_DB_USER", "postgres")
    password: str = os.getenv("LIBRARY_DB_PASSWORD", "postgres")

    def as_dict(self) -> dict:
        """psycopg2.connect() 에 그대로 넘길 수 있는 dict 를 반환한다."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


DB = DatabaseConfig()


# ─────────────────────────────────────
# 2. 대출 정책
# ─────────────────────────────────────
LOAN_DAYS            = int(os.getenv("LIBRARY_LOAN_DAYS", "14"))  # 기본 대출 기간 (일)
MAX_LOANS_PER_MEMBER = int(os.getenv("LIBRARY_MAX_LOANS", "5"))   # 1인 최대 대출 권수
