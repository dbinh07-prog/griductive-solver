# Người 4 — Tự thiết kế và code toàn bộ GUI

File chính: `main.py`, `app_controller.py`, `scenes/`, `ui/`, `assets/`, `requirements.txt`, `tests/test_gui.py`.

**Scaffold không có màn hình dựng sẵn.** `docs/GUI_PLAN.md` là đề xuất bố cục/chức năng; người 4 tự quyết định thiết kế chi tiết và triển khai.

## Làm song song

1. Chọn thư viện Python phù hợp, thử một cửa sổ rỗng, chốt dependency có phiên bản. Không cần 3D như Bloxorz.
2. Tự tạo PublicState/Analysis mock trong test để dựng board, evidence, inspector, trace. Không cần đọc secret JSON hoặc chờ engine thật.
3. Làm menu/chọn puzzle/tutorial và một màn bàn chơi chung cho manual/auto.
4. Input chỉ gửi cell ID, Status hoặc yêu cầu hint/step/restart/load cho controller/session; không tính luật trong view.
5. Ghép session/worker người 1; hiển thị loading, bỏ state cũ sau restart/load; không gọi SAT nặng trong render loop.
6. Sau khi controls và trạng thái đúng mới thêm flip/pulse/transition nhẹ.

## Phải thể hiện

Load, Restart, Hint, Auto Solve; chọn card/submit hai verdict; clue selection/highlight; tọa độ/tên/nghề/status/face-down rõ. Thông báo NOT_PROVABLE khác CONTRADICTED; UNKNOWN khác INCONSISTENT. Trace đủ dữ liệu, metrics đúng nghĩa. Pause/Next Step/inspector/export là bổ sung giúp demo.

## Nghiệm thu

Thử nhiều clue dài, card names dài, 3x3/4x4, cửa sổ laptop và scroll. Dùng nhãn/icon ngoài màu. Không lộ clue chưa mở qua hover/detail/animation/log. Không widget nào đọc Puzzle. Hint không tăng bước. Auto không chạy tiếp sau pause/terminal state. Hướng dẫn phím khớp code thật.

Giao người 5 ảnh minh họa, cách chơi và danh sách thao tác demo; hỗ trợ quay GUI nhưng người 5 dựng video. Viết phần GUI của report rồi giao người 5 tổng hợp.
