# Tài liệu tham khảo (đã tra)

> **Ghi chú bản nháp.** Danh mục các tài liệu đã **tra trên mạng ngày 7/11/2026** (tên, tác giả, năm, nơi công bố). Cột "Kiểm tra" cho biết đã đọc tới đâu: "tóm tắt" là mới đọc tóm tắt hoặc trang thông tin; "toàn văn" là đã đọc bài. Trước khi nộp, mỗi tài liệu dùng cho một khẳng định cụ thể phải được đọc toàn văn phần liên quan. Định dạng trích dẫn cuối cùng theo quy định của trường **[ĐỊNH DẠNG]**. Danh sách cũ, có mục "từ trí nhớ", ở `docs/THUAT_TOAN.md` mục 7.

## Phát hiện đối tượng và vật nhỏ

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [YOLO] | J. Redmon, S. Divvala, R. Girshick, A. Farhadi, "You Only Look Once: Unified, Real-Time Object Detection", *CVPR 2016*, tr. 779–788, doi:10.1109/CVPR.2016.91 | Họ YOLO, bộ phát hiện một giai đoạn | Trang thông tin |
| [FPN] | T.-Y. Lin, P. Dollár, R. Girshick, K. He, B. Hariharan, S. Belongie, "Feature Pyramid Networks for Object Detection", *CVPR 2017*, tr. 936–944 (bản IEEE; bản CVF Open Access đánh 2117–2125), doi:10.1109/CVPR.2017.106 | Neck nhiều tầng | Trang thông tin |
| [YOLO26] | Ultralytics, *YOLO26* (tài liệu mô hình, docs.ultralytics.com/models/yolo26; phát hành 14/1/2026, Ultralytics 8.4.0); *Understanding End-to-End Detection in Ultralytics YOLO26* (docs.ultralytics.com/guides/end2end-detection) | Mô hình nền; đầu một-một không NMS là tuỳ chọn, mặc định dự đoán dùng đầu một-nhiều kèm NMS | Trang tài liệu; đối chiếu mã đã cài (8.4.174) |
| [SAHI] | F. C. Akyon, S. O. Altinuc, A. Temizel, "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection", *IEEE ICIP 2022*, tr. 966–970, doi:10.1109/ICIP46576.2022.9897990 (arXiv:2202.06934) | Cắt ô; mốc so sánh bộ cắt ô riêng | Tóm tắt và bảng (bản arXiv v5, đọc 26/11/2026): bộ phát hiện FCOS, VFNet, TOOD (MMDetection); tóm tắt ghi cắt ô lúc suy luận tăng AP 6,8%, 5,1%, 5,3%, thêm tinh chỉnh trên ô tăng cộng dồn 12,7%, 13,4%, 14,5%; bảng báo AP50, VisDrone test-dev và xView val |
| [TinyPerson] | X. Yu, Y. Gong, N. Jiang, Q. Ye, Z. Han, "Scale Match for Tiny Person Detection", *WACV 2020*, tr. 1257–1265 (arXiv:1912.10664) | Người rất nhỏ; khớp thang kích thước lúc huấn luyện | Tóm tắt |
| [AdaptiveResize] | M. Messmer, B. Kiefer, A. Zell, "Gaining Scale Invariance in UAV Bird's Eye View Object Detection by Adaptive Resizing", *ICPR 2022* (arXiv:2101.12694) | **Công trình gần nhất với thu nhỏ theo độ cao**: đổi cỡ ảnh theo độ cao chụp trước khi phát hiện; UAVDT, VisDrone; nhanh hơn 2–3 lần | **Đã đọc** 10/11 (bản arXiv v2): giữ GSD không đổi; độ cao thật chỉ ở tập POG, VisDrone và UAVDT suy độ cao từ box; EfficientDet-D0 UAVDT AP50 34,1 → 58,8; Jetson AGX Xavier khoảng 16 khung/giây; không cắt ô, không khoảng tin cậy |
| [AltTiling] | S. Ahmed, O. Pizarro, "Maritime Small Object Detection from UAVs using Deep Learning with Altitude-Aware Dynamic Tiling", *OCEANS 2025 Brest* (arXiv:2511.19728) | **Công trình gần nhất, cùng tập SeaDronesSee**: thu nhỏ theo độ cao kết hợp số ô động, YOLOv5 + SAHI | **Đã đọc** 10/11 (bản arXiv v1): người 80 px² (cạnh khoảng 9 px), sáu mức 640–3200 px, không phóng to, ô 640 chồng 20% qua SAHI; YOLOv5s; SDS chia lại 70/20/10; mAP50 vật nhỏ 0,34 → 0,47, 1,87 so với 0,60 khung/giây (không ghi phần cứng); một lần chạy, không khoảng tin cậy |

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
| [MIDDTD] | C. Wang, X. Shen, Z. Zhang, C. Tao, Y. Xu, "Cross-Scene Multi-Object Tracking for Drones: Leveraging Meta-Learning and Onboard Parameters with the New MIDDTD", *Drones* 9(5):341, 2025 (đính chính: *Drones* 9(7):510) | **Gần với xác nhận theo mặt đất**: chiếu box xuống mặt đất phẳng từ GPS, độ cao, góc pitch và yaw của bệ camera (mục 3.3.1, công thức 18–22), ghép track trên toạ độ thế giới kết hợp đặc trưng ngoại hình bằng lý thuyết Dempster–Shafer. MIDDTD: DJI M210, 110 chuỗi, 30 khung/giây, 1920 × 1080, bay 50–600 m, phần lớn là xe, ít người. Bảng 2: thêm toạ độ thế giới giảm đổi mã track ở cả sáu bộ theo dõi (ByteTrack 1198 → 1095). Khác đề tài: xử lý từng khung, không xét tần số xử lý thấp, không có luật xác nhận hay cảnh báo | **Đã đọc** toàn văn 26/11/2026 (bản PDF v3, có đính chính) |
| [HZ] | R. Hartley, A. Zisserman, *Multiple View Geometry in Computer Vision*, tái bản lần 2, Cambridge University Press, 2004, ISBN 978-0-521-54051-3 | Mô hình camera lỗ kim, chiếu lên mặt phẳng | Trang thông tin |
| [Rudol08] | P. Rudol, P. Doherty, "Human Body Detection and Geolocalization for UAV Search and Rescue Missions Using Color and Thermal Imagery", *IEEE Aerospace Conference 2008* | Định vị người phát hiện từ UAV lên bản đồ; công trình sớm gần với xác nhận theo mặt đất | Tóm tắt (bản PDF ở ida.liu.se) |

