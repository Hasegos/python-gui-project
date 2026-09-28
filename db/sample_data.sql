-- 개발/시연용 샘플 데이터 (python init_db.py --sample)
-- 이미 데이터가 있으면 중복 삽입하지 않는다.

-- ─────────────────────────────────────
-- 1. 도서
-- ─────────────────────────────────────
INSERT INTO book (isbn, title, author, publisher, published_year, category, quantity) VALUES
    ('9788966262281', '이펙티브 자바', '조슈아 블로크', '인사이트', 2018, '프로그래밍', 2),
    ('9788968481475', '파이썬 코딩의 기술', '브렛 슬라킨', '길벗', 2020, '프로그래밍', 2),
    ('9791162242278', '데이터베이스 개론', '김연희', '한빛아카데미', 2019, '데이터베이스', 3),
    ('9788966263158', '클린 코드', '로버트 C. 마틴', '인사이트', 2013, '소프트웨어공학', 1),
    ('9791158391881', '운영체제', '구현회', '한빛아카데미', 2020, '컴퓨터구조', 2),
    ('9788960777330', '컴퓨터 네트워킹', '제임스 F. 쿠로즈', '퍼스트북', 2021, '네트워크', 1),
    ('9791162241646', '혼자 공부하는 파이썬', '윤인성', '한빛미디어', 2019, '프로그래밍', 3),
    ('9788965402602', '알고리즘 문제 해결 전략', '구종만', '인사이트', 2012, '알고리즘', 1)
ON CONFLICT (isbn) DO NOTHING;

-- ─────────────────────────────────────
-- 2. 대출자
-- ─────────────────────────────────────
INSERT INTO member (student_no, name, department, phone, email) VALUES
    ('20210001', '김민준', '컴퓨터공학과', '010-1234-5678', 'minjun@example.com'),
    ('20210002', '이서연', '컴퓨터공학과', '010-2345-6789', 'seoyeon@example.com'),
    ('20220003', '박지훈', '소프트웨어학과', '010-3456-7890', 'jihoon@example.com'),
    ('20220004', '최수아', '정보통신공학과', '010-4567-8901', 'sua@example.com'),
    ('20230005', '정도윤', '소프트웨어학과', '010-5678-9012', 'doyoon@example.com')
ON CONFLICT (student_no) DO NOTHING;

-- ─────────────────────────────────────
-- 3. 대출 이력
-- ─────────────────────────────────────
-- 반납완료 / 대출중 / 연체 상태가 모두 보이도록 구성
INSERT INTO loan (book_id, member_id, loan_date, due_date, return_date)
SELECT b.book_id, m.member_id, v.loan_date, v.due_date, v.return_date
FROM (VALUES
    ('9788966262281', '20210001', CURRENT_DATE - 120, CURRENT_DATE - 106, CURRENT_DATE - 110),
    ('9788968481475', '20210002', CURRENT_DATE - 95,  CURRENT_DATE - 81,  CURRENT_DATE - 85),
    ('9791162242278', '20220003', CURRENT_DATE - 70,  CURRENT_DATE - 56,  CURRENT_DATE - 60),
    ('9788966262281', '20220004', CURRENT_DATE - 45,  CURRENT_DATE - 31,  CURRENT_DATE - 33),
    ('9791162241646', '20210001', CURRENT_DATE - 40,  CURRENT_DATE - 26,  CURRENT_DATE - 30),
    ('9788966263158', '20230005', CURRENT_DATE - 20,  CURRENT_DATE - 6,   NULL),
    ('9791162242278', '20210002', CURRENT_DATE - 10,  CURRENT_DATE + 4,   NULL),
    ('9788968481475', '20220003', CURRENT_DATE - 3,   CURRENT_DATE + 11,  NULL)
) AS v (isbn, student_no, loan_date, due_date, return_date)
JOIN book b ON b.isbn = v.isbn
JOIN member m ON m.student_no = v.student_no
WHERE NOT EXISTS (SELECT 1 FROM loan);
