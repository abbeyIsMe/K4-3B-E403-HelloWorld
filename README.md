# VLearn NotebookLM (v1.0)
**Universal Grounded Lecture Research Assistant · Batch 04 · Class 3B · Room E403 · Team HelloWorld**

Trợ lý nghiên cứu bài giảng thông minh phong cách **Google NotebookLM** dành cho sinh viên VLearn. Hệ thống tra cứu xuyên suốt toàn bộ **5 bài học (375 trang Slide PDF + 16 video bài giảng ~74 phút)**, trả lời chính xác, trích dẫn minh bạch và tự động điều hướng trực quan đến đúng trang slide và mốc thời gian video.

---

## 🌟 Tính Năng Nổi Bật (v1.0)

1. **Tra Cứu Khái Niệm Xuyên Bài Học (Universal Search):**
   - Sinh viên không cần nhớ khái niệm thuộc bài học nào; hệ thống tự động quét 672 chunks kiến thức từ Day 1 đến Day 5 để tìm đúng nguồn.
2. **Kiến Trúc Hybrid Retrieval & Vector DB Chuẩn Xác:**
   - **Dense Semantic Vector:** 672 chunks được nhúng vector 3072 chiều (`gemini-embedding-001`), chuẩn hóa $L_2$ để tính nhanh Cosine Similarity.
   - **Intent-Aware Contextual Reranking:** Tự động phân tích ý định câu hỏi (Định nghĩa / Quy trình / Tính toán). Các câu hỏi khái niệm (ví dụ: *"Token là gì?"*) ưu tiên tuyệt đối các đoạn chứa vị ngữ định nghĩa cốt lõi, loại bỏ các đoạn chỉ nhắc từ khóa ngẫu nhiên trong bảng tính hay tham số code.
   - **Reciprocal Rank Fusion (RRF):** Kết hợp Dense Vector và Sparse BM25 với cơ chế cân bằng nguồn (Dual-source allocation).
3. **Bộ Thanh Tra Dẫn Chứng Đồng Bộ (Dual-Source Inspector):**
   - Tự động nhảy sang tab Video hoặc Slide khi nhấn vào trích dẫn.
   - **Slide PDF:** Tự động mở đúng số trang vật lý, hỗ trợ lật trang trước/sau.
   - **Video Player:** Tự động tua đến đúng giây bắt đầu của trích dẫn (`start_time`), hỗ trợ HTTP 206 Range Streaming mượt mà.
4. **100% Grounded & Lọc Trích Dẫn Trung Thực:**
   - AI từ chối suy đoán ngoài tài liệu (*Strict Grounding*).
   - Chỉ tạo nút điều hướng cho những nguồn **thực sự được trích dẫn** trong câu trả lời.
5. **Giao Diện NotebookLM Responsive:**
   - Bố cục 2 cột cân đối 50/50, tự động co giãn 1 cột trên Mobile/Tablet.
   - Hỗ trợ đầy đủ Light Mode và Dark Mode.
   - Gợi ý câu hỏi nhanh dạng Pills (`st.pills`) chống vỡ chữ.

---

## 📊 Kết Quả Đánh Giá (Golden Evaluation)

Hệ thống đã được kiểm thử toàn diện trên bộ 12 test cases chuẩn (`eval/golden_set_day01.json`):

| Tiêu chí | Kết quả | Trạng thái |
|---|---|---|
| **Độ chính xác Outcome (Answer / Clarify / Not Found)** | **12 / 12 (100.0%)** | ✅ Đạt tuyệt đối |
| **Độ trung thực trích dẫn (Grounded Precision)** | **100%** | ✅ Không bịa nguồn |
| **Hỗ trợ định dạng kép (PDF & Video)** | Đầy đủ cả 2 nguồn | ✅ Hoàn thành |

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Khởi tạo môi trường
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Cấu hình API Key
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```
Mở `.env` và điền Gemini API Key (lấy miễn phí tại [Google AI Studio](https://aistudio.google.com)):
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

### 3. Chuẩn bị dữ liệu & Index Vector
Dữ liệu gốc đặt trong thư mục `materials/raw/`. Chạy các bước tiền xử lý:
```bash
# Trích xuất slide PDF và tạo metadata chunks
python src/ingest.py

# Xây dựng dense vector index (tự động lưu vào materials/derived/embeddings/)
python scripts/build_vector_index.py
```

### 4. Khởi chạy ứng dụng
```bash
streamlit run app.py
```
Mở trình duyệt tại: **`http://localhost:8501`**.

---

## 📁 Cấu Trúc Dự Án

```text
├── app.py                      # Giao diện chính Streamlit Studio
├── src/
│   ├── ingest.py               # Trích xuất PDF và chuẩn hóa chunks
│   ├── retrieval.py            # BM25 + Intent-Aware Contextual Reranking
│   ├── vector_store.py         # Dense Vector Search & Hybrid RRF
│   └── grounded_answer.py      # Tạo câu trả lời có kiểm chứng & lọc trích dẫn
├── scripts/
│   ├── build_vector_index.py   # Script tạo nhúng vector cho toàn bộ 672 chunks
│   ├── run_eval.py             # Bộ đánh giá tự động (Golden Set Evaluation)
│   ├── inspect_materials.py    # Kiểm toán tính toàn vẹn của dữ liệu gốc
│   └── transcribe_remaining_videos.py # Whisper ASR phiên âm 16 video
├── eval/
│   ├── golden_set_day01.json   # 12 kịch bản kiểm thử chuẩn
│   └── eval_report.md          # Báo cáo đánh giá chi tiết
├── requirements.txt            # Danh mục thư viện ứng dụng
├── .env.example                # File mẫu cấu hình môi trường
└── .gitignore                  # Loại trừ dữ liệu nặng và API keys nhạy cảm
```

---

## 🔒 Bảo Mật & Bản Quyền

- Các file dữ liệu bài giảng (`materials/raw/`, `materials/derived/`) và thông tin bảo mật (`.env`, `.venv/`) được loại bỏ hoàn toàn khỏi Git bằng `.gitignore`.
- Dự án tuân thủ quy chế Hackathon Batch 04 · Lớp 3B · Phòng E403.
