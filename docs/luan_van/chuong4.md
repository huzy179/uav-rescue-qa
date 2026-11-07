# Chương 4. Dữ liệu và thiết lập thí nghiệm

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Nháp 7/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 4. Mọi số liệu lấy từ: `data/processed/*/stats*.json`, `docs/results/` (`flood_truoc_khoa.md`, `sds_det.md`, `afo_E1_E2.md`, `E2c.md`, `E2e.md`, `visdrone_tiled_vs_sahi.md`, `rq3_*.md`), `docs/LABELING.md`, `docs/TECHNICAL.md` mục 5, 13, 14, 15, 16. Chỗ đánh dấu **[CHỜ KHOÁ]** điền sau khi khoá tập ảnh lũ (11/11): số người, phân bố cỡ người, số khung không có người, độ nhất quán khi gán lại, mã băm. Thuật ngữ theo `docs/THUAT_NGU.md`. Số hình, số bảng đánh lại khi dàn trang.

Chương này mô tả dữ liệu dùng để huấn luyện và đánh giá, cách đo, các thí nghiệm trả lời ba câu hỏi nghiên cứu, và môi trường chạy. Mục tiêu là để mọi con số ở chương 5 có thể được hiểu đúng và tái lập được: nó đo trên tập nào, theo định nghĩa nào, với cấu hình nào.

## 4.1. Dữ liệu huấn luyện

### 4.1.1. Các bộ dữ liệu công khai

Chưa có bộ ảnh lũ nhìn từ UAV nào được công bố kèm nhãn người đủ lớn để huấn luyện. Luận văn vì vậy kết hợp các bộ dữ liệu công khai, mỗi bộ bù một mặt mà cảnh lũ cần: người rất nhỏ nhìn từ trên cao, người dưới nước, và người cỡ to trên nền thảm hoạ (Bảng 4.1).

**Bảng 4.1.** Dữ liệu huấn luyện sau khi chuyển về một lớp người.

| Bộ dữ liệu | Bối cảnh | Phần dùng để huấn luyện | Vai trò |
|---|---|---|---|
| VisDrone2019-DET | Ảnh UAV đô thị, nhiều người rất nhỏ; không có nước | 6.471 ảnh, 106.396 người | Học người nhỏ nhìn từ trên cao |
| AFO (Aerial dataset of Floating Objects) | Người bơi, ván, thuyền trên hồ và biển, nhìn từ drone | 2.787 ảnh, 22.272 người | Học người dưới nước |
| C2A | Ảnh thảm hoạ thật (lũ, cháy, nhà sập) có ghép thêm hình người | 6.129 ảnh, 215.821 người | Thí nghiệm thêm người cỡ to (chỉ huấn luyện) |
| HydroVigilance | Người bơi nhô đầu trên sông nước đục | 627 ảnh train, 179 ảnh val | Có cấu hình, chưa dùng trong mô hình chính |

Tập kiểm định dùng trong lúc huấn luyện (để chọn trọng số tốt nhất) là VisDrone val cộng AFO val: 887 ảnh.

### 4.1.2. Chuyển về một lớp "người"

Đề tài chỉ cần biết có người hay không, nên mọi bộ được chuyển về một lớp duy nhất theo định dạng YOLO. VisDrone tách người đứng hoặc đi (`pedestrian`) và người ngồi hoặc nằm (`people`); cả hai đều là người cần cứu nên được gộp. Người đi xe đạp, xe máy bị VisDrone gán vào lớp phương tiện nên không có trong dữ liệu; đây là một giới hạn được ghi nhận. Các vùng VisDrone đánh dấu là không gán nhãn được (`ignored regions`, đám đông, vùng mờ) được giữ làm **vùng bỏ qua** (ignore region): phát hiện rơi vào đó không bị tính đúng cũng không bị tính sai.

