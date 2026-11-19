"""Contratos do Assistente Zela (chat com base de conhecimento)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MensagemHistorico(BaseModel):
    papel: Literal["cidadao", "assistente"]
    texto: str = Field(min_length=1, max_length=1500)


class PerguntaAssistente(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)
    historico: list[MensagemHistorico] = Field(default_factory=list, max_length=12)
    protocolo: str | None = Field(default=None, max_length=20, description="Protocolo do cidadão, se quiser falar dele.")

    @field_validator("pergunta")
    @classmethod
    def _limpar(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("escreva uma pergunta com pelo menos 3 caracteres")
        return v


class SaidaLLMAssistente(BaseModel):
    """Formato que o LLM é obrigado a seguir."""

    resposta: str = Field(min_length=1, max_length=1500)
    citacoes: list[int] = Field(default_factory=list, max_length=8)
    sem_evidencia: bool = False
    fora_do_escopo: bool = False

    @field_validator("citacoes", mode="before")
    @classmethod
    def _limpar_citacoes(cls, v):
        """Modelos pequenos às vezes repetem ou inventam números de fonte: tira repetidos e limita a 8.
        Números que não existem são descartados depois, na pós-verificação."""
        if not isinstance(v, list):
            return v
        vistos = [n for n in dict.fromkeys(v) if isinstance(n, int) and not isinstance(n, bool)]
        return vistos[:8]


class Citacao(BaseModel):
    n: int
    titulo: str
    orgao: str
    url: str
    consultado_em: str
    secao: str
    trecho: str
    tipo: str


class RespostaAssistente(BaseModel):
    resposta: str
    citacoes: list[Citacao]
    sem_evidencia: bool
    fora_do_escopo: bool
    sustentacao: float | None = Field(default=None, description="Fração das frases apoiadas pelas fontes citadas (0 a 1).")
    bloqueios: list[str] = Field(default_factory=list, description="Proteções que alteraram a resposta.")
    avisos: list[str] = Field(default_factory=list)
    recuperacao: dict = Field(default_factory=dict)
    consulta_usada: str
    modelo: str
    latencia_ms: int
