import tkinter as tk
from tkinter import ttk

from core.constants.loan import STATUS_OVERDUE, STATUS_RETURNED
from core.constants.ui import COLOR_DANGER, COLOR_DISABLED_ROW
from models.loan_model import Loan
from templates.widgets import DataTable

# 대출자 이력: 어떤 도서를 빌렸는지 표시
MEMBER_HISTORY_COLUMNS = [
    ("loan_id", "번호", 50, "center"),
    ("title", "도서명", 220, "w"),
    ("loan_date", "대출일", 95, "center"),
    ("due_date", "반납예정일", 95, "center"),
    ("return_date", "반납일", 95, "center"),
    ("status", "상태", 70, "center"),
    ("overdue_days", "연체일수", 65, "center"),
]

# 도서 이력: 누가 빌렸는지 표시
BOOK_HISTORY_COLUMNS = [
    ("loan_id", "번호", 50, "center"),
    ("student_no", "학번", 90, "center"),
    ("name", "이름", 80, "center"),
    ("loan_date", "대출일", 95, "center"),
    ("due_date", "반납예정일", 95, "center"),
    ("return_date", "반납일", 95, "center"),
    ("status", "상태", 70, "center"),
    ("overdue_days", "연체일수", 65, "center"),
]

STATUS_TAGS = {STATUS_OVERDUE: "overdue", STATUS_RETURNED: "returned"}


# ─────────────────────────────────────
# 1. 대출 이력 팝업
# ─────────────────────────────────────
class LoanHistoryDialog(tk.Toplevel):
    """
    도서 또는 대출자 한 건의 전체 대출 이력을 보여주는 팝업 창.

    도서/대출자 목록에서 행을 더블클릭하거나 '대출 이력' 버튼을 누르면 열린다.

    Args:
        master : 부모 위젯
        title  : 팝업 제목 (예: "김민준(20210001) 대출 이력")
        loans  : 표시할 Loan 리스트
        columns: 표 컬럼 정의 (MEMBER_HISTORY_COLUMNS / BOOK_HISTORY_COLUMNS)
    """

    def __init__(self, master, title: str, loans: list[Loan], columns):
        super().__init__(master)
        self.title(title)
        self.minsize(640, 360)
        # 부모 창 위에 떠 있도록 설정 (크기는 내용에 맞춰 자동 결정)
        self.transient(master.winfo_toplevel())

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        table = DataTable(frame, columns, height=10)
        table.pack(fill="both", expand=True)
        table.tag_configure("overdue", foreground=COLOR_DANGER)
        table.tag_configure("returned", foreground=COLOR_DISABLED_ROW)
        table.set_rows(loans, "loan_id", tag_func=lambda l: STATUS_TAGS.get(l.status))

        ttk.Label(frame, text=self._summary(loans)).pack(anchor="w", pady=(8, 0))
        ttk.Button(frame, text="닫기", command=self.destroy).pack(anchor="e", pady=(8, 0))

        # 팝업이 열려 있는 동안 메인 창 조작을 막는다.
        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())

    @staticmethod
    def _summary(loans: list[Loan]) -> str:
        """
        이력 요약 문구를 만든다.

        Args:
            loans: Loan 리스트
        Returns:
            "총 n건 · 미반납 n건 · 연체 n건 · 연체 반납 n건" 문자열
        """
        not_returned = sum(1 for l in loans if not l.is_returned)
        overdue = sum(1 for l in loans if l.status == STATUS_OVERDUE)
        late = sum(1 for l in loans if l.is_returned and l.overdue_days)
        return f"총 {len(loans)}건 · 미반납 {not_returned}건 · 연체 {overdue}건 · 연체 반납 {late}건"