Lớp người được chọn **theo tên** chứ không theo mã số, vì mỗi bộ đánh số lớp khác nhau (AFO có sáu lớp: người, ván, thuyền, phao, thuyền buồm, kayak); chọn sai mã số thì mô hình học nhầm lớp mà không có lỗi nào báo. Sau khi chuyển, nhãn VisDrone được kiểm tra lại với nhãn gốc trên từng ảnh trước khi huấn luyện, vì phát hiện lỗi nhãn sau khi huấn luyện là mất cả một lần chạy nhiều giờ GPU.

### 4.1.3. Phân bố cỡ người

Cỡ người được tính theo **cạnh ngắn** của hộp bao (box), chia bốn nhóm: dưới 8 px, 8–16 px, 16–32 px và trên 32 px. Cách chia này mịn hơn chuẩn COCO (ở COCO "nhỏ" là mọi vật dưới 32 × 32 px), vì người trong ảnh lũ chụp từ UAV phần lớn rơi vào nhóm COCO gọi chung là nhỏ (chương 1, bảng số pixel theo độ cao).

**Bảng 4.2.** Số người theo nhóm cỡ trong VisDrone.

| Phần | Ảnh | Người | < 8 px | 8–16 px | 16–32 px | > 32 px |
|---|---|---|---|---|---|---|
| train | 6.471 | 106.396 | 22.952 | 43.596 | 31.001 | 8.847 |
| val | 548 | 13.969 | 3.306 | 6.364 | 3.793 | 506 |
| test-dev | 1.610 | 27.382 | 12.088 | 9.868 | 4.339 | 1.087 |

Ngược lại, người trong AFO và SeaDronesSee phần lớn trên 32 px (mục 4.2.1). C2A có ảnh nhỏ (cạnh dài khoảng 430 px) nên khi huấn luyện ở 1280 px ảnh bị phóng to khoảng ba lần, làm người trong C2A "to" hơn người VisDrone.

## 4.2. Dữ liệu đánh giá

### 4.2.1. Các tập đánh giá công khai

**Bảng 4.3.** Tập đánh giá công khai.

| Tập | Ảnh | Người | Đặc điểm | Dùng để |
|---|---|---|---|---|
| VisDrone val | 548 | 13.969 | Đô thị, người rất nhỏ; 76 video | Đối chiếu với các nghiên cứu khác; trọng số được chọn theo tập này nên có thiên vị |
| VisDrone test-dev | 1.610 | 27.382 | Như trên, không dùng để chọn trọng số | Bảng chính cho người nhỏ |
| AFO test | 514 | 6.511 | Người dưới nước; ảnh 1280 × 720 tới 3840 × 2160 | Người dưới nước, cùng nguồn với phần huấn luyện |
| AFO test, bỏ ảnh chung địa điểm | 363 | | Bỏ hai nhóm ảnh có cảnh chung với phần huấn luyện | Kiểm tra mức tăng có do trùng cảnh hay không |
| SeaDronesSee val (bản phát hiện) | 317 | 1.055 | 11 video 4K người bơi trên biển; cạnh ngắn trung vị 65 px; 976 người trên 32 px | Người dưới nước, **độc lập** với dữ liệu huấn luyện; người cỡ to |

Với SeaDronesSee, mỗi 15 khung lấy một khung (0,5 s ở 30 khung/giây) để giảm ảnh gần trùng; lớp "swimmer" và "swimmer with life jacket" được tính là người, thuyền bị bỏ. Phần video của SeaDronesSee (bản theo dõi đối tượng, SeaDronesSee-MOT) còn có mã track của từng người và metadata bay thật (vị trí GPS, độ cao, hướng, góc gimbal), được dùng cho câu hỏi 3 (mục 4.4.3).

### 4.2.2. Tập ảnh lũ tự gán nhãn

Tập ảnh lũ là **tập chính** để kết luận về cảnh lũ, và là một đóng góp của luận văn. VisDrone là đô thị khô, AFO và SeaDronesSee là hồ và biển nước trong, C2A là ảnh ghép; không tập nào có mái nhà ngập, nước phù sa, rác trôi và người bám vào vật nổi như cảnh lũ thật.

