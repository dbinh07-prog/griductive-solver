# Hai extensions đã tích hợp

Code Nhân đẩy lên main đã triển khai ParityStrategy và CountCompareStrategy trong logic/encoder.py. Nhánh feature/integrate nối chúng với contract, loader, evaluator độc lập, GUI và kiểm thử. Đây là hai loại khác nhau; even/odd chỉ là hai giá trị của PARITY.

## PARITY — đếm chẵn/lẻ trong một vùng

PARITY(R,k) đúng khi tổng Ci trong R chia 2 dư k. k=0 là chẵn, k=1 là lẻ; bool hoặc giá trị khác bị từ chối. Dùng bốn loại region hiện có.

Encoder hiện duyệt assignment của các ô trong vùng. Mỗi assignment có parity sai sinh một clause cấm đúng assignment đó: biến đang True thành literal âm, biến đang False thành literal dương. Không dùng auxiliary variables. Evaluator tính tổng rồi modulo trực tiếp, không gọi encoder.

- Vùng rỗng: even true (không thêm clause), odd false (clause rỗng).
- Một ô: odd ép Criminal, even ép Innocent.

## COUNT_COMPARE — so số Criminal giữa hai vùng

Schema: region là vế trái, other_region là vế phải, relation là EQ/LT/GT. Dataclass hỗ trợ enum Relation hoặc chuỗi tương ứng; JSON dùng chuỗi. Không dùng cells, status, k ở clue này.

| relation | Ngữ nghĩa |
|---|---|
| EQ | count(trái) = count(phải) |
| LT | count(trái) < count(phải) |
| GT | count(trái) > count(phải) |

Encoder duyệt assignment trên **hợp của hai vùng**, dùng cùng một primary variable cho mỗi ô, rồi cấm từng assignment không thỏa quan hệ. Ô giao có cùng giá trị ở hai vế. Evaluator tính hai tổng trực tiếp rồi so sánh.

- Vùng rời, giao, trùng, rỗng hoặc khác kích thước đều hợp lệ.
- L=R: EQ luôn true, LT/GT luôn false.
- Hai vùng rỗng: EQ true; LT/GT false.
- Đổi hai vế: EQ giữ nguyên; LT tương đương GT sau đổi.

Ví dụ L=hàng 1={A1,B1,C1}, R={A1,C1}. EQ ép B1 Innocent; GT ép B1 Criminal; LT mâu thuẫn. Kết luận chỉ dựa vào clue công khai.

## Kiểm chứng và demo

Tests trong tests/test_extensions.py đối chiếu CNF với evaluator độc lập: PARITY trên các loại vùng; COUNT_COMPARE trên mọi cặp tập con của board 2x2, ba quan hệ và mọi assignment. Có kiểm tra tham số lỗi, vùng giao/rỗng và puzzle progressive.

Puzzle puzzles/examples/example_extensions_3x3.json có sáu core và hai extensions. COUNT_COMPARE là clue mở ban đầu, PARITY xuất hiện trong chuỗi suy luận. Backend thật giải 8 bước; test GUI chạy Auto Solve qua process worker thật và kiểm tra tổng 80 SAT calls. Hint dùng cache, không reveal hoặc chạy SAT thêm.

GUI hiện ghi hai vùng bằng text và highlight hợp hai vùng. Tô hai màu riêng cho hai vế chưa được triển khai. File docs/examples/proposed_extensions_3x3.json là bản đề xuất ban đầu; dùng file trong puzzles/examples/ để chạy demo đã tích hợp.

## Giới hạn và hướng cải tiến

Encoding duyệt assignment có chi phí tăng theo 2^m, với m là số ô của vùng hoặc hợp hai vùng. Phù hợp các demo nhỏ hiện có; không suy rộng kết quả benchmark core thành hiệu năng extensions trên vùng lớn. Worker GUI và runner có giới hạn thời gian, nhưng không làm encoding này nhanh hơn.

Cải tiến có thể nghiên cứu: PARITY dùng XOR chain; COUNT_COMPARE triệt tiêu vùng giao rồi dùng cardinality trên signed literals. Đây là hướng tương lai, **không phải encoding hiện tại**. Khi đổi encoding phải giữ evaluator độc lập, kiểm tra tồn tại assignment auxiliary và uniqueness chỉ block primary variables.

Report cần trình bày đúng encoding đang chạy, ghi số biến/clause/query và giới hạn đo được. Nếu so sánh cấu hình solver, dùng cùng puzzle set; không bỏ clue để tạo bài toán khác rồi coi là cùng benchmark.
