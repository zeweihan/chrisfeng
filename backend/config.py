"""Configuration management."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    DEFAULT_USERNAME: str = os.getenv("DEFAULT_USERNAME", "admin")
    DEFAULT_PASSWORD: str = os.getenv("DEFAULT_PASSWORD", "hr2026")

    # Database
    DB_PATH: str = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.getenv("DATABASE_URL", "sqlite:///../Data/hr_report.db").replace("sqlite:///", ""),
        )
    )

    # Upload
    UPLOAD_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.getenv("UPLOAD_DIR", "../Data/uploads"))
    )
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_TEXT_MODEL: str = os.getenv("LLM_TEXT_MODEL", "gemini-3.1-pro-preview")
    LLM_IMAGE_MODEL: str = os.getenv("LLM_IMAGE_MODEL", "gemini-3-pro-image-preview")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "*"]


settings = Settings()