**Nguồn.** Video quay cảnh lũ có người từ UAV, lấy từ YouTube và báo điện tử, gồm các trận lũ ở Việt Nam và nước ngoài. Mỗi video được ghi nguồn (đường dẫn, ngày tải, độ phân giải, ghi chú bản quyền). Vì phần lớn video có bản quyền, luận văn chỉ công bố nhãn và nguồn, không phát hành lại ảnh.

**Trích khung.** Các khung cùng một video cách nhau ít nhất 2 giây; khung gần trùng với bất kỳ khung đã giữ nào của cùng video (khoảng cách dHash dưới 10 bit) bị bỏ; mỗi video tối đa 30 khung, rải đều theo thời gian; sau đó lọc bằng mắt các khung mờ hoặc không phải cảnh lũ. Giới hạn 30 khung để không một video nào chi phối kết quả, và khoảng cách thời gian để các khung liền nhau gần giống hệt không làm khoảng tin cậy hẹp giả. Khoảng 10–20% khung không có người được giữ lại để đo báo nhầm (sóng, rác, phản chiếu).

**Rà soát trước khi gán.** Ban đầu có 212 khung từ 10 video. Hai bước rà soát được làm trước khi gán nhãn, khi thành phần tập còn được phép sửa:

- *Rò rỉ với dữ liệu huấn luyện* (data leakage): so mã băm dHash của mọi khung với 16.193 ảnh của năm tập huấn luyện (VisDrone train, AFO train, HydroVigilance train và val, C2A train). Ở ngưỡng 5 bit không có cặp nào gần trùng và không có video chung. Ở ngưỡng nới rộng 10 bit có 37 cặp; xem bằng mắt thì không cặp nào cùng cảnh, chúng chỉ giống nhau về bố cục sáng tối.
- *Nguồn trùng bên trong tập*, việc mã băm không bắt được: hai video có tên khác nhau hoá ra cùng là cảnh quay của cảnh sát San Angelo (Texas) trong cùng một trận lũ (cùng logo, cùng chú thích trên mọi khung), tổng cộng 54 khung, vượt giới hạn 30 khung mỗi nguồn. Hai video được gộp thành một nguồn, giữ 15 khung mỗi video rải đều theo thời gian. Một video khác (Washington) nhiều khả năng quay từ trực thăng chứ không phải UAV; được giữ với góc nhìn chếch tương tự UAV và ghi vào phần giới hạn.

Sau rà soát, tập có **188 khung từ 9 nguồn**, với số khung mỗi nguồn là 30, 30, 29, 23, 23, 22, 15, 8 và 8. Bốn trong mười video có độ phân giải dưới 1080p (hai video 480p, hai video 720p, chiếm 74 khung); chúng được giữ vì bỏ đi thì chỉ còn 114 khung, dưới mức tối thiểu 150 khung đặt ra từ đầu; người trong các video này có ít pixel hơn so với cùng độ cao ở 1080p.

**Quy tắc gán nhãn.** Gán bằng CVAT với hai nhãn: `person` (một người) và `ignore` (vùng không gán được). Một người được gán khi chắc chắn là người, kể cả khi chỉ thấy một phần: người lội, bơi, bám vật nổi, đứng trên mái nhà, ngồi trên thuyền; người chỉ vài pixel nếu nhận ra được nhờ hình dáng, bóng hoặc chuyển động ở các khung lân cận. Không gán bóng phản chiếu, bóng đổ, người trong xe hay trong nhà mà không thấy cơ thể. Vật không chắc là người hay không được phủ bằng vùng bỏ qua. Box bao sát phần nhìn thấy được, không đoán phần chìm; người dưới 16 px được vẽ ở mức phóng 300–400%, vì lệch 1–2 px ở cỡ này đủ làm IoU tụt dưới ngưỡng. Mỗi box có hai thuộc tính: *ngập một phần* (nước che từ đầu gối trở lên) và *bị che* (vật khác che từ khoảng một phần ba cơ thể). Mỗi ảnh có bốn thẻ nhiễu: *lóa* (lóa nắng đủ che một người), *thời tiết* (mưa, sương, tối), *nhòe* và *vật trôi* (rác, đồ vật cỡ một người); thẻ dùng để đo recall theo loại nhiễu (câu hỏi con về nhiễu của cảnh lũ).

