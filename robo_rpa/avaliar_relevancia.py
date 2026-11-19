"""Mede a precisão e o recall do filtro de notícias relevantes (etapa A) numa amostra rotulada à mão.

Uso: python avaliar_relevancia.py   (lê dados/teste/noticias_rotuladas.csv)
Critério do rótulo: 1 = notícia útil ao boletim operacional do gestor (chuva, alagamento, árvores, risco
geológico ou estrutural, vistorias, drenagem); 0 = institucional, cultural ou sem ação de zeladoria.
"""

import csv
from pathlib import Path

from etapas.coleta_web import PALAVRAS_RELEVANTES, _norm

ARQUIVO = Path(__file__).parent / "dados" / "teste" / "noticias_rotuladas.csv"


def medir(coluna_ou_filtro) -> dict:
    linhas = list(csv.DictReader(ARQUIVO.open(encoding="utf-8"), delimiter=";"))
    tp = fp = fn = tn = 0
    erros = []
    for x in linhas:
        real = x["rotulo_manual"] == "1"
        previsto = (x[coluna_ou_filtro] == "1") if isinstance(coluna_ou_filtro, str) else coluna_ou_filtro(x["titulo"])
        tp += real and previsto
        fp += (not real) and previsto
        fn += real and not previsto
        tn += (not real) and not previsto
        if real != previsto:
            erros.append(("falso positivo" if previsto else "falso negativo", x["titulo"][:100]))
    return {"noticias": len(linhas), "vp": tp, "fp": fp, "fn": fn, "vn": tn,
            "precisao": round(tp / (tp + fp), 3) if tp + fp else None, "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "erros": erros}


if __name__ == "__main__":
    v1 = medir("marcado_pelo_robo_v1")
    v2 = medir(lambda titulo: bool(PALAVRAS_RELEVANTES.search(_norm(titulo))))
    for nome, r in (("v1 (coleta original)", v1), ("v2 (filtro atual)", v2)):
        print(f"{nome}: precisão {r['precisao']} · recall {r['recall']} · VP {r['vp']} FP {r['fp']} FN {r['fn']} VN {r['vn']}")
        for tipo, titulo in r["erros"]:
            print(f"   {tipo}: {titulo}")
