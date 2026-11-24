# Người 2 (Nhân) — CNF encoder, tự chọn extensions và Logic Agent

File chính: `logic/encoder.py`, `logic/agent.py`, `tests/test_encoder.py`, `tests/test_agent.py`. Không phụ trách semantic evaluator.

## Làm ngay, chưa cần DPLL thật

1. Tạo PublicState nhỏ bằng các dataclass chung. Mapping row-major primary 1..N*N, auxiliary tách riêng.
2. Validate rồi encode FACT, SAME, DIFFERENT; tiếp đến EXACTLY, AT_LEAST, AT_MOST. Không hardcode CNF theo puzzle.
3. Tự tìm hiểu và chọn ít nhất hai extensions khác nhau trong phạm vi đề. `docs/EXTENSIONS.md` chỉ đề xuất PARITY và COUNT_COMPARE; có thể chọn hướng khác. Trước khi code, ghi rõ tên, ngữ nghĩa, schema và các biên; thống nhất với người 1/3 rồi báo người 4. Sau đó tự triển khai encoding và viết ví dụ CNF.
4. Khi evaluator người 3 có, so encoder với nó trên mọi primary assignment ở vùng nhỏ. Nếu có aux, kiểm tra **tồn tại assignment aux** tương ứng, không gán aux tùy ý rồi kết luận lỗi.
5. Viết agent với solver giả trong test để kiểm tra thứ tự consistency query và hai assumptions đối nghịch; sau đó đổi sang DPLL người 1.
6. Implement uniqueness offline: all clues, không solution units, block chỉ primary model.

## Chỗ phải đúng

- Agent không nhận GameEngine/Puzzle/path; không gọi loader.
- Base KB UNSAT ⇒ inconsistent, không verdict. Hai giả thiết đều SAT ⇒ UNKNOWN, không guess.
- Analyze phân loại mọi unresolved; next_forced chọn row-major ổn định.
- Budget timeout cho toàn bộ analysis; ghi từng query đã chạy cùng stats.
- Các extensions thực sự chọn phải có evaluator độc lập, test biên và ví dụ tạo forced move. Nếu chọn COUNT_COMPARE, cần xử lý ô giao dùng cùng biến và kiểm tra bằng hai tổng trực tiếp; đây là lưu ý cho đề xuất đó, không bắt buộc phải chọn nó.
- Đầy đủ clue có UNIQUE không chứng minh public KB đang UNIQUE hoặc progressive solve được.

## Bàn giao

Cho người 1: encoder/agent theo ports, bộ test SAT/UNSAT/UNKNOWN/INCONSISTENT và uniqueness. Cho người 3: chi tiết extensions để evaluator/dataset thống nhất. Cho người 4: mapping, clause counts, query data để inspector hiển thị. Cho người 5: dẫn giải một binary clue, một counting clue, entailment và uniqueness; không yêu cầu người 5 tự viết công thức.
