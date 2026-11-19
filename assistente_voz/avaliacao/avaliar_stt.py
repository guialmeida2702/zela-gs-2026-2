"""Teste de STT: WER (jiwer) sobre as 20 frases, com comparação de opções e análise de viés.

Opções comparadas (parâmetro --opcoes): tamanho do Whisper (tiny, small) e a dica de vocabulário do domínio
("small+vocab" = small com initial_prompt). O WER sai separado por condição (silencioso x ruído), por locutor
e, quando o manifesto traz as colunas opcionais genero, faixa_etaria e sotaque, por grupo (análise de viés).

Uso:
  python avaliacao/avaliar_stt.py --pasta avaliacao/audios_reais       # gravações reais (manifesto.csv)
  python avaliacao/avaliar_stt.py --pasta avaliacao/audios_sinteticos  # linha de base sintética
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import jiwer

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from avaliacao.normalizar import normalizar  # noqa: E402
from voz.stt import VOCABULARIO, Transcritor  # noqa: E402

AQUI = Path(__file__).parent
GRUPOS = ("locutor", "genero", "faixa_etaria", "sotaque")


def _wer(pares: list[tuple[str, str]]) -> float:
    return round(jiwer.wer([r for r, _ in pares], [h for _, h in pares]), 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default=str(AQUI / "audios_sinteticos"))
    ap.add_argument("--opcoes", default="tiny,small,small+vocab", help="tamanhos do Whisper; +vocab liga a dica de vocabulário")
    args = ap.parse_args()
    pasta = Path(args.pasta)
    with open(AQUI / "frases_stt.csv", encoding="utf-8") as f:
        referencia = {r["id"]: r["frase"] for r in csv.DictReader(f, delimiter=";")}
    with open(pasta / "manifesto.csv", encoding="utf-8") as f:
        audios = [a for a in csv.DictReader(f, delimiter=";") if a.get("arquivo")]
    if not audios:
        sys.exit(f"Nenhum áudio listado em {pasta / 'manifesto.csv'}. Veja o README para gravar e preencher o manifesto.")

    linhas, resumo = [], {}
    for opcao in args.opcoes.split(","):
        tamanho, _, extra = opcao.partition("+")
        inicio_carga = time.perf_counter()
        stt = Transcritor(tamanho, cache=os.getenv("MODELOS_CACHE_DIR"), vocabulario=VOCABULARIO if extra == "vocab" else None)
        carga = time.perf_counter() - inicio_carga
        pares, tempos, duracoes = [], [], []
        por_grupo: dict[str, dict[str, list]] = {g: {} for g in ("condicao", *GRUPOS)}
        for a in audios:
            r = stt.transcrever_arquivo(pasta / a["arquivo"])
            par = (normalizar(referencia[a["id"]]), normalizar(r["texto"]))
            pares.append(par)
            for g in por_grupo:
                if a.get(g):
                    por_grupo[g].setdefault(a[g], []).append(par)
            tempos.append(r["segundos"])
            duracoes.append(r["duracao_audio_s"])
            linhas.append({"opcao": opcao, "arquivo": a["arquivo"], "locutor": a["locutor"], "condicao": a["condicao"],
                           "referencia": referencia[a["id"]], "transcricao": r["texto"], "wer": round(jiwer.wer(*par), 3),
                           "segundos": r["segundos"]})
            print(f"[{opcao}] {a['arquivo']:<26} WER {linhas[-1]['wer']:.2f} | {r['texto']}")
        resumo[opcao] = {
            "wer_geral": _wer(pares),
            "wer_por_condicao": {c: _wer(p) for c, p in por_grupo["condicao"].items()},
            **{f"wer_por_{g}": {k: {"wer": _wer(p), "audios": len(p)} for k, p in por_grupo[g].items()}
               for g in GRUPOS if por_grupo[g]},
            "tempo_medio_s": round(sum(tempos) / len(tempos), 2),
            "fator_tempo_real": round(sum(tempos) / sum(duracoes), 3),
            "carga_modelo_s": round(carga, 1),
            "audios": len(audios),
        }
    saida = AQUI / "resultados"
    saida.mkdir(exist_ok=True)
    sufixo = pasta.name
    with open(saida / f"stt_{sufixo}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    (saida / f"stt_{sufixo}.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
