# Griductive Solver — bộ khung làm việc nhóm

**Đây là khung sườn để nhóm tự code, không phải game hoàn chỉnh.** Thuật toán, luật chơi, GUI, kiểm thử và benchmark chưa được triển khai. Các hàm nghiệp vụ cố ý để `NotImplementedError`. Dataclass/enum chỉ chốt kiểu dữ liệu chung.

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
   [docs/EXTENSIONS.md](docs/EXTENSIONS.md) chỉ có đề xuất tham khảo PARITY/COUNT_COMPARE; Nhân tự lựa chọn, không bắt buộc dùng hai đề xuất đó.
4. Hướng dẫn của người phụ trách module; sau đó mới bắt đầu code.

API v1 ở đây là **baseline đề xuất để cả nhóm dùng chung**, chưa phải bằng chứng nhóm đã đồng ý. Nếu đổi chữ ký hàm, kiểu dữ liệu hoặc ý nghĩa kết quả, người 1 cập nhật contract và báo các thành viên liên quan trước khi ghép.

API/schema hiện chốt phần core. Sau khi Nhân chọn extensions, người 1–3 thống nhất thêm kiểu dữ liệu/encoding/evaluator, người 4 bổ sung hiển thị. Yêu cầu bắt buộc của đề vẫn là **ít nhất hai extensions khác nhau**, chưa chốt tên cụ thể.

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
tests/                      vị trí và tên ca kiểm thử, chưa có nội dung test
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

## Kiểm tra bộ khung hiện tại

Dùng Python **3.11 trở lên**, nhóm nên thống nhất Python 3.12. Mở terminal ở thư mục có `main.py`:

```powershell
python main.py --check
python main.py
```

Lệnh đầu chỉ kiểm tra import/chữ ký phụ thuộc, **không kiểm tra thuật toán**. Lệnh thứ hai chỉ thông báo đây là scaffold, không mở game. Nếu máy chưa có lệnh `python`, cài Python chuẩn hoặc chọn đúng interpreter có sẵn. Không ghi đường dẫn riêng của một máy vào repo.

`requirements.txt` chưa cần thư viện ngoài. Người 4 chọn và khóa phiên bản GUI sau. Môi trường ảo, `.env`, cache và file tạm chỉ giữ ở máy cá nhân; `.gitignore` loại chúng khỏi repo.

## Sau khi nhóm tự triển khai

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
python run_experiments.py
```

Hiện test chỉ là khung và được skip có chủ đích; **skip không chứng minh chương trình đúng**. Mỗi người viết nội dung rồi bỏ `@unittest.skip` ở file của mình. Game và benchmark chỉ chạy sau khi nhóm hoàn thiện phần triển khai và nối entry point.

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
