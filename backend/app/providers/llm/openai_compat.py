"""Provedor para qualquer API compatível com o formato OpenAI Chat Completions.

Funciona com Groq, Google Gemini (endpoint /v1beta/openai), OpenAI, OpenRouter e
Ollama local, trocando apenas LLM_BASE_URL, LLM_MODEL e LLM_API_KEY.
"""

import json
import logging
import re

import openai
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.core.erros import (
    LLMConfiguracao,
    LLMIndisponivel,
    LLMRespostaInvalida,
    LLMSobrecarregado,
    LLMTempoEsgotado,
)
from app.pipelines.prompts import mensagem_de_correcao
from app.providers.llm.base import M

log = logging.getLogger("zela.llm")

_CERCA_CODIGO = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extrair_json(conteudo: str) -> dict:
    """Aceita JSON puro, JSON dentro de ```cercas``` ou com texto ao redor."""
    texto = _CERCA_CODIGO.sub("", conteudo.strip()).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio, fim = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise
        return json.loads(texto[inicio : fim + 1])


class ProvedorOpenAICompat:
    nome = "openai_compat"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        modelo: str,
        timeout_s: float = 25.0,
        temperatura: float = 0.1,
        modo_json: str = "json_object",
        reasoning_effort: str = "",
        max_tentativas: int = 2,
        max_tokens: int = 0,
        cliente: AsyncOpenAI | None = None,
    ):
        if not api_key and cliente is None:
            raise LLMConfiguracao(detalhe_tecnico="LLM_API_KEY não configurada")
        self.modelo = modelo
        self.temperatura = temperatura
        self.modo_json = modo_json
        self.reasoning_effort = reasoning_effort
        self.max_tentativas = max(1, max_tentativas)
        # 0 = não envia. Útil em modelos locais, que às vezes não param de gerar listas longas até o tempo esgotar.
        # Em modelos de raciocínio, o limite inclui o raciocínio: deixe 0 ou use um valor alto.
        self.max_tokens = max_tokens
        # max_retries=0: o controle de novas tentativas é nosso (para não estourar o tempo da interface)
        self._cliente = cliente or AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=0)

    def _response_format(self, schema: type[M]) -> dict | None:
        if self.modo_json == "json_object":
            return {"type": "json_object"}
        if self.modo_json == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": False},
            }
        return None

    async def _chamar(self, mensagens: list[dict], schema: type[M]) -> str:
        kwargs: dict = {"model": self.modelo, "messages": mensagens}
        if self.temperatura >= 0:  # alguns modelos de raciocínio não aceitam temperature; use -1 para omitir
            kwargs["temperature"] = self.temperatura
        formato = self._response_format(schema)
        if formato:
            kwargs["response_format"] = formato
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        if self.max_tokens > 0:
            kwargs["max_tokens"] = self.max_tokens
        try:
            resposta = await self._cliente.chat.completions.create(**kwargs)
        except openai.APITimeoutError as exc:
            raise LLMTempoEsgotado(detalhe_tecnico=str(exc)) from exc
        except openai.RateLimitError as exc:
            raise LLMSobrecarregado(detalhe_tecnico=str(exc)) from exc
        except (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError) as exc:
            raise LLMConfiguracao(detalhe_tecnico=f"{type(exc).__name__}: {exc}") from exc
        except openai.BadRequestError as exc:
            raise LLMRespostaInvalida(detalhe_tecnico=f"BadRequest: {exc}") from exc
        except (openai.APIConnectionError, openai.APIStatusError) as exc:
            raise LLMIndisponivel(detalhe_tecnico=f"{type(exc).__name__}: {exc}") from exc
        except openai.OpenAIError as exc:  # qualquer outra falha do SDK
            raise LLMIndisponivel(detalhe_tecnico=f"{type(exc).__name__}: {exc}") from exc

        if not resposta.choices or resposta.choices[0].message.content is None:
            raise LLMRespostaInvalida(detalhe_tecnico="resposta sem conteúdo")
        return resposta.choices[0].message.content

    async def gerar_estruturado(self, system: str, usuario: str, schema: type[M]) -> M:
        mensagens: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": usuario}]
        ultimo_erro = ""
        for tentativa in range(1, self.max_tentativas + 1):
            conteudo = await self._chamar(mensagens, schema)
            try:
                return schema.model_validate(extrair_json(conteudo))
            except (json.JSONDecodeError, ValidationError) as exc:
                ultimo_erro = str(exc)
                log.warning("Saída do LLM inválida (tentativa %s/%s): %s", tentativa, self.max_tentativas, ultimo_erro[:300])
                mensagens += [
                    {"role": "assistant", "content": conteudo[:4000]},
                    {"role": "user", "content": mensagem_de_correcao(ultimo_erro)},
                ]
        raise LLMRespostaInvalida(detalhe_tecnico=ultimo_erro[:1000])