**Kiểm tra chất lượng và khoá.** Sau mỗi 50 khung, toàn bộ được xem lại ở mức phóng 100% để tìm người bị sót. Ít nhất hai ngày sau, 20 khung được gán lại mà không nhìn nhãn cũ để đo độ nhất quán của người gán: **[CHỜ KHOÁ: kết quả gán lại]**. Khi đủ khung và rà xong, toàn bộ ảnh, nhãn, vùng bỏ qua, thuộc tính và thẻ được **khoá** bằng mã băm SHA-256; từ đó không sửa nhãn và không thêm bớt khung, và công cụ chấm từ chối chạy nếu mã băm lệch. Nhãn sai phát hiện sau khi khoá được ghi vào phần giới hạn chứ không sửa. Mọi tham số (ngưỡng tin cậy, cỡ người mục tiêu khi thu nhỏ, số lần thấy để xác nhận…) được chọn trên các tập khác trước khi chạy trên tập ảnh lũ, và mỗi cấu hình cuối chỉ chạy một lần trên tập này. Không dùng mô hình để gán nhãn trước cho tập ảnh lũ, để nhãn không thiên về những gì mô hình đã thấy.

**Bảng 4.4.** Thống kê tập ảnh lũ sau khi khoá. **[CHỜ KHOÁ]**

| Nguồn | Khung | Độ phân giải | Người | < 8 px | 8–16 px | 16–32 px | > 32 px | Khung không có người |
|---|---|---|---|---|---|---|---|---|
| … | | | | | | | | |
| **Tổng** | **188** | | | | | | | |

Tập ảnh lũ không có dữ liệu độ cao bay (video tải từ Internet không kèm telemetry), nên kỹ thuật thu nhỏ theo độ cao bay chỉ được đánh giá trên SeaDronesSee và trong mô phỏng, không trên tập này.

## 4.3. Cách đo

### 4.3.1. Độ chính xác phát hiện

Công cụ đo được viết riêng thay vì dùng con số mAP mà thư viện huấn luyện in ra, vì con số đó không chia theo cỡ người, không hỗ trợ vùng bỏ qua và không có khoảng tin cậy. Quy ước đo cố định cho mọi thí nghiệm:

- **AP50** (average precision ở ngưỡng IoU 0,5), nội suy 101 điểm, tính từ dự đoán ở ngưỡng tin cậy 0,001, tối đa 1.000 box mỗi ảnh.
- **Theo nhóm cỡ người** (mục 4.1.3), cạnh nhóm "tất cả". Một con số chung bị người to (dễ) chi phối; đề tài quan tâm người nhỏ.
- **Thêm IoU 0,3** cạnh IoU 0,5. Với người 6 px, lệch 1–2 px đã làm IoU tụt dưới 0,5 dù phát hiện đúng chỗ; trong cứu hộ, đúng chỗ là đủ.
- **Recall và precision vận hành** ở ngưỡng tin cậy 0,25. AP gộp mọi ngưỡng, còn khi chạy thật phải chọn một ngưỡng; hai con số trả lời hai câu hỏi khác nhau.
- **Vùng bỏ qua**: dự đoán rơi vào vùng bỏ qua (VisDrone, tập ảnh lũ) không bị tính là báo nhầm.

Công cụ được kiểm tra bằng ví dụ tính tay và đối chiếu với con số của thư viện huấn luyện trên mô hình nền: hai cách tính lệch dưới 1% khi tắt vùng bỏ qua.

### 4.3.2. Độ bất định

**Khoảng tin cậy bootstrap.** Mỗi chỉ số kèm khoảng tin cậy 95% bằng bootstrap 1.000 lần: lấy mẫu có hoàn lại theo **ảnh** (không theo box, vì các người trong cùng ảnh chung điều kiện ánh sáng, độ cao), tính lại chỉ số, lấy phân vị 2,5% và 97,5%.

