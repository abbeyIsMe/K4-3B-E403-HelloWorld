# Reflection cá nhân — Trần Tuấn Tú

- **Mã học viên:** 02840
- **Nhóm:** HelloWorld · Lớp 3B · Phòng E403
- **Sản phẩm:** VLearn NotebookLM
- **Vai trò:** Full-stack prototype, tích hợp AI và chuẩn bị demo

## 1. Phần việc tôi đã làm

Tôi phụ trách biến AI Spec và flow CP2 thành prototype có thể chạy được bằng Streamlit. Các phần chính tôi đã thực hiện gồm:

- Xây dựng giao diện Notebook cho người học hỏi về nội dung 5 ngày bài giảng.
- Tích hợp Gemini API vào luồng trả lời trung tâm.
- Kết nối retrieval với giao diện để câu trả lời đi kèm evidence và citation.
- Xây dựng Source Inspector cho hai loại nguồn: mở đúng trang slide PDF và tua video đến timestamp được trích dẫn.
- Xử lý các trạng thái `ANSWER`, `CLARIFY` và `NOT_FOUND` trong UI.
- Thêm chat history, follow-up context, nút Clear, Dark mode và layout Sources / Chat / Inspector.
- Chuẩn bị và kiểm tra flow demo local.

Các phần này tương ứng với `app.py`, phần tích hợp `src/grounded_answer.py`, `src/query_context.py` và các commit giao diện gần nhất của branch `v2-grounded-retrieval`.

## 2. AI đã hỗ trợ tôi như thế nào

Tôi dùng AI như một coding assistant để:

- Đọc và phân tích cấu trúc Streamlit hiện có trước khi sửa.
- Gợi ý cách tổ chức state cho chat history, citation và tab Inspector.
- Viết các thay đổi UI nhỏ, sau đó tự kiểm tra lại bằng compile, unit test và chạy Streamlit.
- Phân tích lỗi video không phát được, lỗi citation không liên quan và lỗi câu hỏi ngoài phạm vi.
- Sinh các trường hợp kiểm thử negative như câu hỏi bóng đá, câu hỏi mơ hồ và prompt injection.

Tôi không giao cho AI quyết định chất lượng sản phẩm một cách mù quáng. Những thay đổi quan trọng đều được tôi kiểm tra lại bằng code, test và luồng chạy thật. Một ví dụ là tôi phát hiện kết quả `100/100` vẫn có thể che giấu lỗi: câu hỏi “dự đoán kết quả bóng đá” từng bị match vào các chunk chứa từ “kết quả”. Sau đó tôi yêu cầu kiểm tra lại evidence gate và thêm regression test riêng.

## 3. Một case fail và bài học

Case đáng nhớ nhất là truy vấn:

> “Dự đoán kết quả bóng đá cho tôi”

Ở một phiên bản trước, hệ thống trả lời như thể đây là câu hỏi hợp lệ và trích dẫn các đoạn bài giảng có những từ rời rạc như “kết quả”, “đoán” hoặc “bóng”. Lỗi không nằm ở Gemini mà bắt đầu từ retrieval: evidence gate cho phép lexical overlap quá thấp và chưa phân biệt được câu hỏi ngoài domain với câu hỏi học tập.

Tôi đã sửa bằng cách:

- Không coi keyword overlap đơn thuần là bằng chứng trực tiếp.
- Yêu cầu thuật ngữ chưa biết phải xuất hiện trong ngữ cảnh giải thích phù hợp.
- Loại các từ chung như “tôi”, “ai” khỏi tín hiệu truy vấn.
- Bổ sung regression test cho câu hỏi bóng đá và “tôi là ai”.

Bài học chính là citation hợp lệ về mặt ID chưa chắc là citation đúng về mặt nội dung. Một hệ thống grounded phải kiểm tra cả quan hệ giữa câu hỏi, evidence và ý định của người học.

## 4. Điều tôi hiểu thêm sau dự án

Ban đầu tôi tập trung nhiều vào việc làm cho câu trả lời trông tự nhiên. Sau khi kiểm thử, tôi hiểu rằng với sản phẩm học tập, độ tin cậy và khả năng đối chứng quan trọng hơn văn phong đẹp. Người dùng cần biết câu trả lời nằm ở slide nào hoặc phút nào trong video, và hệ thống phải dám trả lời “chưa tìm thấy” khi không đủ căn cứ.

Tôi cũng nhận ra rằng một prototype tốt không chỉ là model gọi được API. Nó cần có:

- một lát cắt người dùng rõ;
- một evidence pipeline có thể kiểm tra;
- outcome rõ ràng khi không chắc chắn;
- citation có thể mở đến nguồn gốc;
- test cho cả happy path và failure path.

## 5. Phần tôi sẽ cải thiện nếu có thêm thời gian

- Đưa source filter trực tiếp vào panel Sources thay vì còn phụ thuộc vào sidebar.
- Bổ sung claim-level citation validation thay vì chỉ kiểm tra citation ID tồn tại.
- Làm OCR cho các trang slide dạng ảnh và kiểm tra lại transcript ASR.
- Thử nghiệm với người dùng ngoài nhóm để biết họ có hiểu ngay cách dùng Sources, Chat và Inspector hay không.
