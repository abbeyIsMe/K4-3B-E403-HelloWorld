# Reflection cá nhân — Đào Duy Hiếu

- **Mã học viên:** 2A202602651
- **Nhóm:** HelloWorld · Lớp 3B · Phòng E403
- **Sản phẩm:** VLearn NotebookLM
- **Vai trò:** Retrieval, grounding và prompt chống hallucination

## 1. Phần việc tôi đã làm

Tôi phụ trách phần giúp hệ thống tìm đúng bằng chứng trong slide và transcript video trước khi trả lời, thay vì chỉ thấy từ khóa giống nhau rồi trả lời theo kiến thức chung.

- Xây dựng hướng retrieval kết hợp BM25 cho từ khóa chính xác và dense vector cho các cách hỏi/paraphrase khác nhau.
- Kết hợp hai thứ hạng bằng Reciprocal Rank Fusion (RRF), đồng thời lọc theo bài học và loại nguồn PDF/video người dùng đã chọn.
- Thêm intent-aware reranking để câu hỏi định nghĩa ưu tiên đoạn định nghĩa thay vì đoạn chỉ nhắc từ khóa trong ví dụ tính toán.
- Thiết kế evidence gate; chỉ evidence đủ phù hợp mới được đưa vào bước sinh câu trả lời.
- Viết nguyên tắc prompt/citation: Gemini chỉ dùng citation ID có trong evidence; câu hỏi mơ hồ trả `CLARIFY`, thiếu căn cứ trả `NOT_FOUND`.

Các phần này nằm chủ yếu ở `src/retrieval.py`, `src/vector_store.py`, `src/grounded_answer.py` và `scripts/build_vector_index.py`.

## 2. AI đã hỗ trợ tôi như thế nào

Tôi dùng AI để đọc code, đề xuất cách tách retrieval thành các bước và tạo test case. Tôi vẫn kiểm tra lại bằng các truy vấn cụ thể, xem chunk được chọn có thật sự trả lời câu hỏi hay không rồi mới điều chỉnh heuristic hoặc prompt. Citation có ID hợp lệ chưa chắc đã liên quan đúng nội dung.

## 3. Một case fail và bài học

Case quan trọng là “Token là gì?”. Nếu chỉ dùng BM25, đoạn có nhiều chữ “token” trong phần token budget hoặc chi phí có thể đứng cao hơn đoạn định nghĩa. Hệ thống vẫn có citation nhưng dễ sai trọng tâm.

Tôi xử lý bằng cách nhận diện ý định hỏi định nghĩa, tìm các mẫu câu như “X là…”, “được gọi là…”, rồi tăng điểm cho đoạn định nghĩa và giảm ưu tiên các đoạn thuần số liệu. Sau retrieval còn có evidence gate để loại chunk chỉ trùng từ khóa nhưng chưa đủ căn cứ trả lời.

Bài học là retrieval không chỉ tìm kết quả điểm cao nhất; nó phải kiểm tra đoạn đó có trả lời đúng ý định của người học hay không.

## 4. Điều tôi hiểu thêm sau dự án

Tôi hiểu rõ hơn sự khác nhau giữa “model trả lời hay” và “hệ thống đáng tin”. Người học cần kiểm chứng được câu trả lời tại slide hoặc video. Vì vậy, giá trị của hệ thống là chuỗi kiểm soát: lọc nguồn, chọn evidence phù hợp, ép citation có thật và từ chối khi không chắc chắn.

## 5. Phần tôi sẽ cải thiện nếu có thêm thời gian

- Giảm heuristic viết tay và đánh giá retrieval trên cách diễn đạt đa dạng hơn.
- Kiểm tra từng claim trong câu trả lời có được evidence hỗ trợ hay không.
- Cải thiện transcript ASR và OCR slide dạng ảnh.
