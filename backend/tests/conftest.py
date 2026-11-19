"""Fixtures: API completa com dublês (sem rede, sem chave de LLM, banco em memória)."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.erros import LLMRespostaInvalida, LLMTempoEsgotado
from app.main import create_app
from app.providers.database import Repositorio
from app.providers.llm.mock import ProvedorSimulado
from app.schemas.analise import Clima, Endereco

ORIGEM_FRONT = "http://localhost:8501"


class GeoFalso:
    habilitado = True

    async def buscar_cep(self, cep: str) -> Endereco | None:
        if cep == "00000000":
            return None
        return Endereco(cep=cep, logradouro="Praça da Sé", bairro="Sé", cidade="São Paulo", uf="SP",
                        latitude=-23.5505, longitude=-46.6333, fonte="BrasilAPI")

    async def geocodificar(self, endereco: Endereco, numero: str | None = None):
        return (-23.5506, -46.6334)


class ClimaFalso:
    def __init__(self, mm: float = 2.0):
        self.mm = mm

    async def previsao_chuva(self, lat: float, lon: float) -> Clima | None:
        return Clima(chuva_prevista_mm_72h=self.mm, prob_max_chuva_pct=80, resumo=f"{self.mm} mm em 3 dias")


class LLMQueFalha:
    nome = "falho"
    modelo = "falho-1"

    def __init__(self, erro: Exception):
        self.erro = erro

    async def gerar_estruturado(self, system, usuario, schema):
        raise self.erro


def _settings(**extra) -> Settings:
    base = dict(
        app_env="development", llm_provider="mock", cors_origins=ORIGEM_FRONT, gestor_usuario="gestor",
        gestor_senha="senha-teste", jwt_secret="x" * 40, seed_demo_data=False, rate_limit_por_min=100,
        database_path=":memory:", busca_modo="bm25",
    )
    base.update(extra)
    return Settings(**base)


def _cliente(llm=None, clima=None, **settings_extra) -> TestClient:
    app = create_app(
        _settings(**settings_extra),
        llm=llm or ProvedorSimulado(atraso_s=0),
        geo=GeoFalso(),
        clima=clima or ClimaFalso(),
        repo=Repositorio(":memory:"),
    )
    return TestClient(app)


@pytest.fixture
def cliente():
    with _cliente() as c:
        yield c


@pytest.fixture
def fabrica_cliente():
    return _cliente


@pytest.fixture
def cliente_timeout():
    with _cliente(llm=LLMQueFalha(LLMTempoEsgotado(detalhe_tecnico="Request timed out after 25s"))) as c:
        yield c


@pytest.fixture
def cliente_resposta_invalida():
    with _cliente(llm=LLMQueFalha(LLMRespostaInvalida(detalhe_tecnico="ValidationError: urgencia='urgentissima'"))) as c:
        yield c


RELATO_OK = {
    "descricao": "Tem um buraco enorme na rua perto do ponto de ônibus, os carros desviam em cima da hora.",
    "cep": "01001-000",
    "numero": "100",
}
