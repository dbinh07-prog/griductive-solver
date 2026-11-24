# Puzzle JSON v1

File minh họa core: `puzzles/examples/example_3x3.json`. Đây là mẫu format cho tích hợp, không phải bộ thực nghiệm cuối hoặc bằng chứng loader/solver đã chạy đúng. Schema extensions sẽ bổ sung sau khi Nhân lựa chọn; ví dụ trong docs chỉ là đề xuất.

Top-level: `schema_version=1`, `id`, `title`, `size`, `characters`, `solution`, `clues`, `initially_revealed`.

- `size`: 3 hoặc 4 cho bộ chính; 5 tùy chọn stress. Core có thể hỗ trợ 1/2 cho unit test.
- `characters`: danh sách đủ N*N phần tử `{cell,name,profession}` không trùng ô/tên; row-major, display names alphabet.
- `solution`: object đủ N*N ô, giá trị Boolean. Đây là private; không gửi cho agent/GUI.
- `clues`: object đủ N*N owner cell, mỗi owner có đúng một clue; clue ID không trùng.
- `initially_revealed`: ô hợp lệ, không trùng; khi chơi phải công khai cả status và clue của chúng.

## Clue

| kind | Trường | Ý nghĩa |
|---|---|---|
| FACT | `cells:[a]`, `status:true/false` | a Criminal/Innocent |
| SAME | `cells:[a,b]` | Hai status bằng nhau |
| DIFFERENT | `cells:[a,b]` | Hai status khác nhau |
| EXACTLY | `region`, `k` | Đúng k Criminal |
| AT_LEAST | `region`, `k` | Ít nhất k Criminal |
| AT_MOST | `region`, `k` | Nhiều nhất k Criminal |

Binary operands phải là hai ô khác nhau. Counting `k` là int, không nhận bool, thỏa `0≤k≤|R|`. Với vùng rỗng, k=0 hợp lệ: EXACTLY(0), AT_LEAST(0), AT_MOST(0) đều true. Không diễn giải clue theo status của chủ thẻ: **mọi clue đều đúng**.

FACT/SAME/DIFFERENT dùng `cells`, không dùng region. Ba clue đếm dùng `region` và `k`, không dùng `cells`. Field không liên quan trong dataclass giữ mặc định. Parser phải báo kind chưa hỗ trợ, không âm thầm bỏ qua.

## Extensions chưa chốt

Nhân tự chọn ít nhất hai loại khác nhau; trước khi đưa vào dataset cần chốt kind, trường dữ liệu, ngữ nghĩa/biên, validation, encoder và evaluator. PARITY/COUNT_COMPARE ở [EXTENSIONS.md](EXTENSIONS.md) chỉ là gợi ý, không thuộc các kind core bắt buộc trong bảng trên. File JSON đề xuất nằm riêng trong `docs/examples/`, không phải input mà loader core phải đọc được lúc này.

## Region

```json
{"kind":"ROW","index":2}
{"kind":"COLUMN","index":3}
{"kind":"NEIGHBORS","anchor":"B2"}
{"kind":"EXPLICIT","cells":["A1","C2"]}
```

Chỉ một object mỗi region; ví dụ trên minh họa bốn lựa chọn, không phải một file JSON hoàn chỉnh. ROW/COLUMN index một-based; COLUMN 3 là C. NEIGHBORS gồm ngang/dọc/chéo, bỏ chính anchor. EXPLICIT không trùng và không vượt board. Resolver trả thứ tự row-major ổn định.

## Ba cấp validation

1. Schema/coverage: không thiếu/trùng card, đúng kiểu và tham chiếu hợp lệ.
2. Ngữ nghĩa: từng clue đúng dưới solution khai báo; evaluator phải độc lập với encoder.
3. Dataset: đầy đủ clue có một nghiệm trên primary statuses và puzzle giải được theo progressive reveal từ tập mở ban đầu.

Unique không đồng nghĩa progressively solvable. Kiểm tra đầy đủ clue ở luồng offline; không đưa clue chưa mở vào KB để giúp Hint/Auto Solve.
