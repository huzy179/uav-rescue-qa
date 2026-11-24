# Chương 5. Kết quả và thảo luận

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Nháp 7/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 5. Mọi số liệu chép từ `docs/results/` (mỗi bảng ghi file nguồn), các file đó chép từ CSV trong `runs/`. Chỗ đánh dấu **[CHỜ KHOÁ]** điền sau khi khoá và chấm tập ảnh lũ (11–13/11); phần câu hỏi 2 đã điền 8/11 từ `rq2_t4.md`. Kết quả "sơ bộ" và "mô phỏng" giữ nguyên nhãn đó. Thuật ngữ theo `docs/THUAT_NGU.md`. Số hình, số bảng đánh lại khi dàn trang.

Chương này trình bày kết quả theo ba câu hỏi nghiên cứu. Mỗi câu hỏi con có một tiểu mục: bảng số, điều bảng cho thấy, và giới hạn của nó. Cách đo, tập dữ liệu và mã thí nghiệm đã mô tả ở chương 4; ở đây chỉ nhắc lại khi cần để đọc đúng một bảng.

Ba quy ước đọc bảng xuyên suốt chương:

- **AP50** là độ chính xác trung bình ở IoU 0,5, tính từ dự đoán ở ngưỡng độ tin cậy (conf) 0,001. **Recall vận hành** là tỉ lệ người được phát hiện ở conf 0,25, ngưỡng mà một hệ thống thật sẽ dùng.
- **KTC 95%** là khoảng tin cậy 95% bằng bootstrap 1.000 lần, lấy mẫu theo ảnh, hoặc theo video khi các ảnh cùng video (SeaDronesSee).
- Khi so hai mô hình, "**có ý nghĩa**" nghĩa là khoảng tin cậy 95% của **hiệu số** (bootstrap cặp, cùng bộ ảnh cho cả hai mô hình) không chứa 0. Hai khoảng tin cậy riêng chồng nhau không có nghĩa là hai mô hình như nhau (mục 4.3).

## 5.1. Câu hỏi 1: phát hiện người nhỏ

### 5.1.1. Người nhỏ tới đâu thì bị bỏ sót (RQ1a)

**Mô hình chưa huấn luyện thêm.** Bảng 5.1 là mốc xuất phát: YOLO26s huấn luyện sẵn trên COCO, chạy toàn ảnh ở hai cỡ đầu vào, trên VisDrone val.

**Bảng 5.1.** Mô hình gốc trên VisDrone val, IoU 0,5 (`visdrone_baseline.md`).

| Cách chạy | Nhóm cỡ | AP50 | Recall vận hành | Recall tối đa |
|---|---|---|---|---|
| Toàn ảnh, đầu vào 640 (E0) | tất cả | 0,277 | 0,151 | 0,467 |
| | < 8 px | 0,050 | 0,007 | 0,105 |
| | 8–16 px | 0,255 | 0,105 | 0,462 |
| Toàn ảnh, đầu vào 1280 (E1) | tất cả | 0,497 | 0,322 | 0,720 |
| | < 8 px | 0,167 | 0,053 | 0,401 |
| | 8–16 px | 0,507 | 0,304 | 0,753 |
| | 16–32 px | 0,716 | 0,539 | 0,913 |
| | > 32 px | 0,836 | 0,733 | 0,966 |

Hai điều rút ra. Thứ nhất, **cỡ đầu vào quyết định trước tiên**: thu ảnh về 640 làm hơn một nửa số người không được phát hiện ở bất kỳ ngưỡng nào (recall tối đa 0,467), đúng như bảng số pixel theo độ cao ở chương 1 dự báo. Thứ hai, **mô hình gốc "thấy" người nhỏ nhưng không tự tin**: ở đầu vào 1280, recall tối đa của nhóm dưới 8 px là 0,401 nhưng recall vận hành chỉ 0,053. Phần lớn người nhỏ có box nhưng với độ tin cậy dưới ngưỡng. Đây là động lực trực tiếp cho việc tinh chỉnh mô hình (mục 5.1.2).

Hạ IoU từ 0,5 xuống 0,3 làm AP của nhóm dưới 8 px tăng từ 0,167 lên 0,339 (E1): ở người vài pixel, phần lớn "bỏ sót" theo IoU 0,5 thực ra là box lệch vài pixel. Với bài toán cứu hộ, một box lệch vài pixel quanh đúng người vẫn có ích, nên mọi bảng của nhóm dưới 8 px được báo thêm ở IoU 0,3 (chương 4).

**Recall theo số pixel trên người.** Để biết ngưỡng bỏ sót chính xác hơn bốn nhóm cỡ, ảnh 4K của SeaDronesSee được thu nhỏ 1, 2, 3, 4 và 6 lần, rồi chạy cắt ô sao cho một pixel ảnh đúng bằng một pixel vào mạng ở mọi mức. Như vậy số pixel trên người là biến duy nhất thay đổi (Bảng 5.2, Hình 5.1).

**Bảng 5.2.** Recall vận hành theo cạnh ngắn của người, SeaDronesSee thu nhỏ, bootstrap theo video (`e6_sds_pilot.md`). **Sơ bộ.**

| Cạnh ngắn (px) | Số người | Mô hình gốc (E1) | Mô hình chính (E2c) |
|---|---|---|---|
| 0–4 | 24 | 0,000 | 0,000 |
| 4–6 | 160 | 0,006 | 0,256 |
| 6–8 | 257 | 0,047 | 0,494 |
| 8–11 | 500 | 0,124 | 0,532 |
| 11–16 | 758 | 0,210 | 0,588 |
| 16–23 | 868 | 0,198 | 0,624 |
| 23–32 | 655 | 0,260 | 0,537 |
| 32–45 | 706 | 0,357 | 0,516 |
| 45–64 | 492 | 0,514 | 0,390 |
| 64–91 | 357 | 0,529 | 0,261 |
| ≥ 91 | 498 | 0,637 | 0,133 |

![Hình 5.1. Recall theo cạnh ngắn người](../results/e6_sds_recall_by_pixels.png)

**Hình 5.1.** Recall vận hành theo cạnh ngắn của người trên SeaDronesSee thu nhỏ.

Dưới khoảng 6 px cả hai mô hình gần như không thấy người; muốn mô hình chính còn recall khoảng 0,5 thì người cần ít nhất khoảng 6–8 px. Đây là giới hạn dưới cho độ cao bay: với camera 4K và góc nhìn 82°, nó tương ứng với một độ cao tối đa cụ thể (bảng ở chương 1). Bảng 5.2 còn cho thấy một điều không dự kiến: **mô hình chính tụt mạnh với người to** (từ 45 px trở lên kém mô hình gốc). Mục 5.1.4 xử lý điểm yếu này.

Giới hạn: 1.055 người lặp lại ở năm mức thu nhỏ nên các nhóm cỡ không độc lập; 11 video nên khoảng tin cậy rất rộng (bảng đầy đủ kèm khoảng tin cậy ở `e6_sds_pilot.md`); thu nhỏ ảnh không tái tạo nhiễu cảm biến và nhoè của camera thật.

**Trên tập ảnh lũ.** Bảng 5.x là kết quả chính của câu hỏi 1 trên dữ liệu đích: năm mô hình chốt trước, mỗi mô hình chạy một lần sau khi khoá tập (188 khung, 509 người, chương 4), bootstrap theo 9 nguồn (`flood.md`).

**Bảng 5.x.** AP50 và recall vận hành (conf 0,25) trên tập ảnh lũ, IoU 0,5; cột cuối là AP50 nhóm dưới 8 px ở IoU 0,3. Trong ngoặc: khoảng tin cậy 95%.

| Mô hình | Chỉ số | Tất cả | <8 px | 8–16 px | 16–32 px | >32 px | <8 px, IoU 0,3 |
|---|---|---|---|---|---|---|---|
| Gốc (E1) | AP50 | 0,269 (0,183–0,411) | 0,123 (0,015–0,258) | 0,124 (0,092–0,182) | 0,332 (0,182–0,585) | 0,661 (0,515–0,911) | 0,298 (0,070–0,414) |
|  | Recall | 0,216 (0,164–0,332) | 0,057 (0,000–0,085) | 0,098 (0,067–0,159) | 0,279 (0,147–0,522) | 0,588 (0,429–0,781) | |
| Tinh chỉnh VisDrone (E2) | AP50 | 0,147 (0,062–0,313) | 0,068 (0,012–0,150) | 0,073 (0,049–0,253) | 0,249 (0,063–0,530) | 0,402 (0,225–0,681) | 0,228 (0,076–0,313) |
|  | Recall | 0,283 (0,207–0,440) | 0,216 (0,043–0,667) | 0,229 (0,123–0,437) | 0,375 (0,209–0,625) | 0,338 (0,151–0,691) | |
| Mô hình chính (E2c) | AP50 | 0,148 (0,070–0,334) | 0,083 (0,043–0,319) | 0,082 (0,061–0,202) | 0,233 (0,060–0,532) | 0,434 (0,282–0,687) | 0,308 (0,131–0,468) |
|  | Recall | 0,244 (0,186–0,364) | 0,182 (0,054–0,591) | 0,205 (0,117–0,356) | 0,316 (0,194–0,625) | 0,287 (0,128–0,571) | |
| Thêm P2 (E3) | AP50 | 0,162 (0,079–0,332) | 0,097 (0,024–0,181) | 0,094 (0,071–0,251) | 0,227 (0,042–0,482) | 0,468 (0,324–0,735) | 0,279 (0,093–0,383) |
|  | Recall | 0,240 (0,173–0,345) | 0,171 (0,014–0,429) | 0,220 (0,133–0,374) | 0,287 (0,163–0,472) | 0,287 (0,096–0,611) | |
| Mô hình chính + cắt ô (E4tiled) | AP50 | 0,161 (0,058–0,315) | 0,048 (0,015–0,302) | 0,098 (0,066–0,239) | 0,251 (0,049–0,449) | 0,376 (0,218–0,620) | 0,237 (0,080–0,521) |
|  | Recall | 0,295 (0,227–0,445) | 0,171 (0,056–0,706) | 0,263 (0,145–0,491) | 0,404 (0,200–0,583) | 0,325 (0,175–0,611) | |
| | Số người | 509 | 88 | 205 | 136 | 80 | 88 |

