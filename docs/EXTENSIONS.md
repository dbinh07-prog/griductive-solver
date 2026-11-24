# Ý tưởng extensions tham khảo — chưa chốt

**Nhân tự nghiên cứu và chọn ít nhất hai extensions khác nhau theo đề. PARITY và COUNT_COMPARE dưới đây chỉ là đề xuất, không phải quyết định bắt buộc của nhóm.** Có thể chọn hai hướng khác phù hợp hơn. Đề còn gợi ý connectivity, compound clues và advanced region expressions.

Sau khi chọn, Nhân ghi lại tên/ngữ nghĩa, giải thích vì sao chọn, ví dụ, schema, cách encode và các biên; thống nhất với người 1/3 rồi báo người 4. Khi đó mới cập nhật contract/schema/test/dataset và phần report tương ứng. Yêu cầu ít nhất hai loại khác nhau của thầy vẫn bắt buộc; danh tính hai loại chưa chốt.

Các mô tả toán học, trường dữ liệu và checklist bên dưới **chỉ áp dụng nếu chọn đề xuất tương ứng**. Chúng không phải phần bắt buộc của API core hiện tại. Không có code thuật toán triển khai sẵn.

## Đề xuất 1: PARITY — số Criminal chẵn/lẻ trong một vùng

`PARITY(R,k)` đúng khi `(Σ Ci, i∈R) mod 2 = k`, với `k=0` là chẵn và `k=1` là lẻ. Có thể triển khai bằng XOR chain có auxiliary variables hoặc một encoding đúng khác; người 2 tự chọn và giải thích.

- Vùng rỗng có tổng 0: even true, odd false.
- Một ô: odd ép Criminal, even ép Innocent.
- Không tính even và odd thành hai extensions.
- Evaluator người 3 tính tổng/modulo trực tiếp; không gọi encoder.

## Đề xuất 2: COUNT_COMPARE — so số Criminal giữa hai vùng

Schema gợi ý nếu chọn: `region` (trái), `other_region` (phải), `relation` (EQ/LT/GT). `other_region` và `relation` **chưa có trong dataclass Clue core**; chỉ bổ sung sau khi Nhân lựa chọn và nhóm thống nhất. Các vùng có thể tái sử dụng ROW/COLUMN/NEIGHBORS/EXPLICIT. Không thay counting `k` cố định của core bằng một ý nghĩa khác.

Đặt `count(R)=Σ Ci, i∈R`:

| relation | Ngữ nghĩa |
|---|---|
| EQ | count(trái) = count(phải) |
| LT | count(trái) < count(phải) |
| GT | count(trái) > count(phải) |

Hai vùng có thể khác kích thước, giao nhau, giống nhau hoặc rỗng. Không so kích thước vùng thay cho số Criminal. Mọi ô trên board chỉ có **một** primary variable, kể cả khi xuất hiện ở cả hai vế.

## Hướng suy ra CNF để nhóm tự triển khai

Đây là gợi ý toán học, không phải yêu cầu dùng đúng một encoding hoặc thuật toán có sẵn.

1. Gọi hai vùng là L và R. Phần giao có cùng biến ở hai phía nên triệt tiêu trong `count(L) - count(R)`.
2. Đặt A=L\R, B=R\L. Khi đó so sánh `Σ(A)Ci - Σ(B)Ci` với 0.
3. Đặt S là tổng truth value của **signed literals**: `Ci` với i∈A và `¬Ci` với i∈B. Vì `¬Ci = 1-Ci`, ta có `count(L)-count(R)=S-|B|`.
4. Quan hệ chuyển thành cardinality trên signed literals:

| Quan hệ | Ràng buộc tương đương |
|---|---|
| EQ | S = \|B\| |
| LT | S ≤ \|B\|−1 |
| GT | S ≥ \|B\|+1 |

Như vậy người 2 có thể tái sử dụng helper cardinality tổng quát nhận literal có dấu. Không cần tạo hai bộ primary variables độc lập cho hai vùng. Auxiliary nếu có phải tách riêng và có mapping/count xác định.

**Biên của helper nội bộ:** at-most âm là false; at-most ≥ số literals là true; at-least ≤0 là true; at-least > số literals là false. Encode true bằng không thêm clause; false bằng clause rỗng. Ngưỡng nội bộ này có thể ngoài [0,m], khác với `k` của core clue từ người dùng vốn phải được validate trong miền hợp lệ.

Người 3 viết evaluator bằng hai tổng trực tiếp rồi so, không tái sử dụng phép đổi signed literals làm oracle. Có thể dùng chung resolver vùng.

## Ví dụ dễ kiểm tra bằng tay

Trên board 3x3: L=hàng 1={A1,B1,C1}, R={A1,C1}. Khi EQ, hai phía triệt tiêu A1/C1, còn `CB1=0`, nên B1 Innocent mà không đọc hidden solution.

- Cùng ví dụ với GT ép B1 Criminal.
- LT ở ví dụ này luôn false, vì L chứa R và số Criminal không âm.
- L=R: EQ luôn true, LT/GT luôn false.
- Hai vùng rỗng: EQ true; LT/GT false.
- Đổi trái/phải: EQ giữ nguyên; LT tương đương GT sau đổi.

## Gợi ý kiểm thử nếu chọn hai đề xuất này

- So truth của CNF với evaluator độc lập trên toàn bộ primary assignments ở board/vùng nhỏ.
- Nếu có aux, kiểm tra tồn tại assignment aux tương ứng, không chọn aux tùy ý rồi kết luận.
- Phủ EQ/LT/GT, vùng rời/giao/trùng/rỗng, kích thước khác nhau, ô biên và tham số lỗi.
- Regression: sáu core templates và PARITY vẫn giữ đúng ngữ nghĩa sau khi tổng quát hóa helper.
- Test COUNT_COMPARE ép được verdict qua entailment khi clue đang công khai; clue chưa reveal không được vào KB.

## Gợi ý khai thác chiều sâu nếu chọn COUNT_COMPARE

- Report: giải thích phép triệt tiêu vùng giao, signed literals, CNF, ví dụ và các biên.
- GUI: phân biệt hai vùng và ô giao; không lộ counts từ solution.
- Dataset: có case buộc sử dụng extension ở một bước suy luận; chỉ đổi nhãn clue mà không ảnh hưởng deduction chưa phải minh chứng tốt.
- Experiments: ghi số biến/clause và query cost của các case có extension. Không khẳng định extension luôn tăng độ khó hoặc cải thiện tốc độ; kết luận dựa trên số liệu nhóm tự chạy.
- So sánh cấu hình solver vẫn phải dùng cùng puzzle set. Không bỏ một clue để tạo một bài toán khác rồi trình bày như so sánh hiệu năng cùng bài toán.

Mẫu [examples/proposed_extensions_3x3.json](examples/proposed_extensions_3x3.json) chỉ minh họa hai đề xuất. Nó nằm trong docs, không thuộc schema core/dataset chạy chính và không bắt loader hỗ trợ các kind chưa chốt. Nếu chọn hướng khác, không cần dùng mẫu này.
