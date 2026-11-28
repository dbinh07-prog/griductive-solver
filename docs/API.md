# API chung v1

Đây là hợp đồng dùng chung. Phần người 1 (DPLL, session, worker và factory) đã triển khai; phần người 2–4 vẫn theo phân công. Người 1 quản lý thay đổi API; không yêu cầu tên hàm giống repo tham khảo nếu contract này đã rõ và thống nhất.

## Kiểu dữ liệu và quy ước

Nguồn chuẩn: `contracts/models.py`; interface tối thiểu: `contracts/ports.py`.

- Ô được định danh `A1`, `B1`, ...; chữ là cột, số là hàng, hàng tăng xuống dưới.
- Thứ tự chuẩn: row-major `A1,B1,C1,A2,...`; display name sắp alphabet theo thứ tự ô. Không dùng tên/nghề làm dữ kiện logic.
- Primary variable `A1=1, B1=2, ...`; auxiliary IDs phải lớn hơn `N*N`. Literal dương là Criminal, âm là Innocent.
- `bool True` trong dữ liệu là Criminal; `False` là Innocent. API verdict dùng `Status`, không truyền chuỗi tùy ý hoặc `UNKNOWN` như một đề nghị phán quyết.
- Dữ liệu chia sẻ là frozen dataclass và tuple; không nhét dict/list có thể bị sửa vào snapshot. Muốn tra cứu có thể tạo dict cục bộ rồi bỏ.
- `PublicState` chỉ chứa metadata hiển thị, verdict đã chứng minh, clue đã mở và revision. Tuyệt đối không thêm đáp án hoặc clue chưa mở.
- `Puzzle` là dữ liệu riêng của loader/validator/engine. GUI và agent không được giữ tham chiếu hoặc tự mở file JSON.
- `Analysis.puzzle_id` phải khớp `PublicState.puzzle_id`; `revision` tăng mỗi lần reveal thành công và restart. Không dùng analysis của puzzle khác hoặc revision cũ. Load puzzle khác hủy worker cũ; controller dùng generation token để bỏ kết quả cũ kể cả khi load lại cùng ID/revision.
- Các hàm suy luận không sửa input. Bắt lỗi dữ liệu bằng `ValueError`. Hết thời gian bằng `SolverTimeout`, không trả UNSAT/UNKNOWN để che timeout.

## DPLL — người 1

`DPLLSolver.solve(cnf, assumptions=(), *, timeout_s=5.0) -> SATResult`

- `cnf.clauses` là tuple các clause; `()` là công thức true; clause `()` làm công thức false.
- Thêm assumptions tạm thời, không sửa CNF gốc và không giữ assumptions qua lần gọi kế tiếp.
- SAT trả assignment đầy đủ cho **mọi biến 1..variable_count**, kể cả biến không xuất hiện. UNSAT trả assignment rỗng.
- Chọn biến/nhánh quyết định theo quy tắc ổn định, ghi trong báo cáo.
- `decisions`: số nút chọn biến rẽ nhánh; `propagations`: số phép gán mới do unit propagation; `backtracks`: số nhánh thử thất bại phải quay lui. Cùng định nghĩa trong mọi thực nghiệm.
- Runtime là mili giây của toàn bộ lần solve; mỗi lần gọi có stats mới. Hết deadline phải phát sinh `SolverTimeout`.
- Pure-literal và heuristic nâng cao là tùy chọn. Nếu thêm option thì người 1 cập nhật constructor/experiment config và docs cùng lúc.

Bản DPLL hiện tại chọn biến chưa gán có ID nhỏ nhất, thử False rồi True. Unit propagation xử lý unit theo `(abs(literal), literal)`; literal trùng được bỏ, clause tautology được loại. Assumptions được thêm thành unit tạm, nên phép gán mới do assumption cũng nằm trong propagation count. Không dùng thư viện SAT bên ngoài.

## Encoder — người 2

| API | Contract |
|---|---|
| `CNFEncoder.validate_clue(clue, size)` | Kiểm tra loại clue, số operand, ô, vùng, biên `k`, parity; sai thì `ValueError`. |
| `CNFEncoder.encode(public_state) -> CNF` | Chỉ encode clue công khai và unit của verdict đã chứng minh; mapping xác định; số biến/clause có thể tính từ kết quả. |