## Mạng và nhiễu

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [Gilbert60] | E. N. Gilbert, "Capacity of a Burst-Noise Channel", *Bell System Technical Journal* 39(5):1253–1265, 1960, doi:10.1002/j.1538-7305.1960.tb03959.x | Mô hình mất theo cụm hai trạng thái | Tóm tắt |
| [Elliott63] | E. O. Elliott, "Estimates of Error Rates for Codes on Burst-Noise Channels", *Bell System Technical Journal* 42(5):1977–1997, 1963, doi:10.1002/j.1538-7305.1963.tb00955.x | Như trên (mô hình Gilbert–Elliott) | Tóm tắt |

## Tổng quan cứu nạn từ trên không

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [SARSurvey] | X. Zhang, Y. Feng, N. Wang, G. Lu, S. Mei, "Aerial Person Detection for Search and Rescue: Survey and Benchmarks", *Journal of Remote Sensing* 5:0474, doi:10.34133/remotesensing.0474 **[NĂM]** | Bối cảnh chương 2: người nhìn từ trên không nhỏ, thưa, mờ, tư thế đa dạng nên đặc trưng yếu | Tóm tắt (bản ghi Scopus trên pure.nwpu.edu.cn, 26/11/2026); trang nhà xuất bản chặn truy cập tự động |
| [MaritimeSurvey] | J. P. Martinez-Esteso, F. J. Castellanos, J. Calvo-Zaragoza, A. J. Gallego, "Maritime Search and Rescue Missions with Aerial Images: A Survey", *Computer Science Review* 57, 2025 (arXiv:2411.07649) | Bối cảnh chương 2; dữ liệu thật và tổng hợp; người quá nhỏ so với mặt biển rộng, cần nhiều dữ liệu có nhãn | Tóm tắt và phần mở đầu (arXiv v2, đọc 26/11/2026) |

## Bối cảnh

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [UNRCO-Yagi] | Văn phòng Điều phối viên Liên Hợp Quốc tại Việt Nam, *Viet Nam: Typhoon Yagi – Office of the Resident Coordinator Situation Update No. 5*, 23/10/2024, vietnam.un.org/en/node/281770 | Chương 1: thiệt hại của bão Yagi (321 người chết, 24 mất tích, số của Cục Quản lý đê điều và Phòng, chống thiên tai đến 23/10/2024) | **Đã đọc** trang báo cáo 26/11/2026 |

## Thiết bị biên

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [TensorRT] | NVIDIA, *NVIDIA TensorRT Documentation*, bản 10.16.1 (docs.nvidia.com/deeplearning/tensorrt/10.x.x/), mục "Version Compatibility" và "Working with Quantized Types" | Chương 2: engine mặc định chỉ chạy trên đúng loại thiết bị và đúng bản TensorRT đã dựng; INT8 cần dữ liệu hiệu chỉnh hoặc lượng tử hoá tường minh. Cùng bản đã dùng khi đo trên T4 (`runs/rq2`, tensorrt 10.16.1.11) | **Đã đọc** hai trang 26/11/2026 |

## Theo dõi mục tiêu

| Mã | Tài liệu | Dùng cho | Kiểm tra |
|---|---|---|---|
| [MathWorks-MOT] | The MathWorks, *Introduction to Multiple Target Tracking*, tài liệu Sensor Fusion and Tracking Toolbox, mathworks.com/help/fusion/ug/introduction-to-multiple-target-tracking.html | Chương 2: luật xác nhận M trên N (track được ghép với phát hiện ít nhất M lần trong N lần nhìn liên tiếp). Thay cho sách Blackman và Popoli (1999) chưa tra được; tìm được sách ở thư viện thì dẫn sách | Trang tài liệu (qua kết quả tìm kiếm, 26/11/2026) |

## Còn phải tra

- TensorRT (tài liệu NVIDIA, phiên bản 10.16 đã dùng).
- Nhiễu Gauss–Markov (Brown và Hwang), luật xác nhận M trên N trong theo dõi radar (Blackman; Bar-Shalom).
- Công trình chiếu phát hiện lên mặt đất và gom qua nhiều khung để xác nhận người: hai lần tìm 7/11 thấy ghép theo toạ độ thế giới cho theo dõi xe ([MIDDTD]) và định vị phát hiện từ UAV ([Rudol08]), chưa thấy bài nào làm trọn chuỗi chiếu lên mặt đất, gom qua khung, xác nhận N lần **ở tần số xử lý thấp** và so với ByteTrack có bù chuyển động. Đóng góp 3 vì vậy nên viết hẹp: phân tích và đo vì sao ghép trên ảnh gãy ở vài khung mỗi giây, và xác nhận theo mặt đất cho cứu nạn; không khẳng định "lần đầu ghép theo toạ độ thế giới". Cần tìm thêm theo "multi-view person localization", "ground-plane track-before-detect", "geo-referenced detection fusion".
