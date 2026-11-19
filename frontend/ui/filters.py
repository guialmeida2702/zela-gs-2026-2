"""Painel de filtros reutilizável (cidadão e gestor), sempre numa linha acima dos gráficos."""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from ui import theme

PERIODOS = {"7 dias": 7, "30 dias": 30, "90 dias": 90, "Tudo": None}


def preparar_df(registros: list[dict]) -> pd.DataFrame:
    """Converte a lista da API em DataFrame com colunas de exibição prontas."""
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["criado_em"] = pd.to_datetime(df["criado_em"], errors="coerce")
    df["dia"] = df["criado_em"].dt.normalize()
    df["categoria_nome"] = df["categoria"].map(lambda c: theme.nome_categoria(c, com_icone=False))
    df["urgencia_nome"] = df["urgencia"].map(lambda u: theme.nome_urgencia(u, com_icone=False))
    df["status_nome"] = df["status"].map(lambda s: theme.nome_status(s, com_icone=False))
    if "bairro" in df:
        df["bairro"] = df["bairro"].fillna("Não informado")
    return df


def painel_filtros(df: pd.DataFrame, chave: str, campos: tuple[str, ...] = ("periodo", "categoria", "urgencia"),
                   periodo_padrao: str = "30 dias") -> tuple[pd.DataFrame, str]:
    """Desenha os controles e devolve (df filtrado, descrição dos filtros para texto alternativo)."""
    if df.empty:
        return df, "sem dados"
    colunas = st.columns([1.5 if c == "periodo" else 1 for c in campos])
    filtrado = df
    descricao: list[str] = []

    for col, campo in zip(colunas, campos, strict=True):
        with col:
            if campo == "periodo":
                escolha = st.segmented_control(
                    "Período", list(PERIODOS), default=periodo_padrao, key=f"{chave}_periodo",
                    help="Mostra apenas solicitações registradas nesse intervalo.",
                ) or periodo_padrao
                dias = PERIODOS[escolha]
                if dias:
                    limite = pd.Timestamp(datetime.now() - timedelta(days=dias))
                    filtrado = filtrado[filtrado["criado_em"] >= limite]
                descricao.append(f"período: {escolha}")
            elif campo == "categoria":
                opcoes = [c for c in theme.CATEGORIAS if c in set(df["categoria"])]
                sel = st.multiselect("Tipo de problema", opcoes, format_func=theme.nome_categoria,
                                     placeholder="Todos os tipos", key=f"{chave}_categoria")
                if sel:
                    filtrado = filtrado[filtrado["categoria"].isin(sel)]
                    descricao.append(f"{len(sel)} tipo(s) de problema")
            elif campo == "urgencia":
                sel = st.multiselect("Urgência", theme.ORDEM_URGENCIA, format_func=theme.nome_urgencia,
                                     placeholder="Todas as urgências", key=f"{chave}_urgencia")
                if sel:
                    filtrado = filtrado[filtrado["urgencia"].isin(sel)]
                    descricao.append("urgência: " + ", ".join(theme.nome_urgencia(u, False) for u in sel))
            elif campo == "status":
                sel = st.multiselect("Situação", theme.ORDEM_STATUS, format_func=theme.nome_status,
                                     placeholder="Todas as situações", key=f"{chave}_status")
                if sel:
                    filtrado = filtrado[filtrado["status"].isin(sel)]
                    descricao.append("situação: " + ", ".join(theme.nome_status(s, False) for s in sel))
            elif campo == "bairro":
                opcoes = sorted(df["bairro"].dropna().unique())
                sel = st.multiselect("Bairro", opcoes, placeholder="Todos os bairros", key=f"{chave}_bairro")
                if sel:
                    filtrado = filtrado[filtrado["bairro"].isin(sel)]
                    descricao.append(f"{len(sel)} bairro(s)")
    return filtrado, "; ".join(descricao) or "sem filtros"