Encoder không gọi evaluator để sinh CNF. Ví dụ `SAME(i,j)` sinh `(¬Ci∨Cj) ∧ (Ci∨¬Cj)`; các câu đếm phải được chuyển tự động, không hardcode CNF theo puzzle.

**Extensions chưa chốt.** Nhân (người 2) tự tìm hiểu và chọn ít nhất hai loại khác nhau thuộc phạm vi đề. PARITY và COUNT_COMPARE trong [EXTENSIONS.md](EXTENSIONS.md) chỉ là đề xuất; không phải hai kind bắt buộc của API v1 hiện tại.

`Clue` hiện mô tả sáu core templates. Sau khi chọn extensions, Nhân thống nhất với người 1–3 về kind, trường dữ liệu, ngữ nghĩa và biên; cập nhật models/schema/validator/evaluator/tests cùng lúc rồi báo người 4. Không dùng field core với ý nghĩa khác hoặc âm thầm bỏ qua kind chưa hỗ trợ. Nếu chọn hai đề xuất, có thể tham khảo schema trong docs rồi bổ sung đúng các field cần thiết; chưa có `other_region`/`relation` trong contract core.

## Logic Agent — người 2

| API | Contract |
|---|---|
| `LogicAgent(encoder, solver)` | Dependency injection theo Protocol; không nhận engine/puzzle/path. |
| `analyze(public_state, *, timeout_s=5.0) -> Analysis` | Kiểm tra KB nhất quán trước. Phân loại mọi ô chưa giải, theo row-major, ghi từng SAT query thực tế. |
| `next_forced(analysis) -> (cell, Status) hoặc None` | Chọn ô đầu tiên forced; `None` nếu inconsistent hoặc không có ô forced. Không đoán. |
| `check_uniqueness(full_clue_state, *, timeout_s=5.0) -> Uniqueness` | Luồng offline trên **đầy đủ clue**, không nhét hidden labels/solution vào state; block model theo primary variables thôi. |

Quy tắc phân loại, sau khi biết KB SAT:

| `KB∧¬Ci` | `KB∧Ci` | Kết luận |
|---|---|---|
| UNSAT | SAT | CRIMINAL |
| SAT | UNSAT | INNOCENT |
| SAT | SAT | UNKNOWN |

KB tự UNSAT thì `Analysis.inconsistent=True`, không chọn verdict. Nếu hai truy vấn cùng UNSAT sau khi base SAT, coi là lỗi solver/state; không âm thầm chọn verdict. `timeout_s` là ngân sách cho toàn bộ analyze/uniqueness, không tự nhân ngân sách cho từng query.

`SATQuery` lưu assumptions (rỗng là base KB), SAT/UNSAT và stats. `Analysis.queries` chứa cả base query; đây là truy vấn đã chạy, không phải truy vấn dựng giả cho đẹp trace.

## Core, regions và semantics — người 3

| API | Contract |
|---|---|
| `load_puzzle(path) -> Puzzle` | Đọc schema v1, báo lỗi rõ; validate coverage, duplicate, clue, vùng và cấu trúc. Kiểm tra truth có thể gọi evaluator sau khi nó hoàn thiện. |
| `all_cells(size)` | Tuple tất cả ô theo row-major. |
| `resolve_region(region,size)` | ROW/COLUMN một-based; NEIGHBORS 8 hướng bỏ anchor; EXPLICIT không trùng ô; trả thứ tự row-major. |
| `referenced_cells(clue,size)` | Vùng/operand dùng chung cho highlight và encoding/evaluation, bỏ trùng và theo row-major. Bổ sung cho các extensions sau khi chốt; không làm suy luận. |
| `evaluate_clue(clue, assignment, size) -> bool` | Assignment đầy đủ; tính ngữ nghĩa trực tiếp, không gọi encoder hay SAT. |
| `validate_puzzle(puzzle, agent) -> ValidationResult` | Offline: tất cả clue đúng; complete clues UNIQUE; và mô phỏng progressive solve. Ba kết quả tách riêng. |