**Lấy mẫu theo video** (cluster bootstrap). Ảnh cùng một video chung cảnh, chung độ cao, nên lỗi của mô hình trên chúng đi cùng nhau; coi chúng là độc lập làm khoảng tin cậy hẹp giả. Với SeaDronesSee (11 video) và tập ảnh lũ (9 nguồn), bootstrap rút theo video: video được rút k lần thì mọi ảnh của nó vào mẫu k lần. Ví dụ trên VisDrone val (548 ảnh từ 76 video), khoảng tin cậy AP50 của cùng một cấu hình rộng 0,034 khi lấy theo ảnh và 0,061 khi lấy theo video.

**So hai cấu hình bằng bootstrap cặp** (paired bootstrap). Hai khoảng tin cậy riêng chồng nhau *không* có nghĩa hai cấu hình như nhau, vì cả hai cùng khó trên những ảnh khó. Bootstrap cặp dùng cùng một mẫu ảnh cho cả hai cấu hình và lấy hiệu:

```
lặp 1.000 lần:
    rút có hoàn lại n ảnh (hoặc n video) từ tập đánh giá, cùng một mẫu cho A và B
    hiệu = chỉ số của B trên mẫu − chỉ số của A trên mẫu
khoảng tin cậy 95% của hiệu = phân vị 2,5% và 97,5%
```

Hiệu có ý nghĩa thống kê ở mức 5% khi khoảng tin cậy của hiệu không chứa 0. Ví dụ trên VisDrone val: bộ cắt ô tự viết và thư viện SAHI có khoảng tin cậy AP50 riêng 0,437–0,470 và 0,444–0,477, chồng nhau gần hết, nhưng khoảng tin cậy của hiệu là −0,011 đến −0,003: bộ tự viết kém hơn một chút và ổn định.

Hai lưu ý khi đọc chương 5. Thứ nhất, so nhiều cặp cùng lúc (năm nhóm cỡ, hai chỉ số, nhiều cấu hình) thì vài cặp sẽ "có ý nghĩa" do ngẫu nhiên; kết luận chính dựa trên nhóm "tất cả" và nhóm người nhỏ, đã định trước. Thứ hai, bootstrap xử lý độ bất định do chọn ảnh; độ bất định do khởi tạo ngẫu nhiên khi huấn luyện (seed) là nguồn khác, đo bằng cách huấn luyện lại với seed khác (mục 4.5).

### 4.3.3. Chỉ số của khâu hệ thống

Câu hỏi 3 đo cả chuỗi sau phát hiện: xác nhận, định vị, gửi cảnh báo. Mỗi cảnh báo được ghép với người thật gần nhất (vị trí người tại thời điểm cảnh báo) nếu cách không quá 10 m (`r_eval`).

**Bảng 4.5.** Chỉ số của khâu hệ thống.

| Chỉ số | Định nghĩa |
|---|---|
| Tỉ lệ bỏ sót | Số người thật không có cảnh báo nào trong khoảng từ lúc vào khung tới 10 s sau lúc rời khung, chia tổng số người |
| Báo nhầm mỗi phút | Số cảnh báo không ứng với người thật nào, chia thời lượng chuyến bay (phút) |
| Gộp nhầm | Số cảnh báo ứng với từ hai người thật trở lên |
| Tách nhầm | Số người thật nhận từ hai cảnh báo trở lên |
| Thời gian tới cảnh báo | Thời điểm cảnh báo đầu tiên trừ thời điểm người vào khung |
| Sai số vị trí | Khoảng cách từ cảnh báo đầu tiên tới người thật; cùng tỉ lệ người nằm trong bán kính sai số cảnh báo tự báo (1σ) và trong vùng tìm 95% |
| Độ trễ gửi | Thời điểm trạm mặt đất xác nhận đã nhận gói toạ độ trừ thời điểm tạo cảnh báo |
| Tỉ lệ mất | Số cảnh báo không bao giờ tới trạm, chia tổng số cảnh báo |
| Dung lượng mỗi cảnh báo | Tổng byte đã gửi (gồm cả gửi lại) chia số cảnh báo |

