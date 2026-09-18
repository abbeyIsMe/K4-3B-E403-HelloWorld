# Reflection cá nhân — Hồ Hoàng Phương Anh

- **Mã học viên:** 02460
- **Nhóm:** HelloWorld · Lớp 3B · Phòng E403
- **Sản phẩm:** VLearn NotebookLM
- **Vai trò:** Business Analyst / Evidence & Spec Lead

## 1. Phần việc tôi đã làm

Tôi đảm nhiệm vai trò BA trong nhóm, tập trung vào việc xác định đúng vấn đề người dùng, kiểm chứng dữ liệu và định nghĩa tiêu chuẩn chất lượng cho sản phẩm trước khi team tôi bắt tay thực hiênj.

- Khảo sát pain point từ chatlog và khảo sát người học để xác định các vấn đề lớn: thiếu citation, trả lời lan man, không rõ nguồn, câu hỏi mơ hồ.
- Chuyển dữ liệu thô thành insight có cấu trúc, không chỉ dựa trên cảm giác: tỷ lệ thiếu citation, tỷ lệ câu hỏi mơ hồ, mức độ cần thiết của grounded search.
- Ghi nhận một điểm quan trọng: “gặp vấn đề nhiều” và “ưu tiên giải pháp” là hai khía cạnh khác nhau. Một vấn đề có thể xuất hiện nhiều hơn, nhưng người dùng lại chọn giải pháp khác vì nó trực tiếp hơn, rõ ràng hơn và dễ thấy giá trị hơn. Đây là yếu tố quan trọng để không đánh giá sai dữ liệu khảo sát.
- Viết AI Spec: User & Job, JTBD, problem statement, impact, giải pháp được chọn, non-goals, failure modes, acceptance criteria.
- Định nghĩa tiêu chí đánh giá: groundedness, citation precision, outcome accuracy, cross-filter correctness.
- Hỗ trợ phản biện và rà soát luồng retrieval/prompt/output để giảm rủi ro hallucination và câu trả lời sai.

## 2. AI đã hỗ trợ tôi như thế nào

AI giúp tôi rút ngắn thời gian xử lý dữ liệu và viết spec, nhưng quyết định cuối cùng vẫn do tôi kiểm chứng lại bằng logic và dữ liệu. Tôi dùng AI để:

- tổng hợp mẫu chatlog và khảo sát;
- sắp xếp insight theo vấn đề và mức ưu tiên;
- viết lại spec rõ ràng hơn;
- sinh test case negative để kiểm tra.

## 3. Một case fail và bài học

Case đáng nhớ nhất là câu hỏi: “Dự đoán kết quả bóng đá cho tôi” hay "Cho biết thêm về Hiêuj ứng thuỷ tinh thể đảo ngược".

Lúc đầu, hệ thống có thể chọn những đoạn có từ khóa “kết quả”, “đoán”, “bóng”, "hiệu ứng", "đảo ngược" dù không có căn cứ trong bài giảng. Đây là lỗi rất rõ của groundedness: câu trả lời có vẻ hợp lý nhưng không đúng phạm vi và không có evidence hợp lệ.

Từ đó, tôi hiểu rằng: keyword overlap không phải là chứng cứ. Với sản phẩm học tập, cần kiểm tra cả ý định người hỏi, ngữ cảnh và độ phù hợp với source. Chúng mình đã bổ sung test cho các trường hợp ngoài lề, câu hỏi mơ hồ, và prompt injection.

## 4. Điều tôi hiểu thêm sau dự án

Tôi học được rằng một sản phẩm AI không chỉ cần trả lời hay, mà còn phải đúng và đáng tin. Với hệ thống học tập, người dùng cần biết câu trả lời đến từ slide/video nào, và khi không có căn cứ thì phải nói rõ “không tìm thấy trong nguồn”.

Một điểm quan trọng nữa là: dữ liệu khảo sát phải được đọc theo đúng tầng. “Gặp vấn đề nhiều” không đồng nghĩa với “ưu tiên giải pháp nhiều”; cần tách rõ pain point, preference và khả năng triển khai để chọn đúng hướng giải pháp.

## 5. Phần tôi sẽ cải thiện nếu có thêm thời gian

- khảo sát người dùng ngoài nhóm;
- thêm metric định lượng cho citation precision và refusal accuracy;
- rà soát lại golden set và acceptance criteria sát với thực tế hơn.

Tóm lại, vai trò của tôi trong dự án là bảo vệ tính đúng đắn của sản phẩm: từ nhu cầu người dùng, dữ liệu, đến tiêu chuẩn đánh giá và quyết định giải pháp.