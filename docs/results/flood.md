# Tập test lũ: phát hiện người theo nhóm cỡ (khoá 24/11/2026)

Câu hỏi 1 trên dữ liệu đích: năm mô hình đã chốt trước (mô hình nền, ba mô hình tinh chỉnh, mô hình chính cộng cắt ô) phát hiện người trong ảnh UAV vùng lũ tốt đến đâu, theo nhóm cỡ người. Mỗi cấu hình chạy **một lần** trên tập này, sau khi khoá; không tham số nào chọn trên tập này.

## Khoá tập

- Khoá lúc 24/11/2026 01:23 (+07), sớm hơn hạn đề xuất 25/11. `data/processed/flood/MANIFEST.sha256`: 566 file (ảnh, nhãn, vùng bỏ qua, `boxes_test.csv`, `tags_test.csv`). Mã băm của chính file MANIFEST: `cd85a903aead33868ea05181ba9fd298248c41e3fb5c960c2f28f220afebbd87`.
- Nguồn nhãn: bốn file xuất CVAT trong `exports/`: `01_washington.zip`, `02_thainguyen.zip`, `03_sanangelo.zip` (xuất 22/11), `04-10_con_lai.zip` (task gộp bảy video, xuất 23/11). Texas và Huế (hue-BIxBHs0dZ3s) được gán hai lần, trong task gộp và trong hai task riêng; **bản chấm là bản trong task gộp** (chốt trước khi chạy mô hình); hai task riêng giữ ở `exports/hai_lan_gan_2311/` để đo độ nhất quán (mục cuối).
- Kiểm rò rỉ ngay trước khoá (`runs/leakage/flood_test`): 188 ảnh, 10 video; tập huấn luyện 16.193 ảnh; 0 video chung, 0 cặp gần trùng (≤ 5 bit).

## Môi trường

RTX 5060 trên WSL, Python 3.12.3, ultralytics 8.4.174, torch 2.14.1; mã ở commit `5600add`, `dirty: false` (`run_config.json` của từng lần chạy). Thời gian trên máy này không phải số liệu thiết bị biên và không dùng ở đây.

| Mã | Mô hình | Cách chạy | Trọng số (sha256, 12 ký tự đầu) |
|---|---|---|---|
| E1 | YOLO26s gốc (COCO) | Toàn ảnh, imgsz 1280 | `646f8bc3fe0a` |
| E2 | Tinh chỉnh trên VisDrone | Toàn ảnh, imgsz 1280 | `eb43853e80f6` |
| E2c | Tinh chỉnh trên VisDrone + AFO (mô hình chính) | Toàn ảnh, imgsz 1280 | `e8b6439bf831` |
| E3 | Như E2c, thêm nhánh P2 | Toàn ảnh, imgsz 1280 | `7cda484a08a4` |
| E4tiled | E2c + cắt ô 640, chồng 0,2, thêm lượt toàn ảnh 1280 | `scripts/run_tiled.py` | `e8b6439bf831` |

Cấu hình: `configs/experiments/<Mã>_flood.yaml`. Quy ước đo như mọi tập: conf 0,001, `max_det` 1000; recall và precision vận hành ở conf 0,25; IoU 0,5, thêm IoU 0,3 cho nhóm dưới 8 px; vùng bỏ qua; khoảng tin cậy bootstrap 1.000 lần theo nguồn (9 cụm; texas và sanangelo một cụm).

## Dữ liệu (Bảng 4.4)

