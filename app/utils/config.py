"""Módulo de configuração do projeto Vozes da Saúde."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class ScraperConfig:
    """Configurações do scraper do Google Maps."""

    headless: bool = True
    timeout: int = 15
    max_reviews_per_ubs: int = 50
    retry_attempts: int = 3
    retry_delay: float = 2.0
    scroll_pause: float = 1.5
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


@dataclass
class PathsConfig:
    """Configurações de caminhos de arquivos."""

    input_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "input")
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "output")
    ubs_input_file: str = "ubs_list.csv"

    def __post_init__(self) -> None:
        """Cria os diretórios se não existirem."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ubs_input_path(self) -> Path:
        """Caminho completo para o arquivo de entrada de UBS."""
        return self.input_dir / self.ubs_input_file


@dataclass
class AppConfig:
    """Configuração principal da aplicação."""

    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )
    chrome_driver_path: Optional[str] = field(
        default_factory=lambda: os.getenv("CHROME_DRIVER_PATH")
    )


def get_config() -> AppConfig:
    """Retorna a configuração da aplicação."""
    return AppConfig()
