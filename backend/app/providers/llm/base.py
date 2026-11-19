"""Contrato comum a qualquer provedor de LLM usado pelo pipeline."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


class ProvedorLLM(Protocol):
    nome: str
    modelo: str

    async def gerar_estruturado(self, system: str, usuario: str, schema: type[M]) -> M:
        """Chama o modelo e devolve uma instância VALIDADA de `schema`.

        Deve levantar LLMTempoEsgotado, LLMIndisponivel, LLMSobrecarregado,
        LLMConfiguracao ou LLMRespostaInvalida — nunca exceções do SDK.
        """
        ...