Kết quả **trái với dự đoán ghi trước khi chấm** (mục 5.1.6): trên tập khoá, mô hình gốc có AP50 cao nhất, cao hơn mô hình chính 0,120 (khoảng −0,191 đến −0,020 cho hiệu E2c − E1, có ý nghĩa). Theo quy trình đã đặt, việc đầu tiên là kiểm tra cấu hình và nhãn. Cấu hình đúng (cùng cỡ đầu vào 1280, ngưỡng 0,001, cùng quy ước như các tập khác). Nhãn có một lỗi: khung `thainguyen_003120` chụp một đám đông trên đường ngập, nhìn rõ nhiều người, nhưng không có nhãn nào. Các mô hình tinh chỉnh báo 135–167 box conf ≥ 0,25 trên riêng khung này (mô hình gốc 14), tất cả bị tính là báo nhầm; với mô hình chính đó là 152 trên 432 box của cả tập. Theo quy tắc khoá, nhãn không sửa; số chính vẫn là Bảng 5.x, và một phân tích độ nhạy chấm lại y hệt nhưng bỏ riêng khung này (lý do bỏ kiểm được từ ảnh và nhãn, không phụ thuộc mô hình nào tốt hơn).

**Bảng 5.y.** AP50 toàn tập khi bỏ khung thiếu nhãn (187 khung; recall không đổi vì khung không có nhãn).

| Mô hình | AP50, tập khoá | AP50, bỏ khung thiếu nhãn | Precision, tập khoá | Precision, bỏ khung |
|---|---|---|---|---|
| Gốc (E1) | 0,269 | 0,286 (0,224–0,411) | 0,615 | 0,667 |
| Tinh chỉnh VisDrone (E2) | 0,147 | 0,220 (0,141–0,340) | 0,262 | 0,377 |
| Mô hình chính (E2c) | 0,148 | 0,233 (0,165–0,349) | 0,287 | 0,443 |
| Thêm P2 (E3) | 0,162 | 0,248 (0,175–0,341) | 0,305 | 0,460 |
| Cắt ô (E4tiled) | 0,161 | 0,219 (0,128–0,332) | 0,209 | 0,265 |

Khi bỏ khung đó, khoảng cách giữa mô hình chính và mô hình gốc thu hẹp còn −0,053 (−0,166 đến −0,001, p 0,050), vẫn nghiêng về mô hình gốc. Ba điều đứng vững ở cả hai cách tính:

- **Tinh chỉnh đổi precision lấy recall ở người nhỏ.** Recall vận hành của mô hình chính cao hơn mô hình gốc có ý nghĩa ở người dưới 8 px (+0,125; ở IoU 0,3 +0,307) và 8–16 px (+0,107, p 0,050). Mô hình gốc thận trọng hơn (precision 0,615 so với 0,287) và mạnh hơn có ý nghĩa ở người trên 32 px (hiệu AP50 −0,226, recall −0,300): cùng điểm yếu với người to đã thấy trên SeaDronesSee (Bảng 5.2). Ở IoU 0,3 và bỏ khung thiếu nhãn, AP50 nhóm dưới 8 px của mô hình chính cao hơn mô hình gốc có ý nghĩa (+0,047).
- **Dưới 8 px vẫn là giới hạn:** recall vận hành cao nhất ở nhóm này là 0,216, khoảng tin cậy rất rộng.
- **P2 không khác mô hình chính** ở nhóm nào; **cắt ô** tăng recall vận hành (+0,051, có ý nghĩa) nhưng không tăng AP50 và có precision thấp nhất (0,209).

### 5.1.2. Dữ liệu huấn luyện nào giúp (RQ1b)

Ba lần tinh chỉnh dùng cùng kiến trúc YOLO26s, cùng đầu vào 1280, chỉ khác dữ liệu:

- **chỉ ảnh drone đô thị** (E2): VisDrone;
- **thêm người dưới nước** (E2c): VisDrone cộng AFO;
- **thêm ảnh thảm hoạ có người cỡ to** (E2e): VisDrone, AFO cộng C2A.

**Ảnh drone đô thị giúp người nhỏ rất mạnh** (Bảng 5.3). Trên VisDrone val, AP50 nhóm dưới 8 px tăng từ 0,167 lên 0,554, và mức tăng giữ nguyên trên test-dev, tập không dùng để chọn trọng số. Mức tăng giảm dần theo cỡ người: mô hình gốc đã tốt với người to.

**Bảng 5.3.** Mô hình gốc (E1) và tinh chỉnh trên VisDrone (E2), IoU 0,5, bootstrap cặp (`visdrone_E2.md`).

| Tập | Nhóm cỡ | Mô hình gốc | Tinh chỉnh VisDrone | Hiệu (KTC 95%) |
|---|---|---|---|---|
| VisDrone val | tất cả | 0,497 | 0,758 | +0,261 (0,248 đến 0,275) |
| | < 8 px | 0,167 | 0,554 | +0,388 (0,361 đến 0,411) |
| | 8–16 px | 0,507 | 0,791 | +0,284 (0,266 đến 0,303) |
| | > 32 px | 0,836 | 0,884 | +0,048 (0,024 đến 0,077) |
| VisDrone test-dev | tất cả | 0,269 | 0,513 | +0,244 (0,231 đến 0,262) |
| | < 8 px | 0,086 | 0,247 | +0,161 (0,145 đến 0,181) |

Mức tăng recall vận hành còn lớn hơn mức tăng AP: trên val, nhóm dưới 8 px tăng từ 0,053 lên 0,480. Khoảng cách giữa recall vận hành và recall tối đa thu hẹp (tất cả cỡ: từ 0,322 so với 0,720 ở mô hình gốc xuống 0,687 so với 0,916), tức tinh chỉnh chủ yếu làm mô hình **tự tin hơn** với người nhỏ mà nó vốn đã thấy. Cái giá là precision vận hành giảm (test-dev, nhóm dưới 8 px: 0,762 xuống 0,573): mô hình bắn ra nhiều box hơn ở vật rất nhỏ. Báo nhầm kiểu này là việc của khâu xác nhận nhiều khung (mục 5.3.2), không phải của detector.

**Nhưng chỉ ảnh đô thị thì mất người dưới nước** (Bảng 5.4). Trên AFO test và SeaDronesSee, mô hình tinh chỉnh trên VisDrone **kém hơn cả mô hình gốc**, có ý nghĩa thống kê trên AFO. Người trong hai tập này phần lớn trên 32 px, nên nguyên nhân không phải kích thước mà là hình dạng: VisDrone chỉ có người đi bộ trên phố nhìn xiên; người bơi nằm ngang, chìm một phần, trên nền nước.

**Bảng 5.4.** AP50 trên dữ liệu có nước, IoU 0,5 (`afo_E1_E2.md`, `E2c.md`, `sds_det.md`).

| Tập | Mô hình gốc | Tinh chỉnh VisDrone | Thêm người dưới nước |
|---|---|---|---|
| AFO test (514 ảnh) | 0,147 | 0,103 | 0,568 |
| AFO test bỏ ảnh chung địa điểm với train (363 ảnh) | 0,188 | 0,105 | 0,734 |
| SeaDronesSee (317 ảnh, 11 video) | 0,535 | 0,186 | 0,468 |

Thêm AFO vào dữ liệu huấn luyện (E2c) lấy lại người dưới nước: trên AFO test hiệu so với mô hình gốc là +0,421 (+0,391 đến +0,454), có ý nghĩa. Trên SeaDronesSee, tập người dưới nước **độc lập** với dữ liệu huấn luyện, E2c hơn hẳn mô hình chỉ học VisDrone (+0,281, +0,053 đến +0,506, có ý nghĩa) nhưng **chưa hơn mô hình gốc** (−0,067, −0,426 đến +0,171, không có ý nghĩa). Vậy mức tăng lớn trên AFO test một phần do test và train cùng nguồn. Cái giá trên ảnh đô thị nhỏ: so với E2, VisDrone val giảm 0,011 (−0,015 đến −0,008) và test-dev giảm 0,006 (−0,010 đến −0,002), có ý nghĩa nhưng nhỏ hơn nhiều so với phần lấy lại được trên nước. **E2c được chọn làm mô hình chính** cho mọi phần sau.

**Thêm ảnh thảm hoạ có người cỡ to là kết quả âm** (Bảng 5.5). C2A được thêm vào để chữa điểm yếu với người to của E2c (Bảng 5.2). Dự đoán là người to tốt lên mà người nhỏ không đổi. Kết quả ngược lại: người nhỏ kém đi rõ trên cả hai tập VisDrone, còn trên SeaDronesSee, nơi người phần lớn to, mức tăng không có ý nghĩa thống kê.

**Bảng 5.5.** Mô hình chính (E2c) và thêm C2A (E2e), AP50 ở IoU 0,5, bootstrap cặp (`E2e.md`).

| Tập | Nhóm cỡ | Mô hình chính | Thêm C2A | Hiệu (KTC 95%) | Có ý nghĩa |
|---|---|---|---|---|---|
| VisDrone val | tất cả | 0,747 | 0,718 | −0,029 (−0,035 đến −0,023) | có |
| | < 8 px | 0,546 | 0,492 | −0,053 (−0,067 đến −0,040) | có |
| VisDrone test-dev | tất cả | 0,507 | 0,466 | −0,041 (−0,047 đến −0,035) | có |
| | < 8 px | 0,241 | 0,202 | −0,040 (−0,048 đến −0,030) | có |
| AFO test | tất cả | 0,568 | 0,624 | +0,057 (+0,037 đến +0,078) | có |
| SeaDronesSee | tất cả | 0,468 | 0,509 | +0,041 (−0,167 đến +0,167) | không |
| | > 32 px | 0,470 | 0,525 | +0,055 (−0,161 đến +0,173) | không |

Ở IoU 0,3 kết luận giữ nguyên. Một giải thích hợp lý, chưa kiểm chứng riêng: C2A chiếm 6.129 trên 15.387 ảnh huấn luyện và toàn người cỡ to, nên tỉ lệ người nhỏ trong dữ liệu giảm và mô hình dồn sức vào người to. Điều này đi ngược đúng cái đề tài cần, vì người trong ảnh lũ từ UAV phần lớn nhỏ. Kết quả âm này được giữ trong luận văn vì nó trả lời trực tiếp câu hỏi "thêm dữ liệu thảm hoạ có giúp không": với cách trộn dữ liệu đơn giản thì không. Cách trộn khác (lấy mẫu một phần C2A, cân bằng theo cỡ người) là hướng phát triển (chương 6).