Evaluator có thể dùng resolver vùng chung, nhưng phần ngữ nghĩa phải độc lập với encoder. Kiểm tra uniqueness chỉ dựa vào đầy đủ clue, không thêm toàn bộ solution dưới dạng unit vì như vậy kết quả UNIQUE sẽ vô nghĩa.

Evaluator cho các extensions được chọn cũng cần độc lập với encoder. Ví dụ nếu chọn COUNT_COMPARE thì tính hai tổng trực tiếp rồi so, không dùng phép biến đổi encoder làm oracle.

## GameEngine — người 3

| API | Contract |
|---|---|
| `GameEngine(puzzle)` | Giữ dữ liệu private; khởi tạo trạng thái ban đầu. |
| `public_state() -> PublicState` | Snapshot chỉ thông tin đã công khai. |
| `restart() -> PublicState` | Công khai cả status và clue của thẻ mở ban đầu; revision mới. |
| `submit_verdict(cell, proposed, analysis) -> SubmitResult` | Chỉ nhận analysis do session tạo cho puzzle ID và revision hiện tại. Kiểm tra ô, consistent, classification và đối chiếu dữ liệu private trước khi reveal. |
| `is_solved() -> bool` | Mọi ô đã được mở bằng verdict được chấp nhận hoặc mở ban đầu. |

Kết quả submit:

- `ACCEPTED`: đúng và được chứng minh, thêm unit status + clue mới, tăng revision.
- `NOT_PROVABLE`: chưa forced; không đổi bất kỳ dữ liệu công khai nào.
- `CONTRADICTED`: opposite verdict đã forced; không đổi state.
- `INCONSISTENT`: KB mâu thuẫn hoặc proof không khớp dataset; không reveal.
- `ALREADY_REVEALED`: ô đã mở; không tạo bước trace mới.

Ô không tồn tại, proposed UNKNOWN, puzzle ID khác hoặc revision cũ là lỗi input `ValueError`. `new_public_state` luôn là snapshot sau kết quả; `revealed_clue` chỉ có giá trị khi ACCEPTED. GUI không tự tạo `Analysis` giả để bỏ qua bước chứng minh.

## Session và worker — người 1

`GameSession(engine, agent)` nối các phần; GUI chỉ gọi public methods của session.

| API | Contract |
|---|---|
| `public_state()` | Public snapshot cho view. |
| `analyze(timeout_s=...)` | Cache theo revision; đếm query đúng một lần khi thực sự chạy. |
| `hint()` | Trả một forced move hoặc None; không submit, không reveal và không đọc đáp án. |
| `submit(cell,proposed)` | Lấy analysis hiện hành → engine.submit_verdict → ghi trace nếu ACCEPTED. |
| `step()` | Tối đa một forced reveal; None khi solved/không có move, caller phân biệt consistent qua analysis. |
| `restart()` | Dừng/hủy worker, reset engine, cache, trace và metrics; public state mới. |
| `export_trace(path)` | JSON/CSV gồm dữ liệu công khai; không export hidden solution. |
| `metrics() -> SessionMetrics` | Counts của KB hiện tại và counters cộng từ query thực tế; không đếm lặp cache hoặc trace. |
| `start_analysis(*, timeout_s=5.0) -> AnalysisJob hoặc None` | Bắt đầu worker do session quản lý; trả job đang chạy hoặc None nếu đã có cache cho snapshot hiện tại. |
| `poll_analysis() -> Analysis hoặc None` | Nhận kết quả worker, kiểm tra state và cache/đếm đúng một lần; None khi chưa có kết quả hoặc job cũ đã bị loại. |
| `cancel_analysis()` | Hủy job do session quản lý, không reveal và không xóa cache hợp lệ đã có. |
| `accept_analysis(analysis) -> Analysis` | Nhận Analysis từ worker ngoài session sau khi controller kiểm tra generation; validate snapshot và đưa vào cache/metrics, không chạy SAT lại. Cùng object nhận lại không được đếm hai lần. |

Mỗi `TraceEntry` có step, revision cũ, IDs clue đang active **trước** reveal, ô/verdict, SAT queries đã dùng và ID clue vừa lộ. Auto Solve do controller lên lịch nhiều `step()`, dừng khi solved/UNKNOWN/INCONSISTENT/error/timeout hoặc người chơi pause.

