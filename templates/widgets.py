import functools
import tkinter as tk
from dataclasses import asdict, is_dataclass
from tkinter import messagebox, ttk

import psycopg2

from core.exceptions import LibraryError


# ─────────────────────────────────────
# 0. 행 데이터 → dict 변환
# ─────────────────────────────────────
def to_dict(row) -> dict:
    """
    model/schema(dataclass) 또는 dict 를 dict 로 변환한다.

    Args:
        row: dataclass 인스턴스 또는 dict
    Returns:
        dict
    """
    if is_dataclass(row):
        return asdict(row)
    return dict(row)


# ─────────────────────────────────────
# 1. 이벤트 핸들러 예외 안내
# ─────────────────────────────────────
def guarded(method):
    """
    화면 이벤트 핸들러에서 발생한 예외를 메시지 박스로 안내하는 데코레이터.

    - LibraryError  : 업무 규칙 위반 → 경고
    - psycopg2.Error: DB 오류 → 에러

    Args:
        method: 위젯 클래스의 메서드
    Returns:
        예외를 처리하도록 감싼 메서드
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        parent = self.winfo_toplevel()
        try:
            return method(self, *args, **kwargs)
        except LibraryError as e:
            messagebox.showwarning("알림", str(e), parent=parent)
        except psycopg2.Error as e:
            detail = (e.pgerror or str(e)).strip()
            messagebox.showerror("데이터베이스 오류", f"DB 처리 중 오류가 발생했습니다.\n\n{detail}", parent=parent)
        return None

    return wrapper


# ─────────────────────────────────────
# 2. 데이터 표 (Treeview)
# ─────────────────────────────────────
class DataTable(ttk.Frame):
    """
    Treeview + 스크롤바 조합 위젯.

    행 데이터(model/schema 객체)를 그대로 보관해 선택한 행을 꺼낼 수 있고, 헤더 클릭 정렬을 지원한다.

    Args:
        master : 부모 위젯
        columns: [(key, 헤더명, 너비, 정렬)] 리스트. 정렬은 "w" | "center" | "e"
        height : 표시할 행 수
    """

    def __init__(self, master, columns, height: int = 15):
        super().__init__(master)
        self.columns = columns
        self._rows: dict[str, object] = {}
        self._sort_desc: dict[str, bool] = {}

        keys = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=keys, show="headings", height=height, selectmode="browse")
        for key, heading, width, anchor in columns:
            self.tree.heading(key, text=heading, command=lambda k=key: self._sort_by(k))
            # 왼쪽 정렬(텍스트) 컬럼만 창 크기에 맞춰 늘어나도록 설정
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=anchor == "w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    # ─────────────────────────────────
    # 2-1. 데이터 설정 / 선택
    # ─────────────────────────────────
    def set_rows(self, rows: list, id_key: str, tag_func=None) -> None:
        """
        표의 모든 행을 새 데이터로 교체한다.

        Args:
            rows    : model/schema 객체 또는 dict 리스트
            id_key  : 행 식별자로 사용할 키 (Treeview iid)
            tag_func: 행을 받아 태그명(색상 구분용)을 반환하는 함수. 없으면 None.
        """
        self.tree.delete(*self.tree.get_children())
        self._rows.clear()
        for row in rows:
            iid = str(self._value(row, id_key))
            tag = tag_func(row) if tag_func else None
            tags = (tag,) if tag else ()
            values = [self._format(self._value(row, key)) for key, *_ in self.columns]
            self.tree.insert("", "end", iid=iid, values=values, tags=tags)
            self._rows[iid] = row

    def selected(self):
        """선택된 행 객체를 반환한다. 선택이 없으면 None."""
        selection = self.tree.selection()
        return self._rows.get(selection[0]) if selection else None

    def select(self, row_id) -> None:
        """row_id 에 해당하는 행을 선택하고 보이도록 스크롤한다."""
        iid = str(row_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def clear_selection(self) -> None:
        """선택을 해제한다."""
        self.tree.selection_remove(*self.tree.selection())

    # ─────────────────────────────────
    # 2-2. 이벤트 / 스타일
    # ─────────────────────────────────
    def on_select(self, callback) -> None:
        """행 선택 시 callback(선택 행) 을 호출한다."""
        self.tree.bind("<<TreeviewSelect>>", lambda _e: callback(self.selected()))

    def on_double_click(self, callback) -> None:
        """행 더블클릭 시 callback(선택 행) 을 호출한다."""
        self.tree.bind("<Double-1>", lambda _e: self.selected() and callback(self.selected()))

    def tag_configure(self, tag: str, **options) -> None:
        """태그별 글자색 등 표시 옵션을 설정한다."""
        self.tree.tag_configure(tag, **options)

    def __len__(self) -> int:
        return len(self._rows)

    # ─────────────────────────────────
    # 2-3. 헤더 클릭 정렬
    # ─────────────────────────────────
    def _sort_by(self, key: str) -> None:
        """
        key 컬럼 기준으로 행을 정렬한다. 같은 헤더를 다시 누르면 순서가 뒤집힌다.

        Args:
            key: 정렬할 컬럼 키
        """
        desc = not self._sort_desc.get(key, True)
        self._sort_desc[key] = desc

        def sort_key(iid):
            value = self._value(self._rows[iid], key)
            # None 은 항상 뒤로, 숫자/문자 혼합을 피하기 위해 타입별로 비교
            return (value is None, value if isinstance(value, (int, float)) else str(value or ""))

        for index, iid in enumerate(sorted(self._rows, key=sort_key, reverse=desc)):
            self.tree.move(iid, "", index)

    @staticmethod
    def _value(row, key: str):
        """dict 는 키로, model/schema 객체는 속성으로 값을 꺼낸다."""
        if isinstance(row, dict):
            return row.get(key)
        return getattr(row, key, None)

    @staticmethod
    def _format(value) -> str:
        """None 은 빈 문자열로 표시한다."""
        return "" if value is None else str(value)


# ─────────────────────────────────────
# 3. 입력 폼
# ─────────────────────────────────────
class FormFields(ttk.Frame):
    """
    라벨 + 입력 위젯을 세로로 배치하는 입력 폼.

    Args:
        master : 부모 위젯
        fields : [(key, 라벨)] 리스트
        choices: {key: 선택지 리스트}. 지정된 key 는 Combobox 로 생성한다.
        width  : 입력 위젯 너비
    """

    def __init__(self, master, fields, choices: dict | None = None, width: int = 22):
        super().__init__(master)
        choices = choices or {}
        self.vars: dict[str, tk.StringVar] = {}
        self.widgets: dict[str, ttk.Widget] = {}
        for row, (key, label) in enumerate(fields):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            var = tk.StringVar()
            if key in choices:
                widget = ttk.Combobox(self, textvariable=var, values=choices[key], width=width - 2)
            else:
                widget = ttk.Entry(self, textvariable=var, width=width)
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.vars[key] = var
            self.widgets[key] = widget
        self.columnconfigure(1, weight=1)

    def get(self) -> dict:
        """입력값을 {key: 문자열} dict 로 반환한다."""
        return {key: var.get() for key, var in self.vars.items()}

    def set(self, data) -> None:
        """
        data 의 값으로 입력란을 채운다. 없는 key 는 빈 값으로 둔다.

        Args:
            data: model 객체 또는 dict
        """
        values = to_dict(data)
        for key, var in self.vars.items():
            value = values.get(key)
            var.set("" if value is None else str(value))

    def clear(self) -> None:
        """모든 입력란을 비운다."""
        for var in self.vars.values():
            var.set("")

    def set_choices(self, key: str, values) -> None:
        """Combobox 입력란의 선택지를 갱신한다."""
        self.widgets[key].configure(values=list(values))

    def focus_first(self) -> None:
        """첫 번째 입력란에 포커스를 둔다."""
        next(iter(self.widgets.values())).focus_set()


# ─────────────────────────────────────
# 4. 검색 가능한 Combobox
# ─────────────────────────────────────
class SearchableCombobox(ttk.Combobox):
    """
    입력한 글자로 선택 목록을 필터링하는 Combobox.

    set_options({표시 문자열: 값}) 으로 선택지를 설정하고, value() 로 선택된 값을 얻는다.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # 주의: ttk 내부 메서드(_options)와 이름이 겹치지 않도록 _choices 사용
        self._choices: dict[str, object] = {}
        self.bind("<KeyRelease>", self._on_key)

    def set_options(self, options: dict) -> None:
        """
        선택지를 교체한다. 현재 입력값이 새 선택지에 없으면 비운다.

        Args:
            options: {표시 문자열: 값} dict
        """
        self._choices = dict(options)
        self.configure(values=list(self._choices))
        if self.get() not in self._choices:
            self.set("")

    def value(self):
        """선택된 항목의 값을 반환한다. 목록에 없는 문자열이면 None."""
        return self._choices.get(self.get())

    def _on_key(self, event) -> None:
        """키 입력마다 입력 글자를 포함하는 항목만 남긴다. (방향키 등 이동 키는 제외)"""
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        keyword = self.get().strip().lower()
        matches = [label for label in self._choices if keyword in label.lower()]
        self.configure(values=matches)


