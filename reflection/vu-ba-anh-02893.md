# Reflection cá nhân — Vũ Bá Anh

- **Mã học viên:** 2A202602893
- **Nhóm:** HelloWorld · Lớp 3B · Phòng E403
- **Sản phẩm:** VLearn Grounded Tutor
- **Vai trò:** Spec owner, xây dựng Golden Set và đo lường kiểm thử

## 1. Phần việc tôi đã làm

Tôi phụ trách `spec.md` — tài liệu sống ghi lại toàn bộ quyết định thiết kế của nhóm từ CP1 đến CP6 — và hệ thống kiểm thử Golden Set đảm bảo sản phẩm không lệch khỏi cam kết ban đầu.

Các phần chính tôi đã thực hiện:

- Viết và cập nhật toàn bộ `spec.md`: Problem Statement, lựa chọn ứng viên bằng số liệu (§2), thiết kế lát cắt một câu (§4), 4 lớp chỗ khó + 8 kịch bản kiểm thử (§5), 6 đường trải nghiệm (§6), và Quality Bar chốt từ hạn nộp.
- Xây dựng bộ Golden Set Day01 gồm 12 test case (`eval/golden_set_day01.json`) bao phủ đủ 4 lớp: happy path, câu hỏi mơ hồ, ngoài phạm vi và cross-filter nguồn PDF/Video.
- Mở rộng lên bộ Golden Set V2 gồm 40 test case (`eval/golden_set_v2.json`) bổ sung các tình huống khó hơn: definition gap, paraphrase, source filter, prompt injection, keyword noise và contextual definition.
- Thiết kế và viết script `scripts/run_eval.py` và `scripts/run_eval_v2.py` để chạy đo lường tự động; tổng hợp kết quả vào các file report trong `eval/`.
- Theo dõi và ghi lại kết quả 5 lượt chạy vào bảng §7 của spec, phân tích nguyên nhân thất bại và phản biện quy trình kiểm thử tại CP6.

## 2. AI đã hỗ trợ tôi như thế nào

Tôi dùng AI để soạn thảo nhanh cấu trúc của các mục trong spec, đề xuất các tình huống kiểm thử còn thiếu, và tổng hợp phân tích lỗi qua nhiều lượt chạy.

Tuy nhiên, các quyết định về nội dung spec đều phải tôi tự đưa ra. Ví dụ: khi AI đề xuất thêm test case cho câu hỏi hành chính, tôi phải tự kiểm tra xem có đủ evidence từ chatlog mining không, ngưỡng Quality Bar ≥ 85% là bao nhiêu thì hợp lý với 39 giờ hackathon, hay tại sao "Embedding là gì?" lại là `NOT_FOUND` thay vì `ANSWER` trong bộ V2. AI không thể trả lời những câu đó thay tôi.

## 3. Một case fail và bài học

Case đáng nhớ nhất trong quá trình build Golden Set là lúc tôi thiết kế TC05 và TC06 — hai test case cross-filter: câu hỏi về Model A 8192 token khi chỉ chọn nguồn PDF, và câu hỏi về link GitHub Classroom khi chỉ chọn nguồn Video.

Ở lượt chạy đầu tiên (Baseline), cả hai case này đều **FAIL** — hệ thống trả về `ANSWER` và bịa citation từ nguồn bị tắt. Điều này cho thấy retrieval không thực sự tôn trọng `allowed_sources`: nó vẫn lấy chunk từ nguồn người dùng đã bỏ chọn để trả lời.

Vấn đề không chỉ nằm ở retrieval mà còn nằm ở chỗ Golden Set ban đầu của tôi chưa có cross-filter case, nên lỗi này tồn tại mà không ai phát hiện. Khi tôi bổ sung TC05 và TC06 vào bộ test, nhóm mới nhận ra và Đào Duy Hiếu sửa lại evidence gate để lọc nghiêm theo nguồn.

Bài học là: **spec và test case không chỉ là tài liệu, mà là cơ chế phát hiện lỗi**. Một lớp chỗ khó chưa được đặt test case tức là một lỗ hổng chưa được đóng.

## 4. Điều tôi hiểu thêm sau dự án

Ban đầu tôi nghĩ vai trò spec owner là viết tài liệu một lần ở đầu rồi xong. Thực tế hoàn toàn ngược lại: `spec.md` phải thay đổi mỗi khi nhóm phát hiện lỗi mới, mỗi khi kết quả eval không khớp với kỳ vọng, hoặc mỗi khi phạm vi sản phẩm mở rộng (như khi nhóm quyết định nâng từ Day01 lên Day01–Day05 Progressive Search).

Tôi cũng hiểu rõ hơn rằng Quality Bar phải được chốt sớm và không thay đổi sau hạn — không phải để tránh làm thêm, mà để nhóm có một mốc khách quan để đánh giá "đã đủ tốt chưa" thay vì mãi tối ưu không điểm dừng.

Điều tôi thực sự thấm là: **một hệ thống grounded không thể chỉ "trông đúng" — nó phải chứng minh được bằng số liệu cụ thể, test case cụ thể, và citation có thể đối chiếu ngược lại tài liệu gốc.**

## 5. Phần tôi sẽ cải thiện nếu có thêm thời gian

- Mở rộng Golden Set cho Day02–Day05 với độ phủ tương đương Day01: hiện tại 40 case V2 vẫn tập trung chủ yếu vào corpus Day01.
- Bổ sung claim-level evaluation: không chỉ kiểm tra citation ID có đúng không, mà kiểm tra từng ý trong câu trả lời có xuất phát từ đoạn evidence đó không.
- Thiết kế Willing User test session theo Mom Test để có evidence định tính thay vì chỉ dựa vào kết quả tự động.
- Thêm test case cho câu hỏi multi-hop: học viên hỏi kết hợp khái niệm từ hai bài khác nhau — đây là tình huống Progressive Search dễ sai nhất mà bộ test hiện tại chưa bao phủ.
