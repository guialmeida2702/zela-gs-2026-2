"""Visão do gestor público (perfil autenticado): fila priorizada, tratamento e qualidade da IA."""

import pandas as pd
import streamlit as st

from providers import dados
from providers.api_client import ErroApi
from state import session
from ui import charts, components, theme
from ui.filters import painel_filtros, preparar_df


def tela() -> None:
    token = session.token_gestor()
    if not token:
        _login()
        return
    aba_fila, aba_ind, aba_img = st.tabs(
        ["📥 Fila de atendimento", "📊 Indicadores e qualidade da IA", "🖼️ Monitoramento por imagens"], key="abas_gestor")
    with aba_fila:
        _fila(token)
    with aba_ind:
        _indicadores(token)
    with aba_img:
        _monitoramento()


def _tratar_erro_auth(erro: ErroApi) -> None:
    if erro.status == 401:
        session.sair_gestor()
        st.warning("Sua sessão de gestor expirou. Entre novamente.", icon="🔐")
    else:
        components.mostrar_erro(erro)


def _login() -> None:
    st.subheader("Entrar como gestor", anchor=False)
    st.caption("Área restrita às equipes da prefeitura. Cidadãos não precisam de login.")
    with st.form("login_gestor"):
        usuario = st.text_input("Usuário", max_chars=50, autocomplete="username")
        senha = st.text_input("Senha", type="password", max_chars=128, autocomplete="current-password")
        entrar = st.form_submit_button("Entrar", type="primary", icon="🔐")
    if not entrar:
        return
    if not usuario.strip() or not senha:
        st.error("Preencha usuário e senha.", icon="✍️")
        return
    try:
        resp = dados.cliente().login(usuario.strip(), senha)
    except ErroApi as erro:
        components.mostrar_erro(erro)
        return
    session.entrar_gestor(resp["access_token"], usuario.strip(), resp["expira_em"])
    st.rerun()


def _fila(token: str) -> None:
    try:
        registros = dados.fila_gestor(token)
    except ErroApi as erro:
        _tratar_erro_auth(erro)
        return
    df = preparar_df(registros)
    if df.empty:
        components.estado_vazio("📭", "Fila vazia", "Nenhuma solicitação registrada até agora.")
        return

    filtrado, _ = painel_filtros(df, "gestor", campos=("periodo", "urgencia", "status", "categoria"),
                                 periodo_padrao="90 dias")
    # O cidadão costuma ligar informando o protocolo: a busca leva direto à solicitação, sem rolar a fila
    busca = st.text_input("Buscar protocolo", max_chars=20, placeholder="ZL-261113-A1B2C3", key="gestor_busca_protocolo",
                          help="Digite o protocolo, ou parte dele, informado pelo cidadão.").strip().upper()
    if busca:
        filtrado = filtrado[filtrado["protocolo"].str.contains(busca, regex=False)]
    if filtrado.empty:
        components.estado_vazio("🔍", "Nenhuma solicitação com esses filtros", "Ajuste os filtros acima.")
        return

    # Prioridade: abertos antes de encerrados; depois urgência (crítica primeiro); depois os mais antigos
    filtrado = filtrado.assign(
        _encerrada=filtrado["status"].isin(["resolvida", "recusada"]),
        _rank=filtrado["urgencia"].map(theme.ORDEM_URGENCIA.index),
    ).sort_values(["_encerrada", "_rank", "criado_em"], ascending=[True, True, True])
    tabela = pd.DataFrame({
        "Protocolo": filtrado["protocolo"],
        "Urgência": filtrado["urgencia"].map(theme.nome_urgencia),
        "Tipo": filtrado["categoria"].map(theme.nome_categoria),
        "Situação": filtrado["status"].map(theme.nome_status),
        "Bairro": filtrado["bairro"],
        "Registrado": filtrado["criado_em"],
        "IA acertou?": (filtrado["categoria_ia"] == filtrado["categoria"]) & (filtrado["urgencia_ia"] == filtrado["urgencia"]),
    })
    st.caption(f"{len(tabela)} solicitações: abertas primeiro, depois por urgência e antiguidade. "
               "Selecione uma linha para tratar.")
    selecao = st.dataframe(
        tabela, hide_index=True, on_select="rerun", selection_mode="single-row", key="tabela_fila", height=320,
        column_config={
            "Registrado": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
            "IA acertou?": st.column_config.CheckboxColumn(help="A classificação da IA foi mantida pelo cidadão/gestor?"),
        },
    )
    linhas = selecao.selection.rows if selecao and selecao.selection else []
    protocolo = tabela.iloc[linhas[0]]["Protocolo"] if linhas else tabela.iloc[0]["Protocolo"]
    sol = next(r for r in registros if r["protocolo"] == protocolo)

    st.markdown(f"#### Tratando {components.seguro(protocolo)}" + ("" if linhas else " (mais prioritária)"),
                unsafe_allow_html=True)
    col_det, col_acao = st.columns([3, 2], gap="large")
    with col_det:
        components.cartao_solicitacao(sol, modo="gestor")
    with col_acao:
        _formulario_tratamento(token, sol)


