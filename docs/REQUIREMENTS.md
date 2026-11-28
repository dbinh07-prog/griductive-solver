# Đối chiếu yêu cầu thầy và chức năng nhóm sẽ tự làm

Nguồn: đề `AI - Project 2 (1).pdf` do nhóm cung cấp, 9 trang. Đây là checklist yêu cầu; trạng thái tích hợp và kiểm thử hiện tại xem README. Các nhận xét ngoài yêu cầu môn học trong tài liệu tham khảo không được coi là lệnh cho nhóm.

## Bắt buộc theo đề

| Mục / điểm | Yêu cầu cần thể hiện | Phụ trách | Minh chứng khi hoàn thành |
|---|---|---|---|
| Chung, trang 5 | Python; tự viết thuật toán chính; supporting library được phép | 1–4 | Code và phần thuật toán report |
| Game, 10đ | GUI desktop/web, lưới, tọa độ, tên/nghề, status, face-up clue, face-down card | 4 | Demo thủ công 3x3/4x4 |
| Game | Submit Criminal/Innocent; chỉ reveal khi đúng và được chứng minh | 3 + 1 + 4 | Đoán đúng nhưng chưa suy ra vẫn bị từ chối |
| Game | Phân biệt NOT_PROVABLE và CONTRADICTED; reject không đổi state | 3 + 1 + 4 | Thử cả hai; card không mở |
| Game | Chọn clue đã mở, highlight đúng ô được nhắc/đếm | 3 + 4 | Vùng hàng/cột/hàng xóm/list |
| Game | Load, Restart, Hint, Auto Solve | 1 + 4 | Hint không reveal; auto không đoán |
| Kiến trúc | Engine giữ secret; agent chỉ nhận revealed clues + proved statuses | 1–3 | Test public snapshot và kiểm tra dependency |
| Encoder, 10đ | Mapping xác định, primary/aux tách biệt, validate tham số/vùng | 2 + 3 | Mapping, lỗi input và test biên |
| Encoder | Tự encode sáu clue FACT/SAME/DIFFERENT/EXACTLY/AT_LEAST/AT_MOST | 2 | Test đối chiếu semantics trên mọi assignment nhỏ |
| Encoder | Ít nhất hai extensions khác nhau | 2 — Nhân tự chọn | Code Nhân hiện triển khai PARITY/COUNT_COMPARE; cần trình bày semantics, CNF, tests và demo |
| Encoder | KB chỉ gồm clue đã mở + units verdict đã chứng minh | 2 | So snapshot trước/sau reveal; không hardcode puzzle |
| Encoder | Báo primary variables, auxiliary variables, clause count | 2 + 4 | Inspector GUI và CSV |
| Semantics | Direct evaluator cho từng core template, không gọi encoder | 3 | Oracle độc lập; nên có cả hai extensions |
| DPLL, 10đ | Unit propagation, conflict detection, chọn biến xác định, branch/backtrack | 1 | CNF SAT/UNSAT và ca bắt buộc backtrack |
| DPLL | SAT trả model đầy đủ, UNSAT đúng; decisions/propagations/backtracks/runtime | 1 | Test model và thống kê thật |
| Agent, 20đ | Phân loại mọi unresolved Criminal/Innocent/Unknown bằng entailment | 2 | Hai truy vấn giả thiết đối nghịch và consistency query |
| Agent | Chỉ chọn forced verdict; reveal tuần tự và cập nhật KB | 2 + 1 + 3 | Trace và auto run |
| Agent | UNKNOWN khi chưa suy ra; INCONSISTENT khi KB UNSAT | 2 + 4 | Không reveal và không giả vờ solved |
| Agent | Trace: step, active clue IDs, SAT queries, verdict, clue mới | 1 + 2 + 4 | Từng assumptions/result, không chỉ số query |
| Agent | Uniqueness check riêng cho **complete clue set** | 2 + 3 | UNIQUE/MULTIPLE/INCONSISTENT, block primary model |
| Experiments, 10đ | Nhiều puzzle 3x3 và 4x4; 5x5 stress tùy chọn | 3 | Dataset phiên bản cố định, không chỉ một case/kích thước |
| Experiments | Variables, clauses, SAT calls, decisions/propagations/backtracks, steps/waves, runtime | 3 | CSV + manifest môi trường |
| Experiments | Cùng tập puzzle giữa các so sánh; giữ cả failure/timeout | 3 | Không lọc bỏ ca xấu; có dòng trạng thái lỗi |
| Report, 30đ | Phân việc và % hoàn thành từng người, đánh giá đúng thực tế | 5 + cả nhóm | Bảng đóng góp có bằng chứng; không tự điền 100% |
| Report | Biến, clue semantics, KB, reveal protocol | 1–3 viết, 5 gom | Nội dung technical từ đúng owner |
| Report | Dẫn giải ít nhất một binary clue và một counting clue | 2 viết, 5 gom | Công thức và ví dụ tự làm |
| Report | DPLL, entailment, uniqueness, loop; thực nghiệm, failures, hạn chế | 1–3 viết, 5 gom | Không lấy số liệu repo khác làm của nhóm |
| Report | References và appendix, gồm cách dùng AI/prompts thực tế nếu có | 5 + cả nhóm | Ghi nguồn và công cụ trung thực |
| Video, 10đ | 5–10 phút, GUI + chơi tay + chạy solver, narration/subtitle Việt/Anh | 5 + 4 hỗ trợ | Kịch bản và link video |
| Video | Drive anyone-with-link; kiểm tra incognito; không dùng YouTube | 5 | Link hoạt động, nằm trong report |
| Submission | ZIP/RAR tên MSSV1_MSSV2_...; Source, Report.pdf, README, requirements | 5 | Checklist đóng gói; hơn 20MB dùng Drive |

