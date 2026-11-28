# Griductive Solver

**Trạng thái tích hợp:** đã ghép GUI từ `feat/gui`, engine/loader/evaluator/dataset/runner từ `feature/engine-and-experiment`, code hiện có trên `main` và phần người 1 (DPLL, session, worker, factory). Các entry point thật được giữ nguyên, không thay bằng fixture trong test.

**Nhánh tích hợp:** `feature/integrate`, đã ghép encoder/agent Nhân đẩy lên `main` đến commit `66c570a`. Luồng thật GUI → session → agent → encoder → DPLL → engine đã chạy, gồm sáu core templates và hai extensions `PARITY`, `COUNT_COMPARE`. Contract, loader, evaluator và text/highlight clue đã cập nhật tương ứng.

## Phân công 5 người

| Thành viên | File/folder làm chính | Công việc |
|---|---|---|
| **1 — Leader** | `algorithms/dpll.py`, `game/session.py`, `game/worker.py`, `contracts/`, `docs/API.md` | DPLL SAT Solver, kiến trúc, ghép engine–encoder–agent–GUI, trace và thống kê tích hợp. **Không tổng hợp report.** |
| **2 — Logic (Nhân)** | `logic/encoder.py`, `logic/agent.py` | CNF encoder, tự tìm hiểu và chọn ít nhất hai extensions khác nhau theo đề, Logic Agent, entailment, uniqueness. |
| **3 — Engine và thực nghiệm** | `core/`, `validation/`, `puzzles/`, `experiments/`, `run_experiments.py` | Game Engine, loader, regions, dataset, semantic evaluator độc lập, kiểm tra puzzle và chạy benchmark. |
| **4 — GUI** | `main.py`, `app_controller.py`, `scenes/`, `ui/`, `assets/`, `requirements.txt` | Tự thiết kế và code toàn bộ giao diện, điều khiển, highlight clue, animation và bảng kết quả. |
| **5 — Tài liệu, không code** | `docs/QA.md`, `report/`, hướng dẫn chơi/chạy trong README | Tổng hợp report, kiểm thử thủ công, ghi lỗi, kịch bản/quay/dựng video, kiểm tra gói nộp. **Không chạy benchmark.** |

Mỗi người tự viết nội dung kỹ thuật và kiểm thử cho phần mình; người 5 biên tập/tổng hợp. Người 3 giao số liệu và nhận xét benchmark. Leader điều phối tích hợp; lỗi trong module nào do người sở hữu module đó sửa.

Hướng dẫn cụ thể: [người 1](docs/members/01-leader.md), [người 2](docs/members/02-logic.md), [người 3](docs/members/03-engine.md), [người 4](docs/members/04-gui.md), [người 5](docs/members/05-report.md).

## Đọc gì trước khi code?

1. [Yêu cầu thầy và tiêu chí nghiệm thu](docs/REQUIREMENTS.md).
2. [API chung v1](docs/API.md) và [format puzzle](docs/DATA_FORMAT.md).
3. [Danh sách chức năng và bố cục GUI đề xuất](docs/GUI_PLAN.md).
   [Hai extensions Nhân đã triển khai](docs/EXTENSIONS.md): PARITY và COUNT_COMPARE.
4. Hướng dẫn của người phụ trách module; sau đó mới bắt đầu code.

API v1 ở đây là **baseline đề xuất để cả nhóm dùng chung**, chưa phải bằng chứng nhóm đã đồng ý. Nếu đổi chữ ký hàm, kiểu dữ liệu hoặc ý nghĩa kết quả, người 1 cập nhật contract và báo các thành viên liên quan trước khi ghép.

API/schema gồm sáu core templates và hai extensions đã được Nhân triển khai. `Clue` có thêm `other_region` và `relation`; sáu core giữ nguyên ngữ nghĩa. Puzzle demo hai extensions: `puzzles/examples/example_extensions_3x3.json`.

## Cấu trúc repo

```text
main.py, app_controller.py   khởi động, ghép module và chuyển màn — người 4 + 1
contracts/                  enum, dataclass, Protocol dùng chung — người 1 quản lý
algorithms/                 DPLL độc lập với game — người 1
logic/                      encoder và agent — người 2
core/                       puzzle loader, regions, private GameEngine — người 3
validation/                 semantic evaluator và kiểm tra dataset — người 3
game/                       session, trace, background worker — người 1
scenes/, ui/, assets/        khung các màn và thành phần GUI — người 4
puzzles/examples/           JSON minh họa format, không phải bộ benchmark cuối
puzzles/benchmark/          nhiều puzzle 3x3, 4x4 do người 3 xây dựng
experiments/                khung chạy thực nghiệm — người 3
tests/                      kiểm thử thuật toán, module và luồng tích hợp thật
docs/                       API, yêu cầu, phân việc, kế hoạch GUI, QA
outputs/                    kết quả chạy máy sinh ra, không commit
report/                     khung báo cáo, số liệu/ảnh được chọn và video checklist
```

## Làm song song trước khi module khác xong

