import tkinter as tk
from tkinter import messagebox, ttk

from core.constants.ui import COLOR_DANGER, COLOR_MUTED
from models.member_model import Member
from services import loan_service, member_service
from templates.history_dialog import MEMBER_HISTORY_COLUMNS, LoanHistoryDialog
from templates.widgets import DataTable, FormFields, SearchBar, guarded

# 목록 컬럼: (key, 헤더명, 너비, 정렬)
COLUMNS = [
    ("member_id", "ID", 40, "center"),
    ("student_no", "학번", 90, "center"),
    ("name", "이름", 80, "center"),
    ("department", "학과", 130, "w"),
    ("phone", "연락처", 120, "center"),
    ("email", "이메일", 170, "w"),
    ("on_loan", "대출중", 60, "center"),
    ("overdue", "연체", 50, "center"),
]

# 입력 폼 항목: (key, 라벨)
FORM_FIELDS = [
    ("student_no", "학번 *"),
    ("name", "이름 *"),
    ("department", "학과"),
    ("phone", "연락처"),
    ("email", "이메일"),
]

# 검색 기준: 화면 표시명 → 서비스 전달값
SEARCH_FIELDS = {
    "전체": "all",
    "학번": "student_no",
    "이름": "name",
    "학과": "department",
    "연락처": "phone",
}


