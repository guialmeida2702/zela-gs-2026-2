"""Gráficos Plotly reutilizáveis (interativos: hover, zoom, pan).

Regras aplicadas (boas práticas de visualização):
- urgência usa a paleta de status + textura (pattern) + rótulo: nunca só a cor;
- séries nominais (ex.: categorias) usam UMA cor; quantidade é mostrada pelo comprimento;
- um único eixo Y por gráfico; grade discreta; legenda sempre que houver 2+ séries;
- todo gráfico tem texto alternativo e uma visão em tabela.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui import theme

_CORES_URG = {theme.URGENCIA[u]["nome"]: theme.URGENCIA[u]["cor"] for u in theme.ORDEM_URGENCIA}
_ORDEM_URG_NOMES = [theme.URGENCIA[u]["nome"] for u in theme.ORDEM_URGENCIA]
_TEXTURA_URG = {"Crítica": "x", "Alta": "/", "Média": ".", "Baixa": ""}
_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"], "scrollZoom": True}


def _estilo(fig: go.Figure, altura: int, titulo: str | None = None) -> go.Figure:
    fig.update_layout(
        height=altura,
        title={"text": titulo, "x": 0, "font": {"size": 16}} if titulo else None,
        margin={"l": 8, "r": 8, "t": 48 if titulo else 12, "b": 8},
        font={"family": "Source Sans Pro, sans-serif", "size": 13, "color": theme.MARCA["texto"]},
        hoverlabel={"font_size": 13, "bgcolor": "#FFFFFF", "bordercolor": theme.MARCA["borda"]},
        separators=",.",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "left", "x": 0, "title": None},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(gridcolor="#E8ECEB", zeroline=False)
    fig.update_yaxes(gridcolor="#E8ECEB", zeroline=False)
    return fig


def exibir(fig: go.Figure, *, alt: str, tabela: pd.DataFrame | None = None, chave: str) -> None:
    """Exibe o gráfico com texto alternativo e, opcionalmente, a mesma informação em tabela."""
    st.plotly_chart(fig, config=_CONFIG, alt=alt, key=chave)
    if tabela is not None and not tabela.empty:
        with st.expander("Ver estes dados em tabela"):
            st.dataframe(tabela, hide_index=True)


def mapa(df: pd.DataFrame, altura: int = 440) -> go.Figure:
    dados = df.dropna(subset=["latitude", "longitude"]).copy()
    dados["data"] = dados["criado_em"].dt.strftime("%d/%m/%Y")
    centro, zoom = _enquadrar(dados["latitude"], dados["longitude"])
    fig = px.scatter_map(
        dados,
        lat="latitude",
        lon="longitude",
        color="urgencia_nome",
        color_discrete_map=_CORES_URG,
        category_orders={"urgencia_nome": _ORDEM_URG_NOMES},
        hover_name="titulo",
        hover_data={"categoria_nome": True, "status_nome": True, "bairro": True, "data": True,
                    "latitude": False, "longitude": False, "urgencia_nome": True},
        labels={"urgencia_nome": "Urgência", "categoria_nome": "Tipo", "status_nome": "Situação",
                "bairro": "Bairro", "data": "Registrado em"},
        center=centro,
        zoom=zoom,
        map_style="carto-positron",
    )
    fig.update_traces(marker={"size": 12, "opacity": 0.9})
    return _estilo(fig, altura)


def _enquadrar(lat: pd.Series, lon: pd.Series) -> tuple[dict, float]:
    """Centro e zoom a partir da extensão dos pontos (o Plotly 7 não centraliza sozinho)."""
    if lat.empty:
        return {"lat": -23.55, "lon": -46.63}, 10  # São Paulo como padrão
    centro = {"lat": float((lat.min() + lat.max()) / 2), "lon": float((lon.min() + lon.max()) / 2)}
    extensao = max(float(lat.max() - lat.min()), float(lon.max() - lon.min()))
    for limite, zoom in ((3.0, 6), (1.5, 7), (0.7, 8), (0.35, 9), (0.17, 10), (0.08, 11), (0.03, 12)):
        if extensao > limite:
            return centro, zoom
    return centro, 13


def barras_por_categoria(df: pd.DataFrame, *, empilhar_urgencia: bool, titulo: str, altura: int = 420) -> go.Figure:
    if empilhar_urgencia:
        dados = df.groupby(["categoria_nome", "urgencia_nome"]).size().reset_index(name="Solicitações")
        ordem = dados.groupby("categoria_nome")["Solicitações"].sum().sort_values().index.tolist()
        fig = px.bar(
            dados, x="Solicitações", y="categoria_nome", color="urgencia_nome", orientation="h",
            color_discrete_map=_CORES_URG, pattern_shape="urgencia_nome", pattern_shape_map=_TEXTURA_URG,
            category_orders={"categoria_nome": ordem, "urgencia_nome": _ORDEM_URG_NOMES},
            labels={"categoria_nome": "", "urgencia_nome": "Urgência"},
        )
        # textura sobreposta à cor (não substitui o preenchimento) + separação de 2px entre segmentos
        fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=2, marker_pattern_fillmode="overlay",
                          marker_pattern_fgcolor="#FFFFFF", marker_pattern_fgopacity=0.55, marker_pattern_size=7)
    else:
        dados = df.groupby("categoria_nome").size().reset_index(name="Solicitações").sort_values("Solicitações")
        fig = px.bar(dados, x="Solicitações", y="categoria_nome", orientation="h", text="Solicitações",
                     labels={"categoria_nome": ""}, color_discrete_sequence=[theme.MARCA["serie"]])
        fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(barcornerradius=4, bargap=0.3)
    totais = dados.groupby("categoria_nome")["Solicitações"].sum()
    fig.update_xaxes(title="Número de solicitações", rangemode="tozero", dtick=_passo_inteiro(totais))
    return _estilo(fig, altura, titulo)


def _passo_inteiro(valores: pd.Series) -> int:
    """Contagens são inteiras: evita marcas como 0,5 no eixo."""
    maximo = int(valores.max()) if len(valores) else 1
    return max(1, -(-maximo // 5))


def linha_do_tempo(df: pd.DataFrame, *, titulo: str, altura: int = 320) -> go.Figure:
    serie = df.groupby("dia").size().rename("Solicitações")
    if not serie.empty:
        dias = pd.date_range(serie.index.min(), serie.index.max(), freq="D")
        serie = serie.reindex(dias, fill_value=0)
    dados = serie.rename_axis("Dia").reset_index()
    fig = px.line(dados, x="Dia", y="Solicitações", markers=True, color_discrete_sequence=[theme.MARCA["serie"]])
    fig.update_traces(line_width=2, marker_size=8,
                      hovertemplate="%{x|%d/%m/%Y}<br><b>%{y} solicitação(ões)</b><extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title=None, tickformat="%d/%m")
    fig.update_yaxes(title="Solicitações por dia", rangemode="tozero", dtick=_passo_inteiro(dados["Solicitações"]))
    return _estilo(fig, altura, titulo)


def barras_por_status(df: pd.DataFrame, *, titulo: str, altura: int = 300) -> go.Figure:
    contagem = df["status"].value_counts().reindex(theme.ORDEM_STATUS, fill_value=0)
    dados = pd.DataFrame({"Situação": [theme.nome_status(s, False) for s in contagem.index],
                          "Solicitações": contagem.values})
    fig = px.bar(dados, x="Situação", y="Solicitações", text="Solicitações",
                 color_discrete_sequence=[theme.MARCA["serie"]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(barcornerradius=4, bargap=0.45)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Solicitações", rangemode="tozero", dtick=_passo_inteiro(dados["Solicitações"]))
    return _estilo(fig, altura, titulo)


def matriz_concordancia(df: pd.DataFrame, *, titulo: str, altura: int = 460) -> go.Figure:
    """Categoria sugerida pela IA x categoria final (após cidadão/gestor). Diagonal = acerto da IA."""
    nomes = {c: theme.nome_categoria(c, False) for c in theme.CATEGORIAS}
    tab = pd.crosstab(df["categoria_ia"].map(nomes), df["categoria"].map(nomes))
    ordem = [n for n in nomes.values() if n in set(tab.index) | set(tab.columns)]
    tab = tab.reindex(index=ordem, columns=ordem, fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=tab.values, x=tab.columns, y=tab.index, colorscale=[[0, "#F4F8FD"], [0.15, "#b7d3f6"], [1, "#104281"]],
        text=tab.values, texttemplate="%{text}", xgap=2, ygap=2,
        hovertemplate="IA sugeriu: %{y}<br>Final: %{x}<br><b>%{z} solicitação(ões)</b><extra></extra>",
        colorbar={"title": "Qtd."},
    ))
    fig.update_xaxes(title="Categoria final (decisão humana)", tickangle=-30)
    fig.update_yaxes(title="Categoria sugerida pela IA", autorange="reversed")
    return _estilo(fig, altura, titulo)
