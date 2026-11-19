"""Painel público da cidade: mapa, linha do tempo e tipos de problema, com filtros."""

import streamlit as st

from providers import dados
from providers.api_client import ErroApi
from ui import charts, components
from ui.filters import painel_filtros, preparar_df


def tela() -> None:
    topo1, topo2 = st.columns([4, 1], vertical_alignment="bottom")
    topo1.subheader("Painel da cidade", anchor=False)
    topo1.caption("O que os moradores estão relatando. Dados anônimos: sem nomes, contatos ou endereço exato.")
    if topo2.button("Atualizar dados", icon="🔄", width="stretch", key="painel_atualizar"):
        dados.solicitacoes_publicas.clear()

    try:
        with st.spinner("Carregando dados da cidade…"):
            registros = dados.solicitacoes_publicas(180)
    except ErroApi as erro:
        components.mostrar_erro(erro)
        components.estado_vazio("📡", "Painel indisponível no momento", "Os dados voltam assim que o serviço normalizar.")
        return

    df = preparar_df(registros)
    if df.empty:
        components.estado_vazio("🗺️", "Ainda não há relatos registrados", "Seja a primeira pessoa a relatar um problema!")
        return

    filtrado, descricao = painel_filtros(df, "painel", campos=("periodo", "categoria", "urgencia", "status"))
    if filtrado.empty:
        components.estado_vazio("🔍", "Nenhuma solicitação com esses filtros",
                                "Tente ampliar o período ou remover algum filtro.")
        return

    abertas = filtrado["status"].isin(["recebida", "em_analise", "encaminhada"])
    resolvidas = int((filtrado["status"] == "resolvida").sum())
    components.linha_indicadores([
        ("Relatos", f"{len(filtrado)}", "Total no período e filtros escolhidos"),
        ("Em andamento", f"{int(abertas.sum())}", "Recebidos, em análise ou encaminhados"),
        ("🚨 Críticos em aberto", f"{int((abertas & (filtrado['urgencia'] == 'critica')).sum())}",
         "Casos com risco imediato ainda não resolvidos"),
        ("Resolvidos", f"{100 * resolvidas / len(filtrado):.0f}%", "Percentual de relatos já resolvidos"),
    ])

    fig = charts.mapa(filtrado)
    charts.exibir(
        fig, chave="painel_mapa",
        alt=f"Mapa com {len(filtrado)} relatos ({descricao}), coloridos por urgência. Use zoom e passe o mouse para detalhes.",
        tabela=filtrado[["titulo", "categoria_nome", "urgencia_nome", "status_nome", "bairro"]].rename(
            columns={"titulo": "Relato", "categoria_nome": "Tipo", "urgencia_nome": "Urgência",
                     "status_nome": "Situação", "bairro": "Bairro"}),
    )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        fig = charts.linha_do_tempo(filtrado, titulo="Relatos por dia")
        por_dia = filtrado.groupby("dia").size().reset_index(name="Relatos")
        por_dia["dia"] = por_dia["dia"].dt.strftime("%d/%m/%Y")
        charts.exibir(fig, chave="painel_tempo", alt=f"Linha do tempo de relatos por dia ({descricao}).",
                      tabela=por_dia.rename(columns={"dia": "Dia"}))
    with c2:
        fig = charts.barras_por_categoria(filtrado, empilhar_urgencia=True, titulo="Tipos de problema e urgência")
        tab = filtrado.groupby(["categoria_nome", "urgencia_nome"]).size().reset_index(name="Relatos")
        charts.exibir(fig, chave="painel_categorias", alt=f"Barras de relatos por tipo de problema e urgência ({descricao}).",
                      tabela=tab.rename(columns={"categoria_nome": "Tipo", "urgencia_nome": "Urgência"}))

    if filtrado["demo"].any():
        st.caption(f"🧪 {int(filtrado['demo'].sum())} dos registros exibidos são fictícios, criados para demonstração.")
