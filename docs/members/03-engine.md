# Người 3 — Engine, dataset, evaluator và benchmark

File chính: `core/`, `validation/`, `puzzles/`, `experiments/runner.py`, `run_experiments.py`, `tests/test_engine.py`, `tests/test_semantics.py`, `tests/test_puzzles.py`.

## Thứ tự tự triển khai

1. `all_cells`, resolver bốn vùng, referenced_cells; đây là phần người 2/4 dùng sớm. Trả thứ tự row-major, không trùng.
2. Loader schema v1: đủ N*N character/status/clue, IDs và initial cards không trùng, đúng kiểu/region/k. Không ép sai kiểu Boolean thành số đếm.
3. Làm evaluator trực tiếp cho sáu core trước. Nhân tự chọn extensions, sau khi thống nhất schema/ngữ nghĩa thì bổ sung evaluator và resolver phù hợp. Không mặc định bắt buộc PARITY/COUNT_COMPARE. Không import encoder hoặc solver; có thể dùng resolver vùng chung. Nếu chọn COUNT_COMPARE thì đếm trực tiếp hai phía, không tái sử dụng phép đổi encoding làm oracle.
4. Engine giữ private Puzzle, snapshot công khai bất biến. Initial/reveal công khai cả status và clue. Validate analysis revision trước submit.
5. Dựng nhiều puzzle 3x3/4x4 từ dễ đến khó, có clue/vùng đa dạng. Tách negative fixtures khỏi bộ chính.
6. Khi agent xong: validate truth, uniqueness complete clues và progressive solvability thành ba kiểm tra riêng.
7. Viết/chạy benchmark theo `docs/EXPERIMENTS.md`; gửi số liệu và nhận xét cho người 5.

## Làm song song

Engine có thể test bằng Analysis tự tạo đúng contract, không phải đợi GUI. Evaluator không cần DPLL. Dataset chuẩn bị từ đầu; chạy thực nghiệm thật sau khi pipeline hoạt động. Các class giả chỉ dùng trong test, không đưa vào gameplay để giả verdict.

## Tiêu chí xong

Neighbors góc/cạnh/giữa lần lượt 3/5/8 ở 3x3 trở lên; center không nằm trong neighbors. Clue luôn đúng bất kể chủ thẻ. Reject giữ nguyên state. PublicState không lộ hidden data kể cả qua nested mutable objects. Bộ chính unique và giải tuần tự được. Failure/timeout còn nguyên dòng CSV. Counters/runtime thật, cùng case set khi so sánh.

## Bàn giao

Người 2/4 nhận resolver và loader format. Người 1 nhận engine theo API. Người 5 nhận bảng/chart đã chọn, môi trường chạy, giải thích kết quả và giới hạn. **Không chuyển chạy benchmark cho người 5.**