Định nghĩa này có một giới hạn: hai người đứng gần nhau hơn 10 m thì mọi cảnh báo về họ bị tính là gộp nhầm, kể cả khi hệ thống cảnh báo đúng từng người.

### 4.3.4. Tốc độ

Tốc độ được đo **theo từng chặng** của pipeline (cắt ô, suy luận, gộp box, định vị, xác nhận) bằng đồng hồ đo khoảng thời gian, tách khỏi đồng hồ mô phỏng của pipeline (mục 4.5). Kết quả chính là đường **recall theo số khung xử lý mỗi giây**, đánh dấu mức 2 khung/giây, để thấy mỗi cấu hình đổi bao nhiêu độ chính xác lấy bao nhiêu tốc độ. Thời gian đo trên máy cá nhân chỉ dùng để so tương đối giữa các cấu hình chạy trên cùng máy, không phải số liệu của thiết bị biên.

## 4.4. Các thí nghiệm

### 4.4.1. Câu hỏi 1: phát hiện người nhỏ

Mọi mô hình dùng YOLO26s làm mô hình nền (đã huấn luyện trên COCO). Bảng 4.6 định nghĩa mã ngắn dùng trong các bảng của chương 5.

**Bảng 4.6.** Các thí nghiệm của câu hỏi 1.

| Mã | Tên mô tả | Câu hỏi nó trả lời |
|---|---|---|
| E0 | Mô hình nền, ảnh thu về 640 px | Điểm xuất phát khi dùng như thông thường |
| E1 | Mô hình nền, ảnh 1280 px | Độ phân giải đầu vào giúp bao nhiêu |
| E2 | Tinh chỉnh trên VisDrone | Tinh chỉnh trên ảnh UAV giúp bao nhiêu so với mô hình COCO |
| E2c | Tinh chỉnh trên VisDrone và AFO (**mô hình chính**) | Thêm người dưới nước có giữ được khả năng trên cảnh nước không |
| E2e | Như E2c, thêm C2A | Thêm người cỡ to có chữa được điểm yếu với người to không |
| E3 | Như E2c, thêm nhánh phát hiện P2 (P2 detection head) | Thêm tầng phát hiện độ phân giải cao có giúp người rất nhỏ không, có đáng chi phí không |
| E4 | Mô hình chính kèm cắt ô (tiling) 640 px chồng 20% | Cắt ô có lợi khi ảnh thật sự lớn không |
| | E4 kèm thu nhỏ theo độ cao bay | Đưa người về cỡ mô hình làm tốt nhất, dựa trên độ cao bay (đóng góp) |
| E5 | Như E2c nhưng dùng YOLO11s | Kết quả có phụ thuộc đời mô hình không. **Không chạy** (cắt vì lịch); ghi vào giới hạn |
| E6 | Thu nhỏ ảnh nhiều mức, đo recall theo số pixel trên người | Bay cao tối đa bao nhiêu thì còn phát hiện được |

**Huấn luyện.** Ảnh 1280 px, batch 8, 55 epoch (E2: 60 epoch), seed 0, các tham số tăng cường dữ liệu mặc định của thư viện trừ lật dọc (bật, vì ảnh nhìn từ trên không có chiều trên dưới cố định). Ảnh được giữ ở 1280 px vì ở 640 px phép tăng cường thu nhỏ ngẫu nhiên xoá nhãn của nhiều người rất nhỏ (tới 26,9% số nhãn khi thu nhỏ 0,5 lần trên VisDrone val), dạy mô hình rằng đó là nền. Trọng số tốt nhất chọn theo tập kiểm định VisDrone val cộng AFO val; vì vậy bảng chính cho người nhỏ dùng VisDrone test-dev.

**Đánh giá.** Toàn ảnh 1280 px, trừ các cấu hình cắt ô. Cắt ô dùng bộ cắt ô tự viết: chạy mô hình theo lô trên mọi ô của một khung, dời box về toạ độ ảnh gốc và gộp box trùng ở vùng chồng nhau; đã đối chiếu với thư viện SAHI bằng bootstrap cặp (mục 4.3.2). Thu nhỏ theo độ cao bay tính số pixel dự kiến của một người cao 0,5 m nhìn từ trên xuống từ độ cao và góc nhìn camera, rồi thu nhỏ khung để người còn khoảng 10 px trước khi cắt ô (chương 3, mục 3.4).

