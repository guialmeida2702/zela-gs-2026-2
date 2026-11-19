"""Saída estruturada do LLM (AnaliseIA) e resposta enriquecida devolvida ao front."""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.schemas.comum import Categoria, Urgencia

TextoCurto = Annotated[str, Field(min_length=3, max_length=220)]


class AnaliseIA(BaseModel):
    """Contrato que o LLM é obrigado a seguir. Qualquer desvio é tratado como resposta inválida."""

    categoria: Categoria
    titulo: str = Field(min_length=3, max_length=90, description="Resumo do problema em poucas palavras.")
    urgencia: Urgencia
    risco_imediato: bool = Field(description="Há risco à vida ou à integridade física agora?")
    justificativa: str = Field(min_length=10, max_length=400, description="Por que essa urgência, em linguagem simples.")
    orientacoes: list[TextoCurto] = Field(min_length=1, max_length=4)
    informacoes_faltantes: list[TextoCurto] = Field(default_factory=list, max_length=3)
    confianca: float = Field(ge=0.0, le=1.0)
    fora_do_escopo: bool = Field(default=False, description="O relato não é um problema de zeladoria urbana.")

    @field_validator("titulo", "justificativa")
    @classmethod
    def _sem_espacos_extras(cls, valor: str) -> str:
        return " ".join(valor.split())


class Endereco(BaseModel):
    cep: str
    logradouro: str | None = None
    bairro: str | None = None
    cidade: str
    uf: str
    latitude: float | None = None
    longitude: float | None = None
    fonte: str

    @property
    def resumo(self) -> str:
        partes = [p for p in (self.logradouro, self.bairro, f"{self.cidade}/{self.uf}") if p]
        return ", ".join(partes)


class Clima(BaseModel):
    chuva_prevista_mm_72h: float
    prob_max_chuva_pct: int | None = None
    resumo: str
    fonte: str = "Open-Meteo"


class Encaminhamento(BaseModel):
    orgao: str
    canal: str
    prazo_referencia: str
    contatos_emergencia: list[str] = Field(default_factory=list)


class ContextoExterno(BaseModel):
    endereco: Endereco | None = None
    clima: Clima | None = None
    fontes_consultadas: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)


class AnaliseResposta(BaseModel):
    analise_id: str
    analise: AnaliseIA
    urgencia_sugerida_pela_ia: Urgencia
    ajustes_de_seguranca: list[str] = Field(
        default_factory=list, description="Regras determinísticas que elevaram a urgência e o motivo."
    )
    encaminhamento: Encaminhamento
    contexto: ContextoExterno
    dados_pessoais_removidos: list[str] = Field(default_factory=list)
    provedor_ia: str
    modelo_ia: str
    latencia_ms: int
    em_cache: bool = False
