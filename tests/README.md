# Kiểm thử

110/110 test chạy đạt, không skip trong lần kiểm tra ngày 28/11/2026. Có test module và luồng production, gồm cả encoder/agent của Nhân. Chạy `python -m unittest discover -s tests -v` từ repo; cần cài requirements để chạy test GUI.

| File | Owner | Nội dung |
|---|---|---|
| test_dpll.py | 1 | SAT/UNSAT, model đủ, assumptions không mutate, branching/backtrack, timeout |
| test_dpll_edges.py | 1 | 2.000 CNF không tautology đối chiếu vét cạn; metamorphic, pigeonhole và nhiều lời gọi độc lập |
| test_encoder.py | 2 | Sáu core; equisatisfiable với evaluator; biên k/aux |
| test_agent.py | 2 | Consistency, forced/unknown, deterministic, complete-clue uniqueness |
| test_engine.py | 3 | Public/private, initial reveal, reject unchanged, revision và restart |
| test_semantics.py | 3 | Truth table độc lập của sáu core và bốn region |
| test_extensions.py | 2 + 3 | PARITY; COUNT_COMPARE EQ/LT/GT, mọi cặp tập con board 2x2; demo/validation |
| test_puzzles.py | 3 | Loader lỗi, truth, uniqueness vs progressive solvability |
| test_integration.py | 1 + 2/3 | End-to-end, no hidden data, trace, metrics, stale workers |
| test_worker.py | 1 | Spawn/poll/cancel, timeout, lỗi agent, process chết, payload lớn |
| test_factory.py | 1 | Ghép đúng module thật, không truyền Puzzle cho agent hoặc dùng fake fallback |
| test_real_component_integration.py | 1 + các module đã ghép | Tự duyệt toàn bộ benchmark với backend production (22 puzzle trong lần kiểm tra); adapter sáu core chỉ xét các puzzle dùng sáu loại clue cơ bản; Auto Solve extensions qua worker thật; controller-session cache |
| test_gui.py | 4 | View callback, không lộ secret, render/resize và terminal states |

Chỉ dùng mock/stub trong test để phát triển song song. Không đưa mock verdict/solver vào sản phẩm rồi trình bày như thuật toán thật. Kiểm thử thủ công người 5 nằm ở `docs/QA.md`.

`member1_data.py` chỉ là fixture FACT nhỏ để kiểm tra DPLL và orchestration trước khi module người 2/3 hoàn thành. Nó không kiểm chứng encoder sáu core/extensions hoặc luật engine thật, và không được import từ production code.

`core_integration_data.py` bổ sung adapter sáu core chỉ trong test. Nó giúp dùng DPLL thật với engine thật/dataset đã ghép; không chứng minh CNFEncoder/LogicAgent production đã đúng và không được dùng làm backend dự phòng của game. Adapter báo lỗi khi nhận loại clue ngoài sáu core, tránh bỏ qua extensions một cách im lặng. Test production vẫn kiểm tra toàn bộ file benchmark, bao gồm extensions; không cố định số lượng file trong assertion.
