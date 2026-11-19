"""Tipos compartilhados entre os schemas (enums e modelo de erro padrão)."""

from enum import Enum

from pydantic import BaseModel


class Categoria(str, Enum):
    BURACO_VIA = "buraco_via"
    ILUMINACAO = "iluminacao_publica"
    LIXO_ENTULHO = "lixo_entulho"
    ALAGAMENTO = "alagamento_drenagem"
    ARVORE = "arvore_poda"
    CALCADA = "calcada_acessibilidade"
    SINALIZACAO = "sinalizacao_semaforo"
    AGUA_ESGOTO = "agua_esgoto"
    FIACAO = "fiacao_energia"
    ESTRUTURA = "estrutura_fissura"
    OUTROS = "outros"


class Urgencia(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

    @property
    def nivel(self) -> int:
        return ORDEM_URGENCIA.index(self)

    @classmethod
    def de_nivel(cls, nivel: int) -> "Urgencia":
        nivel = max(0, min(nivel, len(ORDEM_URGENCIA) - 1))
        return ORDEM_URGENCIA[nivel]


ORDEM_URGENCIA = [Urgencia.BAIXA, Urgencia.MEDIA, Urgencia.ALTA, Urgencia.CRITICA]


class Status(str, Enum):
    RECEBIDA = "recebida"
    EM_ANALISE = "em_analise"
    ENCAMINHADA = "encaminhada"
    RESOLVIDA = "resolvida"
    RECUSADA = "recusada"


class DetalheErro(BaseModel):
    codigo: str
    mensagem: str
    campos: dict[str, str] | None = None


class ErroResposta(BaseModel):
    """Formato único de erro devolvido pela API: sempre amigável, sem detalhes técnicos."""

    erro: DetalheErro
