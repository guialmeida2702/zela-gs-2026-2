"""Entrada do cidadão (validada no back-end, mesmo já tendo sido validada no front)."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.comum import Categoria

_ESPACOS = re.compile(r"\s+")


class EvidenciaVisual(BaseModel):
    """Resumo da análise da foto (a imagem em si não é enviada nem guardada)."""

    classe: Literal["com_fissura", "sem_fissura"]
    probabilidade_max: float = Field(ge=0, le=1)
    blocos_com_fissura: int = Field(ge=0, le=500)
    total_blocos: int = Field(ge=1, le=500)
    modelo: str = Field(default="", max_length=80)


class RelatoEntrada(BaseModel):
    descricao: str = Field(
        min_length=20,
        max_length=1000,
        description="Relato livre do cidadão sobre o problema urbano.",
        examples=["Tem um buraco enorme na rua, perto do ponto de ônibus. Ontem um motoqueiro quase caiu."],
    )
    cep: str = Field(description="CEP do local do problema (8 dígitos, com ou sem hífen).", examples=["01001-000"])
    numero: str | None = Field(default=None, max_length=10, description="Número aproximado do imóvel mais próximo.")
    ponto_referencia: str | None = Field(default=None, max_length=120)
    categoria_sugerida: Categoria | None = Field(
        default=None, description="Palpite opcional do cidadão sobre o tipo de problema."
    )
    evidencia_visual: EvidenciaVisual | None = Field(default=None, description="Resultado da análise da foto, se houver.")

    @field_validator("descricao")
    @classmethod
    def _limpar_descricao(cls, valor: str) -> str:
        valor = _ESPACOS.sub(" ", valor).strip()
        if len(valor) < 20:
            raise ValueError("descreva o problema com pelo menos 20 caracteres")
        if sum(ch.isalpha() for ch in valor) < 10:
            raise ValueError("o relato precisa conter palavras descrevendo o problema")
        return valor

    @field_validator("cep")
    @classmethod
    def _normalizar_cep(cls, valor: str) -> str:
        digitos = re.sub(r"\D", "", valor or "")
        if len(digitos) != 8:
            raise ValueError("o CEP deve ter 8 dígitos")
        return digitos

    @field_validator("numero", "ponto_referencia")
    @classmethod
    def _limpar_opcionais(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = _ESPACOS.sub(" ", valor).strip()
        return valor or None
