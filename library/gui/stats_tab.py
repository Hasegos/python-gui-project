import tkinter as tk
from tkinter import ttk

from library.gui.widgets import DataTable, guarded
from library.service import stats_service

LOAN_COLOR    = "#2f6fdf"
RETURN_COLOR  = "#27ae60"
OVERDUE_COLOR = "#c0392b"

# 표 컬럼: (key, 헤더명, 너비, 정렬)
TOP_BOOK_COLUMNS = [
    ("rank", "순위", 45, "center"),
    ("title", "도서명", 170, "w"),
    ("author", "저자", 110, "w"),
    ("loan_count", "대출", 50, "center"),
]

TOP_MEMBER_COLUMNS = [
    ("rank", "순위", 45, "center"),
    ("student_no", "학번", 85, "center"),
    ("name", "이름", 70, "center"),
    ("department", "학과", 120, "w"),
    ("loan_count", "대출", 50, "center"),
]

CATEGORY_COLUMNS = [
    ("category", "분류", 120, "w"),
    ("book_titles", "도서(종)", 70, "center"),
    ("loan_count", "누적 대출", 70, "center"),
]


# ─────────────────────────────────────
# 1. 요약 카드
# ─────────────────────────────────────
class StatCard(ttk.Frame):
    """
    제목과 큰 숫자를 보여주는 요약 카드.

    Args:
        master: 부모 위젯
        title : 카드 제목
        color : 숫자 글자색. 없으면 기본색.
    """

    def __init__(self, master, title: str, color: str | None = None):
        super().__init__(master, padding=(14, 8), relief="groove", borderwidth=1)
        ttk.Label(self, text=title, foreground="#666").pack(anchor="w")
        self.value = ttk.Label(self, text="-", style="Title.TLabel", foreground=color or "#222")
        self.value.pack(anchor="w")

    def set(self, value) -> None:
        """카드에 표시할 값을 변경한다."""
        self.value.configure(text=str(value))