**Trả lời RQ1b.** Ảnh drone đô thị dạy mô hình người nhỏ; ảnh người dưới nước giữ được người bơi mà không mất nhiều ở người nhỏ; ảnh thảm hoạ ghép người to, trộn thẳng vào, làm mất người nhỏ. Trên tập ảnh lũ thứ tự này không lặp lại theo AP50: cả hai mô hình tinh chỉnh đều có AP50 thấp hơn mô hình gốc, nhưng recall người nhỏ cao hơn có ý nghĩa; mô hình chính và mô hình chỉ tinh chỉnh VisDrone gần như ngang nhau về AP50 (hiệu +0,002), mô hình chính hơn ở AP50 nhóm dưới 8 px khi ghép ở IoU 0,3 (+0,080, có ý nghĩa) và kém một chút ở recall toàn tập (−0,039, có ý nghĩa). Thêm ảnh người dưới nước vì vậy không làm hại trên ảnh lũ; còn tinh chỉnh nói chung có giúp cho ảnh lũ hay không thì phụ thuộc cách đo (mục 5.1.1, 5.1.6).

Giới hạn chung: mỗi cấu hình một seed (mục 4.5); số epoch khác nhau giữa các lần tinh chỉnh do giới hạn 12 giờ của Kaggle (60 epoch cho E2, 55 cho E2c và E2e).

### 5.1.3. Cắt ô và nhánh phát hiện P2 (RQ1c)

**Cắt ô.** Trên VisDrone, cắt ô 640 với lượt toàn ảnh (SAHI, E4) **không hơn** chạy toàn ảnh ở 1280: AP50 0,460 so với 0,497, nhóm dưới 8 px 0,149 so với 0,167 (`visdrone_baseline.md`), mà chậm hơn nhiều trên cùng máy (141,1 so với 19,3 ms/ảnh, RTX 5060). Lý do nằm ở dữ liệu: ba phần tư ảnh val chỉ rộng 1360 px, nên chạy toàn ảnh ở 1280 đã gần như giữ nguyên độ phân giải gốc; cắt ô không thêm chi tiết mà lại sinh box bị cắt ở mép ô. Kết luận này **không** chuyển sang video 4K: ở ảnh 3840 px, chạy toàn ảnh ở 1280 phải thu nhỏ ba lần, còn cắt ô giữ nguyên độ phân giải.

Pipeline trên thiết bị biên dùng một bộ cắt ô riêng thay cho SAHI vì nó chạy mọi ô trong một lô và xuất được sang TensorRT (chương 3). Bootstrap cặp so với SAHI (Bảng 5.6) cho thấy chênh lệch nhỏ nhưng có ý nghĩa, và theo hướng chấp nhận được cho đề tài: kém hơn ở người to, nhỉnh hơn ở người dưới 8 px.

**Bảng 5.6.** Bộ cắt ô riêng so với SAHI, mô hình gốc, VisDrone val, bootstrap cặp (`visdrone_tiled_vs_sahi.md`).

| IoU | Nhóm cỡ | SAHI | Cắt ô riêng | Hiệu (KTC 95%) |
|---|---|---|---|---|
| 0,5 | tất cả | 0,460 | 0,454 | −0,006 (−0,011 đến −0,003) |
| 0,5 | < 8 px | 0,149 | 0,153 | +0,004 (+0,001 đến +0,009) |
| 0,5 | > 32 px | 0,749 | 0,706 | −0,043 (−0,071 đến −0,015) |
| 0,3 | tất cả | 0,569 | 0,585 | +0,016 (+0,011 đến +0,021) |
| 0,3 | < 8 px | 0,300 | 0,324 | +0,024 (+0,017 đến +0,030) |

Bảng này cũng minh hoạ vì sao cần bootstrap cặp: hai khoảng tin cậy riêng của AP50 (0,437–0,470 và 0,444–0,477) chồng nhau, nhìn riêng sẽ kết luận sai là "như nhau". Ở IoU 0,3 bộ cắt ô riêng **cao hơn**: box của nó tìm đúng chỗ nhưng kém khít hơn, vì gộp box giữa các ô bằng cách giữ box điểm cao nhất thay vì hợp nhất toạ độ. Hợp nhất toạ độ đã được thử và bỏ, vì box lớn điểm thấp phủ cả nhóm người kéo box từng người thành box cả nhóm.

**Nhánh P2.** Thêm tầng phát hiện ở bước 4 pixel (E3), cùng dữ liệu và cùng số epoch với mô hình chính, cho mức tăng có ý nghĩa nhưng rất nhỏ ở người dưới 8 px, và đổi lại kém hơn ở người to (Bảng 5.7).

**Bảng 5.7.** Thêm nhánh P2 (E3) so với mô hình chính (E2c), AP50 ở IoU 0,5, bootstrap cặp (`E3.md`).

| Tập | Nhóm cỡ | Mô hình chính | Thêm P2 | Hiệu (KTC 95%) | Có ý nghĩa |
|---|---|---|---|---|---|
| VisDrone val | tất cả | 0,747 | 0,747 | −0,000 (−0,005 đến +0,005) | không |
| | < 8 px | 0,546 | 0,558 | +0,012 (+0,000 đến +0,025) | có |
| | > 32 px | 0,888 | 0,858 | −0,029 (−0,045 đến −0,011) | có |
| VisDrone test-dev | < 8 px | 0,241 | 0,254 | +0,013 (+0,004 đến +0,021) | có |
| | > 32 px | 0,887 | 0,873 | −0,014 (−0,026 đến −0,003) | có |
| SeaDronesSee | tất cả | 0,468 | 0,408 | −0,060 (−0,104 đến +0,013) | không |

Ở IoU 0,3 mức tăng ở người dưới 8 px biến mất (val −0,008, −0,018 đến +0,003): P2 làm box người nhỏ **khít hơn** chứ không **tìm thấy nhiều người hơn**. Recall vận hành trên VisDrone còn thấp hơn (val −0,027, test-dev −0,025). Với chi phí tính toán 115,0 so với 93,9 GFLOPs và batch huấn luyện phải giảm một nửa vì tràn bộ nhớ, P2 không đáng so với mô hình chính.

**Trả lời RQ1c.** Trên ảnh độ phân giải vừa, cả cắt ô lẫn P2 đều không cải thiện đáng kể người nhỏ; mức tăng P2 mang lại (+0,012 AP50 ở nhóm dưới 8 px so với mô hình chính) rất nhỏ so với mức tăng do dữ liệu (+0,388 khi tinh chỉnh trên VisDrone so với mô hình gốc, Bảng 5.3). Cắt ô có ý nghĩa ở ảnh 4K, và khi đó phải đi cùng thu nhỏ theo độ cao (mục 5.1.4).

### 5.1.4. Thu nhỏ khung theo độ cao bay (RQ1d)

Bảng 5.2 cho thấy mô hình chính mạnh nhất với người khoảng 10–30 px và yếu với người trên 45 px. Một giải thích hợp lý: dữ liệu huấn luyện được thu về đầu vào 1280 và co giãn thêm khi tăng cường dữ liệu, nên người khi vào mạng hầu hết nhỏ. Thống kê nhãn ủng hộ giải thích này: ở đầu vào 1280 không co giãn, người trên 32 px chỉ chiếm 0,0477 số người của VisDrone train và 0,1833 của AFO train (`e6_sds_pilot.md`). Hệ quả là cắt ô ảnh 4K bay thấp ở độ phân giải gốc đưa vào mô hình đúng loại người nó yếu.

Đề tài đề xuất **thu nhỏ khung theo độ cao bay** (chương 3): từ độ cao và tiêu cự, ước lượng một người 0,5 m sẽ chiếm bao nhiêu pixel, rồi thu nhỏ khung trước khi cắt ô để người về khoảng một cỡ mục tiêu; không bao giờ phóng to. Bảng 5.8 thử trên SeaDronesSee 4K, tập duy nhất có cả nhãn người lẫn độ cao bay thật.

**Bảng 5.8.** Thu nhỏ theo độ cao, mô hình chính, SeaDronesSee 4K, IoU 0,5, bootstrap theo video (`scale_by_altitude.md`). **Sơ bộ.**

| Cách chạy | AP50 | KTC 95% | Recall vận hành | Precision vận hành |
|---|---|---|---|---|
| Mô hình gốc, toàn ảnh 1280 | 0,535 | 0,362–0,616 | 0,481 | 0,660 |
| Mô hình chính, toàn ảnh 1280 | 0,468 | 0,151–0,554 | 0,465 | 0,640 |
| Mô hình chính, cắt ô ở độ phân giải gốc | 0,235 | 0,083–0,551 | 0,374 | 0,065 |
| Mô hình chính, cắt ô, thu nhỏ về 20 px dự kiến | 0,523 | 0,337–0,660 | 0,510 | 0,690 |
| Mô hình chính, cắt ô, thu nhỏ về 10 px dự kiến | 0,531 | 0,451–0,684 | 0,579 | 0,656 |

So cặp: thu nhỏ về 10 px so với cắt ô ở độ phân giải gốc +0,296 AP50 (+0,061 đến +0,412) và +0,205 recall (+0,118 đến +0,318), có ý nghĩa; so với chạy toàn ảnh, recall cao hơn có ý nghĩa (+0,114, +0,053 đến +0,392) còn AP50 cao hơn nhưng chưa có ý nghĩa; so với mô hình gốc, AP50 ngang nhau (−0,005, −0,115 đến +0,273).

Ba điều rút ra. **Cắt ô ở độ phân giải gốc là cách tệ nhất** cho mô hình tinh chỉnh trên ảnh bay thấp: precision 0,065, nền bị báo nhầm rất nhiều. **Thu nhỏ theo độ cao sửa được gần hết**, và đưa mô hình chính về ngang mô hình gốc trên nước biển, trong khi vẫn giữ lợi thế lớn ở người nhỏ (Bảng 5.3). Điều này trả lời tốt hơn băn khoăn ở mục 5.1.2 ("mô hình chính chưa hơn mô hình gốc với người dưới nước"): một phần khoảng cách đến từ việc đưa người sai cỡ vào mô hình, không phải từ mô hình. Cuối cùng, cách này **dùng một dữ liệu drone vốn có** (độ cao bay) để chọn thang xử lý, thay vì cố định; đây là phần thứ nhất của luận điểm xuyên suốt (mục 5.4).

