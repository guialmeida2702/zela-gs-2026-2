"""Configuração do front-end: variáveis de ambiente ou st.secrets (Streamlit Community Cloud).

O front NÃO conhece a chave do LLM: ele só sabe o endereço da API.
"""

import os

import streamlit as st


def _ler(nome: str, padrao: str) -> str:
    valor = os.getenv(nome)
    if valor:
        return valor
    try:
        return str(st.secrets.get(nome, padrao))
    except Exception:  # sem secrets.toml: usa o padrão
        return padrao


API_URL = _ler("API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_S = float(_ler("API_TIMEOUT_S", "45"))
NOME_APP = "Zela"
SLOGAN = "Sua rua, sua voz."
