"""Orquestra a construção: documentos lidos -> limpeza -> seções -> três corpora -> divisão e estatísticas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .exportacao import CORPORA, dividir, estatisticas
from .geradores import (
    RECUSAS_PADRAO,
    SISTEMA_PADRAO,
    Secao,
    corpus_conversacional,
    corpus_perguntas_respostas,
    corpus_texto_puro,
    secoes,
)
from .leitura import Documento
from .limpeza import Bloco, OpcoesLimpeza, limpar


@dataclass
class Configuracao:
    tamanho_trecho: int = 1200          # caracteres por exemplo de texto puro
    derivar_perguntas: bool = True      # perguntas montadas a partir dos títulos das seções
    turnos: int = 3                     # pares por conversa
    sistema: str = SISTEMA_PADRAO       # mensagem de sistema do corpus conversacional
    escopo: str = ""                    # assuntos que o assistente atende (aparece nas recusas)
    incluir_recusas: bool = True
    fracao_validacao: float = 0.1
    semente: int = 42


@dataclass
class Resultado:
    documentos: list[dict] = field(default_factory=list)          # nome, formato, relatório da limpeza, nº de blocos
    blocos: dict[str, list[Bloco]] = field(default_factory=dict)
    secoes: dict[str, list[Secao]] = field(default_factory=dict)
    corpora: dict[str, list[dict]] = field(default_factory=dict)
    divisoes: dict[str, tuple[list[dict], list[dict]]] = field(default_factory=dict)
    estatisticas: dict = field(default_factory=dict)
    erros: list[tuple[str, str]] = field(default_factory=list)
    opcoes: dict = field(default_factory=dict)
    configuracao: dict = field(default_factory=dict)


def construir(documentos: list[Documento], opcoes: OpcoesLimpeza | None = None, configuracao: Configuracao | None = None,
              pares_extras: list[dict] | None = None, erros: list[tuple[str, str]] | None = None) -> Resultado:
    """Constrói os três corpora. `pares_extras` recebe pares já conferidos de outra origem (por exemplo, os gerados
    por LLM); `erros` repassa os arquivos que não puderam ser lidos, para constarem na ficha."""
    op = opcoes or OpcoesLimpeza()
    cfg = configuracao or Configuracao()
    resultado = Resultado(erros=list(erros or []), opcoes=asdict(op), configuracao=asdict(cfg))
    vistos: set[str] = set()
    for doc in documentos:
        blocos, relatorio = limpar(doc, op, vistos)
        resultado.blocos[doc.nome] = blocos
        resultado.secoes[doc.nome] = secoes(doc, blocos)
        resultado.documentos.append({"nome": doc.nome, "formato": doc.formato, "relatorio": relatorio, "blocos": len(blocos),
                                     "pares_estruturados": len(doc.pares)})
    pares = corpus_perguntas_respostas(documentos, resultado.secoes, op, derivar=cfg.derivar_perguntas)
    conhecidas = {p["pergunta"].lower() for p in pares}
    pares += [p for p in (pares_extras or []) if p["pergunta"].lower() not in conhecidas]
    resultado.corpora = {
        "texto_puro": corpus_texto_puro(resultado.secoes, cfg.tamanho_trecho),
        "perguntas_respostas": pares,
        "conversacional": corpus_conversacional(pares, cfg.sistema, cfg.turnos, RECUSAS_PADRAO if cfg.incluir_recusas else (), cfg.escopo),
    }
    for corpus in CORPORA:
        resultado.divisoes[corpus] = dividir(resultado.corpora[corpus], cfg.fracao_validacao, cfg.semente)
    resultado.estatisticas = estatisticas(resultado.corpora, resultado.divisoes)
    return resultado
