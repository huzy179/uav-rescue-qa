# Tài liệu tham khảo (đã tra)

> **Ghi chú bản nháp.** Danh mục các tài liệu đã **tra trên mạng ngày 7/11/2026** (tên, tác giả, năm, nơi công bố). Cột "Kiểm tra" cho biết đã đọc tới đâu: "tóm tắt" là mới đọc tóm tắt hoặc trang thông tin; "toàn văn" là đã đọc bài. Trước khi nộp, mỗi tài liệu dùng cho một khẳng định cụ thể phải được đọc toàn văn phần liên quan. Định dạng trích dẫn cuối cùng theo quy định của trường **[ĐỊNH DẠNG]**. Danh sách cũ, có mục "từ trí nhớ", ở `docs/THUAT_TOAN.md` mục 7.

## Phát hiện đối tượng và vật nhỏ

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [YOLO26] | Ultralytics, *YOLO26* (tài liệu mô hình, docs.ultralytics.com/models/yolo26; phát hành 14/1/2026, Ultralytics 8.4.0); *Understanding End-to-End Detection in Ultralytics YOLO26* (docs.ultralytics.com/guides/end2end-detection) | Mô hình nền; đầu một-một không NMS là tuỳ chọn, mặc định dự đoán dùng đầu một-nhiều kèm NMS | Trang tài liệu; đối chiếu mã đã cài (8.4.174) |
| [SAHI] | F. C. Akyon, S. O. Altinuc, A. Temizel, "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection", *IEEE ICIP 2022*, tr. 966–970, doi:10.1109/ICIP46576.2022.9897990 (arXiv:2202.06934) | Cắt ô; mốc so sánh bộ cắt ô riêng | Tóm tắt |
| [TinyPerson] | X. Yu, Y. Gong, N. Jiang, Q. Ye, Z. Han, "Scale Match for Tiny Person Detection", *WACV 2020*, tr. 1257–1265 (arXiv:1912.10664) | Người rất nhỏ; khớp thang kích thước lúc huấn luyện | Tóm tắt |
| [AdaptiveResize] | M. Messmer, B. Kiefer, A. Zell, "Gaining Scale Invariance in UAV Bird's Eye View Object Detection by Adaptive Resizing", *ICPR 2022* (arXiv:2101.12694) | **Công trình gần nhất với thu nhỏ theo độ cao**: đổi cỡ ảnh theo độ cao chụp trước khi phát hiện; UAVDT, VisDrone; nhanh hơn 2–3 lần | Tóm tắt; **cần đọc toàn văn** (công thức, cách lấy độ cao) |
| [AltTiling] | S. Ahmed, O. Pizarro, "Maritime Small Object Detection from UAVs using Deep Learning with Altitude-Aware Dynamic Tiling", *OCEANS 2025 Brest* (arXiv:2511.19728) | **Công trình gần nhất, cùng tập SeaDronesSee**: thu nhỏ theo độ cao kết hợp số ô động, YOLOv5 + SAHI | Tóm tắt; **cần đọc toàn văn** |

## Dữ liệu

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [VisDrone] | P. Zhu, L. Wen, D. Du, X. Bian, H. Fan, Q. Hu, H. Ling, "Detection and Tracking Meet Drones Challenge", *IEEE TPAMI* 44(11):7380–7399, 2022, doi:10.1109/TPAMI.2021.3119563 (arXiv:2001.06303) | Dữ liệu huấn luyện và đánh giá người nhỏ | Tóm tắt |
| [AFO] | Gąsienica-Józkowy, Knapik, Cyganek, "An ensemble deep learning method with optimized weights for drone-based water rescue and surveillance", *Integrated Computer-Aided Engineering*, 2021, doi:10.3233/ICA-210649 | Người dưới nước. Giấy phép theo các nguồn mô tả bộ dữ liệu: CC BY-NC-SA 3.0 (khác ghi chú "MIT" của bản Kaggle trong báo cáo 6/11) **[KIỂM TRA GIẤY PHÉP]** | Trang mô tả bộ dữ liệu |
| [SeaDronesSee] | L. A. Varga, B. Kiefer, M. Messmer, A. Zell, "SeaDronesSee: A Maritime Benchmark for Detecting Humans in Open Water", *WACV 2022*, tr. 2260–2270 (arXiv:2105.01922) | Tập đánh giá người dưới nước độc lập; video có telemetry | Tóm tắt |
| [C2A] | R. A. Nihal, B. Yen, K. Itoyama, K. Nakadai, "UAV-Enhanced Combination to Application: Comprehensive Analysis and Benchmarking of a Human Detection Dataset for Disaster Scenarios", arXiv:2408.04922, 2024 | Ảnh thảm hoạ ghép người (thí nghiệm âm) | Tóm tắt |

