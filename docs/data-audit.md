# Kiểm tra dữ liệu bài giảng

Ngày kiểm tra: 17/09/2026. Phạm vi: tải và đánh giá dữ liệu trước khi xây pipeline RAG.

## Kết quả

Đã tải đủ 21 file được liệt kê trong thư mục Drive: 5 PDF và 16 video, tổng 359.991.009 byte (khoảng 360 MB). Giữ nguyên tên và cấu trúc nguồn tại `materials/raw/Data hackathon/`.

| Ngày học | Trang PDF | Video | Tổng thời lượng video |
|---|---:|---:|---:|
| Ngày 1 | 32 | 5 | 18 phút 31 giây |
| Ngày 2 | 49 | 5 | 20 phút 23 giây |
| Ngày 3 | 46 | 4 | 17 phút 34 giây |
| Ngày 4 | 204 | 1 | 7 phút 42 giây |
| Ngày 5 | 44 | 1 | 10 phút 01 giây |
| Tổng | 375 | 16 | 74 phút 12 giây |

Thời lượng từng dòng làm tròn độc lập; tổng lấy từ thời lượng gốc 4.451,827 giây.

- 21/21 file đọc được bằng bộ kiểm tra cuối; không có file trùng SHA-256.
- PDFium trích được chữ ở 373/375 trang, tổng 178.190 ký tự sau khi bỏ khoảng trắng đầu/cuối trang. Không xuất hiện ký tự thay thế Unicode U+FFFD.
- 19 trang có dưới 80 ký tự, gồm 2 trang không có chữ. Đây là tín hiệu để xem lại, không phải kết luận trang bị lỗi.
- 16/16 video có hình H.264 và âm thanh AAC 48 kHz; các mẫu giải mã đều thành công.
- Độ phân giải: 1 video 360p, 13 video 720p và 2 video 1080p.
- Không có file transcript/SRT/VTT riêng hoặc track phụ đề nhúng. Các khung hình đã xem có phụ đề dính trong hình.

## Những điểm ảnh hưởng đến RAG

### Trích chữ PDF ngày 2

pypdf đọc được PDF sau khi cài phần phụ thuộc AES, nhưng tạo nhiều khoảng trắng giữa các ký tự và một số tên glyph. Thử PDFium trên các trang mẫu cho chữ tiếng Việt liền mạch hơn. Script đã chuyển sang PDFium mặc định và chạy lại toàn bộ 5 PDF.

Không phát hiện U+FFFD không đồng nghĩa trích chữ đúng. Vẫn cần kiểm tra thứ tự đọc bảng, sơ đồ, code và các dòng bị ngắt trước khi chia đoạn.

### Hai trang cần OCR

Trang vật lý 118 và 131 của PDF ngày 4 có nội dung về tool calling nhưng không có lớp chữ trích được. Đã render và xem ảnh để xác nhận đây không phải trang trắng. Ảnh nằm trong `materials/derived/audit/pdf-previews/`; chưa chạy OCR.

Các trang vừa có chữ vừa có hình cũng có thể thiếu thông tin nếu chỉ dùng text. Việc kiểm tra trang trống không bao phủ trường hợp này.

### Slide và video không khớp từng trang

PDF ngày 1 chủ yếu là setup và hướng dẫn lab, còn 5 video chứa lý thuyết AI/LLM, attention, token và context. Không suy ra một câu trả lời có bằng chứng trong slide chỉ vì nó xuất hiện ở video cùng ngày.

Nên quản lý mỗi PDF/video bằng một `source_id` riêng, nhóm theo ngày học; citation PDF dùng trang vật lý, citation transcript dùng thời gian trong đúng file video. Số slide in trên trang có thể khác số trang vật lý.

### Tên file thiếu phần mở rộng

Có 6 file thiếu đuôi: PDF ngày 3, 4 video ngày 3 và video ngày 4. Script đã nhận diện đúng từ chữ ký file. Giữ tên gốc để tải lại nhất quán; bước ingest không được chỉ tìm bằng glob `*.pdf` hoặc `*.mp4`.

### Nội dung mẫu trong tài liệu

Một số slide có tên giảng viên hoặc thông tin liên hệ dạng mẫu. Cần tách nội dung hành chính này khỏi kiến thức bài học khi xây bộ câu hỏi kiểm thử; không coi chúng là thông tin liên hệ đã được xác minh.

## Phạm vi đã kiểm tra

Đã tính checksum local, đọc toàn bộ trang PDF, giải mã 3 điểm hình và frame âm thanh đầu tiên của từng video, xem ảnh tổng hợp video và một số trang PDF. Đây không phải kiểm tra giải mã toàn bộ video; chưa đánh giá chất lượng lời nói hay độ chính xác phiên âm. Checksum local dùng nhận diện phiên bản và file trùng, chưa đối chiếu checksum phía Drive.

Chưa phiên âm, OCR, tạo vector DB, gọi LLM hoặc chạy golden set. Nội dung trích xuất và ảnh mẫu đều nằm trong thư mục bị Git ignore.

## Bước tiếp theo

1. Phiên âm thử video `Day1-Token-Context.mp4` (khoảng 4 phút 23 giây), giữ timestamp từng đoạn và đối chiếu thuật ngữ với âm thanh/phụ đề trong hình.
2. Dùng PDF ngày 1 và transcript này để kiểm tra chọn nguồn: chỉ slide, chỉ video, hoặc cả hai. Câu hỏi thiếu bằng chứng phải được nhận diện theo đúng nguồn đang chọn.
3. Khi chất lượng transcript đạt yêu cầu, chia đoạn có metadata rồi mới tạo embedding và xây hỏi đáp cho CP3.

Xem [hướng dẫn chạy lại](../materials/README.md) và [script kiểm tra](../scripts/inspect_materials.py).