# ─────────────────────────────────────
# 2. 월별 대출/반납 막대 차트
# ─────────────────────────────────────
class BarChart(tk.Canvas):
    """
    월별 대출/반납 건수를 그리는 묶음 막대 차트.

    외부 라이브러리 없이 Canvas 에 직접 그리며, 크기가 바뀌면 다시 그린다.
    """

    # 축 라벨/범례가 들어갈 여백
    PADDING = {"left": 40, "right": 16, "top": 30, "bottom": 30}

    def __init__(self, master, **kwargs):
        super().__init__(master, background="#ffffff", highlightthickness=0, height=240, **kwargs)
        self.data: list[dict] = []
        self.bind("<Configure>", lambda _e: self.draw())

    def set_data(self, data: list[dict]) -> None:
        """
        차트 데이터를 교체하고 다시 그린다.

        Args:
            data: {month, loans, returns} dict 리스트
        """
        self.data = data
        self.draw()

    def draw(self) -> None:
        """눈금선, 막대, 월 라벨, 범례 순서로 차트를 그린다."""
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if not self.data or width < 50:
            return
        p = self.PADDING
        plot_w = width - p["left"] - p["right"]
        plot_h = height - p["top"] - p["bottom"]
        max_value = max(max(d["loans"], d["returns"]) for d in self.data)
        # 눈금이 정수로 떨어지도록 최대값을 4의 배수로 올림
        axis_max = max(4, -(-max_value // 4) * 4)

        # ─────────────────────────────
        # 2-1. 가로 눈금선 + 값 라벨
        # ─────────────────────────────
        for i in range(5):
            value = axis_max * i // 4
            y = p["top"] + plot_h - plot_h * value / axis_max
            self.create_line(p["left"], y, width - p["right"], y, fill="#eeeeee")
            self.create_text(p["left"] - 6, y, text=str(value), anchor="e", fill="#888")

        # ─────────────────────────────
        # 2-2. 월별 대출/반납 막대
        # ─────────────────────────────
        group_w = plot_w / len(self.data)
        bar_w = min(26, group_w / 3)
        for index, row in enumerate(self.data):
            center = p["left"] + group_w * index + group_w / 2
            for offset, key, color in ((-bar_w / 2, "loans", LOAN_COLOR), (bar_w / 2, "returns", RETURN_COLOR)):
                value = row[key]
                x0, x1 = center + offset - bar_w / 2, center + offset + bar_w / 2
                y0 = p["top"] + plot_h - plot_h * value / axis_max
                self.create_rectangle(x0, y0, x1, p["top"] + plot_h, fill=color, outline="")
                if value:
                    self.create_text((x0 + x1) / 2, y0 - 8, text=str(value), fill="#444")
            self.create_text(center, height - p["bottom"] + 14, text=row["month"], fill="#444")

        # ─────────────────────────────
        # 2-3. 범례
        # ─────────────────────────────
        x = width - p["right"] - 130
        for label, color in (("대출", LOAN_COLOR), ("반납", RETURN_COLOR)):
            self.create_rectangle(x, 10, x + 12, 22, fill=color, outline="")
            self.create_text(x + 16, 16, text=label, anchor="w", fill="#444")
            x += 60


# ─────────────────────────────────────
# 3. 통계 화면
# ─────────────────────────────────────
class StatsTab(ttk.Frame):
    """
    도서/대출 이력 통계 화면.

    요약 카드, 최근 6개월 대출/반납 추이, 분류별 통계, 인기 도서·다독 대출자 TOP 5 로 구성한다.

    Args:
        master    : 부모 위젯 (Notebook)
        set_status: 하단 상태 표시줄에 메시지를 표시하는 함수
    """

    def __init__(self, master, set_status):
        super().__init__(master, padding=12)
        self.set_status = set_status

        self._build_cards()
        self._build_body()

    # ─────────────────────────────────
    # 3-1. 화면 구성
    # ─────────────────────────────────
    def _build_cards(self) -> None:
        """상단 새로고침 버튼과 요약 카드 7종을 구성한다."""
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Button(header, text="새로고침", command=self.refresh).pack(side="right")

        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(0, 10))
        # summary 집계 키와 같은 이름으로 카드를 만들어 값을 바로 채운다.
        self.cards = {
            "book_titles": StatCard(cards, "보유 도서 (종)"),
            "book_copies": StatCard(cards, "보유 도서 (권)"),
            "members": StatCard(cards, "등록 대출자"),
            "total_loans": StatCard(cards, "누적 대출", LOAN_COLOR),
            "not_returned": StatCard(cards, "미반납", LOAN_COLOR),
            "overdue": StatCard(cards, "연체중", OVERDUE_COLOR),
            "overdue_rate": StatCard(cards, "연체 발생률", OVERDUE_COLOR),
        }
        for index, card in enumerate(self.cards.values()):
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0))
            cards.columnconfigure(index, weight=1)

        ttk.Label(
            header,
            text="연체 발생률 = (연체중 + 연체 후 반납) / 누적 대출",
            foreground="#777",
        ).pack(side="left")

    def _build_body(self) -> None:
        """차트, 분류별 통계, 인기 도서, 다독 대출자 영역을 2x2 로 배치한다."""
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        chart_box = ttk.LabelFrame(body, text="최근 6개월 대출 / 반납 추이", padding=8)
        chart_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.chart = BarChart(chart_box)
        self.chart.pack(fill="both", expand=True)

        category_box = ttk.LabelFrame(body, text="분류별 통계", padding=8)
        category_box.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        self.category_table = DataTable(category_box, CATEGORY_COLUMNS, height=8)
        self.category_table.pack(fill="both", expand=True)

        book_box = ttk.LabelFrame(body, text="인기 도서 TOP 5", padding=8)
        book_box.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.book_table = DataTable(book_box, TOP_BOOK_COLUMNS, height=5)
        self.book_table.pack(fill="both", expand=True)

        member_box = ttk.LabelFrame(body, text="다독 대출자 TOP 5", padding=8)
        member_box.grid(row=1, column=1, sticky="nsew")
        self.member_table = DataTable(member_box, TOP_MEMBER_COLUMNS, height=5)
        self.member_table.pack(fill="both", expand=True)

    # ─────────────────────────────────
    # 3-2. 통계 조회
    # ─────────────────────────────────
    @guarded
    def refresh(self) -> None:
        """통계를 다시 집계하여 카드, 차트, 표를 갱신한다."""
        data = stats_service.get_dashboard()
        summary = data["summary"]
        for key, card in self.cards.items():
            if key in summary:
                card.set(summary[key])
        total = summary["total_loans"]
        overdue_rate = (summary["overdue"] + summary["late_returns"]) / total * 100 if total else 0
        self.cards["overdue_rate"].set(f"{overdue_rate:.1f}%")

        self.chart.set_data(data["monthly"])
        self.category_table.set_rows(data["categories"], "category")
        # 동순위가 있을 수 있어 행 식별자는 순번으로 부여
        self.book_table.set_rows([{**r, "row": i} for i, r in enumerate(data["top_books"])], "row")
        self.member_table.set_rows([{**r, "row": i} for i, r in enumerate(data["top_members"])], "row")
        self.set_status("통계를 갱신했습니다.")
