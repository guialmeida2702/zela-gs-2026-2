"""Solicitações registradas após a confirmação do cidadão (human-in-the-loop)."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.comum import Categoria, Status, Urgencia

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SolicitacaoCriar(BaseModel):
    analise_id: str = Field(min_length=6, max_length=40)
    categoria_final: Categoria
    urgencia_final: Urgencia
    comentario_cidadao: str | None = Field(default=None, max_length=300)
    contato: str | None = Field(default=None, max_length=120, description="E-mail ou telefone (opcional).")
    consentimento_lgpd: bool = Field(description="Cidadão autoriza o uso dos dados para tratar a solicitação.")

    @field_validator("consentimento_lgpd")
    @classmethod
    def _exigir_consentimento(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError("é preciso concordar com o uso dos dados para registrar a solicitação")
        return valor

    @field_validator("contato")
    @classmethod
    def _validar_contato(cls, valor: str | None) -> str | None:
        if valor is None or not valor.strip():
            return None
        valor = valor.strip()
        digitos = re.sub(r"\D", "", valor)
        if _EMAIL.match(valor) or 10 <= len(digitos) <= 13:
            return valor
        raise ValueError("informe um e-mail válido ou telefone com DDD")


class EventoStatus(BaseModel):
    status: Status
    em: datetime
    nota: str | None = None


class SolicitacaoPublica(BaseModel):
    """Visão anônima usada no painel público: sem contato, sem descrição, coordenadas aproximadas."""

    protocolo: str
    criado_em: datetime
    atualizado_em: datetime
    status: Status
    categoria: Categoria
    urgencia: Urgencia
    titulo: str
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    demo: bool = False


class SolicitacaoCidadao(SolicitacaoPublica):
    """O que o próprio cidadão vê ao consultar o protocolo."""

    descricao: str
    endereco_resumo: str | None = None
    orgao: str
    canal: str
    prazo_referencia: str
    orientacoes: list[str] = Field(default_factory=list)
    risco_imediato: bool = False
    feedback_util: bool | None = None
    historico: list[EventoStatus] = Field(default_factory=list)


class SolicitacaoGestor(SolicitacaoCidadao):
    """Visão completa para o gestor: inclui a sugestão original da IA para auditoria."""

    categoria_ia: Categoria
    urgencia_ia: Urgencia
    corrigida_pelo_cidadao: bool
    comentario_cidadao: str | None = None
    confianca_ia: float
    contato: str | None = None
    nota_gestor: str | None = None
    feedback_comentario: str | None = None
    visao: dict | None = None


class FeedbackEntrada(BaseModel):
    util: bool
    comentario: str | None = Field(default=None, max_length=300)


class AtualizacaoGestor(BaseModel):
    status: Status | None = None
    urgencia_final: Urgencia | None = None
    categoria_final: Categoria | None = None
    nota: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _ao_menos_um(self) -> "AtualizacaoGestor":
        if not any([self.status, self.urgencia_final, self.categoria_final, self.nota]):
            raise ValueError("informe ao menos um campo para atualizar")
        return self


class Indicadores(BaseModel):
    total: int
    abertas: int
    criticas_abertas: int
    por_status: dict[str, int]
    por_categoria: dict[str, int]
    por_urgencia: dict[str, int]
    concordancia_categoria_pct: float | None
    concordancia_urgencia_pct: float | None
    feedback_util_pct: float | None
    total_com_feedback: int
    tempo_medio_resolucao_h: float | None
