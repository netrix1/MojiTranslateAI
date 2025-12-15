from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_data_dir: str = "../data"
    pipeline_path: str = "../pipelines/default_page_pipeline.json"

    ocr_engine: str = "mangaocr"  # mangaocr | stub
    ocr_max_blocks: int = 40


    # Regions detection (speech balloons / text boxes)
    regions_min_area: int = 3000
    regions_max_area_ratio: float = 0.25
    regions_pad: int = 8
    dummy_mode: bool = True
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    def data_dir(self) -> Path:
        return Path(self.app_data_dir).resolve()

settings = Settings()
