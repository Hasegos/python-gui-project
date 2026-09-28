import tkinter as tk
from datetime import datetime
from tkinter import ttk

from core.constants.ui import APP_TITLE, WINDOW_MIN_SIZE, WINDOW_SIZE
from core.templates import apply_style
from db.session import close_pool
from templates.book_view import BookView
from templates.loan_view import LoanView
from templates.member_view import MemberView
from templates.stats_view import StatsView

# 탭 목록: (화면 클래스, 탭 제목)
VIEWS = [
    (BookView, "도서 관리"),
    (MemberView, "대출자 관리"),
    (LoanView, "대출 / 반납"),
    (StatsView, "통계"),
]


# ─────────────────────────────────────
# 1. 메인 윈도우
# ─────────────────────────────────────
class MainWindow(tk.Tk):
    """
    기능별 화면(templates/*_view.py)을 탭(Notebook)으로 구성한 메인 윈도우.

    하단 상태 표시줄의 set_status 함수를 각 화면에 넘겨 처리 결과를 표시한다.
    """

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(*WINDOW_MIN_SIZE)
        apply_style(self)

        # 상태 표시줄을 먼저 배치해 창이 작아져도 가려지지 않도록 한다.
        self.status_var = tk.StringVar(value="준비")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 4)).pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        for view_class, title in VIEWS:
            self.notebook.add(view_class(self.notebook, self.set_status), text=f"  {title}  ")

        # 탭을 전환할 때마다 최신 데이터로 갱신 (다른 탭에서 변경된 내용 반영)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────
    # 1-1. 상태 표시줄
    # ─────────────────────────────────
    def set_status(self, message: str) -> None:
        """
        하단 상태 표시줄에 처리 시각과 메시지를 표시한다.

        Args:
            message: 표시할 메시지
        """
        self.status_var.set(f"[{datetime.now():%H:%M:%S}] {message}")

    # ─────────────────────────────────
    # 1-2. 이벤트
    # ─────────────────────────────────
    def _on_tab_changed(self, _event) -> None:
        """선택된 화면의 refresh() 를 호출해 최신 데이터로 갱신한다."""
        view = self.nametowidget(self.notebook.select())
        view.refresh()

    def _on_close(self) -> None:
        """창을 닫을 때 커넥션 풀을 정리하고 종료한다."""
        close_pool()
        self.destroy()
