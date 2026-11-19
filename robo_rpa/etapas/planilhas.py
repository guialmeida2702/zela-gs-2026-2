"""Tema 2 — Tratamento de arquivos e dados com Pandas: planilhas de ordens de serviço das equipes.

As equipes de campo devolvem planilhas (CSV ou Excel) com o resultado de cada ordem de serviço.
O robô lê, padroniza, valida linha a linha e separa:
  - linhas válidas -> viram atualização de status no Zela (via API);
  - linhas rejeitadas -> vão para `rejeitados.csv` com o motivo, para revisão humana.
"""

import hashlib
import re
from pathlib import Path

import pandas as pd

COLUNAS = {"protocolo", "status_os", "data_execucao", "equipe", "observacao"}
MAPA_STATUS = {
    "executada": "resolvida", "concluida": "resolvida", "concluída": "resolvida", "finalizada": "resolvida",
    "em execucao": "encaminhada", "em execução": "encaminhada", "programada": "encaminhada", "agendada": "encaminhada",
    "em vistoria": "em_analise", "vistoria": "em_analise",
    "cancelada": "recusada", "improcedente": "recusada",
}
_PROTOCOLO = re.compile(r"^ZL-\d{6}-[0-9A-F]{6}$")
_DADO_PESSOAL = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\(?\d{2}\)?\s?9?\d{4}-?\d{4}|[\w.+-]+@[\w-]+\.[\w.]+")


def hash_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ler_planilha(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(caminho, dtype=str)
    else:
        df = pd.read_csv(caminho, dtype=str, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns]
    faltando = COLUNAS - set(df.columns)
    if faltando:
        raise ValueError(f"colunas obrigatórias ausentes: {sorted(faltando)}")
    return df.fillna("")


def validar(df: pd.DataFrame, protocolos_existentes: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["protocolo"] = df["protocolo"].str.strip().str.upper()
    df["status_os"] = df["status_os"].str.strip().str.lower()
    df["data_execucao"] = pd.to_datetime(df["data_execucao"], errors="coerce", dayfirst=True)
    motivos = []
    vistos: set[str] = set()
    for _, linha in df.iterrows():
        m = []
        if not _PROTOCOLO.match(linha["protocolo"]):
            m.append("protocolo em formato inválido")
        elif linha["protocolo"] not in protocolos_existentes:
            m.append("protocolo não encontrado no Zela")
        if linha["status_os"] not in MAPA_STATUS:
            m.append(f"status desconhecido: '{linha['status_os']}'")
        if pd.isna(linha["data_execucao"]):
            m.append("data de execução ausente ou inválida")
        elif linha["data_execucao"] > pd.Timestamp.now():
            m.append("data de execução no futuro")
        if linha["protocolo"] in vistos:
            m.append("linha duplicada para o mesmo protocolo")
        if _DADO_PESSOAL.search(str(linha["observacao"])):
            m.append("observação contém dado pessoal (não será enviada)")
        vistos.add(linha["protocolo"])
        motivos.append("; ".join(m))
    df["motivo_rejeicao"] = motivos
    df["status_zela"] = df["status_os"].map(MAPA_STATUS)
    validas = df[df["motivo_rejeicao"] == ""].copy()
    rejeitadas = df[df["motivo_rejeicao"] != ""].copy()
    return validas, rejeitadas
