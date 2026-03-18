"""Pipeline de enriquecimento de dados de UBS com informações do Google Maps."""

import time
from typing import Dict, List, Tuple

from app.ingestion.google_places_client import GooglePlacesClient
from app.storage.models import ReviewModel, UBSInput, UBSModel
from app.utils.config import ScraperConfig
from app.utils.logging import get_logger

logger = get_logger("enrichment_pipeline")


class EnrichmentPipeline:
    """Pipeline para enriquecer dados de UBS via scraping do Google Maps."""

    def __init__(self, config: ScraperConfig) -> None:
        """
        Inicializa o pipeline de enriquecimento.

        Args:
            config: Configurações do scraper.
        """
        self.config = config
        self.stats: Dict[str, int] = {
            "total_ubs": 0,
            "ubs_sucesso": 0,
            "ubs_erro": 0,
            "total_reviews": 0,
        }

    def run(
        self, ubs_list: List[UBSInput]
    ) -> Tuple[List[UBSModel], List[ReviewModel]]:
        """
        Executa o pipeline de enriquecimento para uma lista de UBS.

        Args:
            ubs_list: Lista de UBS de entrada.

        Returns:
            Tupla com (lista de UBS enriquecidas, lista de avaliações).
        """
        all_ubs: List[UBSModel] = []
        all_reviews: List[ReviewModel] = []

        self.stats["total_ubs"] = len(ubs_list)

        logger.info(f"Iniciando pipeline de enriquecimento para {len(ubs_list)} UBS.")

        with GooglePlacesClient(self.config) as client:
            for idx, ubs_input in enumerate(ubs_list, start=1):
                logger.info(
                    f"[{idx}/{len(ubs_list)}] Processando: {ubs_input.nome}"
                )

                try:
                    query = ubs_input.search_query
                    ubs, reviews = client.scrape_ubs(
                        query=query, nome_original=ubs_input.nome
                    )

                    if ubs is not None:
                        all_ubs.append(ubs)
                        all_reviews.extend(reviews)
                        self.stats["ubs_sucesso"] += 1
                        self.stats["total_reviews"] += len(reviews)
                        logger.info(
                            f"Sucesso: {ubs.nome} - "
                            f"{len(reviews)} avaliações coletadas."
                        )
                    else:
                        self.stats["ubs_erro"] += 1
                        logger.warning(
                            f"Falha ao coletar dados de: {ubs_input.nome}"
                        )

                except Exception as e:
                    self.stats["ubs_erro"] += 1
                    logger.error(
                        f"Erro ao processar '{ubs_input.nome}': {e}"
                    )

                # Pausa entre requisições para evitar bloqueio
                if idx < len(ubs_list):
                    delay = self.config.retry_delay
                    logger.debug(f"Aguardando {delay}s antes da próxima UBS...")
                    time.sleep(delay)

        self._log_stats()

        return all_ubs, all_reviews

    def _log_stats(self) -> None:
        """Registra estatísticas finais do pipeline."""
        logger.info("=" * 60)
        logger.info("ESTATÍSTICAS DO PIPELINE DE ENRIQUECIMENTO")
        logger.info(f"  Total de UBS processadas: {self.stats['total_ubs']}")
        logger.info(f"  UBS com sucesso:          {self.stats['ubs_sucesso']}")
        logger.info(f"  UBS com erro:             {self.stats['ubs_erro']}")
        logger.info(f"  Total de avaliações:      {self.stats['total_reviews']}")
        logger.info("=" * 60)