| Video | Khung | Độ phân giải | Người | < 8 px | 8–16 px | 16–32 px | > 32 px | Khung không có người |
|---|---|---|---|---|---|---|---|---|
| duvall-2HE-TIf4Lk0 | 15 | 854×480 | 0 | 0 | 0 | 0 | 0 | 15 |
| hue-BIxBHs0dZ3s | 22 | 1920×1080 | 51 | 2 | 27 | 21 | 1 | 7 |
| hue-short-Ak83K9FSBTY | 23 | 1080×1920 | 35 | 4 | 5 | 16 | 10 | 9 |
| mientrung-short-A-i9t2kJMlU | 23 | 1080×1920 | 0 | 0 | 0 | 0 | 0 | 23 |
| nidarx-flood-1 | 8 | 1920×1080 | 241 | 22 | 116 | 81 | 22 | 0 |
| sanangelo-police | 15 | 1280×720 | 5 | 0 | 0 | 0 | 5 | 13 |
| texas-xBvDRr6vy-k | 15 | 1280×720 | 21 | 3 | 4 | 3 | 11 | 7 |
| thainguyen-6W-QUHCh4ok | 29 | 854×480 | 98 | 57 | 41 | 0 | 0 | 20 |
| vn-tuoitre-1 | 8 | 1920×1080 | 5 | 0 | 3 | 2 | 0 | 6 |
| washington-D4xd0xNP9Gg | 30 | 1920×1080 | 53 | 0 | 9 | 13 | 31 | 9 |
| **Tổng** (9 nguồn, 10 video) | 188 | | 509 | 88 | 205 | 136 | 80 | 109 |

Thuộc tính: người ngập một phần 70, người bị che 68. Thẻ ảnh: loá nước 42 khung, mưa/sương/tối 1, nhoè 54, vật trôi 117. Vùng bỏ qua: 0.

## Kết quả trên tập đã khoá, IoU 0,5

Nguồn: `runs/flood/bang.md` (từ `runs/flood/eval_<Mã>_iou0.5/eval_by_size.csv`, cột cuối từ `eval_<Mã>_iou0.3`). Trong ngoặc: khoảng tin cậy 95%.

| Mô hình | Chỉ số | Tất cả | <8 px | 8–16 px | 16–32 px | >32 px | < 8 px, IoU 0,3 |
|---|---|---|---|---|---|---|---|
| Mô hình nền (E1) | AP50 | 0,269 (0,183–0,411) | 0,123 (0,015–0,258) | 0,124 (0,092–0,182) | 0,332 (0,182–0,585) | 0,661 (0,515–0,911) | 0,298 (0,070–0,414) |
|  | Recall | 0,216 (0,164–0,332) | 0,057 (0,000–0,085) | 0,098 (0,067–0,159) | 0,279 (0,147–0,522) | 0,588 (0,429–0,781) | 0,091 (0,000–0,119) |
| Tinh chỉnh VisDrone (E2) | AP50 | 0,147 (0,062–0,313) | 0,068 (0,012–0,150) | 0,073 (0,049–0,253) | 0,249 (0,063–0,530) | 0,402 (0,225–0,681) | 0,228 (0,076–0,313) |
|  | Recall | 0,283 (0,207–0,440) | 0,216 (0,043–0,667) | 0,229 (0,123–0,437) | 0,375 (0,209–0,625) | 0,338 (0,151–0,691) | 0,398 (0,099–0,728) |
| Mô hình chính (E2c) | AP50 | 0,148 (0,070–0,334) | 0,083 (0,043–0,319) | 0,082 (0,061–0,202) | 0,233 (0,060–0,532) | 0,434 (0,282–0,687) | 0,308 (0,131–0,468) |
|  | Recall | 0,244 (0,186–0,364) | 0,182 (0,054–0,591) | 0,205 (0,117–0,356) | 0,316 (0,194–0,625) | 0,287 (0,128–0,571) | 0,398 (0,100–0,773) |
| Thêm P2 (E3) | AP50 | 0,162 (0,079–0,332) | 0,097 (0,024–0,181) | 0,094 (0,071–0,251) | 0,227 (0,042–0,482) | 0,468 (0,324–0,735) | 0,279 (0,093–0,383) |
|  | Recall | 0,240 (0,173–0,345) | 0,171 (0,014–0,429) | 0,220 (0,133–0,374) | 0,287 (0,163–0,472) | 0,287 (0,096–0,611) | 0,364 (0,071–0,714) |
| Mô hình chính + cắt ô (E4tiled) | AP50 | 0,161 (0,058–0,315) | 0,048 (0,015–0,302) | 0,098 (0,066–0,239) | 0,251 (0,049–0,449) | 0,376 (0,218–0,620) | 0,237 (0,080–0,521) |
|  | Recall | 0,295 (0,227–0,445) | 0,171 (0,056–0,706) | 0,263 (0,145–0,491) | 0,404 (0,200–0,583) | 0,325 (0,175–0,611) | 0,398 (0,115–1,000) |
| | Số người | 509 | 88 | 205 | 136 | 80 | 88 |

