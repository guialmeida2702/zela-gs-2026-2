"""Testes da interface com o AppTest do Streamlit (sem navegador e sem API real)."""

import copy
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from providers import dados
from providers.api_client import ErroApi

ANALISE = {
    "analise_id": "abc123def456",
    "analise": {
        "categoria": "buraco_via", "titulo": "Buraco perto do ponto de ônibus", "urgencia": "alta",
        "risco_imediato": False, "justificativa": "Buraco grande em rua com ônibus.",
        "orientacoes": ["Sinalize o buraco se for seguro."], "informacoes_faltantes": [],
        "confianca": 0.9, "fora_do_escopo": False,
    },
    "urgencia_sugerida_pela_ia": "alta", "ajustes_de_seguranca": [],
    "encaminhamento": {"orgao": "Subprefeitura da região", "canal": "SP156", "prazo_referencia": "até 30 dias",
                       "contatos_emergencia": []},
    "contexto": {"endereco": {"cep": "01001000", "logradouro": "Praça da Sé", "bairro": "Sé", "cidade": "São Paulo",
                              "uf": "SP", "latitude": -23.55, "longitude": -46.63, "fonte": "BrasilAPI"},
                 "clima": None, "fontes_consultadas": ["BrasilAPI"], "avisos": []},
    "dados_pessoais_removidos": [], "provedor_ia": "fake", "modelo_ia": "fake-1", "latencia_ms": 900, "em_cache": False,
}
APP = str(Path(__file__).resolve().parent.parent / "app.py")

SOLICITACAO = {
    "protocolo": "ZL-261111-ABC123", "criado_em": "2026-11-11T10:00:00", "atualizado_em": "2026-11-11T10:00:00",
    "status": "recebida", "categoria": "buraco_via", "urgencia": "alta", "titulo": "Buraco perto do ponto de ônibus",
    "bairro": "Sé", "cidade": "São Paulo", "uf": "SP", "latitude": -23.55, "longitude": -46.63, "demo": False,
    "descricao": "Buraco grande", "endereco_resumo": "Praça da Sé, Sé, São Paulo/SP", "orgao": "Subprefeitura",
    "canal": "SP156", "prazo_referencia": "até 30 dias", "orientacoes": [], "risco_imediato": False,
    "feedback_util": None, "historico": [],
}


class ClienteFalso:
    def __init__(self, falhar_analise: ErroApi | None = None):
        self.falhar_analise = falhar_analise
        self.registros: list[dict] = []

    def saude(self):
        return {"status": "ok", "ia": {"simulada": False, "configurada": True}}

    def buscar_cep(self, cep):
        return ANALISE["contexto"]["endereco"]

    def analisar(self, relato):
        if self.falhar_analise:
            raise self.falhar_analise
        return copy.deepcopy(ANALISE)

    def registrar(self, confirmacao):
        self.registros.append(confirmacao)
        return SOLICITACAO | {"categoria": confirmacao["categoria_final"], "urgencia": confirmacao["urgencia_final"]}

    def publicas(self, dias=90):
        return [SOLICITACAO]

    def perguntar(self, pergunta, historico, protocolo=None):
        self.perguntas = [*getattr(self, "perguntas", []), (pergunta, historico)]
        if getattr(self, "falhar_assistente", None):
            raise self.falhar_assistente
        return {"resposta": "Peça a poda pelo telefone 156 [1].", "sem_evidencia": False, "fora_do_escopo": False,
                "citacoes": [{"n": 1, "titulo": "Como solicitar poda", "orgao": "Subprefeitura Ipiranga",
                              "url": "https://prefeitura.sp.gov.br/x", "consultado_em": "2026-11-12", "secao": "",
                              "trecho": "Solicite pelo 156.", "tipo": "oficial"}],
                "avisos": [], "bloqueios": [], "recuperacao": {"modo": "hibrido"}, "modelo": "fake-1", "latencia_ms": 1200,
                "sustentacao": 1.0, "consulta_usada": pergunta}


@pytest.fixture
def app(monkeypatch):
    def _criar(cliente):
        st.cache_data.clear()
        st.cache_resource.clear()
        monkeypatch.setattr(dados, "cliente", lambda: cliente)
        return AppTest.from_file(APP, default_timeout=30)
    return _criar


