"""Persistência em SQLite (arquivo único, suficiente para a POC; trocável por Postgres).

Guarda apenas o necessário (LGPD: minimização): a descrição já anonimizada,
contato só se o cidadão quiser informar, e nenhum dado de identificação.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.tempo import agora

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analises (
    id TEXT PRIMARY KEY,
    criado_em TEXT NOT NULL,
    entrada_json TEXT NOT NULL,
    resposta_json TEXT NOT NULL,
    provedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    prompt_versao TEXT NOT NULL,
    latencia_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS solicitacoes (
    protocolo TEXT PRIMARY KEY,
    analise_id TEXT UNIQUE NOT NULL,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    status TEXT NOT NULL,
    categoria_ia TEXT NOT NULL,
    urgencia_ia TEXT NOT NULL,
    categoria_final TEXT NOT NULL,
    urgencia_final TEXT NOT NULL,
    corrigida_pelo_cidadao INTEGER NOT NULL,
    comentario_cidadao TEXT,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    endereco_resumo TEXT,
    bairro TEXT,
    cidade TEXT,
    uf TEXT,
    latitude REAL,
    longitude REAL,
    orgao TEXT NOT NULL,
    canal TEXT NOT NULL,
    prazo_referencia TEXT NOT NULL,
    orientacoes_json TEXT NOT NULL,
    risco_imediato INTEGER NOT NULL,
    confianca_ia REAL NOT NULL,
    contato TEXT,
    feedback_util INTEGER,
    feedback_comentario TEXT,
    nota_gestor TEXT,
    historico_json TEXT NOT NULL,
    demo INTEGER NOT NULL DEFAULT 0,
    visao_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_sol_criado ON solicitacoes(criado_em);
CREATE INDEX IF NOT EXISTS ix_sol_status ON solicitacoes(status);
"""

_BOOL = {"corrigida_pelo_cidadao", "risco_imediato", "demo"}
_JSON = {"orientacoes_json": "orientacoes", "historico_json": "historico", "visao_json": "visao"}


class Repositorio:
    def __init__(self, caminho: str):
        if caminho != ":memory:":
            Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(caminho, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            if caminho != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            colunas = {r[1] for r in self._conn.execute("PRAGMA table_info(solicitacoes)")}
            if "visao_json" not in colunas:  # migração simples de bancos criados antes do módulo de visão
                self._conn.execute("ALTER TABLE solicitacoes ADD COLUMN visao_json TEXT")
            self._conn.commit()

    def fechar(self) -> None:
        self._conn.close()

    # ---------------- análises (rascunho antes da confirmação do cidadão) ----------------
    def salvar_analise(self, *, id: str, entrada: dict, resposta: dict, provedor: str, modelo: str,
                       prompt_versao: str, latencia_ms: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO analises VALUES (?,?,?,?,?,?,?,?)",
                (id, agora().isoformat(timespec="seconds"), json.dumps(entrada, ensure_ascii=False),
                 json.dumps(resposta, ensure_ascii=False, default=str), provedor, modelo, prompt_versao, latencia_ms),
            )
            self._conn.commit()

    def obter_analise(self, id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM analises WHERE id = ?", (id,)).fetchone()
        if not row:
            return None
        return {"id": row["id"], "entrada": json.loads(row["entrada_json"]), "resposta": json.loads(row["resposta_json"])}

    # ---------------- solicitações ----------------
    @staticmethod
    def _linha_para_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for campo in _BOOL:
            d[campo] = bool(d[campo])
        if d.get("feedback_util") is not None:
            d["feedback_util"] = bool(d["feedback_util"])
        for coluna, chave in _JSON.items():
            bruto = d.pop(coluna, None)
            d[chave] = json.loads(bruto) if bruto else ([] if chave != "visao" else None)
        return d

    @staticmethod
    def _dict_para_linha(dados: dict[str, Any]) -> dict[str, Any]:
        linha = dict(dados)
        for coluna, chave in _JSON.items():
            if chave in linha:
                valor = linha.pop(chave)
                linha[coluna] = None if valor is None else json.dumps(valor, ensure_ascii=False, default=str)
        for campo in (*_BOOL, "feedback_util"):
            if campo in linha and linha[campo] is not None:
                linha[campo] = int(bool(linha[campo]))
        for campo in ("criado_em", "atualizado_em"):
            if isinstance(linha.get(campo), datetime):
                linha[campo] = linha[campo].isoformat(timespec="seconds")
        return linha

    def criar_solicitacao(self, dados: dict[str, Any]) -> None:
        linha = self._dict_para_linha(dados)
        colunas = ", ".join(linha)
        marcadores = ", ".join("?" for _ in linha)
        with self._lock:
            self._conn.execute(f"INSERT INTO solicitacoes ({colunas}) VALUES ({marcadores})", tuple(linha.values()))
            self._conn.commit()

    def obter_solicitacao(self, protocolo: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM solicitacoes WHERE protocolo = ?", (protocolo,)).fetchone()
        return self._linha_para_dict(row) if row else None

    def obter_por_analise(self, analise_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM solicitacoes WHERE analise_id = ?", (analise_id,)).fetchone()
        return self._linha_para_dict(row) if row else None

    def listar_solicitacoes(self, *, status: str | None = None, categoria: str | None = None,
                            urgencia: str | None = None, desde: datetime | None = None,
                            limite: int = 1000) -> list[dict]:
        sql = "SELECT * FROM solicitacoes WHERE 1=1"
        params: list[Any] = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if categoria:
            sql += " AND categoria_final = ?"
            params.append(categoria)
        if urgencia:
            sql += " AND urgencia_final = ?"
            params.append(urgencia)
        if desde:
            sql += " AND criado_em >= ?"
            params.append(desde.isoformat(timespec="seconds"))
        sql += " ORDER BY criado_em DESC LIMIT ?"
        params.append(limite)
        return [self._linha_para_dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def atualizar_solicitacao(self, protocolo: str, campos: dict[str, Any]) -> None:
        linha = self._dict_para_linha(campos)
        permitidas = {"atualizado_em", "status", "categoria_final", "urgencia_final", "nota_gestor",
                      "historico_json", "feedback_util", "feedback_comentario"}
        if not set(linha) <= permitidas:  # nomes de coluna nunca vêm do usuário, mas garantimos
            raise ValueError(f"colunas não permitidas: {set(linha) - permitidas}")
        atribuicoes = ", ".join(f"{c} = ?" for c in linha)
        with self._lock:
            self._conn.execute(
                f"UPDATE solicitacoes SET {atribuicoes} WHERE protocolo = ?", (*linha.values(), protocolo)
            )
            self._conn.commit()

    def existe_protocolo(self, protocolo: str) -> bool:
        return self._conn.execute("SELECT 1 FROM solicitacoes WHERE protocolo = ?", (protocolo,)).fetchone() is not None

    def contar_solicitacoes(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM solicitacoes").fetchone()[0]
