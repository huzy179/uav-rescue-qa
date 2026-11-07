# Chương 2. Cơ sở lý thuyết và nghiên cứu liên quan

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Nháp 8/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 2. Trích dẫn dùng mã trong `docs/luan_van/tai_lieu_tham_khao.md`, nơi ghi tên, tác giả, năm, nơi công bố đã tra 7/11. Mã có dấu **[TRA]** (TensorRT, Blackman, Bar-Shalom) là tài liệu chưa tra lại (đang dựa trên trí nhớ trong `docs/THUAT_TOAN.md` mục 7): phải tra trước khi nộp. Khẳng định về nội dung một bài mà mới đọc tóm tắt được đánh **[ĐỌC TOÀN VĂN]**. Mục 2.6 (khoảng trống nghiên cứu) phụ thuộc quyết định #19 (ROADMAP), viết theo đề xuất hiện tại. Thuật ngữ theo `docs/THUAT_NGU.md`; lần đầu gặp mỗi thuật ngữ ghi kèm tiếng Anh.

Chương này trình bày nền tảng của các khâu trong hệ thống và vị trí của luận văn so với các nghiên cứu đã có: phát hiện đối tượng và họ mô hình YOLO (2.1), phát hiện vật nhỏ (2.2), dữ liệu ảnh từ UAV cho tìm kiếm cứu nạn (2.3), theo dõi đối tượng qua nhiều khung (2.4), nén mô hình cho thiết bị biên (2.5), và khoảng trống mà luận văn nhắm tới (2.6).

## 2.1. Phát hiện đối tượng và YOLO26

### 2.1.1. Bài toán và cách đo

Phát hiện đối tượng (object detection) là tìm mọi đối tượng thuộc các lớp quan tâm trong ảnh, mỗi đối tượng cho một hộp bao (bounding box, gọi tắt là box) và một điểm tin cậy (confidence score, conf). Một box dự đoán được coi là đúng nếu độ chồng lấn với một box nhãn, đo bằng IoU (intersection over union, phần giao chia phần hợp), vượt một ngưỡng, thường là 0,5. Chất lượng một mô hình thường được tóm bằng AP (average precision): diện tích dưới đường precision theo recall khi quét ngưỡng conf từ cao xuống thấp; AP50 là AP ở ngưỡng IoU 0,5. Luận văn dùng thêm recall và precision ở một ngưỡng conf cố định (0,25) làm điểm vận hành, vì trong cứu hộ điều quan trọng là bao nhiêu người được tìm thấy ở ngưỡng hệ thống thật sự dùng (chương 4, mục 4.3).

Với người rất nhỏ, IoU khắc nghiệt: một box lệch 2 px quanh người 8 px có IoU chỉ khoảng 0,6, lệch 3 px đã dưới 0,5, trong khi chính người gán nhãn khó đặt box chính xác tới 1–2 px. Vì vậy luận văn báo thêm kết quả ở IoU 0,3 cho người dưới 8 px.

### 2.1.2. Bộ phát hiện một giai đoạn và họ YOLO

Các bộ phát hiện một giai đoạn (one-stage) dự đoán box và lớp trực tiếp trên lưới đặc trưng, không qua bước đề xuất vùng riêng; họ YOLO [YOLO] là đại diện được dùng rộng rãi nhất cho phát hiện thời gian thực, với công cụ xuất sang các định dạng triển khai như TensorRT. Một bộ phát hiện hiện đại gồm ba phần:

- **Backbone** trích đặc trưng và giảm dần độ phân giải qua các tầng P1, P2, P3, P4, P5, với bước nhảy (stride) 2, 4, 8, 16, 32 pixel ảnh vào;
- **Neck** trộn đặc trưng nhiều tầng, theo kiểu kim tự tháp đặc trưng (FPN) [FPN] cộng đường đi xuống (PAN), để tầng mịn có thêm ngữ nghĩa và tầng thô có thêm chi tiết;
- **Head** dự đoán box và lớp trên từng tầng.

Đầu ra thông thường gồm nhiều box chồng nhau cho cùng một đối tượng, nên cần bước loại bỏ box trùng (non-maximum suppression, NMS) ở cuối.

