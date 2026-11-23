# Kế hoạch hoàn thành quyển luận văn (từ 21/11/2026)

Cô chốt ngày 21/11 (ROADMAP mục 6, quyết định #21): **quyển viết tiếng Anh, giãn dòng 1,5**, theo mẫu `Thesis_Template_MSE_FPT University.doc` và hướng dẫn trình bày của FSB (Times New Roman 12, lề trên dưới 2,54 cm, trái 3,0 cm, phải 2,8 cm, không lùi đầu dòng, tối đa ba cấp số mục, trích dẫn tác giả–năm, tóm tắt tối đa 150 từ). Chương trình là Thạc sĩ Kỹ thuật phần mềm (môn GRA591): quyển chiếm 50% điểm, trình bày và hỏi đáp 40%, thành tích nghiên cứu 10%. Đề cương môn chấm cả yêu cầu, thiết kế, cài đặt và đảm bảo chất lượng phần mềm, nên quyển thêm hai chương về hệ thống so với dàn ý sáu chương cũ.

Nháp tiếng Việt trong `docs/luan_van/` là nguồn nội dung; bản tiếng Anh viết trong `docs/thesis/`. Số liệu không đổi khi dịch: mọi số vẫn đọc từ `docs/results/` và `runs/`, chỉ đổi dấu thập phân sang dấu chấm (0.497) theo chuẩn tiếng Anh.

## 1. Cấu trúc quyển tiếng Anh

| Phần | Nội dung | Nguồn | Trạng thái |
|---|---|---|---|
| Trang bìa (hai trang), Abstract (≤ 150 từ), Acknowledgments | Theo mẫu Word | Viết mới | Chờ kết quả lũ (tóm tắt) |
| Table of Contents, List of Tables, List of Figures, List of Appendices, List of Abbreviations | Sinh khi dựng Word; bảng viết tắt từ `THUAT_NGU.md` | Tự động + `THUAT_NGU.md` | Chờ |
| Ch. 1 Introduction | Bối cảnh, ba ràng buộc, câu hỏi nghiên cứu, đóng góp, phạm vi, bố cục | `chuong1.md` | **Xong 21/11** (`ch1_introduction.md`) |
| Ch. 2 Background and Related Work | Phát hiện vật nhỏ, ảnh UAV cho cứu nạn, theo dõi, thiết bị biên, khoảng trống | `chuong2.md`, `tai_lieu_tham_khao.md` | **Xong 21/11** (`ch2_background.md`, `references.bib`) |
| **Ch. 3 System Requirements and Architecture** (mới) | Bên liên quan và kịch bản sử dụng; yêu cầu chức năng theo vai trò (drone, trạm mặt đất, điều phối viên, đội cứu hộ); yêu cầu phi chức năng (tốc độ, chịu mất sóng, chạy không mạng, tái lập, chạy trên thiết bị biên); kiến trúc hai phía và luồng dữ liệu; quyết định thiết kế | `chuong3.md` mục 3.1, `TECHNICAL.md` mục 7–12, `ROADMAP.md` mục 2–3 | **Xong 21/11** (`ch3_requirements_architecture.md`) |
| Ch. 4 Methods | Hình học camera, phát hiện và cắt ô, thu nhỏ theo độ cao, tần số theo độ cao, xác nhận theo mặt đất, gửi cảnh báo, công cụ giả lập | `chuong3.md` mục 3.2–3.8 | **Xong 21/11** (`ch4_methods.md`) |
| **Ch. 5 Implementation and Quality Assurance** (mới) | Công nghệ và cấu trúc mã; giao diện từng khối và bản giả; ràng buộc kiến trúc; kiểm thử tự động (số test, phạm vi, ví dụ tính tay); tái lập (`run_config.json`, ghim phiên bản, khoá tập test bằng mã băm); triển khai (Docker, nhóm cài đặt edge/ground); màn hình điều phối và công cụ cho đội cứu hộ | `.claude/rules/pipeline.md`, `tests/`, `pyproject.toml`, `TECHNICAL.md` mục 10–12, `DEMO_BAO_VE.md` | **Xong 21/11** (`ch5_implementation_qa.md`); cập nhật số test lúc khoá mã |
| Ch. 6 Data and Experimental Setup | Dữ liệu, tập lũ tự gán nhãn, cách đo, thí nghiệm, môi trường | `chuong4.md` | **Xong 21/11** (`ch6_data_setup.md`); điền Bảng 6.4 sau khoá |
| Ch. 7 Results and Discussion | Ba câu hỏi nghiên cứu, luận điểm xuyên suốt, phân tích lỗi, minh hoạ hệ thống | `chuong5.md`, `runs/flood/bang.md` | Đang dịch; điền phần lũ sau khoá |
| Ch. 8 Conclusion and Future Work | Trả lời câu hỏi, đóng góp, giới hạn, hướng phát triển | `chuong6.md` | Dịch sau Ch. 7 |
| References | Tác giả–năm (APA) | `tai_lieu_tham_khao.md` → `docs/thesis/references.bib` | Chuyển |
| Appendices | A. Hướng dẫn gán nhãn tóm tắt; B. Lệnh tái lập từng bảng; C. Bảng phụ; D. Danh sách test | `LABELING.md`, `docs/results/`, `tests/` | Viết |

## 2. Lịch

Mốc cứng: khoá tập lũ 25/11 (**đã khoá 24/11**, `docs/results/flood.md`), khoá mã 28/11, bản thảo gửi cô 4/12, bản hoàn chỉnh 11/12, bảo vệ 15/12.

| Ngày | Claude | Học viên |
|---|---|---|
| 21–24/11 | Dựng `docs/thesis/`; dịch Ch. 1, 2, 4, 6; viết Ch. 3, 5; chuyển tài liệu tham khảo sang `.bib`; script kiểm số (mục 3) | Gán nhãn 8 video còn lại, bổ sung thuộc tính và thẻ cho 01, 02; gán lại 20 khung (LABELING mục 7); hỏi cô các câu ở mục 4 |
| 24/11 | ~~Chuyển nhãn, kiểm tra rò rỉ, khoá, chấm (`scripts/eval_flood.sh`), ảnh demo; `docs/results/flood.md`~~ (xong 24/11, sớm một ngày) | ~~Xuất 10 task; xác nhận khoá~~ (xong) |
| 26–27/11 | Điền kết quả lũ vào nháp tiếng Việt và Ch. 7; dịch Ch. 7, 8; viết Abstract | Đọc Ch. 1–3 tiếng Anh, sửa chỗ sai ý |
| 28/11 | **Khoá mã.** Dựng file Word lần đầu từ mẫu của trường; hình và bảng | Chạy notebook Kaggle đo lại thu nhỏ trên GPU nếu còn giờ (có thể bỏ) |
| 29/11–3/12 | Sửa theo góp ý của học viên; danh mục bảng, hình, viết tắt; kiểm số toàn quyển | Đọc toàn quyển; viết Acknowledgments; xin văn bản áp dụng nếu có (mục 5) |
| 4/12 | | **Gửi bản thảo cho cô** |
| 5–11/12 | Sửa theo góp ý của cô; slide; cập nhật kịch bản demo theo ngôn ngữ trình bày | Diễn tập demo có bấm giờ, quay video dự phòng; nộp bản hoàn chỉnh 11/12 |
| 12–14/12 | Câu hỏi hội đồng dễ hỏi (DEMO_BAO_VE mục FAQ) bằng ngôn ngữ trình bày | Diễn tập hai lần |

Trễ thì cắt theo thứ tự: phụ lục C, D → minh hoạ hệ thống trong Ch. 7 → đo lại trên Kaggle → gán lại 20 khung (ghi giới hạn). Không cắt Ch. 3, Ch. 5 (phần chấm của chương trình kỹ thuật phần mềm) và không cắt tập lũ.

## 3. Cách làm và kiểm tra

- **Viết:** Markdown trong `docs/thesis/` (mỗi chương một file, `ch1_introduction.md`…). Thuật ngữ tiếng Anh theo cột "Tiếng Anh" của `THUAT_NGU.md`; mã thí nghiệm luôn kèm tên mô tả.
- **Dựng Word:** pandoc với file tham chiếu dựng từ mẫu của trường (kiểu chữ, lề, giãn dòng 1,5, đánh số trang i, ii… rồi 1, 2…), trích dẫn bằng citeproc (APA). **Cần cài pandoc: hỏi học viên trước.**
- **Kiểm số:** `tools/check_thesis_numbers.py` (có từ 21/11) so mọi số thập phân trong `docs/thesis/` với nguồn đã đo (đổi dấu phẩy sang chấm); số không tìm thấy được liệt kê để kiểm tay. Chạy trước mỗi lần gửi.
- **Kiểm thuật ngữ:** cùng script báo chữ tiếng Việt còn sót; mã thí nghiệm đứng trơn kiểm bằng mắt.
- Sửa nội dung thì sửa cả nháp tiếng Việt lẫn bản tiếng Anh cho tới 4/12; sau 4/12 bản tiếng Anh là bản chính.

## 4. Cần hỏi cô

1. Cấu trúc tám chương ở mục 1 (thêm Ch. 3 yêu cầu và kiến trúc, Ch. 5 cài đặt và đảm bảo chất lượng) có được không?
2. Trình bày và slide bằng tiếng Anh hay tiếng Việt? (Ảnh demo và chữ trên video đang tiếng Việt.)
3. Có cần tóm tắt tiếng Việt kèm theo không; có giới hạn số trang không?
4. Có được dùng văn bản xác nhận của một đơn vị cứu hộ làm minh chứng áp dụng không (mục 5)?

## 5. Điểm thành tích nghiên cứu (10%)

Bài báo cần thư chấp nhận trước 15/12: không khả thi. Còn một đường: văn bản của một đơn vị (đội cứu hộ, cứu nạn, phòng chống thiên tai) đồng ý dùng thử hoặc triển khai kết quả, tối đa 0,5 điểm. Chỉ theo nếu học viên có quan hệ sẵn; không có thì bỏ, điểm quyển tối đa vẫn là 9.
