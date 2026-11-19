"""Teste do LLM do assistente de voz: 30 perguntas (20 diretas, 5 de continuação, 5 fora do escopo).

Mede % de respostas corretas (diretas + continuação) e % de recusas adequadas (fora do escopo),
além de abstenções indevidas e latência. Usa a API do Zela (/assistente/perguntar), que é o
"cérebro" do assistente de voz.

Uso:  python avaliacao/avaliar_llm.py --api http://localhost:8000
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from avaliacao.normalizar import contem_algum  # noqa: E402
from voz.fala import adaptar_para_fala  # noqa: E402

AQUI = Path(__file__).parent
# Sinais de que a resposta fora do escopo cumpriu o papel (recusou e redirecionou)
SINAIS_RECUSA = ["fora do que eu consigo", "nao encontrei", "posso ajudar com", "zeladoria", "156"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    args = ap.parse_args()
    perguntas = json.loads((AQUI / "perguntas_llm.json").read_text(encoding="utf-8"))["perguntas"]
    http = httpx.Client(timeout=400)
    linhas = []
    for p in perguntas:
        inicio = time.perf_counter()
        r = http.post(f"{args.api}/assistente/perguntar", json={"pergunta": p["pergunta"], "historico": p.get("historico", [])})
        segundos = round(time.perf_counter() - inicio, 1)
        r.raise_for_status()
        d = r.json()
        if p["tipo"] == "fora_do_escopo":
            ok = (d["fora_do_escopo"] or d["sem_evidencia"]) and contem_algum(d["resposta"], SINAIS_RECUSA)
            julgamento = "recusa adequada" if ok else "respondeu fora do escopo"
        else:
            ok = (not d["sem_evidencia"]) and contem_algum(d["resposta"], p["esperado"])
            julgamento = "correta" if ok else ("abstenção indevida" if d["sem_evidencia"] else "incorreta/incompleta")
        linhas.append({"id": p["id"], "tipo": p["tipo"], "pergunta": p["pergunta"],
                       "resposta_esperada": p.get("resposta_esperada", ""), "resposta": d["resposta"],
                       "resposta_falada": adaptar_para_fala(d["resposta"]),
                       "fontes": " | ".join(c["titulo"] for c in d["citacoes"]), "sem_evidencia": d["sem_evidencia"],
                       "fora_do_escopo": d["fora_do_escopo"], "bloqueios": ",".join(d["bloqueios"]),
                       "julgamento": julgamento, "ok": ok, "segundos": segundos})
        print(f"[{p['id']}] {julgamento:<24} {segundos:>5}s | {d['resposta'][:110]}")

    def pct(tipo: list[str]) -> float:
        sel = [linha for linha in linhas if linha["tipo"] in tipo]
        return round(100 * sum(linha["ok"] for linha in sel) / len(sel), 1)

    resumo = {
        "perguntas": len(linhas),
        "pct_corretas_diretas": pct(["direta"]),
        "pct_corretas_continuacao": pct(["continuacao"]),
        "pct_corretas_total": pct(["direta", "continuacao"]),
        "pct_recusas_adequadas": pct(["fora_do_escopo"]),
        "abstencoes_indevidas": sum(linha["julgamento"] == "abstenção indevida" for linha in linhas),
        "latencia_media_s": round(sum(linha["segundos"] for linha in linhas) / len(linhas), 1),
        "modelo": http.get(f"{args.api}/health").json()["ia"]["modelo"],
    }
    saida = AQUI / "resultados"
    saida.mkdir(exist_ok=True)
    with open(saida / "llm_30_perguntas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    (saida / "llm_30_perguntas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
