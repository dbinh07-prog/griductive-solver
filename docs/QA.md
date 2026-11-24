# Kiểm thử thủ công — người 5

Chưa có test thực tế; bảng dưới là kế hoạch để dùng sau khi nhóm tự code.

| ID | Thao tác | Kết quả cần có |
|---|---|---|
| Q01 | Load puzzle 3x3/4x4 | Đủ grid, tọa độ, tên/nghề; chỉ card ban đầu có status và clue |
| Q02 | Chọn clue hàng/cột/neighbors/list | Highlight đúng ô; neighbors bỏ anchor và có đường chéo |
| Q03 | Submit một verdict forced | ACCEPTED, đúng status, mở clue mới; trace tăng một bước |
| Q04 | Submit opposite của verdict forced | CONTRADICTED; không đổi state, không mở clue |
| Q05 | Submit một verdict chưa forced | NOT_PROVABLE, kể cả tình cờ trùng đáp án private; không mở clue |
| Q06 | Hint | Chỉ ra forced character; không mở card và không tăng deduction steps |
| Q07 | Auto Solve rồi Pause | Hiện từng bước; pause ngừng bước tiếp theo, không reveal thêm sau pause |
| Q08 | Auto Solve thiếu dữ kiện | UNKNOWN, không đoán, không ghi solved |
| Q09 | Trạng thái mâu thuẫn | INCONSISTENT, dừng, không nhận verdict |
| Q10 | Restart khi đang phân tích | Về initial state; trace/metrics reset; không nhận kết quả worker cũ |
| Q11 | Load puzzle khác khi worker chạy | Worker cũ không làm đổi puzzle mới |
| Q12 | Chọn từng bước trace | Thấy step, clue IDs trước reveal, SAT assumptions/results, verdict, clue vừa mở |
| Q13 | Clue dài/nhiều, tên dài, cửa sổ nhỏ | Cuộn/resize hợp lý; không mất nút, chữ không chồng nhau |
| Q14 | Kiểm tra ít nhất hai extensions Nhân đã chọn | Nội dung/highlight đúng ngữ nghĩa đã thống nhất; không lộ hidden data; checklist chi tiết bổ sung khi chốt |
| Q15 | Export trace/public CNF nếu nhóm làm | Dữ liệu mở đúng; không có secret chưa reveal |
| Q16 | File JSON lỗi và timeout | Báo lỗi rõ; không crash, không đổi thành UNSAT hay reveal |
| Q17 | Tutorial, phím tắt nếu có | Hướng dẫn khớp bản thật, names/professions không tạo luật ngầm |

## Ghi lỗi

```text
Mã lỗi:
Ngày / người thử / phiên bản commit:
Puzzle và revision:
Các bước tái hiện:
Kết quả thực tế:
Kết quả mong đợi:
Ảnh hoặc trace kèm theo:
Người phụ trách sửa:
Đã thử lại trên commit nào:
```

Không điền “pass” trước khi thử. Test thuật toán, encoder và benchmark thuộc người code; người 5 không bị giao chạy script hay tự giải thích kết quả SAT phức tạp.