## Theo dõi đối tượng và xác nhận

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [ByteTrack] | Y. Zhang, P. Sun, Y. Jiang, D. Yu, F. Weng, Z. Yuan, P. Luo, W. Liu, X. Wang, "ByteTrack: Multi-Object Tracking by Associating Every Detection Box", *ECCV 2022*, LNCS 13682, doi:10.1007/978-3-031-20047-2_1 | Mốc so sánh xác nhận theo track | Tóm tắt |
| [BoT-SORT] | N. Aharon, R. Orfaig, B.-Z. Bobrovsky, "BoT-SORT: Robust Associations Multi-Pedestrian Tracking", arXiv:2206.14651, 2022 | Bù chuyển động camera (từ ảnh); đề tài tính từ telemetry | Tóm tắt |
| [MIDDTD] | C. Wang, X. Shen, Z. Zhang, C. Tao, Y. Xu, "Cross-Scene Multi-Object Tracking for Drones: Leveraging Meta-Learning and Onboard Parameters with the New MIDDTD", *Drones* 9(5):341, 2025 (đính chính: *Drones* 9(7):510) | **Gần với xác nhận theo mặt đất**: theo nguồn thứ cấp, đổi phát hiện sang toạ độ thế giới bằng GPS, độ cao, hướng gimbal của drone rồi ghép giữa các khung, giảm đổi mã track. Khác đề tài: theo dõi xe ở tần số khung bình thường, không có luật xác nhận hay cảnh báo cứu hộ | Tóm tắt qua nguồn thứ cấp (trang MDPI chặn truy cập tự động); **cần đọc toàn văn** |
| [Rudol08] | P. Rudol, P. Doherty, "Human Body Detection and Geolocalization for UAV Search and Rescue Missions Using Color and Thermal Imagery", *IEEE Aerospace Conference 2008* | Định vị người phát hiện từ UAV lên bản đồ; công trình sớm gần với xác nhận theo mặt đất | Tóm tắt (bản PDF ở ida.liu.se) |

## Tổng quan cứu nạn từ trên không

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [SARSurvey] | X. Zhang, Y. Feng, N. Wang, G. Lu, S. Mei, "Aerial Person Detection for Search and Rescue: Survey and Benchmarks", *Journal of Remote Sensing* 5:0474, doi:10.34133/remotesensing.0474 **[NĂM]** | Bối cảnh chương 2 | Trang thông tin |
| [MaritimeSurvey] | J. P. Martinez-Esteso, F. J. Castellanos, J. Calvo-Zaragoza, A. J. Gallego, "Maritime Search and Rescue Missions with Aerial Images: A Survey", *Computer Science Review* 57, 2025 (arXiv:2411.07649) | Bối cảnh chương 2; dữ liệu thật và tổng hợp | Tóm tắt |

## Còn phải tra

- Bài gốc YOLO (Redmon và cộng sự, CVPR 2016), FPN (Lin và cộng sự, CVPR 2017), TensorRT (tài liệu NVIDIA).
- Mô hình kênh Gilbert–Elliott (Gilbert 1960; Elliott 1963), nhiễu Gauss–Markov (Brown và Hwang), luật xác nhận M trên N trong theo dõi radar (Blackman; Bar-Shalom).
- Công trình chiếu phát hiện lên mặt đất và gom qua nhiều khung để xác nhận người: hai lần tìm 7/11 thấy ghép theo toạ độ thế giới cho theo dõi xe ([MIDDTD]) và định vị phát hiện từ UAV ([Rudol08]), chưa thấy bài nào làm trọn chuỗi chiếu lên mặt đất, gom qua khung, xác nhận N lần **ở tần số xử lý thấp** và so với ByteTrack có bù chuyển động. Đóng góp 3 vì vậy nên viết hẹp: phân tích và đo vì sao ghép trên ảnh gãy ở vài khung mỗi giây, và xác nhận theo mặt đất cho cứu nạn; không khẳng định "lần đầu ghép theo toạ độ thế giới". Cần tìm thêm theo "multi-view person localization", "ground-plane track-before-detect", "geo-referenced detection fusion".
