import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from core.constants.ui import (
    BASE_FONT_SIZE,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_OFF,
    TABLE_ROW_HEIGHT,
    TITLE_FONT_SIZE,
    WINDOWS_FONT_FAMILY,
)


# ─────────────────────────────────────
# 1. 화면(templates) 공통 스타일 설정
# ─────────────────────────────────────
def apply_style(root: tk.Tk) -> None:
    """
    templates 의 모든 화면에 적용할 ttk 테마, 폰트, 버튼/표 스타일을 설정한다.

    Args:
        root: 최상위 Tk 윈도우
    """
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    # ─────────────────────────────────
    # 1-1. 폰트
    # ─────────────────────────────────
    # Windows 기본 폰트는 한글 가독성이 떨어져 맑은 고딕으로 교체
    family = {"family": WINDOWS_FONT_FAMILY} if sys.platform == "win32" else {}
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(size=BASE_FONT_SIZE, **family)
    tkfont.nametofont("TkHeadingFont").configure(weight="bold")

    title_font = tkfont.nametofont("TkDefaultFont").copy()
    title_font.configure(size=TITLE_FONT_SIZE, weight="bold")
    root.title_font = title_font  # 참조 유지 (GC 로 폰트가 사라지는 것 방지)

    # ─────────────────────────────────
    # 1-2. 위젯 스타일
    # ─────────────────────────────────
    style.configure("Treeview", rowheight=TABLE_ROW_HEIGHT)
    style.configure("Title.TLabel", font=title_font)
    style.configure("Accent.TButton", foreground="#ffffff", background=COLOR_PRIMARY)
    style.map("Accent.TButton", background=[("active", COLOR_PRIMARY_HOVER), ("disabled", COLOR_PRIMARY_OFF)])