## Những điểm dễ hiểu sai

- Clue luôn đúng kể cả chủ thẻ là Criminal; đây không phải bài truth-teller/liar.
- Thẻ mở ban đầu công khai **cả nhãn lẫn clue**. Sau accepted reveal cũng thêm cả hai vào KB.
- Hàng xóm tính cả đường chéo nhưng bỏ chính ô đang xét: góc 3, cạnh không góc 5, giữa 8 (board 3x3 trở lên).
- Một model SAT không đủ chứng minh verdict. Đoán đúng đáp án bí mật vẫn phải NOT_PROVABLE nếu public KB chưa ép được nó.
- Phải kiểm tra base KB UNSAT trước; không suy ra mọi người đều Criminal/Innocent từ KB mâu thuẫn.
- Nghiệm đầy đủ duy nhất chưa bảo đảm mở tuần tự được. Validator phải phân biệt hai thuộc tính.
- Khi có auxiliary variables, uniqueness phải block **primary assignment**, không block cả auxiliary assignment.
- Semantic evaluator phải độc lập với encoder; dùng chung region resolver là hợp lý, dùng encoder làm oracle thì không độc lập.
- NO là EXACTLY(0), không phải một extension riêng. EVEN/ODD là hai giá trị của một extension PARITY.

## Đề xuất bổ sung của nhóm, không phải điểm bắt buộc mới

| Chức năng | Lý do | Owner |
|---|---|---|
| Next Step, Pause và tốc độ Auto Solve | Demo được từng reveal và dừng đúng lúc | 4 + 1 |
| Public KB inspector và variable map | Thể hiện rõ encoding, không lộ đáp án | 4 + 2 |
| Trace export JSON/CSV | Đưa bằng chứng vào report và tái hiện lỗi | 1 |
| Diagnostic offline dataset | Phân biệt multiple, inconsistent, unique-but-stalled | 3 + 2 |
| Background analysis, bỏ kết quả cũ sau restart/load | GUI còn phản hồi, không áp proof cũ | 1 + 4 |
| Timeout rõ ràng | Không biến hết thời gian thành UNSAT hoặc verdict | 1–3 |

Đề trang 3 cho phép nhiều hướng extension. Code Nhân hiện chọn PARITY và COUNT_COMPARE; API/schema, loader, evaluator, demo, GUI và kiểm thử đã cập nhật theo hai loại này. Sáu core templates, bốn vùng bắt buộc, DPLL tự viết, public-only agent, evaluator độc lập và toàn bộ mục benchmark vẫn giữ nguyên.

Thứ tự: hoàn thành yêu cầu bắt buộc → test đúng → thêm chức năng minh họa. Animation chỉ hỗ trợ quan sát, không che lỗi logic. Không thêm tài khoản, cloud, NLP hoặc tính năng không giúp thể hiện bài.