Precision ở conf 0,25 (nhóm tất cả): E1 0,615; E2 0,262; E2c 0,287; E3 0,305; E4tiled 0,209.

### So cặp (bootstrap cặp theo nguồn, B − A; * có ý nghĩa)

Nguồn: `runs/flood/compare_<A>_<B>_iou<iou>/compare.csv`; đủ các nhóm ở `runs/flood/bang.md`.

| So sánh | IoU | Nhóm | Hiệu AP50 | p | Hiệu recall | p |
|---|---|---|---|---|---|---|
| E2c − E1 | 0,5 | Tất cả | −0,120 (−0,191 đến −0,020) * | 0,004 | +0,028 (−0,101 đến +0,120) | 0,544 |
| E2c − E1 | 0,5 | <8 px | −0,041 (−0,084 đến +0,178) | 0,558 | +0,125 (+0,043 đến +0,591) * | 0,008 |
| E2c − E1 | 0,5 | 8–16 px | −0,042 (−0,057 đến +0,037) | 0,450 | +0,107 (+0,014 đến +0,213) * | 0,050 |
| E2c − E1 | 0,3 | <8 px | +0,010 (−0,031 đến +0,238) | 0,690 | +0,307 (+0,060 đến +0,773) * | 0,008 |
| E2c − E2 | 0,5 | Tất cả | +0,002 (−0,010 đến +0,048) | 0,680 | −0,039 (−0,084 đến −0,011) * | 0,024 |
| E2c − E2 | 0,3 | <8 px | +0,080 (+0,044 đến +0,291) * | 0,004 | 0,000 (−0,100 đến +0,133) | 1,000 |
| E3 − E2c | 0,5 | Tất cả | +0,014 (−0,030 đến +0,024) | 0,322 | −0,004 (−0,038 đến +0,010) | 0,764 |
| E4tiled − E2c | 0,5 | Tất cả | +0,013 (−0,073 đến +0,030) | 0,908 | +0,051 (+0,014 đến +0,079) * | 0,000 |
| E4tiled − E2c | 0,5 | 8–16 px | +0,016 (−0,053 đến +0,069) | 0,376 | +0,059 (0,000 đến +0,245) | 0,064 |

## Một khung thiếu nhãn (phát hiện sau khoá) và phân tích độ nhạy

Khung `thainguyen-6W-QUHCh4ok_003120` chụp một đám đông đứng trên đường ngập, nhìn thấy rõ nhiều người, nhưng **không có nhãn nào** (cả ba bản xuất của task thainguyen 12/11, 22/11 sáng và chiều đều trống; không có vùng bỏ qua). Phát hiện khi tìm nguồn báo nhầm sau khi chấm. Theo quy tắc khoá, nhãn **không sửa**; số chính vẫn là số của tập đã khoá ở trên, và khung này ghi vào phần giới hạn.

Số dự đoán conf ≥ 0,25 trên khung này (`runs/flood/nhay_bo_003120/khung_003120.csv`): E1 14, E2 167, E2c 152, E3 135, E4tiled 151. Với các mô hình tinh chỉnh, đó là khoảng một phần ba số dự đoán conf ≥ 0,25 của cả tập (E2c: 152 trên 432), và tất cả bị tính là báo nhầm.

