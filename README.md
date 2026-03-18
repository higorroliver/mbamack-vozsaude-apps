# Vozes da Saúde

Pipeline de dados para coleta, enriquecimento e análise de avaliações de **Unidades Básicas de Saúde (UBS)** em São Paulo, utilizando web scraping do Google Maps.

---

## Visão Geral

O **Vozes da Saúde** é um sistema que automatiza a coleta de avaliações públicas de UBS diretamente do Google Maps. O objetivo é construir uma base de dados estruturada que permita análises futuras de sentimento e clusterização das unidades de saúde.

### O que o sistema faz

1. **Carrega** uma lista de UBS a partir de um arquivo CSV
2. **Busca** cada UBS no Google Maps via Selenium (headless)
3. **Extrai** informações do local (nome, endereço, rating, total de avaliações)
4. **Coleta** avaliações individuais (autor, nota, texto, data)
5. **Salva** os dados em arquivos CSV estruturados (Bronze Layer)

---

## Arquitetura

```
voz-saude/
│
├── app/
│   ├── ingestion/                  # Módulos de ingestão de dados
│   │   ├── ubs_loader.py           # Carregamento de UBS via CSV
│   │   ├── google_places_client.py # Scraper do Google Maps (Selenium)
│   │   └── enrichment_pipeline.py  # Orquestração do pipeline
│   │
│   ├── storage/                    # Módulos de armazenamento
│   │   ├── database.py             # Persistência em CSV/JSON
│   │   └── models.py              # Modelos Pydantic (UBS, Reviews)
│   │
│   └── utils/                      # Utilitários
│       ├── config.py               # Configurações da aplicação
│       └── logging.py              # Logging estruturado
│
├── data/
│   ├── input/                      # Dados de entrada
│   │   └── ubs_list.csv            # Lista de UBS (entrada)
│   └── output/                     # Dados de saída (gerados)
│
├── scripts/
│   └── run_pipeline.py             # Script principal do pipeline
│
├── requirements.txt
├── .env.example
└── README.md
```

### Modelo de Dados

**UBS (Locais)**

| Campo             | Tipo     | Descrição                        |
|-------------------|----------|----------------------------------|
| place_id          | str      | Identificador único (hash MD5)   |
| nome              | str      | Nome da UBS                      |
| endereco          | str      | Endereço completo                |
| rating_medio      | float    | Nota média das avaliações        |
| total_avaliacoes  | int      | Número total de avaliações       |
| collected_at      | datetime | Data/hora da coleta              |

**Reviews (Avaliações)**

| Campo         | Tipo     | Descrição                            |
|---------------|----------|--------------------------------------|
| review_id     | str      | Identificador único da avaliação     |
| place_id      | str      | Referência ao local                  |
| author_name   | str      | Nome do autor                        |
| rating        | int      | Nota (1 a 5)                         |
| review_text   | str      | Texto da avaliação                   |
| review_date   | str      | Data relativa (ex: "2 meses atrás")  |
| collected_at  | datetime | Data/hora da coleta                  |

---

## Como Rodar Localmente

### Pré-requisitos

- Python 3.10+
- Google Chrome instalado
- ChromeDriver compatível com a versão do Chrome

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/higorroliver/mbamack-vozsaude-apps.git
cd mbamack-vozsaude-apps

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
```

### Execução

```bash
# Rodar o pipeline completo (usa dados mock se não houver CSV de entrada)
python scripts/run_pipeline.py

# Especificar arquivo de entrada
python scripts/run_pipeline.py --input data/input/ubs_list.csv

# Limitar número de avaliações por UBS
python scripts/run_pipeline.py --max-reviews 30

# Criar arquivo CSV mock para testes
python scripts/run_pipeline.py --create-mock

# Modo visível (não headless) - para debug
python scripts/run_pipeline.py --no-headless
```

### Argumentos

| Argumento        | Descrição                                  | Padrão |
|------------------|--------------------------------------------|--------|
| `--input`        | Caminho do CSV de entrada                  | `data/input/ubs_list.csv` |
| `--output`       | Diretório de saída                         | `data/output/` |
| `--max-reviews`  | Máximo de avaliações por UBS               | 50 |
| `--no-headless`  | Executar navegador em modo visível         | False |
| `--create-mock`  | Criar CSV mock para testes                 | False |

---

## Exemplo de Output

### CSV de UBS Enriquecidas (`ubs_enriquecidas_YYYYMMDD_HHMMSS.csv`)

```csv
place_id,nome,endereco,rating_medio,total_avaliacoes,collected_at
a1b2c3d4,UBS Vila Mariana,"Rua José de Magalhães, 351 - Vila Mariana",3.5,120,2026-03-18T10:00:00
e5f6g7h8,UBS Jardim São Savério,"Av. do Cursino, 1590 - Vila Moraes",4.0,85,2026-03-18T10:05:00
```

### CSV de Avaliações (`reviews_YYYYMMDD_HHMMSS.csv`)

```csv
review_id,place_id,author_name,rating,review_text,review_date,collected_at
a1b2c3d4_0,a1b2c3d4,João Silva,4,"Bom atendimento, mas demorado.",2 meses atrás,2026-03-18T10:00:00
a1b2c3d4_1,a1b2c3d4,Maria Santos,2,"Fila muito grande.",1 mês atrás,2026-03-18T10:00:00
```

### JSON Bruto - Bronze Layer (`bronze_raw_YYYYMMDD_HHMMSS.json`)

```json
[
  {
    "place_id": "a1b2c3d4",
    "nome": "UBS Vila Mariana",
    "endereco": "Rua José de Magalhães, 351 - Vila Mariana",
    "rating_medio": 3.5,
    "total_avaliacoes": 120,
    "collected_at": "2026-03-18T10:00:00",
    "reviews": [
      {
        "review_id": "a1b2c3d4_0",
        "place_id": "a1b2c3d4",
        "author_name": "João Silva",
        "rating": 4,
        "review_text": "Bom atendimento, mas demorado.",
        "review_date": "2 meses atrás",
        "collected_at": "2026-03-18T10:00:00"
      }
    ]
  }
]
```

---

## Tecnologias

- **Python 3.10+** - Linguagem principal
- **Selenium** - Web scraping do Google Maps
- **Pydantic** - Validação de dados e modelos
- **python-dotenv** - Gerenciamento de variáveis de ambiente

---

## Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
