"""Testes do provedor OpenAI-compatível com um cliente falso (sem rede e sem chave)."""

import asyncio
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.core.erros import LLMConfiguracao, LLMRespostaInvalida, LLMTempoEsgotado
from app.providers.llm.openai_compat import ProvedorOpenAICompat, extrair_json
from app.schemas.analise import AnaliseIA

VALIDO = (
    '{"categoria":"iluminacao_publica","titulo":"Poste apagado","urgencia":"media","risco_imediato":false,'
    '"justificativa":"Rua escura à noite aumenta o risco.","orientacoes":["Anote o número do poste."],'
    '"informacoes_faltantes":[],"confianca":0.85,"fora_do_escopo":false}'
)


class ClienteFalso:
    """Imita AsyncOpenAI.chat.completions.create devolvendo respostas pré-programadas."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        item = self.respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])


def _provedor(respostas, **kw):
    cliente = ClienteFalso(respostas)
    return ProvedorOpenAICompat(api_key="", base_url="http://x", modelo="m", cliente=cliente, **kw), cliente


def _rodar(coro):
    return asyncio.run(coro)


def test_resposta_valida_vira_modelo_pydantic():
    prov, cliente = _provedor([VALIDO])
    analise = _rodar(prov.gerar_estruturado("sys", "usr", AnaliseIA))
    assert isinstance(analise, AnaliseIA) and analise.categoria.value == "iluminacao_publica"
    assert cliente.chamadas[0]["response_format"] == {"type": "json_object"}


def test_aceita_json_em_cerca_markdown():
    prov, _ = _provedor([f"```json\n{VALIDO}\n```"])
    assert _rodar(prov.gerar_estruturado("s", "u", AnaliseIA)).titulo == "Poste apagado"


def test_saida_invalida_faz_nova_tentativa_com_correcao():
    prov, cliente = _provedor(['{"categoria":"inexistente"}', VALIDO], max_tentativas=2)
    analise = _rodar(prov.gerar_estruturado("s", "u", AnaliseIA))
    assert analise.urgencia.value == "media"
    assert len(cliente.chamadas) == 2
    assert "não seguiu o formato" in cliente.chamadas[1]["messages"][-1]["content"]


def test_saida_invalida_persistente_gera_erro_de_dominio():
    prov, _ = _provedor(["isto não é json", "nem isto"], max_tentativas=2)
    with pytest.raises(LLMRespostaInvalida):
        _rodar(prov.gerar_estruturado("s", "u", AnaliseIA))


def test_timeout_do_sdk_vira_erro_de_dominio():
    req = httpx.Request("POST", "http://x")
    prov, _ = _provedor([openai.APITimeoutError(request=req)])
    with pytest.raises(LLMTempoEsgotado):
        _rodar(prov.gerar_estruturado("s", "u", AnaliseIA))


def test_chave_invalida_vira_erro_de_configuracao():
    req = httpx.Request("POST", "http://x")
    resp = httpx.Response(401, request=req)
    prov, _ = _provedor([openai.AuthenticationError("invalid key", response=resp, body=None)])
    with pytest.raises(LLMConfiguracao):
        _rodar(prov.gerar_estruturado("s", "u", AnaliseIA))


def test_reasoning_effort_e_temperature_opcionais():
    prov, cliente = _provedor([VALIDO], reasoning_effort="low", temperatura=-1)
    _rodar(prov.gerar_estruturado("s", "u", AnaliseIA))
    assert cliente.chamadas[0]["reasoning_effort"] == "low"
    assert "temperature" not in cliente.chamadas[0]


def test_extrair_json_com_texto_ao_redor():
    assert extrair_json('Claro! Aqui está: {"a": 1} espero ter ajudado')["a"] == 1
