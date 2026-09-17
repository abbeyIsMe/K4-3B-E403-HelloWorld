# Handoff cho Gemini - CP3 Lesson Notebook

## Prompt dùng trực tiếp

Sao chép nguyên khối prompt dưới đây cho Gemini/Coding Agent:

```text
Bạn đang tiếp tục một hackathon project tại:

/home/tu/VinLab/K4-3B-E403-HelloWorld

Hãy đọc toàn bộ repo trước khi sửa, đặc biệt:
- canvas.md
- cp2-flow.md
- docs/data-audit.md
- materials/README.md
- scripts/inspect_materials.py
- .gitignore
- requirements-data.txt

Tuân thủ AGENTS.md nếu có và /home/tu/.codex/RTK.md. Dùng `rtk` cho lệnh sinh nhiều output. Worktree đang có thay đổi chưa commit từ bước audit dữ liệu; giữ lại, không reset/revert và không ghi đè công việc hiện có. Không in API key hoặc commit secrets. Không commit dữ liệu bài giảng, transcript, ảnh trích xuất hay vector DB; tất cả phải nằm dưới materials/raw/ hoặc materials/derived/ đã được ignore.

Mục tiêu sản phẩm:
Xây một “NotebookLM mini” cho VLearn. Học viên chọn bài học và chọn nguồn slide, video hoặc cả hai, rồi hỏi một câu. Hệ thống chỉ trả lời từ các nguồn đã chọn, kèm citation mở đúng trang PDF hoặc đúng timestamp video. Nếu câu hỏi mơ hồ thì hỏi lại. Nếu không đủ bằng chứng thì nói chưa tìm thấy trong nguồn bài giảng, không dùng kiến thức bên ngoài để bù.

Status hiện tại:
- CP1 và CP2 đã hoàn tất, commit gần nhất `385edd0 done cp2`.
- Đã tải local 21 file từ Google Drive: 5 PDF + 16 video, khoảng 360 MB.
- Dữ liệu nằm tại `materials/raw/Data hackathon/` và đã được Git ignore.
- Audit tạo tại `materials/derived/audit/`, cũng đã ignore.
- Tổng cộng 375 trang PDF và 16 video dài 4.451,827 giây (~74 phút 12 giây).
- 21/21 file đọc được; không trùng checksum.
- PDFium trích được text 373/375 trang, 178.190 ký tự.
- PDF ngày 4 trang vật lý 118 và 131 là ảnh có nội dung nhưng chưa OCR.
- Video có H.264 + AAC, đọc được hình và âm thanh, nhưng không có transcript/SRT/VTT hay subtitle track. Phụ đề nhìn thấy là burned-in trong hình.
- Sáu file thiếu extension; ingest phải nhận diện theo metadata/signature hoặc inventory, không chỉ glob `*.pdf`/`*.mp4`.
- PDF ngày 1 phần lớn là setup/lab trong khi video ngày 1 là lý thuyết. Phải coi mỗi file là nguồn riêng; không giả định slide và video cùng ngày khớp từng đoạn.
- Script audit hiện chạy được và output cuối không có lỗi.
- Chưa có transcription, OCR, embedding, vector DB, app RAG, golden set hay eval.

Thay đổi audit đang chưa commit:
- README.md
- .gitignore
- docs/data-audit.md
- materials/README.md
- requirements-data.txt
- scripts/inspect_materials.py

Hãy hoàn thành CP3 theo thứ tự sau, tự triển khai và kiểm thử thay vì chỉ viết kế hoạch:

1. Xác nhận worktree và chạy lại các kiểm tra hiện có. Không tải lại data nếu 21 file đã tồn tại.

2. Làm pilot trước với bài ngày 1, ưu tiên video:
   `materials/raw/Data hackathon/videos/day01/Day1-Token-Context.mp4`
   Video dài khoảng 263 giây.
   Phiên âm tiếng Việt bằng faster-whisper, giữ timestamp start/end từng segment. Dùng model hợp lý với máy hiện có; CPU int8 phải là fallback. Lưu transcript JSONL và bản dễ đọc dưới `materials/derived/`, không commit transcript. Kiểm tra thủ công một số thuật ngữ như token, context/ngữ cảnh, mô hình; ghi rõ chất lượng và lỗi còn lại.

3. Xây ingest có thể chạy lại:
   - Đọc PDF text đã trích theo trang từ audit hoặc trích lại bằng PDFium.
   - Đọc transcript theo timestamp.
   - Tạo chunk có metadata tối thiểu: chunk_id, source_id, lesson_id, source_type, source_path, text, page hoặc start_seconds/end_seconds.
   - Chunk không được cắt mất metadata citation.
   - Bước đầu chỉ cần index ngày 1, nhưng cấu trúc phải mở rộng được cho ngày 2-5.

4. Xây retrieval và grounded answer:
   - Lọc cứng theo lesson_id và source_type/source_id được người dùng chọn trước khi retrieval.
   - Có thể dùng Chroma local + embedding phù hợp. Nếu Gemini API key có sẵn thì dùng SDK chính thức hiện hành; nếu chưa có key, tạo `.env.example`, giữ retrieval/test offline hoạt động và báo rõ bước cần key để sinh câu trả lời.
   - Ưu tiên giải pháp ít thành phần, chạy local dễ dàng. Không cần LangChain nếu code trực tiếp rõ hơn.
   - Model chỉ được nhận các evidence chunks đã retrieval.
   - Trả structured output để citation tham chiếu chunk_id có thật. Backend phải validate citation; không để model tự bịa page/timestamp.
   - Có ba outcome rõ: ANSWER có citation, CLARIFY khi câu hỏi mơ hồ, NOT_FOUND khi không đủ evidence.
   - Không xem similarity score một mình là bằng chứng đủ; dùng ngưỡng và/hoặc bước kiểm tra support có thể giải thích, rồi eval bằng test cases.

5. Xây app Streamlit đủ demo:
   - Chọn lesson.
   - Checkbox/toggle chọn slide và video, hiển thị tên nguồn thực tế.
   - Ô hỏi một câu.
   - Hiển thị answer, outcome và evidence.
   - Citation PDF hiển thị file + trang vật lý.
   - Citation video hiển thị file + mm:ss-mm:ss; nếu Streamlit hỗ trợ start_time ổn định thì mở video tại timestamp, nếu không thì ít nhất phát đúng file và hiển thị timestamp rõ.
   - Không thêm landing page; mở thẳng trải nghiệm hỏi đáp.

6. Golden set/eval cho pilot ngày 1, ít nhất 12 case:
   - Có answer trong slide.
   - Có answer chỉ trong video Token-Context.
   - Có ở cả hai.
   - Chọn slide nhưng evidence chỉ có trong video -> NOT_FOUND.
   - Chọn video nhưng evidence chỉ có trong slide -> NOT_FOUND.
   - Ngoài nội dung bài học dù model biết -> NOT_FOUND.
   - Câu hỏi mơ hồ như “cái này dùng sao?” -> CLARIFY.
   - Kiểm tra citation tồn tại và metadata đúng.
   - Ghi expected outcome, expected source/page/timestamp khi có thể, actual outcome và pass/fail.
   Không tự bịa expected answer: lấy từ text/trancript thật và dẫn đúng nguồn.

7. Viết tài liệu chạy:
   - Một requirements chính được khóa phiên bản hợp lý.
   - `.env.example` không có secret.
   - Lệnh setup, transcribe, ingest, eval và `python -m streamlit run app.py`.
   - Giải thích artifacts nào bị ignore và cách regenerate.
   - Ghi limitation: hai trang cần OCR, transcript chưa phủ toàn bộ video nếu pilot mới làm một video.

8. Verification:
   - Test unit cho logic quan trọng: filter nguồn, format timestamp, citation validation, NOT_FOUND/CLARIFY routing ở mức deterministic có thể test.
   - Chạy audit/ingest/eval/test thực tế.
   - Chạy app local, kiểm tra không crash và báo URL.
   - `git diff --check` và xác nhận `git ls-files materials/raw materials/derived` không có output.
   - Không commit cho đến khi mọi thứ chạy ổn. Sau đó báo status và đề xuất commit; nếu user trước đó đã yêu cầu tự commit thì commit code/docs, tuyệt đối không commit data/secrets.

Quyết định kỹ thuật ưu tiên:
- Python 3.11/3.12.
- Streamlit cho UI.
- faster-whisper cho transcript local.
- PDFium cho PDF text vì đã thử tốt hơn pypdf với PDF ngày 2.
- Chroma local hoặc vector store local tương đương cho pilot.
- Gemini API cho answer generation nếu có key; giữ các bước data/retrieval/eval có thể chạy độc lập khi thiếu key.

Đừng chỉ tạo scaffold. Hãy đi đến một vertical slice chạy thật: hỏi về token/context từ video ngày 1, retrieval ra đúng timestamp, câu trả lời có citation hợp lệ; đồng thời chứng minh một câu ngoài nguồn bị từ chối. Khi gặp vấn đề package/network/API key, xử lý phần offline trước và ghi blocker chính xác.
```