def _formulario_tratamento(token: str, sol: dict) -> None:
    categorias = theme.opcoes_categoria(sol["categoria"])
    # a chave muda a cada salvamento (o histórico cresce), então o formulário volta limpo
    with st.form(f"tratar_{sol['protocolo']}_{len(sol.get('historico') or [])}", border=True):
        st.markdown("**Revisão do gestor**")
        st.caption("Confirme ou corrija a classificação e atualize a situação. Tudo fica registrado no histórico.")
        status = st.selectbox("Situação", theme.ORDEM_STATUS, index=theme.ORDEM_STATUS.index(sol["status"]),
                              format_func=theme.nome_status)
        urgencia = st.selectbox("Urgência", theme.ORDEM_URGENCIA, index=theme.ORDEM_URGENCIA.index(sol["urgencia"]),
                                format_func=theme.nome_urgencia)
        categoria = st.selectbox("Tipo de problema", categorias, index=categorias.index(sol["categoria"]),
                                 format_func=theme.nome_categoria)
        nota = st.text_area("Nota interna / resposta ao cidadão", max_chars=500, height=90,
                            placeholder="Ex.: Equipe de tapa-buraco agendada para quinta-feira.")
        salvar = st.form_submit_button("Salvar tratamento", type="primary", icon="💾", width="stretch")
    if not salvar:
        return
    mudancas: dict = {}
    if status != sol["status"]:
        mudancas["status"] = status
    if urgencia != sol["urgencia"]:
        mudancas["urgencia_final"] = urgencia
    if categoria != sol["categoria"]:
        mudancas["categoria_final"] = categoria
    if nota.strip():
        mudancas["nota"] = nota.strip()
    if not mudancas:
        st.info("Nada mudou. Altere algum campo ou escreva uma nota.", icon="ℹ️")
        return
    try:
        dados.cliente().gestor_atualizar(token, sol["protocolo"], mudancas)
    except ErroApi as erro:
        _tratar_erro_auth(erro)
        return
    dados.limpar_cache_dados()
    st.toast(f"Solicitação {sol['protocolo']} atualizada.", icon="✅")
    st.rerun()


def _indicadores(token: str) -> None:
    try:
        ind = dados.indicadores_gestor(token)
        registros = dados.fila_gestor(token)
    except ErroApi as erro:
        _tratar_erro_auth(erro)
        return
    if not ind["total"]:
        components.estado_vazio("📊", "Sem dados ainda", "Os indicadores aparecem após os primeiros registros.")
        return

    def pct(v: float | None) -> str:
        return "—" if v is None else f"{v:.0f}%"

    st.markdown("##### Operação")
    tempo = ind.get("tempo_medio_resolucao_h")
    components.linha_indicadores([
        ("Total de solicitações", str(ind["total"]), None),
        ("Em aberto", str(ind["abertas"]), "Recebidas, em análise ou encaminhadas"),
        ("🚨 Críticas em aberto", str(ind["criticas_abertas"]), "Risco imediato ainda sem solução"),
        ("Tempo médio até resolver", "—" if tempo is None else f"{tempo / 24:.1f} dias".replace(".", ","), "Do registro até a situação Resolvida"),
    ])
    st.markdown("##### Qualidade da IA")
    components.linha_indicadores([
        ("Tipo mantido", pct(ind["concordancia_categoria_pct"]),
         "Percentual em que a categoria sugerida pela IA foi mantida por cidadão e gestor"),
        ("Urgência mantida", pct(ind["concordancia_urgencia_pct"]), "Percentual em que a urgência da IA foi mantida"),
        ("Orientação útil", pct(ind["feedback_util_pct"]), f"Entre {ind['total_com_feedback']} avaliações de cidadãos"),
        ("Avaliações recebidas", str(ind["total_com_feedback"]), "Cidadãos que marcaram 👍 ou 👎"),
    ])

    df = preparar_df(registros)
    filtrado, descricao = painel_filtros(df, "ind", campos=("periodo", "categoria"), periodo_padrao="Tudo")
    if filtrado.empty:
        components.estado_vazio("🔍", "Nenhum dado com esses filtros", "Ajuste o período.")
        return

    c1, c2 = st.columns(2, gap="large")
    with c1:
        fig = charts.barras_por_status(filtrado, titulo="Situação das solicitações")
        charts.exibir(fig, chave="ind_status", alt=f"Barras com a quantidade de solicitações por situação ({descricao}).")
    with c2:
        fig = charts.linha_do_tempo(filtrado, titulo="Entrada de solicitações por dia")
        charts.exibir(fig, chave="ind_tempo", alt=f"Linha do tempo de solicitações por dia ({descricao}).")

    st.markdown("##### Onde a IA erra (human-in-the-loop)")
    st.caption("Cada célula conta quantas vezes a IA sugeriu um tipo (linha) e qual foi a decisão final humana (coluna). "
               "Tudo na diagonal é acerto; fora dela, uma correção que ajuda a melhorar o prompt e as regras.")
    fig = charts.matriz_concordancia(filtrado, titulo="Tipo sugerido pela IA × decisão final")
    corrigidas = filtrado[filtrado["categoria_ia"] != filtrado["categoria"]]
    charts.exibir(
        fig, chave="ind_matriz",
        alt=f"Mapa de calor de concordância: {len(filtrado) - len(corrigidas)} de {len(filtrado)} tipos sugeridos pela IA foram mantidos.",
        tabela=corrigidas.assign(
            IA=corrigidas["categoria_ia"].map(theme.nome_categoria), Final=corrigidas["categoria"].map(theme.nome_categoria)
        )[["protocolo", "IA", "Final"]].rename(columns={"protocolo": "Protocolo"}),
    )