### 4.4.2. Câu hỏi 2: tốc độ trên thiết bị biên

Luận văn không có thiết bị Jetson. Câu hỏi 2 được trả lời theo hai bước. Thứ nhất, đo trên GPU Tesla T4 của Kaggle với TensorRT, ở hai mức nén FP16 và INT8 (INT8 hiệu chỉnh trên các ô 640 px cắt từ ảnh kiểm định), cho cấu hình tốt nhất của câu hỏi 1: độ chính xác sau nén, thời gian từng chặng, số khung mỗi giây. T4 cùng nền NVIDIA và TensorRT với Jetson nên **thứ hạng** giữa các cấu hình có giá trị; số khung mỗi giây tuyệt đối thì không quy đổi được. Thứ hai, **giả lập thời gian thiết bị**: pipeline chạy trên máy này nhưng tính thời gian xử lý theo hồ sơ của một thiết bị (thời gian mỗi ô, mỗi lượt toàn ảnh, chi phí cố định), bỏ các khung tới trong lúc thiết bị còn bận, và gửi cảnh báo lúc xử lý xong. Hồ sơ của Jetson Orin Nano Super, Orin NX và AGX Orin được ước lượng từ bảng đo công bố của Ultralytics cho YOLO26, rồi hiệu chỉnh theo số đo trên T4. Mọi số từ giả lập được trình bày trong bảng riêng và gọi là ước lượng.

### 4.4.3. Câu hỏi 3: xác nhận, định vị, gửi cảnh báo

Câu hỏi 3 cần biết người thật ở đâu và lúc nào, điều video lũ tải từ Internet không có. Hai nguồn được dùng:

- **Video thật SeaDronesSee-MOT** có mã track của từng người và telemetry thật. Dùng để so các cách xác nhận trên dữ liệu thật: xác nhận theo toạ độ mặt đất (đóng góp), xác nhận theo track của ByteTrack, và ByteTrack có bù chuyển động camera; chấm trong không gian ảnh, người "đủ điều kiện" là người được thấy trong ít nhất 3 khung đã xử lý.
- **Mô phỏng.** Kịch bản giả lập chuyến bay (thẳng hoặc quét luống cày, độ cao cố định hoặc đổi giữa chuyến), người đặt sẵn trên mặt nước (đứng yên hoặc trôi), nhiễu GPS dạng Gauss–Markov (sai số trôi chậm với thời gian tương quan 30 s, như GPS thật), lệch cố định của la bàn và độ cao, mạng chập chờn (mất gói ngẫu nhiên, khoảng mất sóng). Phát hiện là một bộ phát hiện giả theo **recall đo được** của mô hình theo cỡ người (từ E6 trên SeaDronesSee), kèm báo nhầm ngẫu nhiên. Pipeline chạy đúng mã thật; mô phỏng chỉ thay video và bộ phát hiện. Mỗi tổ hợp tham số chạy 3 seed, báo trung bình và độ lệch chuẩn.

**Bảng 4.7.** Các lưới mô phỏng của câu hỏi 3.

| Lưới | Biến thay đổi | Câu hỏi con |
|---|---|---|
| Nhiễu GPS và cách xác nhận | σ GPS 0–3 m × ba cách xác nhận | Gom theo toạ độ mặt đất hay theo track |
| Nguyên nhân bù chuyển động camera thất bại | σ GPS × thời gian tương quan × độ cao | Như trên |
| Độ cao bay | 30–200 m × mô hình nền hay tinh chỉnh | Bao nhiêu khung mỗi giây là đủ, theo độ cao |
| Tần số theo độ cao | Độ cao × số lần nhìn mỗi người × thu nhỏ theo độ cao | Như trên |
| Độ cao đổi giữa chuyến | Hồ sơ độ cao × tần số | Như trên |
| Sai số vị trí | Độ cao × σ GPS × lệch la bàn × lệch độ cao | Sai số GPS và độ cao làm vị trí lệch bao nhiêu |
| Mạng | Mất gói × khoảng mất sóng × thăm dò đường truyền | Mất sóng làm cảnh báo trễ bao lâu, có mất không |
| Bộ nhớ cảnh báo | Mật độ người × σ GPS × bộ nhớ vị trí đã cảnh báo | Gộp cảnh báo thành sự cố bớt được bao nhiêu cảnh báo lặp |

