"""Linha de comando da ferramenta de construção de corpus.

    python construir.py --entrada exemplos --saida saida
    python construir.py --entrada meus_documentos --saida saida --sem-derivadas --turnos 2
    python construir.py --entrada exemplos --saida saida --llm http://127.0.0.1:8080/v1 --modelo qwen2.5-1.5b-instruct

Lê todos os arquivos aceitos da pasta de entrada, limpa, monta os três corpora (texto puro, perguntas e
respostas, conversacional), grava os arquivos de treino e validação e confere o resultado.
Sai com código 0 quando a conferência não encontra problemas.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from corpus import (
    FORMATOS,
    Configuracao,
    ErroLeitura,
    OpcoesLimpeza,
    construir,
    exportar,
    gerar_pares_com_llm,
    ler_arquivo,
    validar_pasta,
)
from corpus.exportacao import CORPORA, NOMES, linha_de_treino


def registrar(resultado, saida: Path) -> Path:
    """Guarda a execução em corpus_pln/resultados/ (versionado): o relatório de PLN cita estes números."""
    pasta = Path(__file__).resolve().parent / "resultados"
    pasta.mkdir(exist_ok=True)
    limpeza = [{"nome": d["nome"], "formato": d["formato"], "pares_estruturados": d["pares_estruturados"],
                "reducao_pct": d["relatorio"].reducao_pct, **asdict(d["relatorio"])} for d in resultado.documentos]

    def amostra(corpus: str, criterio) -> dict | None:
        treino = resultado.divisoes[corpus][0]
        escolhido = next((e for e in treino if criterio(e)), treino[0] if treino else None)
        return None if escolhido is None else {"fonte": escolhido["fonte"], "secao": escolhido.get("secao", ""),
                                               "origem": escolhido["origem"], "linha": linha_de_treino(corpus, escolhido)}

    amostras = {
        "texto_puro": amostra("texto_puro", lambda e: e["fonte"].endswith(".pdf")),
        "perguntas_respostas": amostra("perguntas_respostas", lambda e: e["origem"] == "extraida"),
        "conversacional": amostra("conversacional", lambda e: e.get("turnos", 1) >= 2),
    }
    gravar = {"estatisticas.json": resultado.estatisticas, "limpeza.json": limpeza, "amostras.json": amostras,
              "configuracao.json": {"opcoes": resultado.opcoes, "configuracao": resultado.configuracao,
                                    "erros": resultado.erros}}
    for nome, dados in gravar.items():
        (pasta / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy(saida / "FICHA_DO_CORPUS.md", pasta / "FICHA_DO_CORPUS.md")
    return pasta


def main() -> int:
    ap = argparse.ArgumentParser(description="Constrói três corpora para fine-tuning a partir de uma pasta de documentos.")
    ap.add_argument("--entrada", required=True, help="pasta com os documentos (" + ", ".join(FORMATOS) + ")")
    ap.add_argument("--saida", required=True, help="pasta onde os corpora serão gravados")
    ap.add_argument("--tamanho-trecho", type=int, default=1200, help="caracteres por exemplo de texto puro")
    ap.add_argument("--turnos", type=int, default=3, help="pares por conversa no corpus conversacional")
    ap.add_argument("--validacao", type=float, default=0.1, help="fração separada para validação")
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--sistema", default=None, help="mensagem de sistema do corpus conversacional")
    ap.add_argument("--escopo", default="", help="assuntos que o assistente atende (aparece nas recusas)")
    ap.add_argument("--sem-derivadas", action="store_true", help="não montar perguntas a partir dos títulos das seções")
    ap.add_argument("--sem-recusas", action="store_true", help="não incluir conversas de recusa fora do escopo")
    ap.add_argument("--sem-mascarar", action="store_true", help="não mascarar dados pessoais (use só com dados públicos)")
    ap.add_argument("--remover-urls", action="store_true")
    ap.add_argument("--minusculas", action="store_true")
    ap.add_argument("--preservar", action="append", default=[], help="trecho que não deve ser mascarado (pode repetir)")
    ap.add_argument("--llm", default=None, help="URL de uma API compatível com a da OpenAI para gerar perguntas extras")
    ap.add_argument("--modelo", default="qwen2.5-1.5b-instruct")
    ap.add_argument("--max-trechos-llm", type=int, default=12, help="quantos trechos enviar ao LLM")
    ap.add_argument("--registrar", action="store_true",
                    help="guarda estatísticas, limpeza, ficha e uma amostra de cada corpus em corpus_pln/resultados/ "
                         "(é o que o relatório de PLN lê)")
    args = ap.parse_args()

    entrada = Path(args.entrada)
    if not entrada.is_dir():
        print(f"A pasta de entrada não existe: {entrada}")
        return 2
    documentos, erros = [], []
    for caminho in sorted(p for p in entrada.iterdir() if p.is_file() and p.suffix.lower() in FORMATOS):
        try:
            documentos.append(ler_arquivo(caminho))
        except ErroLeitura as exc:  # um arquivo ruim não interrompe os outros
            erros.append((caminho.name, str(exc)))
            print(f"[aviso] {caminho.name}: {exc}")
    if not documentos:
        print("Nenhum documento legível na pasta de entrada.")
        return 2

    opcoes = OpcoesLimpeza(mascarar_dados_pessoais=not args.sem_mascarar, remover_urls=args.remover_urls,
                           minusculas=args.minusculas, preservar=tuple(args.preservar))
    cfg = Configuracao(tamanho_trecho=args.tamanho_trecho, derivar_perguntas=not args.sem_derivadas, turnos=args.turnos,
                       escopo=args.escopo, incluir_recusas=not args.sem_recusas, fracao_validacao=args.validacao,
                       semente=args.semente)
    if args.sistema:
        cfg.sistema = args.sistema

    resultado = construir(documentos, opcoes, cfg, erros=erros)
    if args.llm:
        trechos = resultado.corpora["texto_puro"][: args.max_trechos_llm]
        print(f"Gerando perguntas com o LLM para {len(trechos)} trechos (pode demorar)...")
        extras, resumo = gerar_pares_com_llm(trechos, args.llm, args.modelo, os.getenv("LLM_API_KEY", "local"))
        print("LLM:", resumo)
        resultado = construir(documentos, opcoes, cfg, pares_extras=extras, erros=erros)

    exportar(resultado, args.saida)
    if args.registrar:
        print("Execução registrada em", registrar(resultado, Path(args.saida)))
    print(f"\n{len(documentos)} documento(s) lido(s), {len(erros)} com erro.")
    for d in resultado.documentos:
        r = d["relatorio"]
        pares = f", {d['pares_estruturados']} pares prontos" if d["pares_estruturados"] else ""
        print(f"  {d['nome']:<40} {r.caracteres_antes:>7} -> {r.caracteres_depois:>7} caracteres ({r.reducao_pct}% a menos{pares})")
    for corpus in CORPORA:
        e = resultado.estatisticas[corpus]
        print(f"{NOMES[corpus]:<24} {e['exemplos']:>4} exemplos ({e['treino']} treino, {e['validacao']} validação), "
              f"~{e['tokens_estimados']} tokens")
    problemas = validar_pasta(args.saida)
    print(f"\nConferência dos arquivos: {'sem problemas' if not problemas else str(len(problemas)) + ' problema(s)'}")
    for p in problemas[:20]:
        print("  -", p)
    print("Arquivos em", Path(args.saida).resolve())
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
