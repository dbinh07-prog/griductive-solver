# Chức năng và bố cục đề xuất — người 4 tự thiết kế/code

Tài liệu này chỉ chốt thông tin/hành vi cần hiển thị. **Không có GUI triển khai sẵn**, không bắt buộc pixel, font hay thư viện cụ thể. Người 4 có thể chọn Pygame hoặc framework Python phù hợp, rồi ghi phiên bản trong requirements.

## Các màn

1. Menu ngắn: Play, Tutorial, Exit.
2. Chọn puzzle: tên, kích thước, mức khó do nhóm tự quy ước; Load JSON.
3. Bàn chơi và suy luận: một màn chung cho chơi tay, Hint, Step và Auto Solve để dễ so hành vi.
4. Kết quả: solved/unknown/inconsistent/error riêng, số bước và chỉ số; không hiện hidden labels để xử lý stalled.

## Bố cục màn chính

```text
┌────────────────── Tên puzzle / kích thước / trạng thái ──────────────────┐
│ Load  Restart   Hint   Next Step   Auto Solve/Pause   Tốc độ   Tutorial  │
├───────────────────┬───────────────────────────┬─────────────────────────┤
│ Clue công khai    │ Board giữa màn            │ Nhân vật đang chọn      │
│ ID / chủ thẻ      │ Tọa độ hàng/cột            │ Tên, nghề, status       │
│ Nội dung dễ đọc   │ Tên + nghề trên mỗi card   │ Clue nếu đã mở          │
│ Chọn → highlight  │ Mặt úp / đã mở phân biệt   │ Criminal / Innocent     │
│ Cuộn khi nhiều    │ Viền vùng clue được chọn  │ Lý do accept/reject     │
├───────────────────┴───────────────────────────┴─────────────────────────┤
│ Tabs: Deduction Trace | Public KB + SAT queries | Metrics               │
│ Status: tiến độ, lỗi, UNKNOWN/INCONSISTENT      Export trace / CNF      │
└────────────────────────────────────────────────────────────────────────┘
```

Phong cách gợi ý: bàn hồ sơ điều tra 2D, nền sáng dịu, chữ tối, một màu nhấn. Innocent xanh, Criminal đỏ nhưng **luôn có chữ/icon**; không dựa riêng vào màu. Ô đang chọn và vùng được clue nhắc phải có hai kiểu viền khác nhau.

## Phải nhìn thấy rõ

- Card luôn có tọa độ, tên và nghề. Face-down không có clue/status ẩn; đã mở thể hiện status và có cách đọc clue ngay trên card hoặc evidence panel.
- Board 3x3/4x4 đọc được ở cửa sổ laptop; 5x5 nếu làm phải có scaling/zoom hoặc card gọn + detail panel. Không thu chữ đến mức không đọc được.
- Evidence panel hiển thị **mọi clue đã mở**, có scroll; highlight khớp `referenced_cells` cho sáu core và các extensions Nhân thực sự chọn.
- Extensions hiện gồm PARITY và COUNT_COMPARE. Text COUNT_COMPARE ghi riêng hai vùng; board highlight hợp hai vùng. Tô màu riêng hai vế/ô giao là cải tiến hiển thị còn có thể bổ sung. Không hiện thông tin bí mật từ solution để minh họa clue.
- Chọn thẻ chưa mở → hiện nút Criminal/Innocent; người chơi tự quyết định. Không tự bật verdict chỉ vì đáp án private nói đúng.
- NOT_PROVABLE: chưa có bằng chứng ép verdict. CONTRADICTED: đã chứng minh opposite. Hai thông báo khác nhau; card không flip.
- Hint chọn được một forced character, không thêm status/clue. Nếu chưa có forced move thì nói thiếu dữ kiện.
- Auto Solve cho thấy từng verdict → flip → thêm clue → cập nhật KB. Có Pause; dừng ở solved/UNKNOWN/INCONSISTENT/timeout/error.
- Trace bấm từng bước xem active clue IDs và assumptions/SAT/UNSAT thật. Nếu xem trace lịch sử phải dùng dữ liệu của bước đó, không gắn số liệu KB hiện tại vào bước cũ.
- Metrics hiển thị primary/aux/clause count, SAT calls, decisions/propagations/backtracks, steps, runtime; không có thì dùng “chưa có”, không bịa 0.
- Uniqueness của complete clue set nằm ở diagnostic offline, không dùng nhãn đó để nói public state hiện tại chỉ có một nghiệm.

## API view dự kiến

- `BoardView.render(surface, public_state, selected_cell, highlighted_cells)`; callback chọn ô trả cell ID. Tham số riêng cho extensions sẽ chốt sau khi Nhân lựa chọn.
- `EvidencePanel.render(surface, public_state, selected_clue_id)`; callback trả clue ID.
- `InspectorPanel.render(surface, public_state, analysis, selected_cell)`; callback submit trả `(cell, Status)`.
- `TracePanel.render(surface, entries)`; callback chọn bước chỉ xem lại dữ liệu công khai.
- `AppController` gọi session/worker, không chứa thuật toán SAT hay tự sửa trạng thái engine.

Framework có cơ chế render khác thì người 4 đổi phần view nội bộ cho phù hợp, giữ nguyên dữ liệu và hành vi public. Asset chỉ dùng khi có nguồn/quyền sử dụng rõ; thêm nguồn vào report. Không cần avatar/âm thanh để đạt yêu cầu cốt lõi.

## Kiểm tra trước khi ghép

Dùng PublicState/Analysis tự tạo trong test, không gọi solver hay loader thật. Thử số clue dài, tên dài, các terminal states và cửa sổ nhỏ; chụp minh chứng sau khi tự code. Không đọc secret để làm dữ liệu mock.