def _botao(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def _preencher(at: AppTest, descricao: str, cep: str) -> None:
    at.text_area(key="rel_descricao_0").input(descricao)
    at.text_input(key="rel_cep_0").input(cep)
    _botao(at, "Analisar meu relato").click()
    at.run()


def test_app_abre_mesmo_com_api_fora_do_ar(monkeypatch):
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setenv("API_URL", "http://127.0.0.1:9")  # porta fechada
    import config
    monkeypatch.setattr(config, "API_URL", "http://127.0.0.1:9")
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("indisponível" in e.value for e in at.error)


def test_validacao_no_front_nao_chama_api(app):
    cliente = ClienteFalso()
    at = app(cliente).run()
    _preencher(at, "buraco", "01001000")
    assert not at.exception
    assert any("faltam 14" in e.value for e in at.error)
    assert at.session_state.etapa == "relatar"
    assert at.text_area(key="rel_descricao_0").value == "buraco"  # texto preservado


def test_reenvio_apos_erro_usa_texto_novo(app):
    """Regressão: o texto corrigido depois de um erro de validação não pode ser descartado."""
    at = app(ClienteFalso()).run()
    _preencher(at, "buraco", "01001000")
    assert at.session_state.etapa == "relatar"
    _preencher(at, "Tem um buraco enorme na rua perto do ponto de ônibus.", "01001000")
    assert not at.exception
    assert at.session_state.etapa == "revisar"
    assert at.session_state.relato["descricao"].startswith("Tem um buraco enorme")


def test_fluxo_completo_com_revisao_humana(app):
    cliente = ClienteFalso()
    at = app(cliente).run()
    _preencher(at, "Tem um buraco enorme na rua perto do ponto de ônibus.", "01001-000")
    assert not at.exception
    assert at.session_state.etapa == "revisar"

    # sem consentimento: não registra
    _botao(at, "Confirmar e registrar").click()
    at.run()
    assert cliente.registros == []
    assert any("autorização" in e.value for e in at.error)

    # cidadão corrige a urgência (human-in-the-loop) e confirma
    next(s for s in at.selectbox if s.label == "Urgência").select("media")
    at.checkbox[0].check()
    _botao(at, "Confirmar e registrar").click()
    at.run()
    assert not at.exception
    assert cliente.registros and cliente.registros[0]["consentimento_lgpd"] is True
    assert cliente.registros[0]["urgencia_final"] == "media"  # a correção humana foi enviada
    assert at.session_state.etapa == "concluido"
    assert at.session_state.historico[0]["protocolo"] == "ZL-261111-ABC123"


@pytest.mark.parametrize("categoria", ["estrutura_fissura", "categoria_que_o_front_ainda_nao_conhece"])
def test_revisao_abre_para_qualquer_categoria_vinda_da_api(app, monkeypatch, categoria):
    """Regressão: uma categoria ausente do espelho local derrubava a tela de revisão."""
    cliente = ClienteFalso()
    analise = copy.deepcopy(ANALISE)
    analise["analise"]["categoria"] = categoria
    monkeypatch.setattr(cliente, "analisar", lambda relato: copy.deepcopy(analise))
    at = app(cliente).run()
    _preencher(at, "Apareceu uma rachadura grande no muro da escola, perto do portão.", "01001-000")
    assert not at.exception
    assert at.session_state.etapa == "revisar"
    at.checkbox[0].check()
    _botao(at, "Confirmar e registrar").click()
    at.run()
    assert not at.exception
    assert cliente.registros[0]["categoria_final"] == categoria


def test_falha_da_ia_mostra_mensagem_amigavel_e_mantem_texto(app):
    cliente = ClienteFalso(falhar_analise=ErroApi("IA_TEMPO_ESGOTADO", "A análise demorou mais do que o esperado."))
    at = app(cliente).run()
    _preencher(at, "Tem um buraco enorme na rua perto do ponto de ônibus.", "01001-000")
    assert not at.exception
    assert any("demorou mais do que o esperado" in e.value for e in at.error)
    assert at.session_state.etapa == "relatar"
    assert at.session_state.relato["descricao"].startswith("Tem um buraco")


def test_assistente_responde_com_fonte_e_mantem_historico(app):
    cliente = ClienteFalso()
    at = app(cliente).run()
    _botao(at, "Como peço a poda de uma árvore na calçada?").click()
    at.run()
    assert not at.exception
    assert [m["papel"] for m in at.session_state.conversa] == ["user", "assistant"]
    at.chat_input(key="assist_entrada").set_value("E quanto tempo demora?").run()
    assert not at.exception
    pergunta, historico = cliente.perguntas[-1]
    assert pergunta == "E quanto tempo demora?"
    assert [h["papel"] for h in historico] == ["cidadao", "assistente"]  # memória enviada à API


def test_assistente_com_api_fora_do_ar_nao_perde_a_pergunta(app):
    cliente = ClienteFalso()
    cliente.falhar_assistente = ErroApi("API_FORA_DO_AR")
    at = app(cliente).run()
    at.chat_input(key="assist_entrada").set_value("Quem conserta a calçada?").run()
    assert not at.exception
    assert at.session_state.conversa == []
    assert any("Quem conserta a calçada?" in e.value for e in at.error)