**YOLO26** [YOLO26] là thế hệ YOLO của Ultralytics phát hành tháng 1/2026, được luận văn dùng làm mô hình nền (bản `s`, khoảng 10 triệu tham số). Hai điểm liên quan tới luận văn: (i) ngoài đầu dự đoán một-nhiều cần NMS, YOLO26 có thêm đầu **một-một** cho kết quả cuối không cần NMS; theo tài liệu và mã của thư viện, mặc định khi dự đoán và khi xuất vẫn dùng đầu một-nhiều kèm NMS, và luận văn dùng mặc định này cho mọi kết quả; (ii) tầng phát hiện mịn nhất là P3 (stride 8). Ultralytics giới thiệu thêm các thay đổi về hàm mất mát và cách gán nhãn được nói là có lợi cho vật nhỏ; luận văn không kiểm chứng tuyên bố này (thí nghiệm đối chứng với YOLO11 bị cắt vì lịch).

### 2.1.3. Vì sao người nhỏ bị mất

Ba cơ chế cùng làm mô hình bỏ sót người vài pixel:

1. **Lấy mẫu xuống.** Ở tầng P3, mỗi ô của bản đồ đặc trưng ứng với vùng 8 × 8 pixel ảnh vào; người 4 px chỉ chiếm nửa ô và đặc trưng của họ bị trộn với nền.
2. **Thu ảnh trước khi vào mạng.** Mô hình thu ảnh để cạnh dài bằng cỡ đầu vào (thường 640 px). Với video 4K, người bị thu nhỏ đi sáu lần (chương 1, Bảng 1.1).
3. **Tín hiệu học yếu.** Box rất nhỏ có rất ít ô "dương" khi gán nhãn huấn luyện, và tăng cường dữ liệu bằng thu nhỏ ảnh còn xoá nhãn của box dưới 2 px trong khi người vẫn còn trong ảnh (TECHNICAL mục 13.4).

Các mục 2.2 và chương 3 lần lượt xét các cách chống lại từng cơ chế.

## 2.2. Phát hiện vật nhỏ

**Tăng độ phân giải đầu vào.** Cách trực tiếp nhất là đưa ảnh vào mạng ở cỡ lớn hơn (1280 thay vì 640 px). Chi phí tính tăng theo bình phương cạnh ảnh.

**Cắt ô (tiling, slicing).** Chia ảnh lớn thành các ô chồng nhau, phát hiện trên từng ô ở độ phân giải gốc, rồi ghép kết quả. SAHI [SAHI] đóng gói cách làm này thành thư viện dùng được với nhiều bộ phát hiện, cho cả lúc suy luận và lúc tinh chỉnh; trên VisDrone và xView, các tác giả báo AP tăng đáng kể với ba bộ phát hiện khác nhau [ĐỌC TOÀN VĂN để chép số]. Mặc định SAHI còn chạy thêm một lượt trên toàn ảnh để bắt vật to bị cắt đôi giữa các ô, và ghép box giữa các ô bằng cách hợp nhất toạ độ. SAHI chạy mô hình lần lượt từng ô; luận văn viết một bộ cắt ô riêng chạy mọi ô trong một lô để hợp với GPU và với xuất TensorRT (chương 3, mục 3.3).

**Thêm tầng phát hiện mịn hơn.** Thêm đầu dự đoán ở tầng P2 (stride 4) để người 8 px chiếm 2 × 2 ô thay vì một ô, đổi lại tốn thêm tính toán ở neck và head và phải huấn luyện lại phần mới. Luận văn đã thử (chương 5, mục 5.1.3).

**Khớp thang kích thước.** TinyPerson [TinyPerson] chỉ ra rằng chênh lệch thang kích thước vật giữa dữ liệu học trước và dữ liệu phát hiện làm đặc trưng kém đi, và đề xuất co giãn dữ liệu học trước cho khớp thang của dữ liệu đích (Scale Match). Ý chung là: mô hình làm tốt nhất ở khoảng cỡ vật nó đã học.

**Đổi cỡ ảnh theo độ cao bay.** Với ảnh UAV, cỡ vật phụ thuộc chủ yếu vào độ cao chụp. Messmer và cộng sự [AdaptiveResize] đổi cỡ từng ảnh UAV theo độ cao chụp trước khi phát hiện (Adaptive Resizing), báo độ chính xác tăng trên UAVDT và VisDrone và suy luận nhanh hơn hai đến ba lần [ĐỌC TOÀN VĂN: cách tính hệ số, nguồn độ cao]. Ahmed và Pizarro [AltTiling] kết hợp thu nhỏ theo độ cao với số ô thay đổi theo độ cao, đánh giá trên SeaDronesSee với YOLOv5 và SAHI, báo AP của vật nhỏ tăng và tốc độ hơn gấp đôi so với cắt ô cố định [ĐỌC TOÀN VĂN]. Bước thu nhỏ theo độ cao ở chương 3 thuộc cùng hướng này; khác biệt và phần luận văn thêm vào được nêu ở mục 2.6.

