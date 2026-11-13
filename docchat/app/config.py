import os


class Settings:
    data_dir = os.getenv("DATA_DIR", "./data")
    llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_model = os.getenv("LLM_MODEL", "llama3.2")
    llm_api_key = os.getenv("LLM_API_KEY", "ollama")  # Ollama ignores it; hosted free tiers need a real one
    top_k = int(os.getenv("TOP_K", "5"))
    max_distance = float(os.getenv("MAX_DISTANCE", "0.75"))
    chunk_size = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
    max_question_chars = 1000
    history_turns = 6
    allowed_ext = {".pdf", ".txt", ".md"}


settings = Settings()