Phân tích độ nhạy: chấm lại y hệt nhưng bỏ riêng khung này (187 khung; số người không đổi vì khung không có nhãn, nên recall không đổi). Lý do bỏ kiểm được từ ảnh và nhãn, không phụ thuộc mô hình nào tốt hơn. Nguồn: `runs/flood/nhay_bo_003120/bang.md`.

| Mô hình | AP50 tất cả, tập khoá | AP50 tất cả, bỏ 003120 | Precision, tập khoá | Precision, bỏ 003120 |
|---|---|---|---|---|
| E1 | 0,269 (0,183–0,411) | 0,286 (0,224–0,411) | 0,615 | 0,667 |
| E2 | 0,147 (0,062–0,313) | 0,220 (0,141–0,340) | 0,262 | 0,377 |
| E2c | 0,148 (0,070–0,334) | 0,233 (0,165–0,349) | 0,287 | 0,443 |
| E3 | 0,162 (0,079–0,332) | 0,248 (0,175–0,341) | 0,305 | 0,460 |
| E4tiled | 0,161 (0,058–0,315) | 0,219 (0,128–0,332) | 0,209 | 0,265 |

| So sánh, bỏ 003120 | IoU | Nhóm | Hiệu AP50 | p |
|---|---|---|---|---|
| E2c − E1 | 0,5 | Tất cả | −0,053 (−0,166 đến −0,001) * | 0,050 |
| E2c − E1 | 0,5 | <8 px | −0,033 (−0,074 đến +0,178) | 0,568 |
| E2c − E1 | 0,3 | Tất cả | −0,033 (−0,230 đến +0,069) | 0,482 |
| E2c − E1 | 0,3 | <8 px | +0,047 (+0,018 đến +0,238) * | 0,002 |
| E4tiled − E2c | 0,5 | Tất cả | −0,014 (−0,076 đến +0,015) | 0,280 |

## Theo loại nhiễu, mô hình chính (E2c), IoU 0,5

Nguồn: `runs/flood/eval_tags/recall_by_tag.csv` (tập khoá).

| Tập con | Số người | Recall (conf 0,25) | Số khung | Báo nhầm mỗi khung |
|---|---|---|---|---|
| tất cả | 509 | 0,244 (0,186–0,364) | 188 | 1,638 (0,309–3,624) |
| Loá nước | 184 | 0,321 (0,000–0,429) | 42 | 1,738 (0,222–4,408) |
| Mưa, sương, tối | 4 | 0,500 (0,500–0,500) | 1 | 1,000 (1,000–1,000) |
| Nhoè | 223 | 0,305 (0,146–0,469) | 54 | 1,407 (0,257–4,709) |
| Vật trôi | 213 | 0,324 (0,164–0,447) | 117 | 0,863 (0,250–1,855) |
| ảnh không thẻ | 262 | 0,191 (0,000–0,204) | 58 | 3,534 (0,100–6,392) |
| Người ngập một phần | 70 | 0,243 (0,048–0,461) | | |
| Người bị che | 68 | 0,279 (0,136–0,535) | | |
| người không thuộc tính | 373 | 0,236 (0,165–0,362) | | |

Khung 003120 không có thẻ, nên nằm trong nhóm "ảnh không thẻ" và đẩy số báo nhầm mỗi khung của nhóm này lên.

## Độ nhất quán khi gán hai lần (Texas và Huế, 37 khung)

Hai bản nhãn của cùng 37 khung (task gộp và task riêng), `tools/relabel_agreement.py`, ghép ở IoU 0,5 (`runs/flood/hai_lan_gan/agreement.csv`, `tags.csv`). **Hai lần gán cùng ngày 23/11**, không cách hai ngày như LABELING mục 7, và không ghi lại việc lần sau có nhìn lần trước hay không; số này chỉ là chỉ báo, không thay cho phép đo gán lại theo mục 7 (không làm).

