# Dataset — người 3

`examples/example_3x3.json` chỉ minh họa schema v1 với chuỗi FACT đơn giản. Nó không thay thế dataset đa dạng hoặc kiểm thử tất cả clue/region. Nhóm tự triển khai loader/validator và xác nhận bằng chương trình của mình.

Nhân tự chọn ít nhất hai extensions; dataset cho chúng sẽ xây dựng sau khi thống nhất schema/ngữ nghĩa. Mẫu PARITY/COUNT_COMPARE đã để riêng tại `docs/examples/proposed_extensions_3x3.json` để tham khảo, không nằm trong bộ puzzle core và không bắt buộc phải chọn hoặc sử dụng.

`benchmark/` hiện trống. Người 3 thêm nhiều puzzle 3x3/4x4, phủ core/extension/regions và có độ khó khác nhau. Thêm 5x5 nếu có thời gian. Tách ca negative (multiple/inconsistent/unique-but-stalled) sang fixtures test, ghi kết quả mong đợi riêng.

Không thêm CNF viết tay theo puzzle. Không nhập hidden solution vào public state để giúp solver. Chi tiết schema ở `docs/DATA_FORMAT.md`.
