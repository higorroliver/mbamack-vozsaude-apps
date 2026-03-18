"""Cliente de scraping do Google Maps para coleta de dados de UBS."""

import hashlib
import re
import time
import urllib.parse
from typing import List, Optional, Tuple

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.storage.models import ReviewModel, UBSModel
from app.utils.config import ScraperConfig
from app.utils.logging import get_logger

logger = get_logger("google_places_client")


class GooglePlacesClient:
    """Cliente para scraping de dados do Google Maps via Selenium."""

    GOOGLE_MAPS_URL = "https://www.google.com/maps"

    def __init__(self, config: ScraperConfig) -> None:
        """
        Inicializa o cliente do Google Maps.

        Args:
            config: Configurações do scraper.
        """
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None

    def _create_driver(self) -> webdriver.Chrome:
        """Cria e configura o WebDriver do Chrome."""
        chrome_options = Options()

        if self.config.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.config.user_agent}")
        chrome_options.add_argument("--lang=pt-BR")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(5)

        return driver

    def start(self) -> None:
        """Inicia o WebDriver."""
        logger.info("Iniciando WebDriver do Chrome...")
        self.driver = self._create_driver()
        logger.info("WebDriver iniciado com sucesso.")

    def stop(self) -> None:
        """Encerra o WebDriver."""
        if self.driver:
            logger.info("Encerrando WebDriver...")
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver encerrado.")

    def __enter__(self) -> "GooglePlacesClient":
        """Context manager - entrada."""
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager - saída."""
        self.stop()

    def _wait_for_element(
        self, by: By, value: str, timeout: Optional[int] = None
    ) -> object:
        """
        Aguarda um elemento ficar visível na página.

        Args:
            by: Tipo de seletor.
            value: Valor do seletor.
            timeout: Tempo máximo de espera em segundos.

        Returns:
            O elemento encontrado.
        """
        if timeout is None:
            timeout = self.config.timeout
        assert self.driver is not None
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))

    def _generate_place_id(self, nome: str, endereco: str) -> str:
        """
        Gera um place_id baseado no nome e endereço.

        Args:
            nome: Nome do local.
            endereco: Endereço do local.

        Returns:
            Hash MD5 como place_id.
        """
        raw = f"{nome}_{endereco}".lower().strip()
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def search_place(self, query: str) -> bool:
        """
        Busca um local no Google Maps via URL direta.

        Utiliza a URL de busca do Google Maps diretamente para evitar
        dependência de seletores CSS da caixa de busca, que mudam
        frequentemente.

        Args:
            query: Texto de busca.

        Returns:
            True se a busca foi realizada, False caso contrário.
        """
        assert self.driver is not None
        logger.info(f"Buscando no Google Maps: {query}")

        try:
            # Navegar diretamente para a URL de busca do Google Maps
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"{self.GOOGLE_MAPS_URL}/search/{encoded_query}"
            self.driver.get(search_url)
            time.sleep(4)

            # Aceitar cookies se o botão aparecer
            try:
                accept_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Aceitar') or "
                    "contains(text(), 'Accept') or "
                    "contains(text(), 'Aceito')]",
                )
                accept_btn.click()
                time.sleep(1)
            except NoSuchElementException:
                pass

            # Verificar se um resultado específico foi carregado
            # ou se estamos numa lista de resultados
            time.sleep(2)

            # Se houver uma lista de resultados, clicar no primeiro
            try:
                first_result = self.driver.find_element(
                    By.CSS_SELECTOR, "a.hfpxzc"
                )
                first_result.click()
                time.sleep(3)
            except NoSuchElementException:
                # Pode já estar na página de um local específico
                pass

            logger.info(f"Página carregada: {self.driver.current_url}")
            return True

        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Erro ao buscar local '{query}': {e}")
            return False

    def _extract_place_info(self, nome_original: str) -> Optional[UBSModel]:
        """
        Extrai informações do local a partir da página do Google Maps.

        Args:
            nome_original: Nome original da UBS para fallback.

        Returns:
            Modelo UBS preenchido ou None se não encontrar.
        """
        assert self.driver is not None

        try:
            # Extrair nome do local
            try:
                name_element = self.driver.find_element(
                    By.CSS_SELECTOR, "h1.DUwDvf"
                )
                nome = name_element.text.strip()
            except NoSuchElementException:
                nome = nome_original

            # Extrair endereço
            endereco = ""
            try:
                addr_element = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[data-item-id='address'] div.Io6YTe",
                )
                endereco = addr_element.text.strip()
            except NoSuchElementException:
                try:
                    addr_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, "div.Io6YTe.fontBodyMedium"
                    )
                    for elem in addr_elements:
                        text = elem.text.strip()
                        if text and ("Rua" in text or "Av" in text or "São Paulo" in text):
                            endereco = text
                            break
                except NoSuchElementException:
                    pass

            # Extrair rating médio
            rating_medio: Optional[float] = None
            try:
                rating_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div.F7nice span[aria-hidden='true']"
                )
                rating_text = rating_element.text.strip().replace(",", ".")
                rating_medio = float(rating_text)
            except (NoSuchElementException, ValueError):
                pass

            # Extrair total de avaliações
            total_avaliacoes: Optional[int] = None
            try:
                # Tentar via aria-label do span de reviews
                reviews_element = self.driver.find_element(
                    By.CSS_SELECTOR, "div.F7nice span span[aria-label]"
                )
                reviews_text = reviews_element.get_attribute("aria-label") or ""
                # Formato: "123 avaliações" ou "123 reviews"
                num_text = "".join(c for c in reviews_text if c.isdigit())
                if num_text:
                    total_avaliacoes = int(num_text)
            except (NoSuchElementException, ValueError):
                pass

            # Fallback: buscar total de avaliações em botões ou textos
            if total_avaliacoes is None:
                try:
                    all_buttons = self.driver.find_elements(
                        By.TAG_NAME, "button"
                    )
                    for btn in all_buttons:
                        btn_text = btn.text.strip()
                        # Padrão: "123 avaliações" ou "123 reviews"
                        match = re.search(
                            r"(\d[\d.,]*)\s*(?:avalia|review|resenha)",
                            btn_text,
                            re.IGNORECASE,
                        )
                        if match:
                            num_str = match.group(1).replace(".", "").replace(",", "")
                            total_avaliacoes = int(num_str)
                            break
                except (ValueError, AttributeError):
                    pass

            place_id = self._generate_place_id(nome, endereco)

            ubs = UBSModel(
                place_id=place_id,
                nome=nome,
                endereco=endereco,
                rating_medio=rating_medio,
                total_avaliacoes=total_avaliacoes,
            )

            logger.info(
                f"UBS extraída: {ubs.nome} | Rating: {ubs.rating_medio} | "
                f"Avaliações: {ubs.total_avaliacoes}"
            )

            return ubs

        except Exception as e:
            logger.error(f"Erro ao extrair informações do local: {e}")
            return None

    def _open_reviews_panel(self) -> bool:
        """
        Abre o painel de avaliações no Google Maps.

        Tenta múltiplas estratégias para abrir o painel de avaliações,
        incluindo a aba "Reviews" e botões de avaliações.

        Returns:
            True se o painel foi aberto, False caso contrário.
        """
        assert self.driver is not None

        try:
            # Estratégia 1: Clicar na aba "Reviews" (role='tab')
            tabs = self.driver.find_elements(
                By.CSS_SELECTOR, "button[role='tab']"
            )
            for tab in tabs:
                tab_text = (tab.text or "").strip().lower()
                tab_label = (tab.get_attribute("aria-label") or "").lower()
                if "review" in tab_text or "review" in tab_label:
                    tab.click()
                    time.sleep(3)
                    logger.info("Aba de avaliações aberta via tab.")
                    return True

            # Estratégia 2: Botão de avaliações com jsaction
            reviews_buttons = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[jsaction*='reviews'], button.HHrUdb",
            )

            if not reviews_buttons:
                # Estratégia 3: Botão por aria-label
                reviews_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label, 'avaliações') or "
                    "contains(@aria-label, 'Avaliações') or "
                    "contains(@aria-label, 'reviews') or "
                    "contains(@aria-label, 'Reviews')]",
                )

            # Filtrar botões irrelevantes (Write a review, legal disclosure)
            filtered_buttons = []
            for btn in reviews_buttons:
                btn_text = (btn.text or "").strip().lower()
                btn_label = (btn.get_attribute("aria-label") or "").lower()
                if "write" in btn_text or "write" in btn_label:
                    continue
                if "legal" in btn_label or "disclosure" in btn_label:
                    continue
                filtered_buttons.append(btn)

            for btn in filtered_buttons:
                try:
                    btn.click()
                    time.sleep(2)
                    logger.info("Painel de avaliações aberto via botão.")
                    return True
                except WebDriverException:
                    continue

            logger.warning(
                "Não foi possível abrir o painel de avaliações. "
                "Isso pode ocorrer na visualização limitada do Google Maps "
                "(sem login)."
            )
            return False

        except Exception as e:
            logger.error(f"Erro ao abrir painel de avaliações: {e}")
            return False

    def _scroll_reviews(self, max_scrolls: int = 10) -> None:
        """
        Faz scroll no painel de avaliações para carregar mais avaliações.

        Args:
            max_scrolls: Número máximo de scrolls.
        """
        assert self.driver is not None

        try:
            # Encontrar o container scrollável de avaliações
            scrollable_div = self.driver.find_element(
                By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf"
            )

            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_div
            )

            for i in range(max_scrolls):
                self.driver.execute_script(
                    "arguments[0].scrollTo(0, arguments[0].scrollHeight)",
                    scrollable_div,
                )
                time.sleep(self.config.scroll_pause)

                new_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight", scrollable_div
                )

                if new_height == last_height:
                    logger.debug(f"Scroll finalizado após {i + 1} iterações.")
                    break

                last_height = new_height

        except NoSuchElementException:
            logger.warning("Container de avaliações não encontrado para scroll.")
        except Exception as e:
            logger.error(f"Erro durante scroll de avaliações: {e}")

    def _expand_review_texts(self) -> None:
        """Expande textos de avaliações truncados clicando em 'Mais'."""
        assert self.driver is not None

        try:
            more_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, "button.w8nwRe.kyuRq"
            )
            for btn in more_buttons:
                try:
                    btn.click()
                    time.sleep(0.3)
                except WebDriverException:
                    continue
        except Exception:
            pass

    def _extract_reviews(self, place_id: str) -> List[ReviewModel]:
        """
        Extrai avaliações da página atual do Google Maps.

        Args:
            place_id: Identificador do local.

        Returns:
            Lista de avaliações extraídas.
        """
        assert self.driver is not None
        reviews: List[ReviewModel] = []

        try:
            # Expandir textos truncados
            self._expand_review_texts()

            # Encontrar elementos de avaliação
            review_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div.jftiEf.fontBodyMedium"
            )

            logger.info(f"Encontradas {len(review_elements)} avaliações na página.")

            for idx, review_el in enumerate(review_elements):
                if idx >= self.config.max_reviews_per_ubs:
                    break

                try:
                    # Extrair nome do autor
                    try:
                        author_el = review_el.find_element(
                            By.CSS_SELECTOR, "div.d4r55"
                        )
                        author_name = author_el.text.strip()
                    except NoSuchElementException:
                        author_name = "Anônimo"

                    # Extrair rating
                    rating: Optional[int] = None
                    try:
                        stars_el = review_el.find_element(
                            By.CSS_SELECTOR, "span.kvMYJc"
                        )
                        aria_label = stars_el.get_attribute("aria-label") or ""
                        # Formato: "5 estrelas" ou "5 stars"
                        num_text = "".join(c for c in aria_label if c.isdigit())
                        if num_text:
                            rating = int(num_text[0])
                    except (NoSuchElementException, ValueError, IndexError):
                        pass

                    # Extrair texto da avaliação
                    review_text = ""
                    try:
                        text_el = review_el.find_element(
                            By.CSS_SELECTOR, "span.wiI7pd"
                        )
                        review_text = text_el.text.strip()
                    except NoSuchElementException:
                        pass

                    # Extrair data da avaliação
                    review_date = ""
                    try:
                        date_el = review_el.find_element(
                            By.CSS_SELECTOR, "span.rsqaWe"
                        )
                        review_date = date_el.text.strip()
                    except NoSuchElementException:
                        pass

                    review_id = f"{place_id}_{idx}"

                    review = ReviewModel(
                        review_id=review_id,
                        place_id=place_id,
                        author_name=author_name,
                        rating=rating,
                        review_text=review_text,
                        review_date=review_date,
                    )
                    reviews.append(review)

                except Exception as e:
                    logger.warning(f"Erro ao extrair avaliação {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erro ao extrair avaliações: {e}")

        return reviews

    def scrape_ubs(
        self, query: str, nome_original: str
    ) -> Tuple[Optional[UBSModel], List[ReviewModel]]:
        """
        Realiza o scraping completo de uma UBS no Google Maps.

        Args:
            query: Query de busca para o Google Maps.
            nome_original: Nome original da UBS.

        Returns:
            Tupla com (dados da UBS, lista de avaliações).
        """
        ubs: Optional[UBSModel] = None
        reviews: List[ReviewModel] = []

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                logger.info(
                    f"Tentativa {attempt}/{self.config.retry_attempts} "
                    f"para '{nome_original}'"
                )

                if not self.search_place(query):
                    time.sleep(self.config.retry_delay)
                    continue

                # Extrair informações do local
                ubs = self._extract_place_info(nome_original)

                if ubs is None:
                    logger.warning(
                        f"Não foi possível extrair dados de '{nome_original}'"
                    )
                    time.sleep(self.config.retry_delay)
                    continue

                # Abrir painel de avaliações e extrair reviews
                if self._open_reviews_panel():
                    # Scroll para carregar mais avaliações
                    max_scrolls = min(
                        self.config.max_reviews_per_ubs // 5, 20
                    )
                    self._scroll_reviews(max_scrolls=max_scrolls)

                    # Extrair avaliações
                    reviews = self._extract_reviews(ubs.place_id)
                    logger.info(
                        f"Total de {len(reviews)} avaliações extraídas "
                        f"para '{nome_original}'"
                    )

                break

            except Exception as e:
                logger.error(
                    f"Erro na tentativa {attempt} para '{nome_original}': {e}"
                )
                if attempt < self.config.retry_attempts:
                    time.sleep(self.config.retry_delay)

        return ubs, reviews