# ─────────────────────────────────────
# 5. 검색 바
# ─────────────────────────────────────
class SearchBar(ttk.Frame):
    """
    검색 기준 Combobox + 검색어 입력 + 검색/전체보기 버튼 + 건수 표시 묶음.

    Args:
        master   : 부모 위젯
        fields   : {화면 표시명: 검색 기준 키} dict
        on_search: 검색 실행 시 호출할 함수
    """

    def __init__(self, master, fields: dict, on_search):
        super().__init__(master)
        self.fields = fields
        self.on_search = on_search

        self.field_var = tk.StringVar(value=next(iter(fields)))
        ttk.Combobox(
            self, textvariable=self.field_var, values=list(fields), state="readonly", width=8,
        ).pack(side="left")
        self.keyword_var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.keyword_var, width=30)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda _e: on_search())
        ttk.Button(self, text="검색", command=on_search).pack(side="left")
        ttk.Button(self, text="전체보기", command=self.reset).pack(side="left", padx=(6, 0))
        self.count_var = tk.StringVar()
        ttk.Label(self, textvariable=self.count_var).pack(side="right")

    @property
    def field(self) -> str:
        """선택된 검색 기준 키."""
        return self.fields[self.field_var.get()]

    @property
    def keyword(self) -> str:
        """입력된 검색어."""
        return self.keyword_var.get()

    def set_count(self, text: str) -> None:
        """우측 건수 표시 문구를 변경한다."""
        self.count_var.set(text)

    def reset(self) -> None:
        """검색 조건을 초기화하고 다시 검색한다."""
        self.field_var.set(next(iter(self.fields)))
        self.keyword_var.set("")
        self.on_search()
