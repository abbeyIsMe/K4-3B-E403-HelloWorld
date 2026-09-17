# CP1 Canvas - HelloWorld

| # | Dòng | Nội dung |
|---|---|---|
| 1 | Track + đề | Track A - VLearn Tutor: trả lời câu hỏi của học viên theo kiểu NotebookLM, nhưng chỉ dựa trên nguồn của bài học đang chọn: slide và video bài giảng. |
| 2 | Job executor | Học viên đang học trên VLearn, đang xem slide/video bài giảng và muốn hỏi lại một ý chưa rõ trong bài. |
| 3 | Pain một câu | Khi học viên hỏi lại một ý trong bài, tutor dễ trả lời chung chung hoặc dùng kiến thức ngoài bài; học viên không biết câu trả lời dựa trên phần nào của slide/video, nên phải tự tua lại bài giảng hoặc có nguy cơ hiểu sai. |
| 4 | Bằng chứng đầu | Trong `data/vlearn-pack/chatlog/tutor_turns.csv`, K4 có `839/3.097` lượt tutor không có citation (`27,1%`); toàn bộ data có `3.781/13.494` lượt không có citation (`28,0%`). Tutor gần như không hỏi ngược khi thiếu ngữ cảnh: `ask_probing_question` chỉ `28/13.494` lượt (`0,21%`). Mã lượt minh họa không có citation ở K4: `T10288`, `T10289`, `T10291`, `T10293`, `T10296`. |
| 5 | Lát cắt MỘT CÂU | Một học viên đang học VLearn · hỏi một câu về bài đang học · AI chỉ tìm trong slide và transcript video của bài đó để quyết định có đủ căn cứ trả lời hay không · học viên nhận câu trả lời ngắn có citation, hoặc được báo chưa thấy trong nguồn bài giảng. |
| 6 | AI tự làm đến đâu + willing users | Automation: **conditional**. AI tự tìm đoạn liên quan trong slide/video và tổng hợp câu trả lời khi đủ căn cứ; nếu câu hỏi mơ hồ, ngoài phạm vi, hoặc không tìm thấy bằng chứng trong nguồn bài học thì hỏi lại/báo chưa đủ căn cứ thay vì dùng kiến thức ngoài. Lý do: sai hoặc vượt nguồn trong nội dung học tập có thể làm học viên học sai. Willing users: `Ngô Hoàng Thụy Khuê`, `Trương Hoàng Thành An`, `Phan Thị Khánh Linh`. |
| 7 | Phân công có tên | `Hồ Hoàng Phương Anh` - mining evidence + khảo sát nhanh; `Đào Duy Hiếu` - prompt/retrieval ngữ cảnh slide + video; `Trần Tuấn Tú` - prototype/mock flow + AI call; `Vũ Bá Anh` - `spec.md` + golden set/eval;|

## CP2 flow nhẹ

1. Học viên chọn bài học và nguồn của bài: slide, video/transcript, hoặc cả hai.
2. Học viên hỏi một câu về bài đang học.
3. Hệ thống chỉ tìm bằng chứng trong nguồn đã chọn, không dùng web hoặc kiến thức ngoài.
4. Nếu đủ căn cứ: trả lời ngắn kèm citation; nếu không đủ: hỏi lại hoặc báo chưa thấy trong nguồn bài giảng.
