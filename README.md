# IELTS Writing Assistant

Dự án gồm backend FastAPI và frontend tĩnh giúp sinh đề, chấm bài IELTS Writing qua Gemini.

## Chuẩn bị
1. Cài Python 3.10+
2. Sao chép `.env.example` thành `.env` và điền `GOOGLE_API_KEY`

## Cài đặt
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy backend
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

- Health check: `GET http://127.0.0.1:8000/api/health`
- Sinh đề: `GET http://127.0.0.1:8000/api/generate_task`
- Chấm bài: `POST http://127.0.0.1:8000/api/grade` body:

```json
{
  "prompt": "...",
  "essay": "..."
}
```

## Mở frontend
Mở file `frontend/index.html` bằng trình duyệt. Giao diện sẽ gọi API backend tại `http://127.0.0.1:8000`.

## Ghi chú
- Thư viện: `google-genai` (đã thay thế `google-generativeai`).
- Model mặc định: `gemini-2.5-flash` (có thể đổi qua `GEMINI_MODEL` trong `.env`).
- Đảm bảo biến môi trường `GOOGLE_API_KEY` hợp lệ.