## 2.3. Ảnh UAV và dữ liệu cho tìm kiếm cứu nạn

**Dữ liệu ảnh UAV tổng quát.** VisDrone [VisDrone] là bộ dữ liệu UAV lớn, chụp ở nhiều thành phố, có nhãn cho phát hiện ảnh, phát hiện video, theo dõi một và nhiều đối tượng; người trong VisDrone phần lớn rất nhỏ (chương 4, Bảng 4.2), nên nó là nguồn chính để học người nhỏ nhìn từ trên cao. Đổi lại, VisDrone là cảnh đô thị khô, không có nước.

**Người dưới nước.** SeaDronesSee [SeaDronesSee] là bộ dữ liệu UAV lớn đầu tiên về người bơi ngoài biển, gồm phần phát hiện, theo dõi một và nhiều đối tượng, chụp ở nhiều độ cao và góc nhìn, kèm metadata bay (vị trí, độ cao, góc camera). AFO [AFO] gồm người và vật nổi (ván, thuyền, phao) trên mặt nước nhìn từ drone, dựng cho cứu nạn trên nước.

**Thảm hoạ.** C2A [C2A] ghép hình người vào ảnh thảm hoạ thật chụp từ UAV, để có dữ liệu người bị che khuất trong đống đổ nát, nước lũ; các tác giả báo mô hình học thêm C2A tốt hơn trên cảnh thảm hoạ, nhất là khi kết hợp với dữ liệu người tổng quát.

**Tổng quan.** Các bài tổng quan về phát hiện người từ trên không cho tìm kiếm cứu nạn [SARSurvey] và riêng cho cứu nạn trên biển [MaritimeSurvey] điểm qua các phương pháp truyền thống, học sâu, dữ liệu thật và tổng hợp. [ĐỌC TOÀN VĂN để rút hai ba nhận định về khoảng trống, ví dụ thiếu dữ liệu lũ, ít đánh giá trên thiết bị biên.]

**Khoảng trống về dữ liệu.** Theo các nguồn đã rà khi chuẩn bị luận văn (Kaggle, Hugging Face, Zenodo, Roboflow), chưa có bộ dữ liệu công khai nào gồm ảnh UAV chụp lũ thật có nhãn người đủ để đánh giá. Đây là lý do luận văn tự gán nhãn một tập ảnh lũ nhỏ chỉ để đánh giá (chương 4, mục 4.2.2), và học trên tổ hợp các bộ công khai ở trên.

## 2.4. Theo dõi đối tượng qua nhiều khung

**Theo dõi bằng phát hiện.** Các phương pháp theo dõi nhiều đối tượng phổ biến hiện nay ghép phát hiện của khung mới với các track đang có. ByteTrack [ByteTrack] ghép theo độ chồng lấn box giữa vị trí dự đoán (bằng bộ lọc Kalman) và phát hiện mới, qua hai vòng: box điểm cao trước, rồi box điểm thấp, để không bỏ phát hiện bị che khuất. Các phương pháp này được thiết kế và đánh giá trên video người đi bộ ở tần số khung đầy đủ (MOT17, MOT20), khi một người chỉ dịch vài pixel giữa hai khung.

**Bù chuyển động camera.** Khi camera chuyển động, vị trí của mọi đối tượng trên ảnh trôi theo camera. BoT-SORT [BoT-SORT] ước lượng chuyển động camera giữa hai khung từ chính ảnh rồi dời các track trước khi ghép. Trên UAV có thể tính phép dời này từ telemetry thay vì từ ảnh (chương 3, mục 3.6.1).

