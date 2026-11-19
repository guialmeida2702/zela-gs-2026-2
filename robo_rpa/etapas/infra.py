"""Infraestrutura do robô: configuração, log, banco SQL de controle e repetição com espera."""

import json
import logging
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_env(arquivo: Path = RAIZ / ".env") -> None:
    """Lê `robo_rpa/.env` (linhas CHAVE=valor), sem sobrescrever variáveis já definidas no ambiente.
    O arquivo está no .gitignore; o modelo é `robo_rpa/.env.example`."""
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()


@dataclass
class Config:
    api_url: str = field(default_factory=lambda: os.getenv("ZELA_API_URL", "http://localhost:8000"))
    gestor_usuario: str = field(default_factory=lambda: os.getenv("ZELA_GESTOR_USUARIO", "gestor"))
    gestor_senha: str = field(default_factory=lambda: os.getenv("ZELA_GESTOR_SENHA", ""))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_porta: int = field(default_factory=lambda: int(os.getenv("SMTP_PORTA", "587")))
    smtp_usuario: str = field(default_factory=lambda: os.getenv("SMTP_USUARIO", ""))
    smtp_senha: str = field(default_factory=lambda: os.getenv("SMTP_SENHA", ""))
    email_destino: str = field(default_factory=lambda: os.getenv("EMAIL_DESTINO", ""))
    entrada: Path = RAIZ / "dados" / "entrada"
    saida: Path = RAIZ / "saida"
    banco: Path = RAIZ / "saida" / "robo.db"
    limiar_chuva_mm: float = 30.0
    chuva_teste_mm: float | None = None  # só para testes: substitui a previsão real do Open-Meteo
    dry_run: bool = False
    timeout_s: float = 15.0


def configurar_log(pasta: Path) -> logging.Logger:
    pasta.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("robo")
    log.setLevel(logging.INFO)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(etapa)s] %(message)s", defaults={"etapa": "-"})
        for h in (logging.FileHandler(pasta / "robo.log", encoding="utf-8"), logging.StreamHandler()):
            h.setFormatter(fmt)
            log.addHandler(h)
    return log


def com_repeticao[T](funcao: Callable[[], T], *, tentativas: int = 3, espera_s: float = 1.0, log: logging.Logger,
                  etapa: str, descricao: str) -> T:
    """Repete chamadas que podem falhar por instabilidade (rede, SMTP), com espera crescente (1s, 2s, 4s...)."""
    ultimo: Exception | None = None
    for n in range(1, tentativas + 1):
        try:
            return funcao()
        except Exception as exc:  # o chamador decide o caminho seguro após esgotar as tentativas
            ultimo = exc
            log.warning("%s falhou (tentativa %d/%d): %s", descricao, n, tentativas, type(exc).__name__,
                        extra={"etapa": etapa})
            if n < tentativas:
                time.sleep(espera_s * 2 ** (n - 1))
    raise ultimo  # type: ignore[misc]


class BancoRobo:
    """Banco SQL do robô: execuções, eventos (trilha de auditoria) e arquivos já processados (idempotência)."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS execucoes (id INTEGER PRIMARY KEY AUTOINCREMENT, inicio TEXT, fim TEXT,
        dry_run INTEGER, resumo_json TEXT);
    CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, execucao_id INTEGER, em TEXT,
        etapa TEXT, nivel TEXT, mensagem TEXT);
    CREATE TABLE IF NOT EXISTS arquivos_processados (hash TEXT PRIMARY KEY, nome TEXT, processado_em TEXT,
        execucao_id INTEGER, linhas_validas INTEGER, linhas_rejeitadas INTEGER);
    CREATE TABLE IF NOT EXISTS noticias (url TEXT PRIMARY KEY, titulo TEXT, data TEXT, fonte TEXT, relevante INTEGER,
        coletada_em TEXT);
    CREATE TABLE IF NOT EXISTS vistorias_foto (arquivo TEXT, execucao_id INTEGER, classe TEXT, probabilidade REAL,
        rotulo_esperado TEXT, em TEXT);
    """

    def __init__(self, caminho: Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(caminho)
        self.conn.executescript(self.SCHEMA)
        self.execucao_id: int | None = None

    def iniciar(self, dry_run: bool) -> int:
        cur = self.conn.execute("INSERT INTO execucoes (inicio, dry_run) VALUES (?, ?)",
                                (datetime.now().isoformat(timespec="seconds"), int(dry_run)))
        self.conn.commit()
        self.execucao_id = cur.lastrowid
        return self.execucao_id

    def evento(self, etapa: str, nivel: str, mensagem: str) -> None:
        self.conn.execute("INSERT INTO eventos (execucao_id, em, etapa, nivel, mensagem) VALUES (?,?,?,?,?)",
                          (self.execucao_id, datetime.now().isoformat(timespec="seconds"), etapa, nivel, mensagem[:500]))
        self.conn.commit()

    def finalizar(self, resumo: dict) -> None:
        self.conn.execute("UPDATE execucoes SET fim = ?, resumo_json = ? WHERE id = ?",
                          (datetime.now().isoformat(timespec="seconds"), json.dumps(resumo, ensure_ascii=False, default=str),
                           self.execucao_id))
        self.conn.commit()

    def arquivo_ja_processado(self, hash_: str) -> bool:
        return self.conn.execute("SELECT 1 FROM arquivos_processados WHERE hash = ?", (hash_,)).fetchone() is not None

    def marcar_arquivo(self, hash_: str, nome: str, validas: int, rejeitadas: int) -> None:
        self.conn.execute("INSERT OR REPLACE INTO arquivos_processados VALUES (?,?,?,?,?,?)",
                          (hash_, nome, datetime.now().isoformat(timespec="seconds"), self.execucao_id, validas, rejeitadas))
        self.conn.commit()
