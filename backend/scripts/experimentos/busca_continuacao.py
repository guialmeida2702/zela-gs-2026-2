"""Experimento: variantes da busca em perguntas de continuação, sem chamar o LLM.

Para cada turno de continuação dos conjuntos de teste (conversa M1 a M3 do assistente, 5 continuações das 30
perguntas de voz e os turnos das 10 conversas por voz), confere se o trecho com a resposta esperada fica entre
os 4 entregues ao gerador.

Variantes (a âncora é a pergunta mais recente do cidadão que não é uma continuação):
  A  documentos do assunto pela consulta combinada; trecho escolhido pela pergunta atual
  B  documentos pela âncora sozinha; trecho escolhido pelo turno anterior + pergunta atual
  C  como B, com a lista do assunto também restrita aos documentos da âncora
  D  documentos pela âncora e pelos 2 primeiros da consulta combinada; trecho pelo turno anterior + atual
  E  como A, mais uma lista com o turno anterior + pergunta atual quando o turno anterior também era continuação
     (adotada: método Assistente._buscar)

Uso: MODELOS_CACHE_DIR=<cache> python scripts/experimentos/busca_continuacao.py > ../avaliacao/genai/busca_continuacao.txt
"""

import json
import os
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from app.pipelines.assistente import _CONTINUACAO, Assistente  # noqa: E402
from app.pipelines.conhecimento import construir_trechos  # noqa: E402
from app.providers.busca import IndiceBusca  # noqa: E402

K = 4
VOZ = RAIZ.parent / "assistente_voz" / "avaliacao"


def norm(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def continuacao(texto: str) -> bool:
    return len(texto.split()) <= 7 and bool(_CONTINUACAO.search(texto.strip()))


def seguimento(pergunta: str, anteriores: list[str]) -> bool:
    return bool(anteriores) and (len(pergunta.split()) <= 7 or bool(_CONTINUACAO.search(pergunta)))


def fundir(listas: list[list]) -> list:
    pontos, por_id = {}, {}
    for lista in listas:
        for posicao, r in enumerate(lista, start=1):
            pontos[r.trecho.id] = pontos.get(r.trecho.id, 0.0) + 1 / (60 + posicao)
            por_id[r.trecho.id] = r
    return [por_id[i] for i in sorted(pontos, key=pontos.get, reverse=True)][:K]


def casos_de_teste() -> list[tuple[str, list[str], str, list[str]]]:
    casos = [
        ("M2", ["Como peço a poda de uma árvore na calçada?"], "E quanto tempo demora?", ["120 dias"]),
        ("M3", ["Como peço a poda de uma árvore na calçada?", "E quanto tempo demora?"], "E se não fizerem nesse prazo?",
         ["ouvidoria"]),
    ]
    for q in json.loads((VOZ / "perguntas_llm.json").read_text(encoding="utf-8"))["perguntas"]:
        if q["tipo"] == "continuacao":
            anteriores = [m["texto"] for m in q["historico"] if m["papel"] == "cidadao"]
            casos.append((q["id"], anteriores, q["pergunta"], q["esperado"]))
    fonte = (VOZ / "avaliar_e2e.py").read_text(encoding="utf-8")
    inicio = fonte.index("CONVERSAS = [") + len("CONVERSAS = ")
    conversas = eval(fonte[inicio: fonte.index("\n\n\ndef ", inicio)])  # lista literal do próprio repositório
    for i, conversa in enumerate(conversas, start=1):
        anteriores: list[str] = []
        for j, (pergunta, chaves) in enumerate(conversa, start=1):
            if isinstance(chaves, list) and j > 1:
                casos.append((f"V{i}.{j}", list(anteriores), pergunta, chaves))
            anteriores.append(pergunta)
    return casos


def main() -> None:
    indice = IndiceBusca(construir_trechos(), modo="hibrido", cache_modelos=os.getenv("MODELOS_CACHE_DIR"))
    assistente = Assistente(None, indice, k=K)

    def ancora(anteriores: list[str]) -> str:
        return next((a for a in reversed(anteriores) if not continuacao(a)), anteriores[-1])

    def no_assunto(texto: str, documentos: set[str]) -> list:
        return [r for r in indice.buscar(texto, k=4 * K) if r.trecho.doc_id in documentos][: 2 * K]

    def variante(nome: str, pergunta: str, anteriores: list[str]) -> list:
        if not seguimento(pergunta, anteriores):
            return indice.buscar(pergunta, k=K)
        anc = ancora(anteriores)
        combinada = f"{anc} {pergunta}"
        recente = pergunta if anteriores[-1] == anc else f"{anteriores[-1]} {pergunta}"
        tema = indice.buscar(combinada, k=2 * K)
        if nome == "A":
            documentos = {r.trecho.doc_id for r in tema[:K]}
            return fundir([tema, no_assunto(pergunta, documentos)])
        if nome == "B":
            documentos = {r.trecho.doc_id for r in indice.buscar(anc, k=K)}
            return fundir([tema, no_assunto(recente, documentos)])
        if nome == "C":
            documentos = {r.trecho.doc_id for r in indice.buscar(anc, k=K)}
            return fundir([no_assunto(combinada, documentos), no_assunto(recente, documentos)])
        if nome == "D":
            documentos = {r.trecho.doc_id for r in indice.buscar(anc, k=K)} | {r.trecho.doc_id for r in tema[:2]}
            return fundir([tema, no_assunto(recente, documentos)])
        return assistente._buscar(pergunta, combinada, anteriores[-1])  # E: o código atual

    casos = casos_de_teste()
    for nome in "ABCDE":
        faltam = []
        for cid, anteriores, pergunta, chaves in casos:
            achados = variante(nome, pergunta, anteriores)
            if not any(any(norm(c) in norm(r.trecho.texto) for c in chaves) for r in achados):
                faltam.append(cid)
        rotulo = " (adotada)" if nome == "E" else ""
        print(f"{nome}{rotulo}: trecho com a resposta entre os 4 recuperados em {len(casos) - len(faltam)} de {len(casos)} "
              f"turnos de continuação | faltam: {', '.join(faltam) or 'nenhum'}")
    print("\nV5.2 = \"qual é o telefone deles\" depois de \"tem água limpa vazando no meio da rua\": o trecho da Sabesp "
          "fica fora dos 4 em todas as variantes.")


if __name__ == "__main__":
    main()