Cache được đối chiếu cả public snapshot (gồm ID/revision), không chỉ một số revision. Submit kiểm tra classification trước khi gửi verdict cho engine; UNKNOWN/opposite/inconsistent không được gọi commit hay reveal. Stats cộng query của mỗi Analysis hợp lệ nhận được một lần. Worker bị hủy/lỗi/timeout không tạo dữ liệu giả; caller phải ghi trạng thái thất bại riêng khi benchmark, không suy số query còn thiếu từ trace.

`SessionMetrics.primary_variables` có từ board. `auxiliary_variables` và `active_clauses` là **None** khi snapshot hiện tại chưa phân tích (lúc load hoặc sau reveal/restart), không phải 0 và không lấy số liệu snapshot cũ. GUI hiển thị “chưa phân tích” đến khi nhận Analysis. Tổng SAT counters và runtime của các analysis trước vẫn được giữ đến restart.

`AnalysisJob(state,agent,timeout_s).start()/poll()/cancel()` là worker nền nhận public snapshot và agent theo Protocol; không nhận engine/private puzzle/path. Agent được truyền vào phải giữ đúng cấu hình encoder/solver đã chọn, không tự thay bằng một backend khác. `poll()` trả None khi pending, Analysis khi xong; exception phải phân biệt timeout/error. Không update widget từ worker. Worker trả sau restart/load phải bị loại kể cả khi puzzle ID/revision trùng lần load mới.

Bản worker dùng multiprocessing `spawn`, deadline gồm cả thời gian khởi động process. Class của agent/encoder/solver phải ở cấp module, pickle được và không giữ widget/engine. Entry point khởi động ứng dụng phải nằm trong `if __name__ == "__main__":`. Worker trả lỗi agent về parent, worker chết bất thường thành RuntimeError; timeout thành SolverTimeout. `cancel()` dùng được nhiều lần, kết quả sau cancel bị bỏ. Nhận dữ liệu pipe trước khi join để không treo với payload lớn.

Người 4 nên gọi các wrapper của session để worker và cache có cùng lifecycle:

```python
session.start_analysis(timeout_s=5.0)
# Trong update loop, không phải vòng while chặn GUI:
analysis = session.poll_analysis()
if analysis is not None:
    # Render analysis; chỉ enable submit/step khi có kết quả đúng snapshot.
    pass
```

Sau accepted reveal gọi `start_analysis` cho snapshot mới. `session.restart()` tự hủy job cũ; khi đổi/đóng session gọi `cancel_analysis()` của session cũ. Controller vẫn cần generation token khi thay instance session/puzzle. Không sửa state/widget từ process con. `analyze()` đồng bộ phù hợp CLI/benchmark; GUI dùng luồng worker để tránh chặn render.

Controller GUI hiện giữ worker riêng và gọi `accept_analysis` sau kiểm tra generation/ID/revision, rồi mới render kết quả. Đây là cách nối tương đương; không cần vừa tạo worker controller vừa gọi `start_analysis` để chạy hai job cùng lúc. Hint/Submit/Step sau đó dùng đúng cache đã nhận.

## GUI — người 4

GUI library và code hiển thị do người 4 chọn/viết. Các view nhận `PublicState`, `Analysis`, `TraceEntry` và callback; không import private loader hoặc đọc file JSON. Controller nhận đường dẫn từ file dialog rồi nhờ composition/session tạo engine ở phía core.

Khung scene/view bổ sung ở `scenes/` và `ui/`; chi tiết hành vi cần thể hiện trong `docs/GUI_PLAN.md`. `render(surface)`/`handle_event(event)` dùng object trung lập trong scaffold, nhóm thay type bằng thư viện đã chọn khi triển khai.

View hiện nhận tập ô cần highlight của core. Nếu Nhân chọn extension cần nhiều nhóm ô (ví dụ COUNT_COMPARE), nhóm chốt thêm tham số hiển thị sau; hiện chưa ép `BoardView` có dữ liệu hai vùng. Mọi extension đều phải hiển thị bằng public data, không lấy số lượng Criminal bí mật từ solution.
