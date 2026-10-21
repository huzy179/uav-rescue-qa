# Hướng dẫn gán nhãn tập test lũ

Tập test lũ là tập chính để kết luận về cảnh lũ (mục 15.1 của [TECHNICAL.md](TECHNICAL.md)): 250–300 khung, khoá khoảng 4/11/2026. Tập nhỏ nên mỗi nhãn sai đều kéo lệch kết quả; ưu tiên nhất quán hơn tốc độ. Gặp trường hợp hướng dẫn này chưa nói tới thì dừng, quyết một lần, ghi thêm vào mục 6, rồi mới gán tiếp.

## 1. Chọn video và khung

- **Nguồn:** video UAV quay cảnh ngập lụt có người, nhìn từ trên xuống hoặc chếch. Độ phân giải từ 1080p trở lên. Lấy từ nhiều địa điểm và nhiều trận lũ khác nhau; không quá 30 khung từ một video.
- **Ghi nguồn:** mỗi video một dòng trong `data/raw/flood/sources.csv` gồm `video_id, url, ngày tải, độ phân giải, giấy phép hoặc ghi chú bản quyền`. Ảnh không phân phối lại; luận văn chỉ công bố nhãn và nguồn.
- **Lấy khung:** các khung cùng một video cách nhau ít nhất 2 giây và phải khác nhau rõ về khung cảnh. Khung liền nhau gần như giống hệt, không thêm thông tin mà làm khoảng tin cậy hẹp giả.
- **Giữ cả khung không có người** (nước, rác trôi, mái nhà): khoảng 10–20% tập, để đo báo động giả.
- **Tên file:** `<video_id>_<số khung 6 chữ số>.jpg`. Lưu khung ở chất lượng gốc, không thu nhỏ.
- Video dùng cho tập test không được dùng để huấn luyện hay chọn tham số.

## 2. Công cụ

CVAT, một dự án, hai nhãn dạng hình chữ nhật:

| Nhãn | Dùng cho | Thuộc tính (checkbox) |
|---|---|---|
| `person` | Một người | `partly_submerged`, `occluded` |
| `ignore` | Vùng không gán nhãn được | |

Thẻ theo ảnh (tag của CVAT): `glare`, `weather`, `blur`, `floating_debris`.

Xuất định dạng "CVAT for images 1.1" (XML), vì định dạng YOLO làm mất thuộc tính và thẻ. Chuyển sang YOLO bằng `tools/convert_cvat.py`: script báo lỗi nếu gặp nhãn, thuộc tính hoặc thẻ không có trong bảng trên (để lỗi đánh máy trong CVAT không lặng lẽ biến thành mất nhãn), và cảnh báo các khung có trong thư mục mà không có trong XML.

Lưu ý: file XML của CVAT liệt kê mọi ảnh của task, kể cả ảnh chưa ai mở. Ảnh không có box trong XML có thể là "đã xem, không có người" hoặc "chưa gán". Trước khi xuất để khoá, đánh dấu mọi job là hoàn thành trong CVAT.

## 3. Thế nào là một người

Gán `person` khi bạn chắc đó là người, kể cả khi chỉ thấy một phần:

- người lội, bơi, bám vào vật nổi, đứng trên mái nhà, ban công, ngồi trên thuyền hoặc xe;
- người rất nhỏ (vài pixel) nếu nhận ra được nhờ hình dáng, bóng, hoặc chuyển động ở các khung lân cận.

Không gán:

- bóng phản chiếu của người trên mặt nước, bóng đổ;
- người trong xe hoặc trong nhà mà không thấy cơ thể;
- hình người trên biển quảng cáo, ma-nơ-canh, bù nhìn.

Không chắc là người hay vật: vẽ `ignore` quanh vật đó, không gán `person`. Dự đoán rơi vào vùng `ignore` không bị tính đúng cũng không bị tính sai.

## 4. Vẽ box

- **Bao sát phần nhìn thấy được** của người. Không đoán phần chìm dưới nước hay phần bị che.
- Phóng to 300–400% khi vẽ người dưới 16 px. Lệch 1–2 px ở cỡ này đủ làm IoU tụt dưới ngưỡng.
- Vật người đang cầm hoặc bám (phao, can nhựa, sào) không nằm trong box, trừ phần đè lên cơ thể.
- Người bị mép ảnh cắt: bao phần còn trong ảnh.
- Hai người chồng lên nhau: mỗi người một box nếu tách được. Đám đông không tách được từng người: một vùng `ignore` phủ cả đám.

## 5. Thuộc tính và thẻ

| Tên | Mức | Đánh dấu khi |
|---|---|---|
| `partly_submerged` | box | Nước che từ đầu gối trở lên |
| `occluded` | box | Vật khác (cây, mái, thuyền, người khác) che từ khoảng một phần ba cơ thể |
| `glare` | ảnh | Có vùng lóa nắng trên mặt nước đủ lớn để che được một người |
| `weather` | ảnh | Mưa, sương mù, hoặc trời tối làm giảm tương phản rõ rệt |
| `blur` | ảnh | Nhòe do chuyển động hoặc mất nét, mép vật không còn sắc |
| `floating_debris` | ảnh | Có rác, bèo, đồ vật trôi cỡ tương đương một người |

Phân vân giữa có và không thì chọn không: thẻ chỉ có ích khi nó tách ra các trường hợp rõ ràng.

## 6. Các quyết định bổ sung

Ghi vào đây mỗi trường hợp mới gặp và cách đã xử lý, kèm ngày, để các khung sau làm giống hệt.

| Ngày | Trường hợp | Quyết định |
|---|---|---|
| | | |

## 7. Kiểm tra chất lượng

- Sau mỗi 50 khung, xem lại toàn bộ ở mức phóng 100% để tìm người bị sót; người sót thường nằm ở mép ảnh và vùng lóa.
- Một tuần sau khi gán 50 khung đầu, gán lại 20 khung trong số đó mà không nhìn nhãn cũ, rồi so sánh. Lệch nhiều (số người khác nhau, hoặc box lệch quá 2 px ở người nhỏ) thì sửa hướng dẫn và rà lại cả lô.
- Trước khi khoá: mọi khung có nhãn hoặc được xác nhận là không có người; mọi video có dòng trong `sources.csv`.

## 8. Khoá tập

Khi đủ số khung và đã rà xong, tạo `MANIFEST.sha256` cho toàn bộ ảnh và nhãn. Từ lúc đó không sửa nhãn, không thêm bớt khung. Phát hiện nhãn sai sau khi khoá thì ghi vào phần giới hạn của luận văn, không sửa lặng lẽ.

## 9. Mốc

| Hạn | Số khung cộng dồn |
|---|---|
| 16/10 | 50 |
| 23/10 | 100 |
| 30/10 | 200 |
| 4/11 | 250–300, khoá |
