"""Módulo de armazenamento de dados em CSV (Bronze Layer)."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.storage.models import ReviewModel, UBSModel
from app.utils.logging import get_logger

logger = get_logger("database")


class CSVStorage:
    """Classe para persistência de dados em arquivos CSV (Bronze Layer)."""

    def __init__(self, output_dir: Path) -> None:
        """
        Inicializa o storage CSV.

        Args:
            output_dir: Diretório de saída para os arquivos.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Retorna timestamp formatado para nomes de arquivo."""
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """
        Sanitiza texto para CSV, removendo quebras de linha e espaços extras.

        Args:
            text: Texto original.

        Returns:
            Texto limpo em uma única linha.
        """
        if not text:
            return text
        # Substituir quebras de linha por espaço
        cleaned = re.sub(r'[\r\n]+', ' ', text)
        # Remover espaços múltiplos
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()

    def save_ubs(self, ubs_list: List[UBSModel]) -> Path:
        """
        Salva a lista de UBS em arquivo CSV.

        Args:
            ubs_list: Lista de modelos UBS.

        Returns:
            Caminho do arquivo CSV gerado.
        """
        if not ubs_list:
            logger.warning("Nenhuma UBS para salvar.")
            return self.output_dir / "ubs_empty.csv"

        timestamp = self._get_timestamp()
        filename = f"ubs_enriquecidas_{timestamp}.csv"
        filepath = self.output_dir / filename

        fieldnames = [
            "place_id",
            "nome",
            "endereco",
            "rating_medio",
            "total_avaliacoes",
            "collected_at",
        ]

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for ubs in ubs_list:
                row = {
                    "place_id": ubs.place_id,
                    "nome": ubs.nome,
                    "endereco": ubs.endereco,
                    "rating_medio": ubs.rating_medio,
                    "total_avaliacoes": ubs.total_avaliacoes,
                    "collected_at": ubs.collected_at.isoformat(),
                }
                writer.writerow(row)

        logger.info(f"UBS salvas em: {filepath} ({len(ubs_list)} registros)")
        return filepath

    def save_reviews(self, reviews: List[ReviewModel]) -> Path:
        """
        Salva a lista de avaliações em arquivo CSV.

        Args:
            reviews: Lista de modelos de avaliação.

        Returns:
            Caminho do arquivo CSV gerado.
        """
        if not reviews:
            logger.warning("Nenhuma avaliação para salvar.")
            return self.output_dir / "reviews_empty.csv"

        timestamp = self._get_timestamp()
        filename = f"reviews_{timestamp}.csv"
        filepath = self.output_dir / filename

        fieldnames = [
            "review_id",
            "place_id",
            "author_name",
            "rating",
            "review_text",
            "review_date",
            "collected_at",
        ]

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for review in reviews:
                row = {
                    "review_id": review.review_id,
                    "place_id": review.place_id,
                    "author_name": self._sanitize_text(
                        review.author_name
                    ),
                    "rating": review.rating,
                    "review_text": self._sanitize_text(
                        review.review_text
                    ),
                    "review_date": review.review_date,
                    "collected_at": review.collected_at.isoformat(),
                }
                writer.writerow(row)

        logger.info(f"Avaliações salvas em: {filepath} ({len(reviews)} registros)")
        return filepath

    def save_raw_json(
        self, data: List[Dict[str, Any]], prefix: str = "raw"
    ) -> Path:
        """
        Salva dados brutos em formato JSON (Bronze Layer).

        Args:
            data: Dados brutos a serem salvos.
            prefix: Prefixo do nome do arquivo.

        Returns:
            Caminho do arquivo JSON gerado.
        """
        timestamp = self._get_timestamp()
        filename = f"{prefix}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Dados brutos salvos em: {filepath}")
        return filepath
