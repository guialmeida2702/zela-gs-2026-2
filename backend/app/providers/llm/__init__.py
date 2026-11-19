import logging

from app.config import Settings
from app.core.erros import LLMConfiguracao
from app.providers.llm.base import M, ProvedorLLM

log = logging.getLogger("zela.llm")


class ProvedorNaoConfigurado:
    """Usado quando falta a chave: a API sobe, mas a análise responde com erro amigável."""

    nome = "nao_configurado"

    def __init__(self, modelo: str):
        self.modelo = modelo

    async def gerar_estruturado(self, system: str, usuario: str, schema: type[M]) -> M:
        raise LLMConfiguracao(detalhe_tecnico="LLM_API_KEY ausente")


def criar_provedor_llm(settings: Settings) -> ProvedorLLM:
    """Fábrica: escolhe o provedor pelo LLM_PROVIDER do ambiente."""
    if settings.llm_provider == "mock":
        from app.providers.llm.mock import ProvedorSimulado

        log.warning("LLM em MODO SIMULADO (palavras-chave). Use apenas para testes/demonstração.")
        return ProvedorSimulado()

    from app.providers.llm.openai_compat import ProvedorOpenAICompat

    try:
        return ProvedorOpenAICompat(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            modelo=settings.llm_model,
            timeout_s=settings.llm_timeout_s,
            temperatura=settings.llm_temperature,
            modo_json=settings.llm_json_mode,
            reasoning_effort=settings.llm_reasoning_effort,
            max_tentativas=settings.llm_max_tentativas,
            max_tokens=settings.llm_max_tokens,
        )
    except LLMConfiguracao:
        log.error("LLM_API_KEY não configurada: a análise por IA ficará indisponível.")
        return ProvedorNaoConfigurado(settings.llm_model)
