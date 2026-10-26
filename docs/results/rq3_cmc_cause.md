# RQ3 mô phỏng: vì sao ByteTrack có bù chuyển động camera bỏ sót khi GPS nhiễu

**Mô phỏng, chưa phải kết quả chính thức của RQ3.** Câu hỏi còn mở ở `TONG_QUAN.md` mục 3.11: lần chạy thử `rq3_gps.yaml` cho thấy `bytetrack_cmc` bỏ sót 0,200 người ở σ_GPS = 0,5 m và 0,767 ở 1 m, trong khi `geo` gần như không bỏ sót; chưa rõ cơ chế.

## Giả thuyết và cách phân biệt

`bytetrack_cmc` dời box khung trước bằng phép biến đổi tính từ telemetry **đo được** của hai khung (`georef.frame_motion`). Sai số của phép dời vì vậy bằng **độ chênh nhiễu GPS giữa hai khung**, không phải nhiễu tuyệt đối. Nhiễu GPS mô phỏng theo Gauss–Markov với thời gian tương quan τ: τ nhỏ thì GPS nhảy nhanh giữa hai khung, τ lớn thì trôi chậm.

- Nếu nguyên nhân là **độ chênh GPS giữa hai khung**: cùng σ, τ càng lớn càng ít bỏ sót.
- Nếu nguyên nhân là **số pixel lệch tuyệt đối**: đổi độ cao sẽ không đổi kết quả, vì trong mô phỏng cả độ lệch lẫn box người đều tỉ lệ với GSD (`sim/scenario.py`, box cạnh 0,5 m).

Lưới: σ_GPS ∈ {0; 0,5; 1} m × τ ∈ {5; 30; 300} s × độ cao ∈ {50; 100} m × chiến lược ∈ {geo, bytetrack_cmc}, 3 seed; kịch bản như `rq3_gps.yaml` (60 s, 10 người, recall 0,7, 0,5 báo nhầm mỗi khung, 10 m/s, 2 khung/giây, N = 3). Cấu hình `configs/experiments/rq3_cmc_cause.yaml`, kết quả `runs/rq3/cmc_cause/summary.csv`.

## Tỉ lệ bỏ sót (trung bình 3 seed)

### bytetrack_cmc

| Độ cao | τ GPS | σ = 0 m | σ = 0,5 m | σ = 1 m |
|---|---|---|---|---|
| 50 m | 5 s | 0,000 | 0,900 | 1,000 |
| 50 m | 30 s | 0,000 | 0,200 | 0,767 |
| 50 m | 300 s | 0,000 | 0,033 | 0,033 |
| 100 m | 5 s | 0,000 | 0,600 | 0,933 |
| 100 m | 30 s | 0,000 | 0,067 | 0,500 |
| 100 m | 300 s | 0,000 | 0,000 | 0,000 |

### geo

| Độ cao | τ GPS | σ = 0 m | σ = 0,5 m | σ = 1 m |
|---|---|---|---|---|
| 50 m | 5 s | 0,000 | 0,033 | 0,033 |
| 50 m | 30 s | 0,000 | 0,000 | 0,000 |
| 50 m | 300 s | 0,000 | 0,000 | 0,000 |
| 100 m | 5 s | 0,000 | 0,000 | 0,033 |
| 100 m | 30 s | 0,000 | 0,000 | 0,000 |
| 100 m | 300 s | 0,000 | 0,000 | 0,000 |

## Kết luận

1. **Nguyên nhân chính là độ chênh GPS giữa hai khung liên tiếp.** Cùng σ = 0,5 m ở 50 m: τ = 5 s bỏ sót 0,900, τ = 30 s 0,200, τ = 300 s 0,033. GPS càng ổn định ngắn hạn thì bù chuyển động bằng telemetry càng đúng.
2. **geo gần như không bị ảnh hưởng** (bỏ sót tối đa 0,033 ở mọi ô), vì nó so khoảng cách mặt đất với bán kính 3 m, rộng hơn nhiều so với độ chênh GPS giữa hai khung.
3. **Bay cao ít bỏ sót hơn** (τ = 30 s, σ = 0,5 m: 0,200 ở 50 m, 0,067 ở 100 m). Không phải do số pixel (đã loại ở trên); có lẽ do người nằm trong khung lâu hơn ở độ cao lớn (K_max 17 so với 8, TECHNICAL mục 2.4), nên dù track đứt vẫn còn cơ hội nối đủ N lần. Cách giải thích này chưa được kiểm chứng riêng.
4. Hệ quả thiết kế: `bytetrack_cmc` chỉ dùng được khi GPS ổn định ngắn hạn (RTK, hoặc GPS đã lọc qua bộ ước lượng trạng thái của bộ điều khiển bay); geo không đòi hỏi điều này. Với GPS thường, GPS thật thường trôi chậm (τ hàng chục giây) nhưng có bước nhảy khi đổi vệ tinh, cần kiểm tra trên log bay thật.

## Giới hạn

- Mô phỏng: detector giả, người đứng yên, nhiễu GPS Gauss–Markov thuần, không có bước nhảy.
- Mỗi ô 3 seed.

## Tái lập

```bash
python -m sim.sweep_rq3 --config configs/experiments/rq3_cmc_cause.yaml --jobs 8
```