Hai biến thể của cùng ý tưởng đã được thử và không giữ lại: thêm một lượt toàn ảnh sau khi thu nhỏ để bắt người to bị cắt đôi giữa các ô không làm tăng AP50 (−0,013, −0,071 đến +0,001) mà tốn thêm một lượt suy luận mỗi khung (`full_pass.md`); theo chiều ngược lại, phóng to khung khi người dự kiến dưới 8 px không cải thiện có ý nghĩa ở mức thu nhỏ nào, trong khi số ô tăng hơn gấp đôi ở mức thu nhỏ 6 lần (`upscale_small.md`). Đặt ngưỡng tin cậy riêng cho từng cỡ box (thấp cho box nhỏ) cũng không giúp: chọn trên VisDrone val, recall chung trên chính tập đó chỉ từ 0,6655 lên 0,6657, vì phải nâng ngưỡng người 8–16 px để giữ precision (`conf_by_size.md`). Người dưới khoảng 6–8 px vì vậy vẫn là giới hạn dưới của khâu phát hiện; cách chữa là bay thấp hơn (mục 5.3.1).

Giới hạn: một tập, 11 video, người phần lớn to; cỡ mục tiêu 10 và 20 px được chọn sau khi xem kết quả trên chính tập này, nên đây là khảo sát chứ chưa phải đánh giá độc lập; góc nhìn camera giả định chung 82°, và ước lượng số pixel thường thấp hơn cỡ người trong nhãn. Tập ảnh lũ không có độ cao bay (video YouTube) nên không đánh giá được cách này trên ảnh lũ (quyết định đã ghi ở chương 4); phần kiểm chứng thêm nằm ở mô phỏng (mục 5.3.1).

### 5.1.5. Nhiễu riêng của cảnh lũ (RQ1e)

**Bảng 5.z.** Recall vận hành và báo nhầm mỗi khung của mô hình chính theo thẻ ảnh và thuộc tính người, tập khoá, IoU 0,5 (`flood.md`).

| Tập con | Số người | Recall | Số khung | Báo nhầm mỗi khung |
|---|---|---|---|---|
| Tất cả | 509 | 0,244 (0,186–0,364) | 188 | 1,638 (0,309–3,624) |
| Loá nước | 184 | 0,321 (0,000–0,429) | 42 | 1,738 (0,222–4,408) |
| Mưa, sương, tối | 4 | 0,500 | 1 | 1,000 |
| Nhoè | 223 | 0,305 (0,146–0,469) | 54 | 1,407 (0,257–4,709) |
| Vật trôi | 213 | 0,324 (0,164–0,447) | 117 | 0,863 (0,250–1,855) |
| Khung không thẻ | 262 | 0,191 (0,000–0,204) | 58 | 3,534 (0,100–6,392) |
| Người ngập một phần | 70 | 0,243 (0,048–0,461) | | |
| Người bị che | 68 | 0,279 (0,136–0,535) | | |
| Người không thuộc tính | 373 | 0,236 (0,165–0,362) | | |

Không thẻ nào cho recall thấp hơn toàn tập một cách rõ ràng; khoảng tin cậy quá rộng để kết luận (chỉ một khung có thời tiết xấu). Khung loá, nhoè, vật trôi thậm chí có recall điểm cao hơn khung không thẻ, có lẽ vì chúng thường là cảnh gần, người to hơn, chứ không phải nhiễu giúp mô hình. Nhóm khung không thẻ có báo nhầm mỗi khung cao nhất, một phần do khung thiếu nhãn (không có thẻ) nằm trong nhóm này. Độ tin của thẻ cũng hạn chế: khi gán hai lần 37 khung, thẻ loá và vật trôi chỉ trùng 0,649 và 0,595 (chương 4). Kết luận cho RQ1e: trên 188 khung này, không đo được ảnh hưởng riêng của loá, nhoè hay vật trôi lên recall.

### 5.1.6. Từ ảnh đô thị và biển sang cảnh lũ (RQ1f)

**Bảng 5.w.** AP50 toàn bộ (IoU 0,5) của cùng các mô hình trên ba tập (`E2c.md`, `E3.md`, `sds_det.md`, `flood.md`). Mô hình thêm C2A không chạy trên tập lũ (chương 4).

| Mô hình | VisDrone test-dev | SeaDronesSee | Tập lũ, khoá | Tập lũ, bỏ khung thiếu nhãn |
|---|---|---|---|---|
| Gốc (E1) | 0,269 | 0,535 | 0,269 | 0,286 |
| Tinh chỉnh VisDrone (E2) | 0,513 | 0,186 | 0,147 | 0,220 |
| Mô hình chính (E2c) | 0,507 | 0,468 | 0,148 | 0,233 |
| Thêm P2 (E3) | 0,510 | 0,408 | 0,162 | 0,248 |

Thứ hạng trên tập lũ **giống SeaDronesSee hơn VisDrone**: mô hình gốc đứng đầu ở cả hai tập có nước, trong khi trên VisDrone nó kém xa. Vậy một tập ảnh đô thị, dù nhiều người nhỏ, không dự báo được mô hình nào tốt cho cảnh lũ; AP50 trên ảnh đô thị đo được độ khó "người nhỏ trên nền phố", không đo được báo nhầm trên mặt nước, mái nhà và đám đông. Khác với SeaDronesSee, trên tập lũ khoảng cách giữa mô hình chính và mô hình chỉ tinh chỉnh VisDrone gần như không còn, có lẽ vì người trong ảnh lũ phần lớn đứng hoặc lội chứ không bơi như AFO và SeaDronesSee.

Dự đoán trước khi chấm, ghi lại để đối chiếu: người trong 188 khung lũ có cả người nhỏ trên mái lẫn người cỡ vừa dưới nước, nên mô hình chính được kỳ vọng hơn mô hình gốc ở người nhỏ và không kém ở người dưới nước. Nếu kết quả trái dự đoán thì việc đầu tiên là kiểm tra cấu hình và nhãn, chưa kết luận ngay.

## 5.2. Câu hỏi 2: chạy kịp trên thiết bị biên

Câu hỏi 2 đo trên GPU Tesla T4 của Kaggle với TensorRT, vì đề tài không có Jetson (chương 4). Số đo trên T4 không phải số của Jetson; điều nó cho biết là **thứ hạng tương đối** giữa các cấu hình trên cùng phần cứng và **khâu nào tốn thời gian nhất**. Thời gian đo trên máy cá nhân trong các mục trước (Mac, RTX 5060) chỉ dùng để so sánh tương đối và không xuất hiện trong mục này.

### 5.2.1. Nén mô hình và cấu hình tốt nhất (RQ2a, RQ2b)

Một lựa chọn đã thử trước khi đo trên T4: YOLO26 có đầu ra một-một không cần NMS, được giới thiệu là đơn giản cho thiết bị biên. Cùng trọng số mô hình chính, đầu này làm recall vận hành giảm có ý nghĩa trên VisDrone, nhiều nhất ở người dưới 8 px (val −0,056, test-dev −0,029), trong khi AP50 gần như giữ và thời gian trên PyTorch không đổi (`nms_free.md`). Mọi cấu hình dưới đây dùng đầu mặc định có NMS. Một cách giảm khối lượng tính khác cũng đã thử và bỏ: khi drone đứng yên, dùng lại kết quả của ô gần như không đổi làm số ô phải chạy còn 0,518–0,852 so với chạy đủ, nhưng recall giảm tới 0,238 vì người bơi vẫn cử động mà phép so ô thu nhỏ không thấy (`tile_skip.md`).


Chín cấu hình được đo trên T4: mô hình chính ở PyTorch, TensorRT FP16 và TensorRT INT8, mỗi loại chạy toàn ảnh 1280, cắt ô 640 ở độ phân giải gốc, và cắt ô sau khi thu nhỏ về 10 px dự kiến theo độ cao. Tốc độ là của **cả pipeline** trên thiết bị biên (đọc khung, thu nhỏ, cắt ô, suy luận, gộp box, chiếu xuống mặt đất, xác nhận) trên 100 khung của một đoạn video SeaDronesSee 4K có telemetry thật; độ chính xác chấm trên SeaDronesSee val và VisDrone test-dev.

**Bảng 5.8a.** Tốc độ cả pipeline trên khung 4K, Tesla T4 (`rq2_t4.md`). Chỉ so sánh tương đối.

| Cấu hình | Số ô | Thu nhỏ khung p50 (ms) | Suy luận p50 (ms) | Tổng p50 (ms) | Khung/giây theo p95 |
|---|---|---|---|---|---|
| PyTorch, toàn ảnh | 1 | 0,00 | 54,37 | 54,71 | 18,01 |
| FP16, toàn ảnh | 1 | 0,00 | 23,72 | 24,06 | 39,90 |
| INT8, toàn ảnh | 1 | 0,00 | 20,11 | 20,37 | 44,58 |
| PyTorch, cắt ô gốc | 32 | 0,05 | 385,50 | 386,06 | 2,48 |
| FP16, cắt ô gốc | 32 | 0,05 | 120,10 | 120,57 | 7,50 |
| INT8, cắt ô gốc | 32 | 0,05 | 105,98 | 106,58 | 9,04 |
| PyTorch, thu nhỏ 10 px | 6 | 46,35 | 90,97 | 138,49 | 6,32 |
| FP16, thu nhỏ 10 px | 6 | 46,28 | 30,56 | 77,34 | 11,58 |
| INT8, thu nhỏ 10 px | 6 | 45,74 | 25,84 | 72,10 | 11,98 |

**FP16 gần như không mất gì.** So với PyTorch cùng cách chạy, FP16 nhanh hơn 1,833–3,028 lần (theo p95). Trên SeaDronesSee hiệu AP50 và recall vận hành không có ý nghĩa thống kê; trên VisDrone AP50 giảm 0,005 và recall vận hành của người dưới 8 px không khác có ý nghĩa (`rq2_t4.md`).

**INT8 mất recall vận hành, không phải khả năng phân biệt.** Bảng 5.8b trả lời câu hỏi "INT8 mất gì ở người nhỏ" trên VisDrone test-dev (SeaDronesSee val gần như không có người dưới 16 px).

**Bảng 5.8b.** INT8 so với PyTorch, toàn ảnh 1280, VisDrone test-dev, IoU 0,5 (`rq2_t4.md`).