| Nhóm | Người (bản chấm) | Khớp | Khớp ở IoU 0,3 | Chỉ bản chấm | Chỉ bản kia | IoU trung vị | Lệch mép lớn nhất, trung vị (px) |
|---|---|---|---|---|---|---|---|
| tất cả | 72 | 58 | 61 | 14 | 10 | 0,738 | 3,890 |
| <8 px | 5 | 3 | 3 | 2 | 0 | 0,630 | 2,770 |
| 8–16 px | 31 | 21 | 22 | 10 | 4 | 0,656 | 2,960 |
| 16–32 px | 24 | 22 | 24 | 2 | 5 | 0,725 | 3,765 |
| >32 px | 12 | 12 | 12 | 0 | 1 | 0,794 | 6,015 |

Thuộc tính trên người khớp: ngập một phần trùng 0,500, bị che 0,655. Thẻ trùng: loá 0,649 (13 khung so với 0), mưa/sương 1,000, nhoè 0,892, vật trôi 0,595 (36 so với 21).

## Nhận xét

- **Tinh chỉnh không nâng AP50 trên ảnh lũ, khác với VisDrone và SeaDronesSee** (`visdrone_E2.md`, `sds_det.md`, `E2c.md`). Trên tập khoá, E1 cao hơn E2c về AP50 toàn tập (hiệu −0,120, có ý nghĩa). Phần lớn khoảng cách này đến từ khung thiếu nhãn: bỏ khung đó, hiệu còn −0,053, vẫn có ý nghĩa nhưng sát ngưỡng (p 0,050). Kết quả trái với dự đoán trong ROADMAP; đã kiểm cấu hình (cùng imgsz 1280, conf 0,001, cùng quy ước như các tập khác) và tìm ra khung thiếu nhãn, không thấy lỗi cấu hình.
- **Tinh chỉnh đổi precision lấy recall ở người nhỏ.** Recall vận hành của E2c cao hơn E1 có ý nghĩa ở <8 px (+0,125; ở IoU 0,3 +0,307) và 8–16 px (+0,107, p 0,050); E1 thận trọng hơn: precision 0,615 so với 0,287, và mạnh hơn có ý nghĩa ở người > 32 px (hiệu AP50 E2c − E1 −0,226, khoảng −0,280 đến −0,149; hiệu recall −0,300; `compare_E1_E2c_iou0.5/compare.csv`), giống điểm yếu với người to đã thấy trên SeaDronesSee (`scale_by_altitude.md`). Ở IoU 0,3 và bỏ khung thiếu nhãn, AP50 nhóm <8 px của E2c cao hơn E1 có ý nghĩa (+0,047).
- **Dưới 8 px vẫn là giới hạn:** recall vận hành cao nhất ở nhóm này là 0,216 (E2), khoảng tin cậy rất rộng.
- **P2 (E3) không khác E2c** ở nhóm nào (mọi hiệu không có ý nghĩa), như trên VisDrone và SeaDronesSee.
- **Cắt ô (E4tiled)** tăng recall vận hành toàn tập (+0,051, có ý nghĩa) nhưng không tăng AP50 và có precision thấp nhất (0,209).
- **Theo loại nhiễu:** khoảng tin cậy quá rộng để kết luận thẻ nào làm giảm recall; khung loá, nhoè, vật trôi không có recall thấp hơn toàn tập.

## Giới hạn

- Khung 003120 thiếu nhãn (mục trên). Khung `thainguyen-6W-QUHCh4ok_000144` cũng không có nhãn và có 17 dự đoán conf ≥ 0,25 của E2c; chưa xem ảnh, không biết là thiếu nhãn hay báo nhầm. Không rà lại các khung trống khác sau khoá.
- Không có vùng bỏ qua nào; đám đông khó tách người (nidarx, thainguyen) được gán từng hộp hoặc không gán.
- nidarx-flood-1 chiếm 241/509 người trong 8 khung, nên nặng ký trong số chung; bootstrap theo 9 nguồn làm khoảng tin cậy rộng.
- Hai video (duvall, miền Trung) không có người nào: chỉ đóng góp báo nhầm.
- Không gán lại 20 khung theo LABELING mục 7; chỉ có phép đo hai lần gán cùng ngày ở trên.
- Một người gán nhãn; thẻ ảnh (loá, vật trôi) lệch nhiều giữa hai lần gán.

