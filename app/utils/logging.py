"""Módulo de logging estruturado para o projeto Vozes da Saúde."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "vozes_da_saude",
    level: str = "INFO",
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Configura e retorna um logger estruturado.

    Args:
        name: Nome do logger.
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Formato customizado para as mensagens de log.

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(module)s:%(funcName)s:%(lineno)d | %(message)s"
        )

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna um logger filho para um módulo específico.

    Args:
        module_name: Nome do módulo.

    Returns:
        Logger configurado para o módulo.
    """
    return logging.getLogger(f"vozes_da_saude.{module_name}")
