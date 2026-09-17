# Dữ liệu bài giảng

## Cài môi trường

Chạy từ thư mục gốc repo. Đã kiểm tra bằng Python 3.12 trên Linux.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-data.txt
```

Các công cụ này tải và kiểm tra file, chưa gọi LLM, chưa cần API key. PyAV đọc video bằng thư viện FFmpeg đi kèm wheel; bộ kiểm tra không gọi lệnh `ffmpeg` hệ thống.

## Tải dữ liệu

```bash
gdown 'https://drive.google.com/drive/folders/1nALOfjZBr_EPHwsn5_zKABFOJzI51F_V' \
  --no-cookies --continue --retries 3 --timeout 60 \
  -O materials/raw/
```

Lệnh giữ nguyên cấu trúc và tên file trên Drive. Với thư mục hiện tại, file nằm trong `materials/raw/Data hackathon/`. Tùy chọn `--continue` tiếp tục file tải dở và bỏ qua file đã tải; không dùng nó để xác nhận một bản local đã đồng bộ với nội dung Drive bị thay thế.

Không cần đổi tên những file thiếu phần mở rộng để kiểm tra: script nhận diện PDF và MP4 từ nội dung đầu file.

## Kiểm tra và trích nội dung

```bash
python scripts/inspect_materials.py
```

Script thực hiện:

- Tính SHA-256, gán mã nguồn theo nội dung file và suy ra ngày học từ tên file.
- Trích chữ PDF theo trang, giữ số trang vật lý bắt đầu từ 1 để dùng cho citation.
- Thống kê trang không có chữ hoặc dưới 80 ký tự; render ảnh các trang không có chữ để kiểm tra thủ công.
- Đọc thời lượng, codec, độ phân giải, track âm thanh và track phụ đề của video.
- Thử giải mã hình tại khoảng 10%, 50%, 90% thời lượng và frame âm thanh đầu tiên.
- Ghi lỗi từng file và trả exit code khác 0 nếu có lỗi đọc file.

Kết quả nằm trong `materials/derived/audit/`:

| Đường dẫn | Nội dung |
|---|---|
| `inventory.json` | Danh sách nguồn, checksum, metadata và thống kê |
| `pages/*.jsonl` | Chữ từng trang cùng `source_id` và `page` |
| `pdf-previews/*.png` | Ảnh các trang không trích được chữ |
| `frames/*.jpg` | Khung hình giữa mỗi video |
| `video-contact-sheet.jpg` | Ảnh tổng hợp để xem nhanh 16 video |

PDFium là bộ trích chữ mặc định sau khi kiểm tra dữ liệu thực tế. Có thể chạy pypdf để đối chiếu vào thư mục riêng:

```bash
python scripts/inspect_materials.py \
  --pdf-engine pypdf --output materials/derived/audit-pypdf
```

`pypdf[crypto]` được cài để đọc PDF ngày 2 dùng AES. Script chưa OCR, phiên âm, tạo embedding hay kiểm tra toàn bộ frame video. Exit code 0 chỉ xác nhận các phép kiểm tra đã chạy thành công, không có nghĩa dữ liệu đã hoàn chỉnh để RAG.

## Quy tắc lưu trữ

`materials/raw/` và `materials/derived/` đều được ignore, kể cả file không có đuôi mở rộng. Đặt transcript, ảnh OCR và vector index phát sinh vào `materials/derived/` để không đưa nội dung bài giảng lên repo.

```bash
git check-ignore -v materials/raw/example.pdf materials/derived/transcript.json
git ls-files materials/raw materials/derived
```

Lệnh thứ hai phải không in file nào. Git chỉ lưu hướng dẫn, script và [báo cáo tổng hợp](../docs/data-audit.md).