## Ảnh trình bày

`tools/demo_panels.py`, ba quy tắc ghi trước khoá (`docs/DEMO_BAO_VE.md`), E1 so với E2c, `runs/demo/flood_panels/picks.csv`: `nho_nhat` thainguyen-6W-QUHCh4ok_002160, `tieu_bieu` nidarx-flood-1_000300, `loi` nidarx-flood-1_000600. Không khung chỉ định thêm.

## Tái lập

```bash
.venv/bin/python tools/convert_cvat.py --xml exports/*.zip --images data/raw/flood/frames --dst data/processed/flood --split test
.venv/bin/python tools/check_leakage.py --train data/processed/visdrone/images/train data/processed/afo/images/train \
    data/processed/hydrovigilance/images/train data/processed/hydrovigilance/images/val data/processed/c2a/images/train \
    --eval data/processed/flood/images/test --output runs/leakage/flood_test
(cd data/processed/flood && find -L images/test labels/test ignore/test boxes_test.csv tags_test.csv -type f | sort \
    | xargs sha256sum > MANIFEST.sha256)
scripts/eval_flood.sh exports/ E1 E2 E2c E3 E4tiled          # -> runs/flood/bang.md
.venv/bin/python tools/demo_panels.py --images data/processed/flood/images/test --labels data/processed/flood/labels/test \
    --ignore data/processed/flood/ignore/test --run-a runs/flood/E1 --run-b runs/flood/E2c \
    --title-a "YOLO26s gốc" --title-b "Đã tinh chỉnh (E2c)" --output runs/demo/flood_panels
.venv/bin/python tools/relabel_agreement.py --orig exports/04-10_con_lai.zip \
    --relabel exports/hai_lan_gan_2311/05_texas_task_rieng.zip exports/hai_lan_gan_2311/06_hue_task_rieng.zip \
    --output runs/flood/hai_lan_gan

# Phân tích độ nhạy: bỏ khung 003120 khỏi ảnh và dự đoán, chấm lại y hệt
N=runs/flood/nhay_bo_003120; X=thainguyen-6W-QUHCh4ok_003120; D=data/processed/flood
CLUSTER='^(?:sanangelo-police|texas-xBvDRr6vy-k)?(.*?)_\d+$'
mkdir -p $N/images
for f in $D/images/test/*; do b=$(basename $f); [ "${b%.*}" = $X ] || ln -s $(realpath $f) $N/images/$b; done
for e in E1 E2 E2c E3 E4tiled; do mkdir -p $N/$e; cp runs/flood/$e/run_config.json $N/$e/
  for f in per_image.csv boxes.csv; do grep -v "^$X" runs/flood/$e/$f > $N/$e/$f; done
  for iou in 0.5 0.3; do .venv/bin/python eval/eval_by_size.py --runs $N/$e --images $N/images --labels $D/labels/test \
      --ignore $D/ignore/test --iou $iou --cluster-pattern "$CLUSTER" --output $N/eval_${e}_iou$iou; done; done
for pair in "E1 E2" "E2 E2c" "E1 E2c" "E2c E3" "E2c E4tiled"; do read -r a b <<< "$pair"; for iou in 0.5 0.3; do
  .venv/bin/python eval/compare_runs.py --a $N/$a --b $N/$b --images $N/images --labels $D/labels/test --ignore $D/ignore/test \
      --iou $iou --cluster-pattern "$CLUSTER" --output $N/compare_${a}_${b}_iou$iou; done; done
.venv/bin/python eval/flood_tables.py --runs-dir $N --names E1 E2 E2c E3 E4tiled --output $N/bang.md
```