| Người | Làm ngay | Chưa cần chờ |
|---|---|---|
| 1 | DPLL với CNF nhỏ tự tạo; thiết kế session/worker theo contract | Loader, GUI và dataset cuối |
| 2 | Encoder từ `PublicState` tự tạo; agent với solver giả trong test | DPLL thật và engine hoàn chỉnh |
| 3 | Loader/regions/engine; evaluator độc lập; chuẩn bị dataset và script thực nghiệm | GUI; benchmark thật chạy sau khi ghép |
| 4 | Menu, bàn chơi, các panel với `PublicState`/`Analysis` giả | Engine và solver thật |
| 5 | Checklist QA, khung report, biểu mẫu lỗi và kịch bản video | Bản game; kiểm thử/quay thật làm sau |

Luồng ghép: **GUI → GameSession → LogicAgent → CNFEncoder → DPLLSolver**. Khi verdict được chứng minh, session gửi analysis hiện hành cho **GameEngine** để cập nhật trạng thái. Agent không nhận engine, puzzle hoặc đường dẫn JSON. GUI không tự xác định verdict.

## Chạy chương trình

Dùng Python **3.11 trở lên**, nhóm nên thống nhất Python 3.12. Mở terminal ở thư mục có `main.py`:

```powershell
python -m pip install -r requirements.txt
python main.py --check
python main.py
```

Lệnh cài thư viện lấy Pygame theo requirements. `--check` chỉ kiểm tra import/chữ ký, **không chứng minh backend đã hoàn thành**. `python main.py` mở GUI đã ghép. Nếu máy chưa có lệnh `python`, cài Python chuẩn hoặc chọn đúng interpreter có sẵn. Không ghi đường dẫn riêng của một máy vào repo.

`requirements.txt` đã khóa `pygame==2.6.1` theo nhánh GUI. Môi trường ảo, `.env`, cache và file tạm chỉ giữ ở máy cá nhân; `.gitignore` loại chúng khỏi repo.

## Kiểm thử và thực nghiệm

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
python run_experiments.py
```

Toàn bộ 104 test đã chạy đạt, không skip: DPLL, encoder, agent, extensions, session, worker, factory, engine, loader, evaluator và GUI. Có đối chiếu CNF với vét cạn/evaluator độc lập, kiểm tra vùng giao/rỗng, UNKNOWN/INCONSISTENT, timeout và restart/load khi worker đang chạy.

Kiểm tra tích hợp ngày 28/11/2026: 18 puzzle benchmark 3x3/4x4/5x5 × 3 lượt, đủ 54/54 `SOLVED` và `UNIQUE`. Demo extensions cũng được kiểm tra với backend thật và Auto Solve qua worker GUI. Đây là kiểm tra tích hợp cấu hình `dpll_baseline`; nhóm vẫn cần thực nghiệm/nhận xét cho report theo đề.

Kiểm tra riêng phần người 1:

```powershell
python -m unittest tests.test_dpll tests.test_integration tests.test_worker tests.test_factory -v
```

`tests/member1_data.py` là fixture nhỏ chỉ hỗ trợ FACT, phục vụ kiểm tra tích hợp với DPLL thật; không phải encoder/agent/engine hoàn chỉnh để nộp bài. `create_session` luôn nối module thật và báo lỗi nếu phần phụ thuộc chưa triển khai, không tự chuyển sang fixture.

`tests/core_integration_data.py` là adapter sáu core chỉ dùng trong test hồi quy. `tests/test_real_component_integration.py` còn chạy cả 18 puzzle với encoder/agent production và Auto Solve demo extensions bằng worker thật. File này cũng kiểm tra GUI đưa Analysis vào cache session, không chạy SAT lần hai khi Hint/Submit. Factory và script thực nghiệm luôn dùng backend production.

## Mốc tích hợp

1. Chốt API/dữ liệu; ai cũng import được contract.
2. DPLL chạy CNF nhỏ; encoder được so với semantic evaluator độc lập.
3. Một puzzle 3x3 chạy xuyên suốt, đúng hai kiểu từ chối và không lộ clue ẩn.
4. GUI đủ controls; Hint/Auto Solve/trace/metrics hoạt động; xử lý UNKNOWN/INCONSISTENT.
5. Hoàn thiện dataset 3x3/4x4, chạy thực nghiệm, report và video.

Không đợi gần hạn mới ghép. Mỗi PR tập trung vào module của mình; sửa API phải cập nhật docs cùng lúc.

## Tham khảo và nộp bài

- Cách tổ chức scaffold dựa trên ZIP Bloxorz mà nhóm cung cấp (commit `467598f61060871e68397da4e7fbc3092cdb460e`).
- Đã xem repo Griductive mẫu tại [TranTai35/griductive-solver](https://github.com/TranTai35/griductive-solver), mốc `52c8a4d09a6ac15f13d76b03f58413e6c800afee`. Bộ khung này không chép phần triển khai game/thuật toán/GUI của repo đó.
- Yêu cầu chính lấy từ đề Griductive do nhóm cung cấp; bảng đối chiếu nằm trong `docs/REQUIREMENTS.md`.
- Người 5 xem [checklist nộp bài](report/SUBMISSION.md). Ghi nguồn tham khảo và cách dùng AI/prompts thực tế trong phụ lục; không tự tạo kết quả hoặc khai là chưa dùng nếu đã dùng.
