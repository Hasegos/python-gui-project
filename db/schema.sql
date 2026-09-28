-- 도서 대출 관리 시스템 스키마 (PostgreSQL)
-- 여러 번 실행해도 안전하도록 IF NOT EXISTS 사용

-- ─────────────────────────────────────
-- 1. 도서
-- ─────────────────────────────────────
-- quantity 는 보유 권수, 대출 가능 권수는 loan 테이블에서 계산한다.
CREATE TABLE IF NOT EXISTS book (
    book_id        SERIAL       PRIMARY KEY,
    isbn           VARCHAR(20)  UNIQUE,
    title          VARCHAR(200) NOT NULL,
    author         VARCHAR(100) NOT NULL,
    publisher      VARCHAR(100),
    published_year INTEGER      CHECK (published_year BETWEEN 1000 AND 9999),
    category       VARCHAR(50),
    quantity       INTEGER      NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────
-- 2. 대출자
-- ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS member (
    member_id  SERIAL       PRIMARY KEY,
    student_no VARCHAR(20)  NOT NULL UNIQUE,
    name       VARCHAR(50)  NOT NULL,
    department VARCHAR(100),
    phone      VARCHAR(20),
    email      VARCHAR(100),
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────
-- 3. 대출 기록
-- ─────────────────────────────────────
-- return_date 가 NULL 이면 대출중, due_date 경과 시 연체
CREATE TABLE IF NOT EXISTS loan (
    loan_id     SERIAL  PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES book (book_id) ON DELETE CASCADE,
    member_id   INTEGER NOT NULL REFERENCES member (member_id) ON DELETE CASCADE,
    loan_date   DATE    NOT NULL DEFAULT CURRENT_DATE,
    due_date    DATE    NOT NULL,
    return_date DATE,
    CONSTRAINT chk_loan_due CHECK (due_date >= loan_date),
    CONSTRAINT chk_loan_return CHECK (return_date IS NULL OR return_date >= loan_date)
);

-- ─────────────────────────────────────
-- 4. 인덱스
-- ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_loan_book_id ON loan (book_id);
CREATE INDEX IF NOT EXISTS idx_loan_member_id ON loan (member_id);
-- 미반납 대출 조회(대출중/연체 필터) 최적화용 부분 인덱스
CREATE INDEX IF NOT EXISTS idx_loan_not_returned ON loan (due_date) WHERE return_date IS NULL;
