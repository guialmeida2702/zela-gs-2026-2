"""Recuperação de trechos: BM25 (lexical), denso (embeddings multilíngues) e híbrido (fusão RRF).

- BM25 acerta termos exatos ("poda", "calçada", "199") e não precisa de modelo.
- Denso entende paráfrases ("água jorrando" ~ "vazamento"), com o modelo
  paraphrase-multilingual-MiniLM-L12-v2 via fastembed (ONNX, sem PyTorch).
- Híbrido combina as duas listas por Reciprocal Rank Fusion (k=60), sem calibrar pesos.
Se o modelo denso não puder ser carregado (sem internet, sem pacote), a busca cai
para BM25 e registra o aviso: o assistente continua funcionando.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from app.pipelines.conhecimento import Trecho

log = logging.getLogger("zela.busca")

MODELO_DENSO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_STOP = set([
    "a", "o", "e", "é", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "um", "uma", "uns",
    "umas", "para", "por", "com", "sem", "que", "se", "ao", "aos", "à", "às", "como", "mais", "mas", "ou", "ser",
    "foi", "são", "está", "estão", "ter", "tem", "há", "me", "meu", "minha", "seu", "sua", "seus", "suas", "eu",
    "você", "vocês", "ele", "ela", "eles", "elas", "isso", "isto", "esse", "essa", "este", "esta", "qual",
    "quais", "quando", "onde", "porque", "pelo", "pela", "pelos", "pelas", "já", "não", "sim", "muito", "pode",
    "posso", "devo", "deve", "também", "sobre", "entre", "até", "depois", "antes", "quem", "lhe", "lhes", "nosso",
    "nossa", "num", "numa", "faz", "fazer"
])


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()


def _radical(p: str) -> str:
    """Redução leve de sufixos (plural e formas comuns) para o BM25 casar 'calçadas' com 'calçada'."""
    for suf, rep in (("coes", "cao"), ("oes", "ao"), ("aes", "ao"), ("is", "l"), ("es", ""), ("s", "")):
        if len(p) > 4 and p.endswith(suf):
            return p[: -len(suf)] + rep
    return p


def tokenizar(texto: str) -> list[str]:
    return [_radical(t) for t in re.findall(r"[a-z0-9]{2,}", normalizar(texto)) if t not in _STOP]


@dataclass
class Resultado:
    trecho: Trecho
    score: float
    rank_bm25: int | None = None
    rank_denso: int | None = None
    cos_denso: float | None = None


class IndiceBusca:
    def __init__(self, trechos: list[Trecho], modo: str = "hibrido", cache_modelos: str | None = None):
        self.trechos = trechos
        self.bm25 = BM25Okapi([tokenizar(t.texto_indexado) for t in trechos])
        self.modo_pedido = modo
        self.modelo = None
        self.matriz: np.ndarray | None = None
        self.avisos: list[str] = []
        if modo in ("hibrido", "denso"):
            try:
                from fastembed import TextEmbedding

                self.modelo = TextEmbedding(MODELO_DENSO, cache_dir=cache_modelos)
                self.matriz = self._normalizar(np.array(list(self.modelo.embed([t.texto_indexado for t in trechos]))))
            except Exception as exc:  # resiliência: sem modelo denso, segue com BM25
                log.warning("Busca densa indisponível (%s): usando BM25.", type(exc).__name__)
                self.avisos.append("busca densa indisponível; usando apenas BM25")
                self.modelo = None
        self.modo = modo if self.modelo is not None or modo == "bm25" else "bm25"

    @staticmethod
    def _normalizar(m: np.ndarray) -> np.ndarray:
        return m / np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-9, None)

    def _ranking_bm25(self, consulta: str) -> tuple[np.ndarray, np.ndarray]:
        scores = self.bm25.get_scores(tokenizar(consulta))
        return np.argsort(-scores), scores

    def _ranking_denso(self, consulta: str) -> tuple[np.ndarray, np.ndarray]:
        q = self._normalizar(np.array(list(self.modelo.embed([consulta]))))[0]
        cos = self.matriz @ q
        return np.argsort(-cos), cos

    def buscar(self, consulta: str, k: int = 4, modo: str | None = None) -> list[Resultado]:
        modo = modo or self.modo
        if modo != "bm25" and self.modelo is None:
            modo = "bm25"
        ordem_b, scores_b = self._ranking_bm25(consulta)
        rank_b = {int(i): r for r, i in enumerate(ordem_b)}
        if modo == "bm25":
            return [Resultado(self.trechos[i], float(scores_b[i]), rank_bm25=r) for r, i in enumerate(ordem_b[:k])]
        ordem_d, cos = self._ranking_denso(consulta)
        rank_d = {int(i): r for r, i in enumerate(ordem_d)}
        if modo == "denso":
            return [Resultado(self.trechos[i], float(cos[i]), rank_denso=r, cos_denso=float(cos[i]))
                    for r, i in enumerate(ordem_d[:k])]
        rrf = {i: 1 / (60 + rank_b[i] + 1) + 1 / (60 + rank_d[i] + 1) for i in range(len(self.trechos))}
        melhores = sorted(rrf, key=rrf.get, reverse=True)[:k]
        return [Resultado(self.trechos[i], rrf[i], rank_bm25=rank_b[i], rank_denso=rank_d[i], cos_denso=float(cos[i]))
                for i in melhores]

    def sinais(self, consulta: str) -> dict:
        """Sinais de confiança da recuperação (usados para decidir abster-se antes de chamar o LLM)."""
        _, scores_b = self._ranking_bm25(consulta)
        saida = {"bm25_max": float(scores_b.max()) if len(scores_b) else 0.0}
        if self.modelo is not None:
            _, cos = self._ranking_denso(consulta)
            saida["cos_max"] = float(cos.max())
        return saida
