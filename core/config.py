import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────
# 0. .env 파일 로드
# ─────────────────────────────────────
def _load_env_file(path: Path) -> None:
    """
    프로젝트 루트의 .env 파일을 읽어 환경 변수로 등록한다.

    이미 설정된 환경 변수는 덮어쓰지 않는다. (실행 환경 값 우선)

    Args:
        path: .env 파일 경로
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:

    # ───────────────────────────
    # 1. 데이터 베이스(Postgresql)
    # ───────────────────────────
    DB_HOST    : str = os.getenv("LIBRARY_DB_HOST", "localhost")
    DB_PORT    : int = int(os.getenv("LIBRARY_DB_PORT", "5432"))
    DB_NAME    : str = os.getenv("LIBRARY_DB_NAME", "library")
    DB_USER    : str = os.getenv("LIBRARY_DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("LIBRARY_DB_PASSWORD", "postgres")

    # DB 커넥션 풀
    POOL_MIN_CONN: int = int(os.getenv("LIBRARY_POOL_MIN", "1"))
    POOL_MAX_CONN: int = int(os.getenv("LIBRARY_POOL_MAX", "5"))

    # ───────────────────────────
    # 2. 대출 정책
    # ───────────────────────────
    LOAN_DAYS           : int = int(os.getenv("LIBRARY_LOAN_DAYS", "14"))  # 기본 대출 기간 (일)
    MAX_LOANS_PER_MEMBER: int = int(os.getenv("LIBRARY_MAX_LOANS", "5"))   # 1인 최대 대출 권수

    # ──────────────────────────
    # 3. 계산된 프로퍼티 (접속 정보)
    # ──────────────────────────
    @property
    def DB_CONNECT_ARGS(self) -> dict:
        """
        psycopg2.connect() 에 그대로 넘길 수 있는 접속 정보 dict 를 반환한다.
        """
        return {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "dbname": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
        }

    @property
    def DB_DISPLAY(self) -> str:
        """
        오류 안내용 접속 정보 문자열 (비밀번호 제외).
        """
        return f"{self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