**Định vị và ghép theo toạ độ thế giới.** Đổi vị trí phát hiện trên ảnh sang toạ độ mặt đất bằng mô hình camera lỗ kim và vị trí, hướng của camera là kỹ thuật hình học cơ bản [HZ]. Rudol và Doherty [Rudol08] đã định vị người phát hiện từ UAV (ảnh màu và ảnh nhiệt) lên bản đồ cho tìm kiếm cứu nạn. Gần đây, Wang và cộng sự [MIDDTD] đổi phát hiện từ drone sang toạ độ thế giới bằng tham số bay (GPS, độ cao, góc gimbal) rồi ghép giữa các khung, và báo giảm số lần đổi mã track khi theo dõi xe [ĐỌC TOÀN VĂN: tần số khung, cách ghép]. Luật xác nhận một mục tiêu khi nó được thấy M lần trong N lần quét là luật kinh điển trong theo dõi mục tiêu bằng radar [Blackman, Bar-Shalom, TRA].

## 2.5. Thiết bị biên và nén mô hình

**Thiết bị biên.** Máy tính nhúng gắn được trên UAV, như dòng NVIDIA Jetson, có GPU nhỏ và chạy ở vài chục watt trở xuống; tốc độ phụ thuộc chế độ công suất và giảm khi máy nóng. Đo tốc độ đúng cách trên thiết bị cần khoá chế độ công suất, bỏ các lần chạy đầu, đo đủ lâu và báo phân vị (p50, p95) chứ không chỉ trung bình (TECHNICAL mục 14.2).

**TensorRT và lượng tử hoá.** TensorRT [TensorRT, TRA] biên dịch mô hình thành engine cho đúng một loại GPU: gộp lớp, chọn kernel nhanh nhất, và giảm độ chính xác số. FP16 (số thực 16 bit) thường gần như không mất độ chính xác; INT8 (số nguyên 8 bit) nhanh hơn nữa nhưng cần dữ liệu hiệu chỉnh để đo dải giá trị kích hoạt, và có thể làm hại vật nhỏ nhiều nhất vì tín hiệu yếu bị lượng tử hoá thô. Engine không mang sang thiết bị khác được: engine xây trên GPU T4 không chạy trên Jetson. Trong lúc làm luận văn, TensorRT 11 đổi cách lượng tử hoá INT8 (chỉ còn dạng lượng tử hoá tường minh) và bước xuất INT8 không build được trên T4; luận văn dùng TensorRT 10 (chương 4, mục 4.5).

**Đo khi không có thiết bị.** Khi không có thiết bị đích, các công bố thường báo tốc độ trên GPU khác và chỉ so sánh tương đối, hoặc dẫn bảng benchmark của nhà phát triển. Luận văn làm cả hai và thêm một bước giả lập thời gian thiết bị (chương 3, mục 3.8.3), ghi rõ là ước lượng.

## 2.6. Khoảng trống nghiên cứu

[Viết theo đề xuất của quyết định #19, chờ cô duyệt và chờ đọc toàn văn ba bài [AdaptiveResize], [AltTiling], [MIDDTD].]

Từ các mục trên, ba khoảng trống mà luận văn nhắm tới:

1. **Chưa có đánh giá phát hiện người theo cỡ người trong cảnh lũ chụp từ UAV.** Các bộ dữ liệu cứu nạn hiện có là cảnh đô thị, biển, hoặc thảm hoạ có ghép người; chưa có tập ảnh lũ thật có nhãn người, và kết quả thường báo theo AP chung chứ không theo cỡ người, trong khi bỏ sót tập trung ở người vài pixel.
2. **Xác nhận người khi chỉ xử lý vài khung mỗi giây.** Các phương pháp theo dõi thông dụng được thiết kế cho tần số khung đầy đủ. Trên thiết bị biên chỉ xử lý được vài khung mỗi giây, khi UAV bay nhanh, một người dịch hàng trăm pixel giữa hai khung xử lý; ghép theo toạ độ thế giới đã được dùng cho theo dõi xe, nhưng chưa thấy công trình nào đo nó so với ghép trên ảnh ở tần số thấp như vậy, cho bài toán xác nhận người trước khi cảnh báo cứu nạn.
3. **Dùng dữ liệu bay ở nhiều khâu trong cùng một hệ thống trên thiết bị biên.** Đổi cỡ ảnh theo độ cao đã được đề xuất và đo cho độ chính xác và tốc độ phát hiện; luận văn đặt nó trong một pipeline chạy theo telemetry từng khung, đo cùng lúc tác dụng lên độ chính xác theo cỡ người và lên số ô phải tính trên thiết bị yếu, cạnh việc dùng chính telemetry đó để định vị và xác nhận.
