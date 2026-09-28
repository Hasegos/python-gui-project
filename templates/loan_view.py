import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from core.config import settings
from core.constants.loan import (
    DEFAULT_LOAN_FILTER,
    LOAN_STATUS_FILTERS,
    MAX_LOAN_DAYS,
    MIN_LOAN_DAYS,
    STATUS_OVERDUE,
    STATUS_RETURNED,
)
from core.constants.ui import COLOR_DANGER, COLOR_DISABLED_ROW, COLOR_MUTED
from models.loan_model import Loan
from services import loan_service
from templates.widgets import DataTable, SearchableCombobox, guarded

# 목록 컬럼: (key, 헤더명, 너비, 정렬)
COLUMNS = [
    ("loan_id", "번호", 50, "center"),
    ("title", "도서명", 200, "w"),
    ("student_no", "학번", 85, "center"),
    ("name", "이름", 75, "center"),
    ("loan_date", "대출일", 95, "center"),
    ("due_date", "반납예정일", 95, "center"),
    ("return_date", "반납일", 95, "center"),
    ("status", "상태", 70, "center"),
    ("overdue_days", "연체일수", 65, "center"),
]

# 상태 → 표 태그 (연체: 빨간색, 반납완료: 회색)
STATUS_TAGS = {STATUS_OVERDUE: "overdue", STATUS_RETURNED: "returned"}


