---
name: friday-report
description: Soạn báo cáo tiến độ thứ Sáu gửi thầy hướng dẫn cho đồ án FloodEye, dựa trên lịch trong ROADMAP, lịch sử git của tuần và kết quả trong docs/results. Dùng khi người dùng nói "viết báo cáo tuần", "báo cáo thứ Sáu", "chuẩn bị họp với thầy".
argument-hint: [ngày thứ Sáu, mặc định là thứ Sáu gần nhất sắp tới]
---

# Báo cáo thứ Sáu

Người đọc là thầy hướng dẫn: nắm đề tài, không theo dõi mã hằng ngày, đọc trong vài phút trước buổi họp. Viết bằng tiếng Việt, câu đầy đủ, không dùng tên hàm hay tên file khi một cụm từ thường diễn đạt được.

## Thu thập

1. Dòng của tuần này trong bảng mục 1.3 của `docs/ROADMAP.md`: các cột Code, Thí nghiệm, Gán nhãn, Viết, và cột "Báo cáo thứ Sáu" cho biết tuần này phải trình gì. Đọc thêm các khối "Cập nhật" ở mục 1.1 và bảng trạng thái ở mục 8 của `docs/TONG_QUAN.md`.
2. `git log --since=<thứ Sáu tuần trước> --stat`: việc đã làm thật.
3. Các file trong `docs/results/` thay đổi trong tuần: số liệu mới.
4. Mục 6 của ROADMAP: quyết định còn treo có hạn rơi vào tuần này hoặc đã quá hạn.
5. Hỏi người dùng những thứ không có trong kho: số khung đã gán nhãn, tiến độ viết chương, việc làm ngoài máy, ý kiến của thầy ở buổi trước.
6. Báo cáo trước trong `docs/reports/` (nếu có): việc hứa tuần trước mà tuần này chưa làm phải nhắc lại.

## Bố cục

1. **Tóm tắt**: hai ba câu. Tuần này đạt gì so với kế hoạch, và có trễ không.
2. **Đã làm**: đối chiếu từng cột của ROADMAP, ghi xong, xong một phần, hay chưa làm.
3. **Kết quả**: bảng số quan trọng nhất của tuần và điều nó cho thấy. Chỉ lấy số từ `docs/results/` hoặc `runs/`; mỗi bảng ghi tập dữ liệu và cấu hình.
4. **Vướng mắc và trễ hạn**: việc gì trễ, vì sao, và định cắt gì theo thứ tự cắt của ROADMAP.
5. **Cần thầy quyết**: từng câu hỏi kèm phương án đề xuất, để thầy chỉ cần đồng ý hoặc sửa.
6. **Tuần tới**: dòng kế tiếp của ROADMAP, đã chỉnh theo phần trễ.

## Quy tắc

- Việc chưa xong thì viết là chưa xong. Không viết "đang hoàn thiện" cho việc chưa bắt đầu.
- Không đưa số liệu ước lượng hay số chưa chạy ra. Kết quả "sơ bộ" hay "mô phỏng" trong `docs/results/` giữ nguyên nhãn đó khi đưa vào báo cáo.
- Dài không quá một trang; chi tiết thì dẫn tới file trong `docs/`.

Lưu vào `docs/reports/<YYYY-MM-DD>.md` theo ngày thứ Sáu, rồi đưa nội dung cho người dùng xem lại trước khi gửi.
