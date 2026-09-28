import tkinter as tk
from datetime import datetime
from tkinter import ttk

from library import db
from library.gui.book_tab import BookTab
from library.gui.widgets import apply_style

# 탭 목록: (화면 클래스, 탭 제목)
TABS = [
    (BookTab, "도서 관리"),
]


# ─────────────────────────────────────
# 1. 메인 윈도우
# ─────────────────────────────────────
class LibraryApp(tk.Tk):
    """
    기능별 화면을 탭(Notebook)으로 구성한 메인 윈도우.

    하단 상태 표시줄의 set_status 함수를 각 탭에 넘겨 처리 결과를 표시한다.
    """

    def __init__(self):
        super().__init__()
        self.title("도서 대출 관리 시스템")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        apply_style(self)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        for tab_class, title in TABS:
            self.notebook.add(tab_class(self.notebook, self.set_status), text=f"  {title}  ")

        self.status_var = tk.StringVar(value="준비")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 4)).pack(fill="x")

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
        """선택된 탭의 refresh() 를 호출해 최신 데이터로 갱신한다."""
        tab = self.nametowidget(self.notebook.select())
        tab.refresh()

    def _on_close(self) -> None:
        """창을 닫을 때 커넥션 풀을 정리하고 종료한다."""
        db.close_pool()
        self.destroy()
