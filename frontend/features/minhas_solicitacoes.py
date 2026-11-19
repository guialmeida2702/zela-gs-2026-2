"""Histórico do cidadão (guardado no st.session_state) + consulta de protocolo + avaliação."""

import re

import streamlit as st

from providers import dados
from providers.api_client import ErroApi
from state import session
from ui import charts, components
from ui.filters import preparar_df

_PROTOCOLO = re.compile(r"^ZL-\d{6}-[0-9A-F]{6}$")


def avaliacao(sol: dict, chave: str) -> None:
    """Feedback humano sobre a orientação (reutilizado no sucesso e no histórico)."""
    protocolo = sol["protocolo"]
    ja = session.feedback_enviado(protocolo)
    if ja is None and sol.get("feedback_util") is not None:
        ja = sol["feedback_util"]
    if ja is not None:
        st.caption("Obrigado pela avaliação! " + ("👍 Você achou a orientação útil." if ja else "👎 Vamos melhorar."))
        return
    st.markdown("**A orientação foi útil para você?**")
    valor = st.feedback("thumbs", key=f"fb_{chave}_{protocolo}")
    if valor is None:
        return
    util = bool(valor)
    try:
        atualizada = dados.cliente().avaliar(protocolo, util)
    except ErroApi as erro:
        components.mostrar_erro(erro)
        return
    session.marcar_feedback(protocolo, util)
    session.atualizar_no_historico(atualizada)
    st.toast("Avaliação registrada. Obrigado!", icon="🙏")
    st.rerun()


def tela() -> None:
    st.subheader("Minhas solicitações", anchor=False)
    st.caption("Os relatos desta sessão ficam listados aqui. Guarde os protocolos para consultar depois.")

    with st.form("consulta_protocolo", border=False):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        protocolo = c1.text_input("Acompanhar um protocolo", placeholder="ZL-261111-A1B2C3", max_chars=20)
        consultar = c2.form_submit_button("Consultar", icon="🔎", width="stretch")
    if consultar:
        codigo = protocolo.strip().upper()
        if not _PROTOCOLO.match(codigo):
            st.error("O protocolo tem o formato ZL-AAMMDD-XXXXXX (ex.: ZL-261111-A1B2C3).", icon="✍️")
        else:
            try:
                session.adicionar_ao_historico(dados.cliente().consultar(codigo))
                st.toast("Protocolo encontrado!", icon="✅")
            except ErroApi as erro:
                components.mostrar_erro(erro)

    historico = session.historico()
    if not historico:
        components.estado_vazio("🗂️", "Nenhuma solicitação por aqui ainda",
                                "Use a aba “Relatar problema” para registrar o primeiro, ou consulte um protocolo acima.")
        return

    df = preparar_df(historico)
    abertas = int(df["status"].isin(["recebida", "em_analise", "encaminhada"]).sum())
    components.linha_indicadores([
        ("Nesta sessão", str(len(df)), "Solicitações registradas ou consultadas nesta sessão"),
        ("Em andamento", str(abertas), "Recebidas, em análise ou encaminhadas"),
        ("Resolvidas", str(int((df["status"] == "resolvida").sum())), None),
        ("Análises da IA", str(session.obter("analises_feitas")), "Inclui análises que você revisou e não enviou"),
    ])
    if len(df) >= 2:
        fig = charts.barras_por_categoria(df, empilhar_urgencia=True, titulo="Seus relatos por tipo e urgência", altura=280)
        charts.exibir(fig, chave="graf_minhas", alt=f"Gráfico de barras com {len(df)} relatos seus, por tipo e urgência.",
                      tabela=df[["protocolo", "categoria_nome", "urgencia_nome", "status_nome"]].rename(
                          columns={"protocolo": "Protocolo", "categoria_nome": "Tipo", "urgencia_nome": "Urgência",
                                   "status_nome": "Situação"}))

    for sol in historico:
        components.cartao_solicitacao(sol, modo="cidadao")
        c1, c2 = st.columns([1, 3])
        if c1.button("Atualizar situação", key=f"atualizar_{sol['protocolo']}", icon="🔄"):
            try:
                session.atualizar_no_historico(dados.cliente().consultar(sol["protocolo"]))
                st.rerun()
            except ErroApi as erro:
                components.mostrar_erro(erro)
        with c2:
            avaliacao(sol, chave="hist")
