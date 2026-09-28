import tkinter as tk
from tkinter import messagebox, ttk

from library.gui.widgets import DataTable, FormFields, guarded
from library.service import book_service

# 목록 컬럼: (key, 헤더명, 너비, 정렬)
COLUMNS = [
    ("book_id", "ID", 40, "center"),
    ("isbn", "ISBN", 125, "center"),
    ("title", "제목", 170, "w"),
    ("author", "저자", 100, "w"),
    ("publisher", "출판사", 90, "w"),
    ("published_year", "출판연도", 65, "center"),
    ("category", "분류", 85, "center"),
    ("quantity", "보유", 45, "center"),
    ("available", "대출가능", 65, "center"),
]

# 입력 폼 항목: (key, 라벨)
FORM_FIELDS = [
    ("isbn", "ISBN"),
    ("title", "제목 *"),
    ("author", "저자 *"),
    ("publisher", "출판사"),
    ("published_year", "출판연도"),
    ("category", "분류"),
    ("quantity", "보유 권수 *"),
]

# 검색 기준: 화면 표시명 → 서비스 전달값
SEARCH_FIELDS = {
    "전체": "all",
    "제목": "title",
    "저자": "author",
    "ISBN": "isbn",
    "출판사": "publisher",
    "분류": "category",
}


# ─────────────────────────────────────
# 1. 도서 관리 화면
# ─────────────────────────────────────
class BookTab(ttk.Frame):
    """
    도서 등록/수정/삭제 및 목록 조회 화면.

    좌측은 검색 조건 + 도서 목록, 우측은 도서 정보 입력 폼으로 구성한다.

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
        """좌측 검색 조건과 도서 목록을 구성한다."""
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        search = ttk.Frame(left)
        search.pack(fill="x", pady=(0, 8))
        self.field_var = tk.StringVar(value="전체")
        ttk.Combobox(
            search, textvariable=self.field_var, values=list(SEARCH_FIELDS),
            state="readonly", width=8,
        ).pack(side="left")
        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(search, textvariable=self.keyword_var, width=30)
        keyword_entry.pack(side="left", padx=6)
        keyword_entry.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(search, text="검색", command=self.refresh).pack(side="left")
        ttk.Button(search, text="전체보기", command=self._reset_search).pack(side="left", padx=(6, 0))
        self.count_var = tk.StringVar()
        ttk.Label(search, textvariable=self.count_var).pack(side="right")

        self.table = DataTable(left, COLUMNS, height=20)
        self.table.pack(fill="both", expand=True)
        # 대출 가능 권수가 0인 도서는 빨간색으로 표시
        self.table.tag_configure("unavailable", foreground="#c0392b")
        self.table.on_select(self._on_select)

    def _build_form(self) -> None:
        """우측 도서 정보 입력 폼과 등록/수정/삭제 버튼을 구성한다."""
        right = ttk.LabelFrame(self, text="도서 정보", padding=12)
        right.grid(row=0, column=1, sticky="ns")

        self.mode_var = tk.StringVar()
        ttk.Label(right, textvariable=self.mode_var, style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        self.form = FormFields(right, FORM_FIELDS, choices={"category": []})
        self.form.pack(fill="x")
        ttk.Label(right, text="* 필수 입력 / ISBN 은 하이픈 없이 입력", foreground="#777").pack(anchor="w", pady=(4, 12))

        buttons = ttk.Frame(right)
        buttons.pack(fill="x")
        self.create_btn = ttk.Button(buttons, text="신규 등록", style="Accent.TButton", command=self._create)
        self.update_btn = ttk.Button(buttons, text="수정", command=self._update)
        self.delete_btn = ttk.Button(buttons, text="삭제", command=self._delete)
        clear_btn = ttk.Button(buttons, text="입력 초기화", command=self._clear_form)
        for i, btn in enumerate((self.create_btn, self.update_btn, self.delete_btn, clear_btn)):
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        buttons.columnconfigure((0, 1), weight=1)

        self._clear_form()

    # ─────────────────────────────────
    # 1-2. 목록 조회
    # ─────────────────────────────────
    @guarded
    def refresh(self) -> None:
        """
        검색 조건으로 도서 목록을 다시 조회한다.

        탭 전환 시에도 호출되어 다른 탭에서 변경된 대출 가능 권수를 반영한다.
        """
        field = SEARCH_FIELDS[self.field_var.get()]
        books = book_service.search_books(self.keyword_var.get(), field)
        self.table.set_rows(
            books, "book_id",
            tag_func=lambda b: "unavailable" if b["available"] <= 0 else None,
        )
        self.count_var.set(f"총 {len(books)}건")
        self.form.set_choices("category", book_service.get_categories())
        # 새로고침 후에도 선택하던 도서를 유지
        if self.selected_id is not None:
            self.table.select(self.selected_id)

    def _reset_search(self) -> None:
        """검색 조건을 초기화하고 전체 목록을 조회한다."""
        self.field_var.set("전체")
        self.keyword_var.set("")
        self.refresh()

    # ─────────────────────────────────
    # 1-3. 입력 폼 상태 (신규 / 수정 모드)
    # ─────────────────────────────────
    def _on_select(self, book: dict | None) -> None:
        """
        목록에서 도서를 선택하면 폼에 채우고 수정 모드로 전환한다.

        Args:
            book: 선택된 도서 dict. 선택 해제 시 None.
        """
        if book is None:
            return
        self.selected_id = book["book_id"]
        self.form.set(book)
        self.mode_var.set(f"도서 수정 (ID {book['book_id']})")
        self.update_btn.state(["!disabled"])
        self.delete_btn.state(["!disabled"])

    def _clear_form(self) -> None:
        """폼을 비우고 신규 등록 모드로 전환한다."""
        self.selected_id = None
        self.table.clear_selection()
        self.form.clear()
        self.form.set({"quantity": 1})
        self.mode_var.set("신규 도서 등록")
        self.update_btn.state(["disabled"])
        self.delete_btn.state(["disabled"])
        self.form.focus_first()

    # ─────────────────────────────────
    # 1-4. 등록 / 수정 / 삭제
    # ─────────────────────────────────
    @guarded
    def _create(self) -> None:
        """입력한 정보로 도서를 등록하고, 등록된 도서를 선택 상태로 둔다."""
        book_id = book_service.create_book(self.form.get())
        self.selected_id = book_id
        self.refresh()
        self.set_status(f"도서가 등록되었습니다. (ID {book_id})")

    @guarded
    def _update(self) -> None:
        """선택한 도서 정보를 수정한다."""
        if self.selected_id is None:
            return
        book_service.update_book(self.selected_id, self.form.get())
        self.refresh()
        self.set_status(f"도서 정보가 수정되었습니다. (ID {self.selected_id})")

    @guarded
    def _delete(self) -> None:
        """확인 대화상자를 띄운 뒤 선택한 도서를 삭제한다."""
        book = self.table.selected()
        if book is None:
            return
        if not messagebox.askyesno(
            "도서 삭제",
            f"'{book['title']}' 을(를) 삭제하시겠습니까?\n해당 도서의 대출 이력도 함께 삭제됩니다.",
            parent=self.winfo_toplevel(),
        ):
            return
        book_service.delete_book(book["book_id"])
        self._clear_form()
        self.refresh()
        self.set_status(f"도서가 삭제되었습니다. ({book['title']})")