# ─────────────────────────────────────
# 1. 대출 / 반납 화면
# ─────────────────────────────────────
class LoanView(ttk.Frame):
    """
    대출 처리, 반납 처리, 대출 현황 검색 및 상태 필터링 화면.

    상단은 대출 처리 영역, 하단은 대출 현황 목록으로 구성한다.

    Args:
        master    : 부모 위젯 (Notebook)
        set_status: 하단 상태 표시줄에 메시지를 표시하는 함수
    """

    def __init__(self, master, set_status):
        super().__init__(master, padding=12)
        self.set_status = set_status

        self._build_borrow_form()
        self._build_list()

    # ─────────────────────────────────
    # 1-1. 화면 구성
    # ─────────────────────────────────
    def _build_borrow_form(self) -> None:
        """상단 대출 처리 영역 (도서/대출자 선택, 대출 기간, 대출 버튼) 을 구성한다."""
        box = ttk.LabelFrame(self, text="대출 처리", padding=12)
        box.pack(fill="x", pady=(0, 10))

        ttk.Label(box, text="도서").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.book_combo = SearchableCombobox(box, width=42)
        self.book_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        ttk.Label(box, text="대출자").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.member_combo = SearchableCombobox(box, width=30)
        self.member_combo.grid(row=0, column=3, sticky="ew", padx=(0, 16))

        ttk.Label(box, text="대출 기간(일)").grid(row=0, column=4, sticky="w", padx=(0, 6))
        self.days_var = tk.StringVar(value=str(settings.LOAN_DAYS))
        ttk.Spinbox(
            box, from_=MIN_LOAN_DAYS, to=MAX_LOAN_DAYS, textvariable=self.days_var, width=5,
        ).grid(row=0, column=5, padx=(0, 16))

        ttk.Button(box, text="대출", style="Accent.TButton", command=self._borrow).grid(row=0, column=6, ipadx=12)

        # 대출 기간을 바꾸면 반납 예정일 안내 문구를 바로 갱신
        self.due_var = tk.StringVar()
        ttk.Label(
            box, textvariable=self.due_var, foreground=COLOR_MUTED,
        ).grid(row=1, column=1, columnspan=6, sticky="w", pady=(6, 0))
        self.days_var.trace_add("write", lambda *_: self._update_due_hint())
        self._update_due_hint()
        box.columnconfigure((1, 3), weight=1)

    def _build_list(self) -> None:
        """하단 대출 현황 영역 (상태 필터, 검색, 반납 버튼, 목록, 요약) 을 구성한다."""
        box = ttk.LabelFrame(self, text="대출 현황", padding=12)
        box.pack(fill="both", expand=True)

        toolbar = ttk.Frame(box)
        toolbar.pack(fill="x", pady=(0, 8))
        self.status_filter = tk.StringVar(value=DEFAULT_LOAN_FILTER)
        for label, value in LOAN_STATUS_FILTERS.items():
            ttk.Radiobutton(
                toolbar, text=label, value=value, variable=self.status_filter, command=self.refresh,
            ).pack(side="left", padx=(0, 10))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(toolbar, textvariable=self.keyword_var, width=24)
        keyword_entry.pack(side="left", padx=(6, 6))
        keyword_entry.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(toolbar, text="검색", command=self.refresh).pack(side="left")
        ttk.Label(toolbar, text="도서명 / 이름 / 학번", foreground=COLOR_MUTED).pack(side="left", padx=6)

        self.return_btn = ttk.Button(toolbar, text="반납 처리", command=self._return)
        self.return_btn.pack(side="right")

        self.table = DataTable(box, COLUMNS, height=12)
        self.table.pack(fill="both", expand=True)
        self.table.tag_configure("overdue", foreground=COLOR_DANGER)
        self.table.tag_configure("returned", foreground=COLOR_DISABLED_ROW)
        self.table.on_select(self._on_select)
        self.table.on_double_click(lambda _loan: self._return())

        self.summary_var = tk.StringVar()
        ttk.Label(box, textvariable=self.summary_var).pack(anchor="w", pady=(8, 0))

    # ─────────────────────────────────
    # 1-2. 목록 / 선택지 조회
    # ─────────────────────────────────
    @guarded
    def refresh(self) -> None:
        """
        대출 가능 도서·대출자 선택지와 대출 현황 목록, 상태별 요약을 다시 조회한다.
        """
        self._load_options()
        loans = loan_service.search_loans(self.status_filter.get(), self.keyword_var.get())
        self.table.set_rows(loans, "loan_id", tag_func=lambda l: STATUS_TAGS.get(l.status))
        counts = loan_service.get_status_counts()
        self.summary_var.set(
            f"조회 {len(loans)}건   |   전체 현황  대출중 {counts.on_loan}건 · "
            f"연체 {counts.overdue}건 · 반납완료 {counts.returned}건"
        )
        self.return_btn.state(["disabled"])

    def _load_options(self) -> None:
        """대출 가능한 도서와 대출자 목록을 Combobox 선택지로 설정한다."""
        books, members = loan_service.get_borrow_options()
        self.book_combo.set_options({
            f"[{b.book_id}] {b.title} - {b.author} (대출가능 {b.available}권)": b.book_id
            for b in books
        })
        self.member_combo.set_options({
            f"{m.student_no} {m.name}" + (f" ({m.department})" if m.department else ""): m.member_id
            for m in members
        })

    def _update_due_hint(self) -> None:
        """입력한 대출 기간으로 반납 예정일과 대출 규칙 안내 문구를 표시한다."""
        try:
            days = int(self.days_var.get())
        except ValueError:
            self.due_var.set("대출 기간을 숫자로 입력해 주세요.")
            return
        due = date.today() + timedelta(days=days)
        self.due_var.set(
            f"반납 예정일: {due:%Y-%m-%d}   ·   1인 최대 {settings.MAX_LOANS_PER_MEMBER}권 / "
            "연체 도서가 있으면 대출 불가   ·   목록은 입력한 글자로 필터링됩니다."
        )

    def _on_select(self, loan: Loan | None) -> None:
        """
        미반납 건을 선택했을 때만 반납 버튼을 활성화한다.

        Args:
            loan: 선택된 Loan. 선택 해제 시 None.
        """
        if loan and not loan.is_returned:
            self.return_btn.state(["!disabled"])
        else:
            self.return_btn.state(["disabled"])

    # ─────────────────────────────────
    # 1-3. 대출 / 반납 처리
    # ─────────────────────────────────
    @guarded
    def _borrow(self) -> None:
        """
        선택한 도서와 대출자로 대출을 처리한다.

        처리 후 미반납 목록으로 전환하고 새로 생긴 대출 기록을 선택한다.
        """
        result = loan_service.borrow_book(
            self.book_combo.value(), self.member_combo.value(), self.days_var.get(),
        )
        self.book_combo.set("")
        self.status_filter.set(DEFAULT_LOAN_FILTER)
        self.refresh()
        self.table.select(result.loan_id)
        self.set_status(
            f"대출 완료: {result.name} - '{result.title}' (반납 예정일 {result.due_date:%Y-%m-%d})"
        )

    @guarded
    def _return(self) -> None:
        """확인 대화상자를 띄운 뒤 선택한 대출 기록을 반납 처리한다. 연체 반납이면 연체일수를 안내한다."""
        loan = self.table.selected()
        if loan is None or loan.is_returned:
            return
        if not messagebox.askyesno(
            "반납 처리",
            f"{loan.name} 님의 '{loan.title}' 을(를) 반납 처리하시겠습니까?",
            parent=self.winfo_toplevel(),
        ):
            return
        result = loan_service.return_book(loan.loan_id)
        self.refresh()
        message = f"반납 완료: {result.name} - '{result.title}'"
        if result.overdue_days:
            message += f" ({result.overdue_days}일 연체 반납)"
        self.set_status(message)
