# Vị trí kiểm thử để nhóm tự viết

Các lớp test hiện `@unittest.skip` và các hàm chỉ có `NotImplementedError`, giống scaffold Bloxorz đã cung cấp. Chưa có bài test nghiệp vụ nào hoàn thành; chạy được test discovery không chứng minh game đúng. Owner viết test thật rồi bỏ skip.

| File | Owner | Nội dung |
|---|---|---|
| test_dpll.py | 1 | SAT/UNSAT, model đủ, assumptions không mutate, branching/backtrack, timeout |
| test_encoder.py | 2 | Sáu core; equisatisfiable với evaluator; biên k/aux |
| test_agent.py | 2 | Consistency, forced/unknown, deterministic, complete-clue uniqueness |
| test_engine.py | 3 | Public/private, initial reveal, reject unchanged, revision và restart |
| test_semantics.py | 3 | Truth table độc lập của sáu core và bốn region |
| test_extensions.py | 2 + 3 | Khung chung cho ít nhất hai extensions sau khi Nhân chọn; chưa mặc định tên/biên cụ thể |
| test_puzzles.py | 3 | Loader lỗi, truth, uniqueness vs progressive solvability |
| test_integration.py | 1 + 2/3 | End-to-end, no hidden data, trace, metrics, stale workers |
| test_gui.py | 4 | View callback, không lộ secret, render/resize và terminal states |

Chỉ dùng mock/stub trong test để phát triển song song. Không đưa mock verdict/solver vào sản phẩm rồi trình bày như thuật toán thật. Kiểm thử thủ công người 5 nằm ở `docs/QA.md`.
