# VLearn NotebookLM (v2.0)
**Progressive Grounded Lecture Research Assistant · Batch 04 · Class 3B · Room E403 · Team HelloWorld**

## Thành viên nhóm & Phân công

| Họ và tên | Mã học viên | Vai trò chính | Phần việc trong dự án |
|---|---:|---|---|
| Hồ Hoàng Phương Anh | 02460 | Evidence / research | Mining chatlog, khảo sát, số liệu pain point và impact, pdf cuối |
| Đào Duy Hiếu | 02651 | Retrieval / prompt | BM25, dense retrieval, RRF, evidence gate và grounded prompt |
| Trần Tuấn Tú | 02840 | Prototype / integration | Streamlit app, Gemini integration, chat UI, PDF/video inspector và demo |
| Vũ Bá Anh | 02893 | Spec / evaluation | AI Spec, golden set, evaluation và phản biện |

Trợ lý nghiên cứu bài giảng thông minh phong cách **Google NotebookLM** dành cho sinh viên VLearn. Hệ thống tra cứu tích lũy từ **Day01 đến bài học hiện tại** (hiện gồm 5 bài: 375 trang Slide PDF + 16 video ~74 phút), trả lời có căn cứ, trích dẫn minh bạch và tự động điều hướng đến đúng trang slide hoặc mốc thời gian video. Khi có Day06, dữ liệu Day06 được bổ sung vào cùng kho tri thức.

---

## 🌟 Tính Năng Nổi Bật (v2.0)

1. **Tra Cứu Tích Lũy Đến Bài Hiện Tại (Progressive Search):**
   - Sinh viên không cần nhớ khái niệm thuộc bài nào; hệ thống tìm trong corpus từ Day01 đến bài hiện tại. Corpus hiện có 672 chunks từ Day01–Day05 và sẽ mở rộng khi có bài mới.
2. **Kiến Trúc Hybrid Retrieval & Vector DB Chuẩn Xác:**
   - **Dense Semantic Vector:** 672 chunks được nhúng vector 3072 chiều (`gemini-embedding-001`), chuẩn hóa $L_2$ để tính nhanh Cosine Similarity.
   - **Intent-Aware Contextual Reranking:** Tự động phân tích ý định câu hỏi (Định nghĩa / Quy trình / Tính toán). Các câu hỏi khái niệm (ví dụ: *"Token là gì?"*) ưu tiên tuyệt đối các đoạn chứa vị ngữ định nghĩa cốt lõi, loại bỏ các đoạn chỉ nhắc từ khóa ngẫu nhiên trong bảng tính hay tham số code.
   - **Reciprocal Rank Fusion (RRF):** Kết hợp Dense Vector và Sparse BM25 với cơ chế cân bằng nguồn (Dual-source allocation).
3. **Bộ Thanh Tra Dẫn Chứng Đồng Bộ (Dual-Source Inspector):**
   - Tự động nhảy sang tab Video hoặc Slide khi nhấn vào trích dẫn.
   - **Slide PDF:** Tự động mở đúng số trang vật lý, hỗ trợ lật trang trước/sau.
   - **Video Player:** Tự động tua đến đúng giây bắt đầu của trích dẫn (`start_time`), hỗ trợ HTTP 206 Range Streaming mượt mà.
4. **Grounded answer & Lọc Trích Dẫn Trung Thực:**
   - Nội dung từ slide/video được tách khỏi kiến thức bổ sung ngoài bài giảng.
   - Câu hỏi không có evidence phù hợp bị từ chối thay vì gán citation rác.
   - Chỉ tạo nút điều hướng cho những nguồn **thực sự được trích dẫn** trong câu trả lời.
5. **Giao Diện NotebookLM Responsive:**
   - Bố cục Sources / Chat / Source Inspector theo workflow NotebookLM.
   - Hỗ trợ đầy đủ Light Mode và Dark Mode.
   - Gợi ý câu hỏi nhanh dạng Pills (`st.pills`) chống vỡ chữ.

---

## 📊 Kết Quả Đánh Giá

Hệ thống có bộ kiểm thử v2 cho retrieval/evidence và một lượt E2E Gemini riêng:

| Tiêu chí | Kết quả | Trạng thái |
|---|---|---|
| **Local retrieval regression** | **100 / 100 (100.0%)** | ✅ Không gọi Gemini |
| **Evidence golden set v2** | **40 / 40 (100.0%)** | ✅ Direct/contextual gate |
| **E2E Gemini outcome** | **20 / 20** | ✅ Citation contract |
| **Claim-level factuality** | Chưa tự động đo | Cần human review |

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
├── app.py                      # Source chính của giao diện Streamlit
├── codebase/
│   ├── app.py                  # Entry point theo cấu trúc repo nộp bài
│   └── README.md               # Cách chạy prototype từ codebase/
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
│   ├── golden_set_day01.json   # Golden set truy hồi
│   ├── golden_set_v2.json      # Golden set evidence v2
│   └── eval_report.md          # Báo cáo đánh giá chi tiết
├── reflection/
│   └── tran-tuan-tu-02840.md   # Reflection cá nhân
├── requirements.txt            # Danh mục thư viện ứng dụng
├── .env.example                # File mẫu cấu hình môi trường
└── .gitignore                  # Loại trừ dữ liệu nặng và API keys nhạy cảm
```

`validation/` chưa được tạo vì nhóm chưa thu thập được nhật ký dùng thử từ
người ngoài một cách hợp lệ. Nhóm chấp nhận không lấy điểm bonus R6 thay vì tạo
dữ liệu giả. `demo-slides.pdf` do các thành viên khác phụ trách.

---

## 🔒 Bảo Mật & Bản Quyền

- Các file dữ liệu bài giảng (`materials/raw/`, `materials/derived/`) và thông tin bảo mật (`.env`, `.venv/`) được loại bỏ hoàn toàn khỏi Git bằng `.gitignore`.
- Dự án tuân thủ quy chế Hackathon Batch 04 · Lớp 3B · Phòng E403.
