# Kế hoạch thực nghiệm — người 3 tự triển khai và chạy

Khung runner có chữ ký, chưa có xử lý. Người 5 không chạy benchmark; chỉ nhận bảng/biểu đồ và nhận xét từ người 3.

## Bộ case

- Nhiều puzzle 3x3 và 4x4, ít nhất có nhiều hơn một case mỗi kích thước. 5x5 tùy chọn stress.
- Phủ các core clue và hai extensions; vùng row/column/neighbors/explicit.
- Khi Nhân chọn extensions, bổ sung case/biên tương ứng và puzzle mà mỗi extension thực sự tạo một forced move. Nếu chọn đề xuất COUNT_COMPARE thì có thể phủ EQ/LT/GT và vùng giao/rời/trùng/rỗng; chưa bắt buộc xây nhóm case riêng cho đề xuất chưa được chọn.
- Bộ chính là valid, unique và progressively solvable. Ca multiple/inconsistent/unique-but-stalled nằm nhóm chẩn đoán riêng; không trộn rồi giấu kết quả.
- Puzzle JSON không chứa CNF viết tay. Có manifest danh sách file và hash để giữ nguyên tập giữa các so sánh.

## Mỗi dòng CSV

`case_id,size,configuration,repeat,status,primary_variables,auxiliary_variables,active_clause_peak,complete_clue_clauses,sat_calls,decisions,propagations,backtracks,deduction_steps,play_runtime_ms,total_runtime_ms,uniqueness,error`

`status`: SOLVED / UNKNOWN / INCONSISTENT / TIMEOUT / ERROR. Dòng failure vẫn được ghi; trường chưa đo được để trống, không tự đặt 0.

## Định nghĩa đo

- Play runtime bắt đầu **trước lần analyze đầu tiên**, không gồm animation và không lẫn thời gian render GUI.
- SAT calls và counters cộng mọi query thực sự chạy trong gameplay, kể cả consistency query; cache không tính thành lần chạy mới. Không cộng lặp bằng cách sum trace chứa cùng snapshot.
- Complete-clue uniqueness là pha offline riêng. Ghi runtime riêng nếu đo; không lẫn vào counters gameplay khi chưa ghi rõ scope.
- Clause count có tên rõ: peak active KB khác với full-clue CNF. Auxiliary count là tổng biến trừ primary, không đoán rằng luôn bằng 0.
- Có timeout cấp solve và deadline toàn case; hết thời gian không coi là UNSAT. Ưu tiên tiến trình riêng để parent dừng được case treo.
- Nếu dùng multiprocessing + pipe/queue, parent nhận kết quả trước khi join để tránh trace lớn làm đầy pipe.
- Ghi Python version, OS/CPU, cấu hình solver, timeout, số lần lặp và manifest case. Chỉ so sánh khi cùng bộ case và quy tắc đo.

## So sánh đề xuất

DPLL cơ bản với một cải tiến tùy chọn (pure-literal hoặc deterministic heuristic khác), nếu nhóm có thời gian. DPLL cơ bản phải đủ unit propagation và backtracking. Không thêm solver thư viện để thay thuật toán chính. Nếu không làm cải tiến, báo cáo độ khó/kích thước cùng giới hạn của một cấu hình và không giả vờ đã có ablation.

Người 3 cung cấp CSV gốc, biểu đồ/bảng đã chọn, mô tả failure/timeout và nhận xét cho người 5. Không lấy số liệu của repo mẫu làm kết quả nhóm.

Có thể bổ sung cột đặc trưng của các extensions thực sự chọn để giải thích chi phí theo dạng clue. Ví dụ cột parity/count-compare chỉ phù hợp nếu nhóm chọn các đề xuất đó. Không mặc định case chứa extension khó hơn; đo rồi mới nhận xét. Mọi cấu hình solver vẫn chạy cùng tập puzzle.