# ─────────────────────────────────────
# 1. 대출자 관리 화면
# ─────────────────────────────────────
class MemberView(ttk.Frame):
    """
    대출자 등록/수정/삭제, 목록 조회, 대출자별 대출 이력 화면.

    좌측은 검색 조건 + 대출자 목록, 우측은 대출자 정보 입력 폼으로 구성한다.

    Args:
        master    : 부모 위젯 (Notebook)
        set_status: 하단 상태 표시줄에 메시지를 표시하는 함수
    """

    def __init__(self, master, set_status):
        super().__init__(master, padding=12)
        self.set_status = set_status
        self.selected_id: int | None = None

        self._build_list()
        self._build_form()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    # ─────────────────────────────────
    # 1-1. 화면 구성
    # ─────────────────────────────────
    def _build_list(self) -> None:
        """좌측 검색 바와 대출자 목록을 구성한다."""
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.search_bar = SearchBar(left, SEARCH_FIELDS, self.refresh)
        self.search_bar.pack(fill="x", pady=(0, 8))

        self.table = DataTable(left, COLUMNS, height=20)
        self.table.pack(fill="both", expand=True)
        # 연체 도서가 있는 대출자는 빨간색으로 표시
        self.table.tag_configure("overdue", foreground=COLOR_DANGER)
        self.table.on_select(self._on_select)
        self.table.on_double_click(lambda _member: self._show_history())

    def _build_form(self) -> None:
        """우측 대출자 정보 입력 폼과 등록/수정/삭제/이력 버튼을 구성한다."""
        right = ttk.LabelFrame(self, text="대출자 정보", padding=12)
        right.grid(row=0, column=1, sticky="ns")

        self.mode_var = tk.StringVar()
        ttk.Label(right, textvariable=self.mode_var, style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        self.form = FormFields(right, FORM_FIELDS, choices={"department": []})
        self.form.pack(fill="x")
        ttk.Label(right, text="* 필수 입력 / 연락처 예: 010-1234-5678", foreground=COLOR_MUTED).pack(anchor="w", pady=(4, 12))

        buttons = ttk.Frame(right)
        buttons.pack(fill="x")
        self.create_btn = ttk.Button(buttons, text="신규 등록", style="Accent.TButton", command=self._create)
        self.update_btn = ttk.Button(buttons, text="수정", command=self._update)
        self.delete_btn = ttk.Button(buttons, text="삭제", command=self._delete)
        clear_btn = ttk.Button(buttons, text="입력 초기화", command=self._clear_form)
        for i, btn in enumerate((self.create_btn, self.update_btn, self.delete_btn, clear_btn)):
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        self.history_btn = ttk.Button(buttons, text="대출 이력 보기", command=self._show_history)
        self.history_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(8, 2))
        buttons.columnconfigure((0, 1), weight=1)

        self._clear_form()

    # ─────────────────────────────────
    # 1-2. 목록 조회
    # ─────────────────────────────────
    @guarded
    def refresh(self) -> None:
        """
        검색 조건으로 대출자 목록을 다시 조회한다.

        탭 전환 시에도 호출되어 대출/반납으로 바뀐 대출중·연체 권수를 반영한다.
        """
        members = member_service.search_members(self.search_bar.keyword, self.search_bar.field)
        self.table.set_rows(
            members, "member_id",
            tag_func=lambda m: "overdue" if m.overdue else None,
        )
        self.search_bar.set_count(f"총 {len(members)}명")
        self.form.set_choices("department", member_service.get_departments())
        # 새로고침 후에도 선택하던 대출자를 유지
        if self.selected_id is not None:
            self.table.select(self.selected_id)

    # ─────────────────────────────────
    # 1-3. 입력 폼 상태 (신규 / 수정 모드)
    # ─────────────────────────────────
    def _on_select(self, member: Member | None) -> None:
        """
        목록에서 대출자를 선택하면 폼에 채우고 수정 모드로 전환한다.

        Args:
            member: 선택된 Member. 선택 해제 시 None.
        """
        if member is None:
            return
        self.selected_id = member.member_id
        self.form.set(member)
        self.mode_var.set(f"대출자 수정 (ID {member.member_id})")
        self._set_edit_buttons(True)

    def _clear_form(self) -> None:
        """폼을 비우고 신규 등록 모드로 전환한다."""
        self.selected_id = None
        self.table.clear_selection()
        self.form.clear()
        self.mode_var.set("신규 대출자 등록")
        self._set_edit_buttons(False)
        self.form.focus_first()

    def _set_edit_buttons(self, enabled: bool) -> None:
        """선택된 대출자가 있을 때만 수정/삭제/이력 버튼을 활성화한다."""
        state = ["!disabled"] if enabled else ["disabled"]
        for btn in (self.update_btn, self.delete_btn, self.history_btn):
            btn.state(state)

    # ─────────────────────────────────
    # 1-4. 등록 / 수정 / 삭제
    # ─────────────────────────────────
    @guarded
    def _create(self) -> None:
        """입력한 정보로 대출자를 등록하고, 등록된 대출자를 선택 상태로 둔다."""
        member_id = member_service.create_member(self.form.get())
        self.selected_id = member_id
        self.refresh()
        self.set_status(f"대출자가 등록되었습니다. (ID {member_id})")

    @guarded
    def _update(self) -> None:
        """선택한 대출자 정보를 수정한다."""
        if self.selected_id is None:
            return
        member_service.update_member(self.selected_id, self.form.get())
        self.refresh()
        self.set_status(f"대출자 정보가 수정되었습니다. (ID {self.selected_id})")

    @guarded
    def _delete(self) -> None:
        """확인 대화상자를 띄운 뒤 선택한 대출자를 삭제한다."""
        member = self.table.selected()
        if member is None:
            return
        if not messagebox.askyesno(
            "대출자 삭제",
            f"{member.name}({member.student_no}) 님을 삭제하시겠습니까?\n"
            "해당 대출자의 대출 이력도 함께 삭제됩니다.",
            parent=self.winfo_toplevel(),
        ):
            return
        member_service.delete_member(member.member_id)
        self._clear_form()
        self.refresh()
        self.set_status(f"대출자가 삭제되었습니다. ({member.name})")

    # ─────────────────────────────────
    # 1-5. 대출자별 대출 이력
    # ─────────────────────────────────
    @guarded
    def _show_history(self) -> None:
        """선택한 대출자의 전체 대출 이력을 팝업으로 보여준다."""
        member = self.table.selected()
        if member is None:
            return
        loans = loan_service.get_history(member_id=member.member_id)
        LoanHistoryDialog(self, f"{member.name}({member.student_no}) 대출 이력", loans, MEMBER_HISTORY_COLUMNS)
