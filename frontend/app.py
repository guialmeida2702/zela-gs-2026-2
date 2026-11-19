"""Zela — front-end Streamlit (ponto de entrada).

Rodar:  streamlit run app.py   (a API precisa estar no ar em API_URL)

Este arquivo só monta a página: barra lateral, perfil e abas. A lógica de cada
tela está em features/, os componentes visuais em ui/, o estado em state/ e o
acesso à API em providers/.
"""

import streamlit as st

st.set_page_config(
    page_title="Zela — sua rua, sua voz",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Zela: POC CitizenTech para relatos de zeladoria urbana com IA (FIAP — Global Solution)."},
)

from features import assistente, gestor, minhas_solicitacoes, painel_cidade, relatar, sobre  # noqa: E402
from providers import dados  # noqa: E402
from state import session  # noqa: E402
from ui import acessibilidade, components, theme  # noqa: E402

session.iniciar()
theme.aplicar_estilo(session.obter("alto_contraste"), session.obter("tamanho_fonte"))
acessibilidade.definir_idioma_pagina()


def barra_lateral() -> str:
    with st.sidebar:
        st.markdown("## 📍 Zela\n*Sua rua, sua voz.*")
        perfil = st.radio("Quem está usando?", ["Cidadão", "Gestor público"], key="perfil",
                          help="Cidadãos relatam e acompanham. Gestores tratam as solicitações (exige login).")

        st.divider()
        st.markdown("**Acessibilidade**")
        st.toggle("Alto contraste", key="alto_contraste", help="Aumenta o contraste de textos, bordas e selos.")
        st.select_slider("Tamanho do texto", options=list(theme.TAMANHOS_FONTE), key="tamanho_fonte")

        st.divider()
        servico = dados.status_servico()
        if servico is None:
            st.error("Serviço indisponível no momento. Tente em alguns minutos.", icon="🔴")
        else:
            st.success("Serviço no ar", icon="🟢")
            ia = servico.get("ia", {})
            if ia.get("simulada"):
                st.warning("Modo demonstração: a IA está **simulada** por palavras-chave.", icon="🧪")
            elif not ia.get("configurada", True):
                st.warning("Análise por IA em manutenção.", icon="🛠️")
        components.aviso_emergencia(compacto=True)

        if perfil == "Gestor público" and session.token_gestor():
            st.divider()
            st.caption(f"Conectado como **{components.seguro(session.obter('usuario_gestor'))}**")
            if st.button("Sair", icon="🚪"):
                session.sair_gestor()
                dados.limpar_cache_dados()
                st.rerun()
    return perfil


perfil = barra_lateral()

if perfil == "Cidadão":
    components.cabecalho("Relate problemas da sua rua. A IA organiza, você confere e a prefeitura recebe.")
    aba_relatar, aba_assistente, aba_minhas, aba_painel, aba_sobre = st.tabs(
        ["📝 Relatar problema", "💬 Tire dúvidas", "🗂️ Minhas solicitações", "🗺️ Painel da cidade", "ℹ️ Como funciona"],
        key="abas_cidadao",
    )
    with aba_relatar:
        relatar.tela()
    with aba_assistente:
        assistente.tela()
    with aba_minhas:
        minhas_solicitacoes.tela()
    with aba_painel:
        painel_cidade.tela()
    with aba_sobre:
        sobre.tela()
else:
    components.cabecalho("Área do gestor público: priorize, trate e acompanhe a qualidade da IA.")
    gestor.tela()
