"""Acesso a dados com cache do Streamlit.

- @st.cache_resource: o cliente HTTP (conexões reaproveitadas entre reruns e usuários).
- @st.cache_data: respostas que mudam pouco (categorias, CEP, painel público), para não
  repetir chamadas à API a cada rerun. Exceções NÃO são cacheadas pelo Streamlit,
  então uma falha momentânea não "gruda" no cache.
A análise da IA NÃO é cacheada aqui: ela fica no st.session_state (é do cidadão) e o
back-end tem seu próprio cache por conteúdo.
"""

import streamlit as st

import config
from providers.api_client import ClienteZela, ErroApi


@st.cache_resource(show_spinner=False)
def cliente() -> ClienteZela:
    return ClienteZela(config.API_URL, config.API_TIMEOUT_S)


@st.cache_data(ttl=20, show_spinner=False)
def status_servico() -> dict | None:
    try:
        return cliente().saude()
    except ErroApi:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def categorias() -> list[dict]:
    return cliente().categorias()


@st.cache_data(ttl=24 * 3600, show_spinner=False, max_entries=500)
def endereco_por_cep(cep: str) -> dict:
    return cliente().buscar_cep(cep)


@st.cache_data(ttl=60, show_spinner=False)
def solicitacoes_publicas(dias: int = 90) -> list[dict]:
    return cliente().publicas(dias)


@st.cache_data(ttl=30, show_spinner=False)
def fila_gestor(token: str) -> list[dict]:
    return cliente().gestor_listar(token)


@st.cache_data(ttl=30, show_spinner=False)
def indicadores_gestor(token: str) -> dict:
    return cliente().gestor_indicadores(token)


def limpar_cache_dados() -> None:
    """Chamado depois de uma escrita (novo registro, atualização do gestor)."""
    solicitacoes_publicas.clear()
    fila_gestor.clear()
    indicadores_gestor.clear()
