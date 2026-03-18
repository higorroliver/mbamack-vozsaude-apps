#!/usr/bin/env python3
"""
Script principal do pipeline Vozes da Saúde.

Executa o fluxo completo:
1. Carrega lista de UBS de um arquivo CSV
2. Realiza web scraping no Google Maps para cada UBS
3. Salva dados enriquecidos em arquivos CSV

Uso:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --input data/input/ubs_list.csv
    python scripts/run_pipeline.py --max-reviews 30
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Adicionar o diretório raiz ao path para imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.ingestion.enrichment_pipeline import EnrichmentPipeline  # noqa: E402
from app.ingestion.ubs_loader import create_mock_ubs_csv, load_ubs_from_csv  # noqa: E402
from app.storage.database import CSVStorage  # noqa: E402
from app.utils.config import get_config  # noqa: E402
from app.utils.logging import setup_logger  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Processa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Vozes da Saúde - Pipeline de coleta de avaliações de UBS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/run_pipeline.py
  python scripts/run_pipeline.py --input minha_lista.csv
  python scripts/run_pipeline.py --max-reviews 100 --no-headless
        """,
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Caminho para o arquivo CSV de entrada com a lista de UBS",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Diretório de saída para os arquivos gerados",
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=50,
        help="Número máximo de avaliações por UBS (padrão: 50)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Executar o navegador em modo visível (não headless)",
    )
    parser.add_argument(
        "--create-mock",
        action="store_true",
        help="Criar arquivo CSV mock para testes",
    )

    return parser.parse_args()


def main() -> None:
    """Função principal do pipeline."""
    args = parse_args()
    config = get_config()

    # Configurar logging
    logger = setup_logger(level=config.log_level)

    logger.info("=" * 60)
    logger.info("  VOZES DA SAÚDE - Pipeline de Coleta de Avaliações")
    logger.info("=" * 60)

    start_time = time.time()

    # Configurar caminhos
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = config.paths.ubs_input_path

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = config.paths.output_dir

    # Criar mock se solicitado ou se o arquivo de entrada não existir
    if args.create_mock or not input_path.exists():
        if not input_path.exists():
            logger.info(
                f"Arquivo de entrada não encontrado: {input_path}. "
                "Criando arquivo mock..."
            )
        create_mock_ubs_csv(input_path)

    # Atualizar configurações do scraper
    config.scraper.max_reviews_per_ubs = args.max_reviews
    if args.no_headless:
        config.scraper.headless = False

    try:
        # Etapa 1: Carregar lista de UBS
        logger.info("ETAPA 1: Carregando lista de UBS...")
        ubs_list = load_ubs_from_csv(input_path)

        if not ubs_list:
            logger.error("Nenhuma UBS encontrada no arquivo de entrada.")
            sys.exit(1)

        logger.info(f"Total de {len(ubs_list)} UBS carregadas.")

        # Etapa 2: Enriquecimento via scraping do Google Maps
        logger.info("ETAPA 2: Iniciando scraping do Google Maps...")
        pipeline = EnrichmentPipeline(config=config.scraper)
        enriched_ubs, reviews = pipeline.run(ubs_list)

        # Etapa 3: Salvar dados
        logger.info("ETAPA 3: Salvando dados coletados...")
        storage = CSVStorage(output_dir=output_dir)

        # Salvar dados brutos (Bronze Layer - JSON)
        raw_data: List[Dict[str, Any]] = []
        for ubs in enriched_ubs:
            ubs_dict: Dict[str, Any] = ubs.model_dump()
            ubs_reviews = [
                r.model_dump() for r in reviews if r.place_id == ubs.place_id
            ]
            ubs_dict["reviews"] = ubs_reviews
            raw_data.append(ubs_dict)

        json_path = storage.save_raw_json(raw_data, prefix="bronze_raw")
        logger.info(f"Dados brutos salvos em: {json_path}")

        # Salvar CSV de UBS enriquecidas
        ubs_csv_path = storage.save_ubs(enriched_ubs)
        logger.info(f"CSV de UBS salvo em: {ubs_csv_path}")

        # Salvar CSV de avaliações
        reviews_csv_path = storage.save_reviews(reviews)
        logger.info(f"CSV de avaliações salvo em: {reviews_csv_path}")

        # Resumo final
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("  PIPELINE FINALIZADO COM SUCESSO")
        logger.info(f"  Tempo total: {elapsed:.1f} segundos")
        logger.info(f"  UBS enriquecidas: {len(enriched_ubs)}")
        logger.info(f"  Avaliações coletadas: {len(reviews)}")
        logger.info(f"  Arquivos gerados em: {output_dir}")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrompido pelo usuário.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erro inesperado no pipeline: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
