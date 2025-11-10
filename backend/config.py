from pydantic import BaseModel
from dotenv import load_dotenv
import os


class Settings(BaseModel):
    """Cấu hình ứng dụng đọc từ biến môi trường."""

    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    environment: str = "development"


def get_settings() -> Settings:
    """Nạp .env và trả về Settings."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise RuntimeError(
            "Thiếu GOOGLE_API_KEY. Hãy tạo file .env và điền khóa API."
        )
    return Settings(google_api_key=api_key, gemini_model=model)