def _monitoramento() -> None:
    """Sequência de fotos de vistoria (câmera veicular, drone ou equipe de campo) analisada em lote."""
    st.subheader("Monitoramento de estruturas por imagens", anchor=False)
    st.caption("Envie uma sequência de fotos de muros, viadutos, pontes ou calçadas. O modelo sinaliza possíveis fissuras "
               "para priorizar vistorias. Ele não mede a gravidade: a decisão é sempre do técnico.")
    with st.form("form_lote", border=True):
        fotos = st.file_uploader("Fotos (até 40)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                                 key="lote_fotos")
        enviar = st.form_submit_button("Analisar sequência", type="primary", icon="🔎")
    if not enviar:
        return
    if not fotos:
        st.error("Escolha pelo menos uma foto.", icon="🖼️")
        return
    if len(fotos) > 40:
        st.error("Envie no máximo 40 fotos por vez.", icon="🖼️")
        return
    with st.spinner(f"Analisando {len(fotos)} fotos…"):
        try:
            res = dados.cliente().analisar_lote([(f.name, f.getvalue(), f.type or "image/jpeg") for f in fotos])
        except ErroApi as erro:
            components.mostrar_erro(erro)
            return
    validos = [r for r in res["resultados"] if "erro" not in r]
    components.linha_indicadores([
        ("Fotos analisadas", str(len(validos)), None),
        ("Com sinais de fissura", str(res["com_fissura"]), None),
        ("Fotos por segundo", f"{res['imagens_por_segundo'] or 0:.0f}", "Inclui envio, leitura e análise de cada foto."),
        ("Tempo total", f"{res['tempo_total_s']:.2f} s".replace(".", ","), None),
    ])
    tabela = pd.DataFrame([{
        "Arquivo": r["arquivo"],
        "Resultado": ("⚠️ Possível fissura" if r["classe"] == "com_fissura" else "✔️ Sem sinais") if "erro" not in r
        else "❌ " + r["erro"],
        "Confiança máxima": r.get("probabilidade_max"),
        "Áreas sinalizadas": f"{r['blocos_com_fissura']}/{r['total_blocos']}" if "erro" not in r else "-",
        "Tempo (ms)": r.get("latencia_ms"),
    } for r in res["resultados"]])
    tabela = tabela.sort_values("Confiança máxima", ascending=False, na_position="last")
    st.dataframe(tabela, hide_index=True, width="stretch",
                 column_config={"Confiança máxima": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    sinalizadas = {r["arquivo"] for r in validos if r["classe"] == "com_fissura"}
    if sinalizadas:
        st.markdown("**Fotos para vistoria prioritária**")
        colunas = st.columns(4)
        for i, f in enumerate(f for f in fotos if f.name in sinalizadas):
            colunas[i % 4].image(f.getvalue(), caption=f.name, width="stretch")