| Nhóm cỡ | AP50 PyTorch → INT8 | Recall vận hành (conf 0,25) | Recall tối đa (mọi ngưỡng) |
|---|---|---|---|
| < 8 px | 0,241 → 0,223 | 0,217 → 0,108 | 0,477 → 0,461 |
| 8–16 px | 0,623 → 0,592 | 0,572 → 0,407 | 0,853 → 0,834 |
| 16–32 px | 0,823 → 0,808 | 0,783 → 0,664 | 0,951 → 0,945 |
| > 32 px | 0,888 → 0,879 | 0,853 → 0,768 | 0,969 → 0,970 |

Hiệu AP50 dưới 8 px là −0,018 (KTC 95% −0,041 đến −0,015), còn hiệu recall vận hành dưới 8 px là −0,109 (−0,176 đến −0,096); ở IoU 0,3 tương ứng −0,035 và −0,172. Recall tối đa gần như giữ, còn số box có độ tin cậy từ 0,25 trở lên giảm từ 19.423 (FP16) xuống 10.940 và phân vị 99 của độ tin cậy từ 0,639 xuống 0,492. Nghĩa là **INT8 nén độ tin cậy xuống**: thứ tự giữa các box gần như giữ nên AP ít đổi, nhưng ngưỡng 0,25 chọn cho mô hình không nén cắt mất một nửa số người dưới 8 px. Đổi lại, INT8 chỉ nhanh hơn FP16 ít (Bảng 5.8a). Trên SeaDronesSee với thu nhỏ theo độ cao, INT8 không khác PyTorch có ý nghĩa, nhưng khoảng tin cậy rộng (recall vận hành −0,025, từ −0,100 đến +0,010).

**Thu nhỏ theo độ cao vừa đúng hơn vừa nhanh hơn, và đẩy chỗ tốn thời gian sang khâu đổi cỡ khung.** Trên khung 4K, cắt ô ở độ phân giải gốc phải chạy 32 ô và cho AP50 thấp nhất (0,234; INT8 0,164); thu nhỏ về 10 px còn 6 ô, AP50 0,534 với FP16 (hiệu +0,301, KTC 95% +0,060 đến +0,414). Nhưng đổi cỡ một khung 4K trên CPU mất 46,28 ms (trung vị, FP16), nhiều hơn suy luận của 6 ô (30,56 ms với FP16). Từ đây, muốn nhanh hơn nữa thì phải tối ưu khâu đổi cỡ khung (làm trên GPU hoặc giải mã video ở độ phân giải thấp hơn), không phải nén mô hình thêm.

**Đổi cỡ khung trên GPU (sơ bộ, đo trên máy cá nhân, chỉ so tương đối).** Nguyên nhân khâu này chậm là thư viện Ultralytics ép OpenCV chạy một luồng khi được nạp. Đổi cỡ bằng torch trên GPU giảm chặng chuẩn bị khung trên SeaDronesSee val từ 21,34 ms xuống 5,39 ms (trung vị), tổng mỗi ảnh từ 50,60 ms xuống 43,55 ms, mà AP50 và recall không khác có ý nghĩa (AP50 −0,021, KTC 95% −0,038 đến +0,017; `gpu_resize.md`). Chưa đo trên T4 nên các bảng trên vẫn là số đo với đổi cỡ trên CPU.

**Bảng 5.8c.** Biên Pareto recall vận hành theo tốc độ, SeaDronesSee val (`rq2_t4.md`; hình: `runs/rq2/rq2_sds_det.png`).

| Cấu hình | Khung/giây theo p95 | Recall vận hành | AP50 | Trên biên |
|---|---|---|---|---|
| INT8, toàn ảnh | 44,58 | 0,443 | 0,470 | có |
| FP16, toàn ảnh | 39,90 | 0,468 | 0,457 | có |
| PyTorch, toàn ảnh | 18,01 | 0,466 | 0,468 | |
| INT8, thu nhỏ 10 px | 11,98 | 0,554 | 0,524 | có |
| FP16, thu nhỏ 10 px | 11,58 | 0,580 | 0,534 | có |
| INT8, cắt ô gốc | 9,04 | 0,290 | 0,164 | |
| FP16, cắt ô gốc | 7,50 | 0,372 | 0,234 | |
| PyTorch, thu nhỏ 10 px | 6,32 | 0,579 | 0,531 | |
| PyTorch, cắt ô gốc | 2,48 | 0,374 | 0,234 | |

**Trả lời RQ2a, RQ2b.** Trên T4, FP16 là mức nén nên dùng: nhanh hơn PyTorch 1,833–3,028 lần mà độ chính xác gần như giữ. INT8 nhanh thêm ít và, với ngưỡng hiện tại, mất một nửa recall vận hành ở người dưới 8 px vì độ tin cậy bị nén; muốn dùng phải chọn lại ngưỡng riêng trên tập val. Biên Pareto có hai nhóm: toàn ảnh (39,90–44,58 khung/giây theo p95, recall vận hành 0,443–0,468) và thu nhỏ theo độ cao (11,58–11,98 khung/giây, recall 0,554–0,580). Vì trần tần số cần thiết ở mục 5.3.1 là 8 khung mỗi giây, cấu hình được chọn là **FP16 với thu nhỏ theo độ cao**: recall cao nhất trên biên và vẫn trên mức cần thiết trên T4. Thiết bị yếu hơn có theo kịp không là câu hỏi của mục 5.2.2.

### 5.2.2. Thiết bị yếu (RQ2c)

Không có Jetson, nên câu hỏi này trả lời bằng **giả lập thời gian thiết bị** (chương 3): pipeline chạy trên máy cá nhân nhưng "bận" theo hồ sơ của thiết bị khác, khung tới lúc bận bị bỏ. Hồ sơ được hiệu chỉnh từ số đo trên T4 ở mục 5.2.1; với Jetson, nó nhân thêm tỉ lệ thời gian suy luận công bố (Jetson so với T4), nên **mọi số trong mục này là ước lượng**, không đặt cạnh số đo. Khi đo trên T4 thấy khâu thu nhỏ khung tốn nhiều, hồ sơ được bổ sung một hệ số thời gian thu nhỏ theo megapixel; nếu không, giả lập sẽ bỏ qua đúng phần nặng nhất của cấu hình được chọn.

**Bảng 5.8d.** Thiết bị yếu theo kịp không: cùng chuyến bay như Bảng 5.10, thu nhỏ về 10 px, pipeline xin 8 khung mỗi giây (`rq2_t4.md`). **Mô phỏng, hồ sơ Jetson là ước lượng.**

| Độ cao | Thiết bị | Độ trễ mỗi khung, trung vị (ms) | Khung xử lý trong 60 s | Tỉ lệ bỏ sót |
|---|---|---|---|---|
| 30 m | T4 (hồ sơ đo) | 54,283 | 480 | 0,000 |
| 30 m | AGX Orin | 83,659 | 480 | 0,000 |
| 30 m | Orin NX | 131,878 | 240 | 0,067 |
| 30 m | Orin Nano Super | 145,935 | 240 | 0,067 |
| 50 m | T4 (hồ sơ đo) | 69,283 | 480 | 0,000 |
| 50 m | Orin Nano Super | 186,295 | 240 | 0,033 |
| 100 m | T4 (hồ sơ đo) | 136,783 | 240 | 0,000 |
| 100 m | Orin Nano Super | 367,915 | 160 | 0,000 |

**Trả lời RQ2c.** Theo ước lượng, Orin NX và Orin Nano Super chỉ xử lý được 4 trong 8 khung mỗi giây khi bay 30–50 m, nên bỏ sót 0,067 ở 30 m, bằng đúng mức của việc chỉ xin 4 khung mỗi giây; ở 100 m mọi thiết bị đều không bỏ sót vì 2 khung mỗi giây đã đủ (Bảng 5.10). Thiết bị yếu thiếu sức đúng lúc bay thấp, khi tần số cần cao nhất. Cũng lúc đó mỗi khung chỉ có 2 ô, nên độ trễ chủ yếu nằm ở khâu thu nhỏ khung 4K chứ không ở suy luận: nén thêm mô hình (INT8) giúp ít, còn đổi cỡ khung trên GPU hoặc lấy video ở độ phân giải thấp hơn khi bay thấp mới là hướng đúng (chưa làm, chương 6). Các số này phụ thuộc vào một giả định chưa kiểm chứng, rằng phần chạy trên CPU của Jetson chậm hơn T4 theo cùng tỉ lệ với phần suy luận.

## 5.3. Câu hỏi 3: báo đúng về trạm mặt đất

Phần lớn kết quả của câu hỏi 3 là **mô phỏng**: một chuyến bay giả với telemetry, người đứng yên ở vị trí biết trước, và một detector giả có recall lấy từ đường đo được ở Bảng 5.2. Mô phỏng cho phép đổi từng yếu tố (độ cao, GPS, mạng) trong khi giữ nguyên các yếu tố khác, điều không làm được với vài đoạn video thật. Phần dữ liệu thật là ba đoạn SeaDronesSee có telemetry (mục 5.3.2). Mọi số mô phỏng là trung bình 3 seed (chương 4, Bảng 4.7).

Một giả định chung cần nhớ khi đọc mục này: trong mô phỏng, các khung **độc lập** với nhau, người khó thấy ở khung này không khó hơn ở khung sau. Thực tế lỗi tương quan theo thời gian (sóng, loá kéo dài nhiều giây), nên mô phỏng **lạc quan** với các cấu hình dựa vào nhiều lần nhìn.

### 5.3.1. Bao nhiêu khung mỗi giây là đủ (RQ3a)

**Độ cao và cỡ người.** Bay cao thì người nhỏ đi nên mỗi khung khó thấy hơn, nhưng người nằm trong khung lâu hơn nên được nhìn nhiều lần hơn. Bảng 5.9 cho thấy với mô hình chính, lực thứ hai thắng.

**Bảng 5.9.** Tỉ lệ bỏ sót theo độ cao, 2 khung mỗi giây, recall theo cỡ người (`rq3_altitude.md`). **Mô phỏng.**

| Độ cao | Mô hình gốc | Mô hình chính |
|---|---|---|
| 30 m | 0,767 | 0,567 |
| 50 m | 0,567 | 0,033 |
| 80 m | 0,533 | 0,000 |
| 120 m | 0,600 | 0,000 |
| 160 m | 0,967 | 0,000 |
| 200 m | 0,900 | 0,000 |

