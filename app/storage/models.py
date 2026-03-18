"""Modelos de dados do projeto Vozes da Saúde usando Pydantic."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UBSModel(BaseModel):
    """Modelo de dados para Unidades Básicas de Saúde (UBS)."""

    place_id: str = Field(..., description="Identificador único do local no Google Maps")
    nome: str = Field(..., description="Nome da UBS")
    endereco: str = Field(default="", description="Endereço completo da UBS")
    rating_medio: Optional[float] = Field(
        default=None, description="Nota média das avaliações"
    )
    total_avaliacoes: Optional[int] = Field(
        default=None, description="Número total de avaliações"
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data e hora da coleta dos dados",
    )

    class Config:
        """Configuração do modelo Pydantic."""

        json_schema_extra = {
            "example": {
                "place_id": "ChIJ0WGkg4FEzpQRrlsz_whLqZs",
                "nome": "UBS Vila Mariana",
                "endereco": "Rua Example, 123 - Vila Mariana, São Paulo - SP",
                "rating_medio": 3.5,
                "total_avaliacoes": 120,
                "collected_at": "2026-03-18T10:00:00",
            }
        }


class ReviewModel(BaseModel):
    """Modelo de dados para avaliações de UBS."""

    review_id: str = Field(
        ..., description="Identificador único da avaliação"
    )
    place_id: str = Field(
        ..., description="Identificador do local associado à avaliação"
    )
    author_name: str = Field(
        default="Anônimo", description="Nome do autor da avaliação"
    )
    rating: Optional[int] = Field(
        default=None, ge=1, le=5, description="Nota da avaliação (1 a 5)"
    )
    review_text: str = Field(
        default="", description="Texto da avaliação"
    )
    review_date: str = Field(
        default="", description="Data relativa da avaliação (ex: '2 meses atrás')"
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data e hora da coleta dos dados",
    )

    class Config:
        """Configuração do modelo Pydantic."""

        json_schema_extra = {
            "example": {
                "review_id": "abc123_0",
                "place_id": "ChIJ0WGkg4FEzpQRrlsz_whLqZs",
                "author_name": "João Silva",
                "rating": 4,
                "review_text": "Bom atendimento, mas demorado.",
                "review_date": "2 meses atrás",
                "collected_at": "2026-03-18T10:00:00",
            }
        }


class UBSInput(BaseModel):
    """Modelo de entrada para UBS (dados do CSV de entrada)."""

    nome: str = Field(..., description="Nome da UBS")
    endereco: str = Field(default="", description="Endereço da UBS")
    cidade: str = Field(default="São Paulo", description="Cidade da UBS")
    estado: str = Field(default="SP", description="Estado da UBS")

    @property
    def search_query(self) -> str:
        """Gera a query de busca para o Google Maps."""
        parts = [self.nome]
        if self.endereco:
            parts.append(self.endereco)
        parts.append(self.cidade)
        parts.append(self.estado)
        return ", ".join(parts)