## Status ngắn để báo đội

CP1 và CP2 đã xong và đã commit. Data bài giảng đã tải đủ local: 5 PDF, 16 video, khoảng 360 MB. Audit xác nhận 21/21 file đọc được, 375 trang PDF và khoảng 74 phút video. Text PDF đã trích được 373/375 trang bằng PDFium; hai trang 118 và 131 của PDF ngày 4 cần OCR. Video có âm thanh nhưng không có subtitle/transcript riêng nên bước kế tiếp là chạy faster-whisper.

Data gốc và artifacts trong `materials/raw/`, `materials/derived/` đã được ignore và kiểm tra không bị Git track. Repo hiện có thay đổi audit chưa commit. CP3 còn thiếu transcription, chunking, embedding/vector index, grounded answer, Streamlit app và golden-set eval. Pilot hợp lý nhất là Day 1 với video `Day1-Token-Context.mp4`, sau đó mới mở rộng toàn khóa.

## Git status tại thời điểm handoff

```text
 M README.md
?? .gitignore
?? docs/data-audit.md
?? materials/README.md
?? requirements-data.txt
?? scripts/inspect_materials.py
?? docs/handoff-gemini.md
```

Commit gần nhất:

```text
385edd0 done cp2
dc1f3ba Add CP1 canvas
97f1ef3 first commit
```