Mô hình gốc không dùng được khi bay cao (bỏ sót từ 0,900 trở lên ở 160 m). Mô hình chính không bỏ sót ai từ 80 m tới 200 m, nhưng **bay thấp lại tệ**: ở 30 m người chỉ nằm trong ít khung mà vẫn cần thấy 3 lần.

**Tần số theo độ cao.** Thay vì cố định 2 khung mỗi giây, tần số được tính để mỗi người được nhìn một số lần định trước (`min_views`): tần số bằng số lần nhìn nhân vận tốc chia chiều dài vùng chụp, kẹp trong một trần. Bảng 5.10 so cách này với tần số cố định.

**Bảng 5.10.** Tỉ lệ bỏ sót / số khung chạy detector trong 60 s (`rq3_adaptive.md`). **Mô phỏng.**

| Độ cao | Cố định 2 khung/giây | Cố định 8 khung/giây | 12 lần nhìn, trần 8 |
|---|---|---|---|
| 30 m | 0,567 / 120 | 0,000 / 480 | 0,033 / 279,7 |
| 50 m | 0,067 / 120 | 0,000 / 480 | 0,000 / 169,3 |
| 80 m | 0,000 / 120 | 0,000 / 480 | 0,000 / 106,7 |
| 120 m | 0,000 / 120 | 0,000 / 480 | 0,000 / 71,7 |

Tần số theo độ cao **chuyển khung từ chỗ thừa sang chỗ thiếu**: bay thấp thì chạy nhiều khung hơn và gần hết bỏ sót (30 m: 0,033 so với 0,567), bay cao thì chạy ít khung hơn mà không bỏ sót (120 m: 71,7 khung so với 120). Số lần nhìn phải chọn theo recall: 6 lần nhìn là quá ít với recall mỗi khung khoảng 0,5 của mô hình chính (bỏ sót 0,100–0,333 ở mọi độ cao, `rq3_adaptive.md`). Trần tần số là chỗ câu hỏi 2 nối vào: nếu thiết bị chỉ chạy được 2 khung mỗi giây thì ở 30 m mọi mức số lần nhìn đều bị cắt về 2 và lợi ích biến mất.

Khi độ cao **đổi giữa chuyến** (dò ở 120 m rồi hạ xuống 40 m), 12 lần nhìn với trần 8 bỏ sót 0,033 với 137 khung, gần bằng xử lý cố định 8 khung mỗi giây (0,000 với 480 khung); thêm thu nhỏ về 10 px thì không bỏ sót ai (`rq3_altprofile.md`). Trong mô phỏng, thu nhỏ theo độ cao chỉ cải thiện nhỏ, vì người ở 30–120 m nằm trong khoảng 8–45 px, nơi đường recall của mô hình chính gần phẳng (Bảng 5.2); lợi ích đo được trên SeaDronesSee (Bảng 5.8) đến từ người trên 45 px và từ báo nhầm khi cắt ô người to, hai thứ mô phỏng không có. Một lý do nữa: mô phỏng giả định người rộng 0,5 m, trong khi box người trong nhãn SeaDronesSee, nguồn của đường recall, lớn hơn khoảng 1,8–2,6 lần ở khung nhìn thẳng. Lặp lại mô phỏng với người 1,0 m, bay 30 m bỏ sót 0,867 và thu nhỏ về 10 px dự kiến giảm còn 0,400; ở 50 m từ 0,133 còn 0,033 (`person_px_check.md`, **mô phỏng**). Con số bỏ sót khi bay thấp vì vậy phụ thuộc mạnh vào cỡ người giả định.

**Trả lời RQ3a.** Không có một tần số đủ cho mọi độ cao. Tần số cần thiết phụ thuộc độ cao, vận tốc và recall của detector; tính nó từ telemetry giúp vừa giảm bỏ sót khi bay thấp vừa giảm tính toán khi bay cao. Đối chiếu với câu hỏi 2: cấu hình được chọn chạy 11,58 khung mỗi giây (p95) trên T4 với khung 4K, trên trần 8; thiết bị yếu hơn theo ước lượng chỉ đạt 4 khung mỗi giây khi bay 30–50 m (Bảng 5.8d).

### 5.3.2. Gom theo toạ độ mặt đất hay theo dõi trên ảnh (RQ3b)

Khâu xác nhận chỉ gửi cảnh báo khi một người được thấy đủ N = 3 lần. Hai cách ghép các lần thấy: **gom theo toạ độ mặt đất** (geo: chiếu box xuống mặt đất bằng telemetry, gom các điểm trong bán kính 3 m và cửa sổ 5 s), và **theo dõi trên ảnh** (ByteTrack, ghép box giữa hai khung theo độ chồng lấn; có hoặc không bù chuyển động camera bằng telemetry). **Sơ bộ** trên ba đoạn video thật SeaDronesSee-MOT có GPS, độ cao, hướng thật và nhãn người theo từng khung (Bảng 5.11).

**Bảng 5.11.** Xác nhận trên video thật, mô hình chính, 2 khung mỗi giây (`sds_mot_confirm.md`). **Sơ bộ.**

| Đoạn video | Cách xác nhận | Người được cảnh báo / đủ điều kiện | Cảnh báo | Nhầm | Lặp | Thời gian tới cảnh báo (s, trung vị) |
|---|---|---|---|---|---|---|
| v21, 40 m, 34 người | geo | 12 / 19 | 37 | 13 | 12 | 2,00 |
| | ByteTrack | 2 / 19 | 2 | 0 | 0 | 25,25 |
| | ByteTrack bù chuyển động | 2 / 19 | 4 | 0 | 2 | 21,00 |
| v5, 122–140 m, 6 người | geo | 6 / 6 | 9 | 3 | 0 | 1,00 |
| | ByteTrack | 6 / 6 | 11 | 0 | 5 | 1,50 |
| v13, 91 m, 2 người | geo | 2 / 2 | 4 | 0 | 2 | 3,00 |
| | ByteTrack | 1 / 2 | 2 | 0 | 1 | 1,00 |

(ByteTrack ở ngưỡng tạo track 0,1; ngưỡng 0,25 cho cùng số người được cảnh báo.)

Trên đoạn đông người nhất (v21), gom theo toạ độ mặt đất xác nhận được 12 trên 19 người, ByteTrack chỉ 2. **Nguyên nhân là tần số khung, không phải cách dùng tracker**: ở 2 khung mỗi giây, IoU giữa box thật của cùng một người ở hai khung liên tiếp có trung vị 0,46 (v21), 0,53 (v5) và chỉ 0,05 (v13), trong khi ở 30 khung mỗi giây là 0,93, 0,94 và 0,84. Drone trôi, xoay nhẹ, người bơi di chuyển và box nhỏ làm độ chồng lấn thấp ngay cả khi drone gần như đứng yên; cộng với recall mỗi khung thấp, ByteTrack gần như mỗi khung tạo track mới (v21: 314 lần ghép, 299 ID khác nhau). Chạy lại ở 10 khung mỗi giây thì ByteTrack hoạt động trở lại (12 trên 26 người).

Cái giá của geo là **cảnh báo lặp và cảnh báo nhầm**: một người bị tách thành nhiều cụm khi GPS thật trôi, và vật cố định được phát hiện lặp lại thành cảnh báo. Mục 5.3.5 xử lý cảnh báo lặp.

**Vì sao bù chuyển động bằng telemetry không đủ.** Có thể nghĩ dời box khung trước bằng chuyển động tính từ telemetry sẽ cứu được ByteTrack. Mô phỏng ở Bảng 5.12 cho thấy cách này gãy khi GPS nhiễu, và chỉ ra cơ chế: sai số của phép dời bằng **độ chênh nhiễu GPS giữa hai khung**, nên GPS càng nhảy nhanh (thời gian tương quan τ nhỏ) thì càng bỏ sót.

**Bảng 5.12.** Tỉ lệ bỏ sót theo nhiễu GPS, ở 50 m (`rq3_cmc_cause.md`). **Mô phỏng.**

| τ GPS | σ GPS | ByteTrack bù chuyển động | geo |
|---|---|---|---|
| 5 s | 0,5 m | 0,900 | 0,033 |
| 5 s | 1 m | 1,000 | 0,033 |
| 30 s | 0,5 m | 0,200 | 0,000 |
| 30 s | 1 m | 0,767 | 0,000 |
| 300 s | 0,5 m | 0,033 | 0,000 |
| 300 s | 1 m | 0,033 | 0,000 |

Geo gần như không bị ảnh hưởng (bỏ sót tối đa 0,033 ở mọi ô của lưới), vì nó so khoảng cách mặt đất với bán kính 3 m, rộng hơn nhiều so với độ chênh GPS giữa hai khung. Bù chuyển động bằng telemetry chỉ dùng được với GPS ổn định ngắn hạn (RTK, hoặc GPS đã lọc qua bộ ước lượng trạng thái của bộ điều khiển bay).

**Camera nghiêng.** Phép chiếu xuống mặt đất ban đầu giả định camera nhìn thẳng xuống. Mọi đoạn SeaDronesSee có drone di chuyển đều quay với gimbal nghiêng, nên phép chiếu được mở rộng để tính góc nghiêng và kiểm tra bằng độ tản vị trí của người gần như đứng yên (`georef_pitch.md`, **sơ bộ**). Kết quả lẫn lộn: tốt hơn rõ khi drone di chuyển với camera nghiêng vừa phải (ví dụ đoạn v8, pitch −48,0°: độ tản 4,982 m giảm còn 1,301 m), nhưng kém hơn khi camera gần chân trời và khi drone gần như đứng yên; tính chung trung vị độ tản tăng (1,336 lên 1,603 m) và chỉ 0,515 số track tốt hơn. Phép chiếu theo góc nghiêng vì vậy để tuỳ chọn, chưa bật mặc định.

**Trả lời RQ3b.** Khi chỉ xử lý vài khung mỗi giây, gom theo toạ độ mặt đất bền hơn theo dõi trên ảnh, cả trên video thật lẫn trong mô phỏng có nhiễu GPS. Đây là phần thứ ba của luận điểm xuyên suốt: telemetry của drone thay thế cho tính liên tục giữa các khung mà tracker trên ảnh cần. Giới hạn: ba đoạn video, drone gần như đứng yên; trường hợp drone bay nhanh vẫn dựa vào mô phỏng.

