import sys
import tkinter as tk
from tkinter import messagebox

import psycopg2

from core.config import settings
from core.logger import get_logger
from db.init_db import init_schema
from db.session import check_connection
from templates.main_window import MainWindow

logger = get_logger("main")


# ─────────────────────────────────────
# 1. 프로그램 실행
# ─────────────────────────────────────
def main() -> int:
    """
    DB 연결을 확인하고 스키마를 준비한 뒤 메인 윈도우를 실행한다.

    DB 에 연결할 수 없으면 접속 정보와 함께 안내 메시지를 띄우고 종료한다.

    Returns:
        종료 코드 (정상 0, DB 연결 실패 1)
    """
    try:
        check_connection()
        init_schema()
    except psycopg2.Error as e:
        logger.error("DB 연결 실패: %s", e)
        # 메인 윈도우 없이 오류 대화상자만 띄우기 위해 빈 루트 창을 숨김
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "DB 연결 실패",
            "PostgreSQL 에 연결할 수 없습니다.\n"
            f"접속 정보: {settings.DB_DISPLAY}\n\n"
            ".env 또는 LIBRARY_DB_* 환경 변수, DB 서버 상태를 확인해 주세요.\n\n"
            f"{e}",
        )
        root.destroy()
        return 1

    MainWindow().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
