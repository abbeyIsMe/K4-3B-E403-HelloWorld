# CP1 Canvas - HelloWorld

| # | Dòng | Nội dung |
|---|---|---|
| 1 | Track + đề | Track A - VLearn Tutor: làm rõ ngữ cảnh cho câu hỏi của học viên dựa trên slide và video bài giảng. |
| 2 | Job executor | Học viên đang học trên VLearn, đang xem slide/video bài giảng và muốn hỏi lại một ý chưa rõ trong bài. |
| 3 | Pain một câu | Khi học viên hỏi tutor bằng một câu ngắn hoặc mơ hồ, tutor dễ trả lời chung chung hoặc lệch ngữ cảnh; học viên không biết câu trả lời dựa trên phần nào của slide/video, nên phải tự tua lại bài giảng hoặc có nguy cơ hiểu sai. |
| 4 | Bằng chứng đầu | Trong `data/vlearn-pack/chatlog/tutor_turns.csv`, K4 có `839/3.097` lượt tutor không có citation (`27,1%`); toàn bộ data có `3.781/13.494` lượt không có citation (`28,0%`). Tutor gần như không hỏi ngược khi thiếu ngữ cảnh: `ask_probing_question` chỉ `28/13.494` lượt (`0,21%`). Mã lượt minh họa không có citation ở K4: `T10288`, `T10289`, `T10291`, `T10293`, `T10296`. |
| 5 | Lát cắt MỘT CÂU | Một học viên đang học VLearn · hỏi một câu chưa rõ về nội dung slide/video bài giảng · AI quyết định cần làm rõ ngữ cảnh nào từ nguồn bài học và chỉ trả lời khi gắn được với đoạn slide/video phù hợp, nếu thiếu thì hỏi lại một câu · học viên nhận câu trả lời ngắn có nguồn để kiểm tra lại. |
| 6 | AI tự làm đến đâu + willing users | Automation: **conditional**. AI tự xác định ngữ cảnh liên quan trong slide/video và trả lời kèm nguồn khi đủ căn cứ; nếu câu hỏi mơ hồ, ngoài phạm vi, hoặc không tìm thấy đoạn nguồn thì hỏi lại/báo chưa đủ căn cứ thay vì đoán. Lý do: sai ngữ cảnh trong nội dung học tập có thể làm học viên học sai. Willing users: `Ngô Hoàng Thụy Khuê`, `Trương Hoàng Thành An`, `Phan Thị Khánh Linh`. |
| 7 | Phân công có tên | `Hồ Hoàng Phương Anh` - mining evidence + khảo sát nhanh; `Đào Duy Hiếu` - prompt/retrieval ngữ cảnh slide + video; `Trần Tuấn Tú` - prototype/mock flow + AI call; `Vũ Bá Anh` - `spec.md` + golden set/eval;|

## CP2 flow nhẹ

1. Học viên nhập câu hỏi ngắn và chọn bài/slide/video đang học.
2. Hệ thống tìm ngữ cảnh liên quan trong slide và transcript video.
3. Nếu đủ nguồn: trả lời ngắn, hiển thị trang slide hoặc mã đoạn video/transcript.
4. Nếu thiếu nguồn/ngữ cảnh: hỏi lại một câu để thu hẹp phạm vi, không đoán.

## Placeholder còn phải điền

- 3 willing users ngoài nhóm đã đồng ý thử prototype.
- Tên thành viên thật trong dòng phân công.
