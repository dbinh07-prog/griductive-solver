# Người 1 — DPLL, kiến trúc và tích hợp

**Người 1 phụ trách DPLL, không tổng hợp report.** Logic Agent thuộc người 2; lỗi của từng module do người sở hữu module đó sửa.

## Phần đã triển khai

- `DPLLSolver`: validation, unit propagation, conflict, nhánh xác định, backtrack, assumptions tạm, complete model, timeout và counters.
- `GameSession`: phân tích public state, cache, Hint/Step/Submit, chống reveal không được chứng minh, trace JSON/CSV, metrics và restart.
- `AnalysisJob`: process nền spawn, poll/cancel, deadline và truyền lỗi; session có wrapper quản lý job và loại kết quả cũ.
- `create_session`: ghép loader/engine/encoder/DPLL/agent thật, không có fallback sang fixture.
- Test DPLL đối chiếu vét cạn trên CNF nhỏ; test session/worker/factory với fixture có ghi rõ phạm vi. Game hoàn chỉnh vẫn chờ các module của thành viên khác.

## File chính

`algorithms/dpll.py`, `game/session.py`, `game/worker.py`, `game/factory.py`, `contracts/`, `docs/API.md`, `tests/test_dpll.py`, `tests/test_integration.py`.

Kiểm thử bổ sung ở `tests/test_worker.py`, `tests/test_factory.py`; `tests/member1_data.py` chỉ phục vụ test. Người 4 xem mục session/worker trong API để dùng `start_analysis`, `poll_analysis`, `cancel_analysis`.

## Thứ tự tự triển khai

1. Xem models/ports; chốt API với người 2–4. DPLL chỉ nhận CNF, không phụ thuộc game/GUI.
2. Unit propagation → phát hiện conflict → chọn biến xác định → đệ quy branch/backtrack → model đầy đủ → stats và deadline.
3. Test CNF nhỏ tự tạo: true formula, empty clause, units mâu thuẫn, SAT nhiều nghiệm, nhánh đầu thất bại, assumptions. Chưa cần đợi dataset.
4. Ghép một encoder/agent với một engine ở session. Hint không reveal; submit chỉ accepted khi analysis đúng revision.
5. Cache analysis theo revision; ghi query thực tế, trace accepted reveals; reset thống kê đúng khi restart.
6. Worker nền chỉ nhận public snapshot; xử lý cancel/load/restart/stale result và lỗi khác timeout.
7. Cùng người 4 ghép một puzzle 3x3 xuyên suốt, rồi mới mở rộng.

## Bàn giao

- Cho người 2: DPLL đúng `solve(CNF, assumptions, timeout_s)` và nghĩa của counters.
- Cho người 4: session/worker/factory đúng API; không bắt GUI biết secret hoặc thuật toán.
- Cho người 3: metrics đúng nghĩa và cấu hình solver dùng cho benchmark.
- Cho người 5: đoạn mô tả DPLL, kiến trúc public/private, pseudo-code và kết quả test; **chỉ phần mình làm**.

## Tiêu chí xong

SAT model thỏa CNF + assumptions và đủ biến; UNSAT không nhầm timeout. Giữ input nguyên vẹn giữa các solve. Ca backtrack thật chạy đúng. Rejected verdict không đổi state. Không có dependency từ solver/agent sang private puzzle. Worker cũ không sửa state mới. Test xong thì bỏ skip ở file của mình.
