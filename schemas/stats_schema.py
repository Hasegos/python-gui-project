from dataclasses import dataclass


# ─────────────────────────────────────
# 1. 요약 지표 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class StatsSummary:
    """
    통계 화면 상단 요약 카드 지표.

    Args:
        book_titles : 보유 도서 종수
        book_copies : 보유 도서 권수
        members     : 등록 대출자 수
        total_loans : 누적 대출 건수
        not_returned: 미반납 건수
        overdue     : 연체중 건수
        late_returns: 연체 후 반납 건수
        returned    : 반납완료 건수
    """
    book_titles  : int
    book_copies  : int
    members      : int
    total_loans  : int
    not_returned : int
    overdue      : int
    late_returns : int
    returned     : int

    @property
    def overdue_rate(self) -> float:
        """연체 발생률(%) = (연체중 + 연체 후 반납) / 누적 대출."""
        if not self.total_loans:
            return 0.0
        return (self.overdue + self.late_returns) / self.total_loans * 100


# ─────────────────────────────────────
# 2. 월별 대출/반납 건수 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class MonthlyCount:
    """
    월별 대출/반납 건수.

    Args:
        month  : 'YYYY-MM'
        loans  : 대출 건수
        returns: 반납 건수
    """
    month   : str
    loans   : int
    returns : int


# ─────────────────────────────────────
# 3. 인기 도서 순위 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class TopBook:
    """
    인기 도서 순위 한 행.

    Args:
        rank      : 순위 (동점은 같은 순위)
        title     : 도서 제목
        author    : 저자
        loan_count: 누적 대출 건수
    """
    rank       : int
    title      : str
    author     : str
    loan_count : int


# ─────────────────────────────────────
# 4. 다독 대출자 순위 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class TopMember:
    """
    다독 대출자 순위 한 행.

    Args:
        rank      : 순위 (동점은 같은 순위)
        student_no: 학번
        name      : 이름
        department: 학과
        loan_count: 누적 대출 건수
    """
    rank       : int
    student_no : str
    name       : str
    department : str | None
    loan_count : int


# ─────────────────────────────────────
# 5. 분류별 통계 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class CategoryStat:
    """
    분류별 도서 종수와 누적 대출 건수.

    Args:
        category   : 분류 (없으면 '미분류')
        book_titles: 도서 종수
        loan_count : 누적 대출 건수
    """
    category    : str
    book_titles : int
    loan_count  : int


# ─────────────────────────────────────
# 6. 통계 화면 전체 응답 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class StatsDashboard:
    """
    통계 화면에 필요한 집계 결과 묶음.

    Args:
        summary    : 요약 지표
        monthly    : 월별 대출/반납 건수 리스트
        top_books  : 인기 도서 순위 리스트
        top_members: 다독 대출자 순위 리스트
        categories : 분류별 통계 리스트
    """
    summary     : StatsSummary
    monthly     : list[MonthlyCount]
    top_books   : list[TopBook]
    top_members : list[TopMember]
    categories  : list[CategoryStat]