### 5.3.3. Sai số vị trí cảnh báo (RQ3c)

Mỗi cảnh báo mang toạ độ người và một bán kính sai số 1σ do hệ thống tự tính từ mô hình lan truyền sai số (chương 3: GPS 3 m, độ cao 2 m, hướng 2°, nghiêng 1° theo mặc định). Bảng 5.13 hỏi hai điều: vị trí lệch bao nhiêu khi GPS thật tốt hoặc tệ, và bán kính ghi kèm có chứa người thật không.

**Bảng 5.13.** Sai số vị trí ở cảnh báo đầu tiên của mỗi người, chỉ nhiễu GPS (`rq3_geoerr.md`). **Mô phỏng.**

| Độ cao | σ GPS | Sai số trung vị (m) | Trong bán kính 1σ | Trong vùng 95% | Bỏ sót |
|---|---|---|---|---|---|
| 50 m | 0 m | 0,250 | 1,000 | 1,000 | 0,000 |
| 50 m | 1 m | 1,282 | 1,000 | 1,000 | 0,000 |
| 50 m | 3 m | 3,956 | 0,278 | 1,000 | 0,033 |
| 50 m | 5 m | 6,591 | 0,181 | 0,833 | 0,100 |
| 100 m | 3 m | 4,275 | 0,274 | 1,000 | 0,033 |
| 100 m | 5 m | 7,362 | 0,241 | 0,763 | 0,033 |

**GPS là nguồn sai số chính**: sai số trung vị đi theo σ của GPS và gần như không đổi theo độ cao. **Vòng 1σ quá hẹp để đi tìm người**: khi GPS thật đúng bằng giả định (σ 3 m), chỉ khoảng một phần tư số người nằm trong bán kính 1σ (0,278 và 0,274). Điều này khớp lý thuyết: sai số hai chiều có phân bố Rayleigh, vòng 1σ chỉ chứa khoảng 39% xác suất. Vùng 95% (bán kính 2,448σ) chứa mọi người ở mọi ô có σ GPS không quá 3 m; vì vậy bản đồ ở trạm mặt đất vẽ **vùng tìm 95%**, không phải vòng 1σ. Khi GPS thật tệ hơn giả định (σ 5 m), vùng 95% không còn đủ (0,763–0,833): bán kính chỉ đúng khi mô hình sai số đặt theo GPS thật của drone. Đề tài vì vậy cho phép lấy σ GPS từ độ chính xác bộ thu tự báo ở từng khung. Trong mô phỏng, khi bộ thu báo đúng, vùng 95% chứa mọi người ở mọi ô, kể cả khi GPS kém đi giữa chuyến (σ cố định chỉ chứa 0,833–0,933 trong trường hợp này), và hẹp lại khi GPS tốt (50 m, σ 1 m: bán kính 8,069 xuống 4,141 m); nếu bộ thu báo lạc quan bằng nửa sai số thật thì vùng hẹp quá, chỉ còn 0,652–0,963 (`rq3_gpsacc.md`, **mô phỏng**).

**Lệch hướng bay gây tách nhầm khi bay cao.** Với GPS σ 1 m, la bàn lệch cố định 5° làm một người bị tách thành nhiều cảnh báo: trung bình 5,333 lần tách nhầm mỗi kịch bản ở 100 m, so với 0,333 ở 50 m (`rq3_geoerr.md`). Lệch hướng xoay toạ độ quanh điểm ngay dưới drone; bay càng cao thì cùng một góc lệch đẩy điểm chiếu đi càng xa, vượt bán kính gom 3 m. Trạm mặt đất gộp lại được phần này thành một sự cố (mục 5.3.5). Đề tài thêm một bước tự hiệu chỉnh trên UAV: khi bay thẳng, hướng di chuyển tính từ GPS là phép đo độc lập của hướng mũi máy, nên trung vị hiệu yaw − hướng di chuyển ước lượng được lệch la bàn (chương 3). Trong mô phỏng, lệch ước lượng sai tối đa 0,228° khi bay thẳng với GPS σ 1 m, và tách nhầm ở 100 m, lệch 5° giảm từ 5,333 xuống 0,333 mỗi kịch bản; khi la bàn không lệch, cái giá là sai số vị trí tăng nhẹ (1,387 lên 1,538 m) (`rq3_yawcalib.md`, **mô phỏng**). Đây thêm một ví dụ cho luận điểm xuyên suốt: chính telemetry của drone dùng để sửa telemetry.

Giới hạn: người đứng yên, camera nhìn thẳng xuống, detector giả có box đúng tâm người; người có cảnh báo lệch quá 10 m bị tính là bỏ sót và loại khỏi tỉ lệ "trong vùng", nên ở σ 5 m các tỉ lệ đó lạc quan.

### 5.3.4. Mất sóng và độ trễ cảnh báo (RQ3d)

Cảnh báo được ghi xuống đĩa trước khi gửi, và gửi lại với thời gian chờ tăng gấp đôi sau mỗi lần hỏng, trần 30 s (chương 3). Đề tài thêm **thăm dò đường truyền**: khi mọi gói đang chờ và đã 2 s không gửi gì, thử gửi gói toạ độ cũ nhất; gửi được thì gửi ngay mọi gói đang chờ. Bảng 5.14 so có và không thăm dò.

**Bảng 5.14.** Độ trễ cảnh báo tới trạm (`rq3_network.md`). **Mô phỏng.**

| Mất gói | Mất sóng | Thăm dò | Độ trễ trung vị (s) | Độ trễ lớn nhất (s) | Mất cảnh báo |
|---|---|---|---|---|---|
| 0 | không | không | 0,000 | 0,000 | 0,000 |
| 0 | 15–45 s | không | 8,667 | 36,500 | 0,000 |
| 0 | 15–45 s | có | 5,917 | 27,500 | 0,000 |
| 0,5 | không | không | 0,250 | 41,167 | 0,000 |
| 0,5 | không | có | 1,167 | 8,333 | 0,000 |
| 0,5 | 20–35 s | không | 3,000 | 48,000 | 0,033 |
| 0,5 | 20–35 s | có | 3,417 | 17,333 | 0,000 |
| 0,5 | 15–45 s | không | 10,583 | 60,500 | 0,000 |
| 0,5 | 15–45 s | có | 9,000 | 29,167 | 0,000 |

**Khi có thăm dò thì không mất cảnh báo nào**, kể cả mất một nửa số gói cộng 30 s mất sóng; không thăm dò thì có một ô mất 0,033 (một cảnh báo trong ba kịch bản không tới trạm sau 60 s gửi bù). **Độ trễ trung vị nhỏ; độ trễ lớn nhất mới là vấn đề**: với thời gian chờ tăng gấp đôi, một gói hỏng ngay trước khi sóng có lại có thể đợi thêm gần 30 s. Thăm dò cắt phần chờ thừa đó (mất gói 0,5: độ trễ lớn nhất 41,167 s còn 8,333 s) mà gần như không tốn thêm dữ liệu (2,647 so với 2,629 KB mỗi cảnh báo khi mất sóng 20–35 s), vì mỗi lần thăm dò chỉ là một gói toạ độ. Phần trễ còn lại khi đã thăm dò chủ yếu là chính khoảng mất sóng: cảnh báo tạo trong lúc mất sóng không thể tới trạm trước khi sóng có lại.

**Mất theo cụm.** Bảng 5.14 giả định mỗi lần gửi mất độc lập. Sóng yếu thật thường kéo dài, nên mô phỏng thêm mất theo cụm (mô hình Gilbert–Elliott: đường truyền đổi qua lại giữa trạng thái tốt và xấu, trạng thái xấu mất mọi gói) và so với mất rải rác ở **cùng tỉ lệ mất trung bình** (Bảng 5.14b; chuyến 120 s, 5 seed, nên không so thẳng với Bảng 5.14).

**Bảng 5.14b.** Mất rải rác so với mất theo cụm, tỉ lệ mất trung bình 0,5, có thăm dò (`rq3_burst.md`). **Mô phỏng.**

| Cách mất | Độ trễ trung vị (s) | Độ trễ lớn nhất (s) | Mất cảnh báo |
|---|---|---|---|
| Rải rác 0,5 | 0,850 | 8,400 | 0,000 |
| Cụm xấu 10 s / tốt 10 s | 4,350 | 15,800 | 0,000 |
| Cụm xấu 30 s / tốt 30 s | 19,900 | 44,400 | 0,000 |

Cùng tỉ lệ mất, cụm càng dài cảnh báo càng trễ, vì mọi lần gửi trong cụm đều hỏng; phần trễ này là chính độ dài cụm, không cách gửi lại nào rút ngắn được. Thăm dò vẫn giữ không mất cảnh báo nào ở mọi ô; không thăm dò thì các ô cụm 30 s mất 0,080–0,180 số cảnh báo.

Giới hạn: không có số đo mạng thật để chọn độ dài cụm; số seed ít so với độ dao động của cụm dài, nên độ trễ lớn nhất dao động mạnh giữa các seed (độ lệch chuẩn ở `rq3_network.md`, `rq3_burst.md`).

### 5.3.5. Gộp cảnh báo thành sự cố (RQ3e)

Geo sinh cảnh báo lặp (Bảng 5.11). Hai cách giảm lặp được so sánh trên ba đoạn video thật:

- **Bỏ ở thiết bị biên**: cảnh báo mới nằm trong 3 m quanh một cảnh báo đã gửi trong 60 s thì không gửi. Cách này giảm lặp (v21: 12 xuống 7) nhưng **mất người**: v21 còn 10 thay vì 12 người được cảnh báo, vì người bơi gần nhau bị coi là một (`alert_memory.md`).
- **Gộp ở trạm mặt đất**: mọi cảnh báo vẫn được gửi, trạm gắn mỗi cảnh báo vào sự cố gần nhất còn mở. Không cảnh báo nào bị bỏ; người vận hành mở sự cố vẫn thấy từng cảnh báo và ảnh cắt.

**Bảng 5.15.** Gộp cảnh báo geo thành sự cố ở trạm, theo bán kính gộp (`alert_memory.md`).

