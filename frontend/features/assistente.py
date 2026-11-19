"""Assistente Zela (cidadão): dúvidas sobre zeladoria respondidas com base em fontes oficiais, sempre citadas."""

import re

import streamlit as st

from providers import dados
from providers.api_client import ErroApi
from state import session
from ui import acessibilidade, components

SUGESTOES = [
    "Como peço a poda de uma árvore na calçada?",
    "Quem conserta a calçada em frente à minha casa?",
    "O que fazer se a minha rua alagar?",
]


def _historico_api() -> list[dict]:
    return [{"papel": "cidadao" if m["papel"] == "user" else "assistente", "texto": m["texto"][:1500]}
            for m in session.conversa()[-12:]]


def _mostrar_resposta(m: dict, indice: int) -> None:
    r = m["resposta"] or {}
    if r.get("sem_evidencia"):
        st.info(m["texto"], icon="🔎")
    elif r.get("fora_do_escopo"):
        st.info(m["texto"], icon="🧭")
    else:
        st.markdown(components.seguro(m["texto"]), unsafe_allow_html=True)
    citacoes = r.get("citacoes") or []
    if citacoes:
        with st.expander(f"Fontes consultadas ({len(citacoes)})"):
            for c in citacoes:
                secao = f" · {components.seguro(c['secao'])}" if c.get("secao") else ""
                link = f" · [abrir página]({c['url']})" if c.get("url", "").startswith("https://") else ""
                st.markdown(f"**[{c['n']}] {components.seguro(c['titulo'])}** · {components.seguro(c['orgao'])}{secao}"
                            f" · consultado em {c['consultado_em']}{link}", unsafe_allow_html=True)
                st.caption(c["trecho"] + ("…" if len(c["trecho"]) >= 300 else ""))
    for aviso in r.get("avisos", []):
        st.caption(f"ℹ️ {aviso}")
    if r:
        st.caption(f"Respondido em {r['latencia_ms'] / 1000:.1f}s · modelo {r['modelo']} · "
                   f"busca {r['recuperacao'].get('modo', '-')}")
        if indice == len(session.conversa()) - 1:
            acessibilidade.botao_ouvir(re.sub(r"\[\d+\]", "", m["texto"]), rotulo="🔊 Ouvir a resposta")


def _perguntar(pergunta: str, protocolo: str | None) -> None:
    historico = _historico_api()
    session.adicionar_mensagem("user", pergunta)
    with st.chat_message("user", avatar="🧑"):
        st.markdown(components.seguro(pergunta), unsafe_allow_html=True)
    with st.chat_message("assistant", avatar="🏙️"), st.spinner("Procurando nas fontes oficiais…"):
        try:
            resposta = dados.cliente().perguntar(pergunta, historico, protocolo)
        except ErroApi as erro:
            session.conversa().pop()  # a pergunta volta para o cidadão tentar de novo
            components.mostrar_erro(erro, acao=f"Envie a pergunta de novo: “{components.seguro(pergunta)}”.")
            return
    session.adicionar_mensagem("assistant", resposta["resposta"], resposta)
    st.rerun()


def tela() -> None:
    st.subheader("Tire dúvidas sobre zeladoria", anchor=False)
    st.caption("As respostas vêm de páginas oficiais da Prefeitura de São Paulo e do guia do Zela, sempre com a fonte. "
               "Se a informação não estiver nas fontes, o assistente diz que não sabe. Ele não dá orientação médica, "
               "jurídica ou financeira e não substitui o 156 nem os serviços de emergência.")
    with st.expander("Perguntar sobre uma solicitação sua (opcional)"):
        st.text_input("Protocolo", key="assist_protocolo", max_chars=20, placeholder="ZL-AAMMDD-XXXXXX",
                      help="Com o protocolo, o assistente consegue explicar a situação do seu pedido.")
    protocolo = (st.session_state.get("assist_protocolo") or "").strip().upper() or None
    if protocolo and not re.fullmatch(r"ZL-\d{6}-[0-9A-F]{6}", protocolo):
        st.caption("⚠️ O protocolo tem o formato ZL-AAMMDD-XXXXXX. Ele será ignorado até estar completo.")
        protocolo = None

    conversa = session.conversa()
    if not conversa:
        st.markdown("**Experimente perguntar:**")
        colunas = st.columns(len(SUGESTOES))
        for col, sugestao in zip(colunas, SUGESTOES, strict=True):
            if col.button(sugestao, key=f"sug_{sugestao[:12]}", width="stretch"):
                st.session_state["assist_pendente"] = sugestao
    for i, m in enumerate(conversa):
        with st.chat_message(m["papel"], avatar="🧑" if m["papel"] == "user" else "🏙️"):
            if m["papel"] == "user":
                st.markdown(components.seguro(m["texto"]), unsafe_allow_html=True)
            else:
                _mostrar_resposta(m, i)

    digitada = st.chat_input("Escreva sua pergunta (sem CPF, telefone ou endereço completo)", max_chars=500,
                             key="assist_entrada")
    pergunta = digitada or st.session_state.pop("assist_pendente", None)
    if pergunta:
        pergunta = " ".join(pergunta.split())
        if len(pergunta) < 3:
            st.warning("Escreva uma pergunta um pouco maior.", icon="✍️")
        else:
            _perguntar(pergunta, protocolo)
    if conversa and st.button("Começar nova conversa", icon="🧹"):
        session.limpar_conversa()
        st.rerun()