Tham số chung khi không thay đổi: chuyến bay 60 s, 10 m/s, 2 khung/giây, ảnh 4K, góc nhìn 82° chéo, xác nhận khi thấy 3 lần trong 5 s, bán kính gom 3 m.

## 4.5. Môi trường và tái lập

**Phần cứng.** Huấn luyện và đo tốc độ chính chạy trên Kaggle (Tesla T4, 16 GB). Đánh giá độ chính xác và mô phỏng chạy trên máy cá nhân (GPU RTX 5060 qua WSL2); số đo thời gian trên máy cá nhân chỉ dùng để so tương đối. Một lần huấn luyện mô hình chính mất trung vị 10,0 phút mỗi epoch trên T4; tập có C2A mất 18,7–19,1 phút mỗi epoch, vượt giới hạn 12 giờ của một phiên Kaggle nên được chia hai phiên: phiên sau nạp lại trạng thái bộ tối ưu và lịch tốc độ học của phiên trước, nên tương đương một lần chạy liền.

**Phần mềm.** Python 3.12, PyTorch 2.14, Ultralytics 8.4.174 (máy cá nhân); trên Kaggle Python 3.13, PyTorch 2.11; đo tốc độ dùng TensorRT 10.16 (ghim trong notebook, vì với TensorRT 11 bản mới nhất, bước xuất INT8 không build được trên T4). Mọi phiên bản thư viện được ghim chính xác.

**Tái lập.** Mỗi lần chạy ghi một tệp cấu hình kèm theo: lệnh, tham số, phiên bản thư viện, mã băm SHA-256 của trọng số, thiết bị, thời điểm. Mỗi thí nghiệm có một tệp cấu hình riêng, không sửa sau khi đã có kết quả. Notebook huấn luyện chỉ lấy mã nguồn ở một commit cố định rồi gọi script huấn luyện, nên mọi logic nằm trong mã có phiên bản. Pipeline không đọc đồng hồ máy: thời gian lấy từ dấu thời gian của khung hình, mọi ngẫu nhiên (nhiễu GPS, mạng, thời gian chờ gửi lại) dùng seed cố định, nên một lần mô phỏng chạy lại cho đúng cùng kết quả. Bộ kiểm thử tự động (hơn 200 trường hợp, chạy không cần GPU hay dữ liệu) kiểm tra công thức đo bằng ví dụ tính tay, phép chiếu toạ độ bằng phép đi một vòng pixel → GPS → pixel, và chỉ số của khâu hệ thống.

**Seed.** Phần lớn thí nghiệm huấn luyện mới có một seed do giới hạn GPU; cấu hình cuối được huấn luyện thêm hai seed nếu kịp, nếu không thì ghi vào giới hạn (chương 6). **[CẬP NHẬT sau tuần 14–20/11]**

## Tóm tắt chương

Luận văn dùng bốn bộ dữ liệu công khai để huấn luyện, bốn tập công khai và một tập ảnh lũ tự gán nhãn (188 khung, 9 nguồn, khoá bằng mã băm trước khi chạy mô hình) để đánh giá. Độ chính xác được đo theo nhóm cỡ người ở hai ngưỡng IoU, kèm khoảng tin cậy bootstrap lấy mẫu theo video khi ảnh không độc lập, và so hai cấu hình bằng bootstrap cặp. Khâu hệ thống được đo trên video thật có track và trong mô phỏng chạy đúng mã của pipeline. Tốc độ được đo trên T4 và giả lập cho Jetson. Chương 5 trình bày kết quả theo đúng các định nghĩa này.