| Đoạn video | Bán kính gộp | Cảnh báo | Sự cố | Sự cố lẫn hơn một người | Người bị tách |
|---|---|---|---|---|---|
| v21 (12 người được báo) | 3 m | 37 | 27 | 6 | 6 |
| | 5 m | 37 | 19 | 5 | 6 |
| | 10 m | 37 | 10 | 3 | 3 |
| v5 (6 người) | 3 m | 9 | 9 | 0 | 0 |
| | 5 m | 9 | 8 | 0 | 0 |
| | 10 m | 9 | 4 | 2 | 0 |
| v13 (2 người) | 3 m | 4 | 3 | 0 | 1 |
| | 5 m | 4 | 2 | 0 | 0 |
| | 10 m | 4 | 1 | 1 | 0 |

Bán kính 5 m được chọn làm mặc định: hai đoạn thưa người gộp đúng hoàn toàn (v13 hết lặp, v5 không lẫn người), đoạn đông người v21 giảm 37 cảnh báo xuống 19 sự cố. Ở v21 không bán kính nào vừa hết tách vừa hết lẫn, vì người bơi sát nhau hơn độ trôi của vị trí: đó là giới hạn của định vị, không chữa được bằng luật gộp. Vì gộp ở trạm không bỏ cảnh báo nào, cái giá là hiển thị gộp nhóm chứ không phải mất người. Với cứu hộ, bỏ sót một người đắt hơn nhiều một cảnh báo thừa, nên đề tài **giữ mọi cảnh báo ở biên và gộp ở trạm**.

Giới hạn: ba đoạn video, đối chiếu với nhãn trong không gian ảnh; luật gộp theo sai số ghi kèm cảnh báo chưa thử được vì lúc chạy bán kính sai số còn là hằng số.

**Số người mỗi sự cố.** Gộp ở trạm làm một nhóm người thành một sự cố, nên mỗi cảnh báo mang ước tính số người trong 5 m (chương 3); sự cố giữ số lớn nhất. Đếm theo phát hiện của khung xác nhận hụt khi detector bỏ sót vài người của nhóm ở đúng khung đó; đếm thêm các cụm đã thấy ít nhất hai lần gần đây sửa được phần lớn. Trong mô phỏng người theo nhóm 4 người, recall 0,7, tỉ lệ cảnh báo đúng số người tăng từ 0,303 lên 0,524 (recall 0,9: 0,533 lên 0,900), với người lẻ không đổi (**mô phỏng**). Nhưng trên đoạn video thật đông người v21, cách đếm này kém hơn đếm theo khung (đúng số người 0,792 xuống 0,583, đếm thừa 8 trên 24 cảnh báo): vị trí một người trôi theo GPS nên người đó bị tách thành nhiều cụm, và các cụm thừa bị đếm như người khác (`rq3_group.md`). Một cách thứ ba (số người thấy cùng lúc ở ít nhất hai khung) tránh được đếm thừa đó nhưng cũng không hơn (0,750). Đề tài giữ đếm theo khung. Đây là một ví dụ mô phỏng bỏ qua đúng hiện tượng quyết định kết quả, nên mọi kết luận mô phỏng ở chương này cần được đọc cùng phần kiểm chứng trên video thật.

## 5.4. Luận điểm xuyên suốt: dữ liệu bay giúp cả ba khâu

Ba kết quả ở ba câu hỏi có chung một cơ chế: **dùng telemetry sẵn có của drone (độ cao, GPS, hướng) thay cho một giả định cố định**.

- **Phát hiện (RQ1d):** độ cao cho biết người sẽ to bao nhiêu pixel, nên chọn được mức thu nhỏ đưa người về cỡ mô hình làm tốt. Trên SeaDronesSee 4K, cách này nâng AP50 của mô hình chính khi cắt ô từ 0,235 lên 0,531 (Bảng 5.8).
- **Tốc độ (RQ2c):** cùng mức thu nhỏ đó giảm số ô phải chạy; cùng độ cao và vận tốc cho biết cần bao nhiêu khung mỗi giây (Bảng 5.10). Trên khung 4K, số ô giảm từ 32 xuống 6 và tổng thời gian trung vị với FP16 từ 120,57 ms xuống 77,34 ms trên T4 (Bảng 5.8a), đồng thời AP50 tăng.
- **Xác nhận (RQ3b):** GPS và hướng cho phép ghép các lần thấy theo toạ độ mặt đất, không cần box chồng lấn giữa hai khung; nhờ đó xác nhận được người ở 2 khung mỗi giây, nơi tracker trên ảnh gãy (Bảng 5.11, 5.12).

Mặt trái của luận điểm cũng phải nêu: hệ thống phụ thuộc vào chất lượng telemetry. GPS tệ hơn giả định làm vùng tìm 95% không còn đủ (Bảng 5.13), la bàn lệch gây tách nhầm khi bay cao, và góc gimbal nhiễu làm phép chiếu theo góc nghiêng kém hơn ở một số đoạn (mục 5.3.2). Khi không có telemetry, như tập ảnh lũ, không dùng được thu nhỏ theo độ cao và kết quả chỉ còn phụ thuộc detector (mục 5.1.1).

## 5.5. Phân tích lỗi

Các khung minh hoạ lấy theo ba quy tắc ghi trước khi khoá (`tools/demo_panels.py`, chương 4), so mô hình gốc với mô hình chính: khung nhiều người nhỏ nhất (`thainguyen_002160`, 69 người đều dưới 16 px: mô hình gốc thấy 11, mô hình chính 27 nhưng thêm 42 báo nhầm so với 7), khung tiêu biểu (`nidarx_000300`) và khung nhiều lỗi nhất (`nidarx_000600`, 67 người: mô hình gốc thấy 7, mô hình chính 19) (`runs/demo/flood_panels/picks.csv`). [Hình 5.x: ba khung, chèn khi dàn trang.]

Loại lỗi lớn nhất về số lượng không phải của mô hình mà của nhãn: đám đông nhìn rõ trong khung `thainguyen_003120` không được gán (mục 5.1.1). Theo hướng dẫn, đám đông không tách được từng người phải được phủ bằng vùng bỏ qua; khung này bị để trống. Một khung khác cùng video (`thainguyen_000144`) cũng không có nhãn và có 17 box conf ≥ 0,25 của mô hình chính; khung này chưa được xem lại. Báo nhầm còn lại tập trung ở video 480p Thái Nguyên, nơi người dưới 16 px và mô hình tinh chỉnh bắn nhiều box nhỏ; phân tích lỗi theo từng ảnh cắt chưa làm.

Hai loại báo nhầm đã thấy trên dữ liệu có nước, ghi lại để đối chiếu: trên AFO, ván, thuyền và vật nổi bị gọi là người (precision vận hành của mô hình gốc 0,300, `afo_E1_E2.md`); trên SeaDronesSee, vật cố định được phát hiện lặp lại thành cảnh báo nhầm (v21: 13 trên 37 cảnh báo, Bảng 5.11).

## 5.6. Minh hoạ hệ thống

Phần này không đo gì mới; nó cho thấy các thành phần chạy cùng nhau thành một hệ thống.

- **Chuyến bay mô phỏng quét vùng lũ** (chương 3): drone bay zíc zắc, ảnh được dựng từ một cảnh lũ tổng hợp có mái nhà, cây, vật trôi và người, pipeline trên thiết bị biên chạy đúng như với video thật, trạm mặt đất hiện vị trí drone, vùng đã quét, cảnh báo và vùng tìm 95% trên bản đồ. Vì biết trước vị trí người, bản đồ đối chiếu được từng sự cố với người thật: tìm đúng, người nằm trong vùng tìm, bỏ sót, báo nhầm.
- **Video thật SeaDronesSee** với telemetry thật: cùng giao diện, cảnh báo trên ảnh 4K thật.
- **Hai drone** cùng gửi về một trạm (`multi_uav_demo.md`, **minh hoạ**): 37 cảnh báo mỗi drone gộp thành 20 sự cố, 18 sự cố có cả hai drone cùng thấy; hai drone phát lại cùng một đoạn video, chỉ khác GPS, nên đây là kiểm tra luồng dữ liệu, không phải đo độ chính xác gộp.
- **Sân thử** trong giao diện thử nghiệm: đổi độ cao, vận tốc, GPS, mạng, thiết bị, chạy lại chuyến bay và so các lần chạy cạnh nhau.

[Hình 5.x: ảnh chụp màn hình điều phối khi đang quét; Hình 5.y: bản đồ sau chuyến bay với lớp đối chiếu. Chụp khi dàn trang, từ `scripts/demo_bao_ve.sh`.]

## Tóm tắt chương

- **Câu hỏi 1.** Dữ liệu huấn luyện quyết định nhiều nhất cho người nhỏ; kiến trúc (P2) và cắt ô trên ảnh độ phân giải vừa giúp rất ít. Mô hình tinh chỉnh yếu với người to; thu nhỏ theo độ cao bù được trên SeaDronesSee. Thêm ảnh thảm hoạ người to theo cách đơn giản làm mất người nhỏ. Trên tập ảnh lũ, tinh chỉnh tăng recall người nhỏ nhưng không tăng AP50: mô hình gốc thận trọng hơn và giữ AP50 cao nhất, kể cả khi bỏ một khung thiếu nhãn; thứ hạng trên ảnh lũ giống SeaDronesSee hơn VisDrone; không đo được ảnh hưởng riêng của loá, nhoè, vật trôi.
- **Câu hỏi 2.** Trên T4, TensorRT FP16 nhanh hơn PyTorch 1,833–3,028 lần mà gần như không mất độ chính xác; INT8 nhanh thêm ít và nén độ tin cậy, mất một nửa recall vận hành ở người dưới 8 px với ngưỡng hiện tại. Cấu hình được chọn là FP16 với thu nhỏ theo độ cao, nằm trên biên Pareto với recall cao nhất. Khâu tốn thời gian nhất của nó là thu nhỏ khung 4K, không phải suy luận; theo ước lượng, thiết bị yếu thiếu sức đúng lúc bay thấp.
- **Câu hỏi 3.** Trong mô phỏng và trên ba đoạn video thật: gom theo toạ độ mặt đất bền hơn theo dõi trên ảnh ở 2 khung mỗi giây; tần số theo độ cao giảm bỏ sót khi bay thấp và giảm tính toán khi bay cao; vùng tìm 95% chứa người thật khi GPS không tệ hơn giả định; thăm dò đường truyền giữ không mất cảnh báo và cắt độ trễ lớn nhất; gộp ở trạm giảm lặp mà không bỏ cảnh báo.
