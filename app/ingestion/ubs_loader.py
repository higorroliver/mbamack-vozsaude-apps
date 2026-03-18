"""Módulo para carregamento de dados de UBS a partir de arquivo CSV."""

import csv
from pathlib import Path
from typing import List

from app.storage.models import UBSInput
from app.utils.logging import get_logger

logger = get_logger("ubs_loader")


def load_ubs_from_csv(file_path: Path) -> List[UBSInput]:
    """
    Carrega a lista de UBS a partir de um arquivo CSV.

    O CSV deve conter as colunas: nome, endereco, cidade, estado.
    As colunas cidade e estado são opcionais (padrão: São Paulo, SP).

    Args:
        file_path: Caminho para o arquivo CSV.

    Returns:
        Lista de objetos UBSInput.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o CSV estiver mal formatado.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")

    ubs_list: List[UBSInput] = []

    logger.info(f"Carregando UBS do arquivo: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"Arquivo CSV vazio ou sem cabeçalho: {file_path}")

        # Verificar coluna obrigatória
        if "nome" not in reader.fieldnames:
            raise ValueError(
                f"Coluna 'nome' não encontrada no CSV. "
                f"Colunas encontradas: {reader.fieldnames}"
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                nome = row.get("nome", "").strip()
                if not nome:
                    logger.warning(f"Linha {row_num}: nome vazio, pulando.")
                    continue

                ubs_input = UBSInput(
                    nome=nome,
                    endereco=row.get("endereco", "").strip(),
                    cidade=row.get("cidade", "São Paulo").strip() or "São Paulo",
                    estado=row.get("estado", "SP").strip() or "SP",
                )
                ubs_list.append(ubs_input)

            except Exception as e:
                logger.warning(f"Linha {row_num}: erro ao processar - {e}")
                continue

    logger.info(f"Total de {len(ubs_list)} UBS carregadas com sucesso.")
    return ubs_list


def create_mock_ubs_csv(file_path: Path) -> None:
    """
    Cria um arquivo CSV mock com dados de UBS para testes.

    Args:
        file_path: Caminho onde salvar o CSV.
    """
    mock_data = [
        {
            "nome": "UBS Vila Mariana",
            "endereco": "Rua José de Magalhães, 351 - Vila Mariana",
            "cidade": "São Paulo",
            "estado": "SP",
        },
        {
            "nome": "UBS Jardim São Savério",
            "endereco": "Av. do Cursino, 1590 - Vila Moraes",
            "cidade": "São Paulo",
            "estado": "SP",
        },
        {
            "nome": "UBS Parque Bristol",
            "endereco": "Rua Prof. Artur Primavesi, 700 - Parque Bristol",
            "cidade": "São Paulo",
            "estado": "SP",
        },
        {
            "nome": "UBS Vila Guarani",
            "endereco": "Rua Bom Pastor, 800 - Vila Guarani",
            "cidade": "São Paulo",
            "estado": "SP",
        },
        {
            "nome": "UBS Chácara Inglesa",
            "endereco": "Rua Loefgren, 1587 - Vila Clementino",
            "cidade": "São Paulo",
            "estado": "SP",
        },
    ]

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["nome", "endereco", "cidade", "estado"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mock_data)

    logger.info(f"Arquivo CSV mock criado com {len(mock_data)} UBS em: {file_path}")
