"""Roda o iSPD em modo terminal para cada modelo, lê o relatório HTML e calcula a comparação 2 x 4 workers.

Requisitos: Java 8+ e o iSPD.jar (https://www.dcce.ibilce.unesp.br/spd/downloads/iSPD.jar).
Em servidor sem tela, o iSPD precisa de um display virtual para gerar os gráficos: o script usa xvfb-run se existir.

Uso: python simular.py --ispd /caminho/iSPD.jar
Saídas: resultados/<modelo>/result.html (relatório do iSPD), resultados/comparacao.csv e resultados/comparacao.json
"""

import argparse
import csv
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from gerar_modelos import CENARIOS, parametros

AQUI = Path(__file__).parent
MODELOS = AQUI / "modelos"
RESULTADOS = AQUI / "resultados"


def rodar(jar: Path, modelo: Path, destino: Path, execucoes: int = 1) -> str:
    """execucoes > 1: o iSPD repete a simulação (cargas sorteadas de novo) e informa a média."""
    destino.mkdir(parents=True, exist_ok=True)
    cmd = ["java", "-jar", str(jar.resolve()), "-n", str(execucoes), "-o", str(destino.resolve()), modelo.name]
    if shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a", *cmd]
    proc = subprocess.run(cmd, cwd=modelo.parent, capture_output=True, text=True, timeout=600)
    (destino / "saida_terminal.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if "Total Simulated Time" not in proc.stdout:
        raise RuntimeError(f"iSPD falhou em {modelo.name}:\n{proc.stdout[-800:]}")
    return proc.stdout


def ler_relatorio(destino: Path) -> dict:
    texto = html.unescape((destino / "result.html").read_text(encoding="latin-1"))
    simples = re.sub(r"<[^>]+>", " ", texto)

    def numero(rotulo: str) -> float:
        return float(re.search(rf"{rotulo}\s*=\s*([\d.Ee+-]+)", simples).group(1))

    recursos = []
    for bloco in texto.split("</tr>"):
        linha = bloco.rsplit("<tr>", 1)[-1]
        celulas = [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", linha, flags=re.S)]
        if len(celulas) == 4 and celulas[0] not in ("Label", ""):
            recursos.append({"recurso": celulas[0], "dono": celulas[1], "processamento": float(celulas[2]),
                             "comunicacao": float(celulas[3])})
    return {
        "tempo_total_simulado_s": numero("Total Simulated Time"),
        "satisfacao_pct": numero("Satisfaction"),
        "ociosidade_processamento_pct": numero("Idleness of processing resources"),
        "ociosidade_comunicacao_pct": numero("Idleness of communication resources"),
        "recursos": recursos,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ispd", required=True, help="caminho do iSPD.jar")
    jar = Path(ap.parse_args().ispd)
    RESULTADOS.mkdir(exist_ok=True)
    comparacao = []
    for cenario in CENARIOS:
        r = {}
        p = parametros(cenario)
        # Com tamanhos sorteados, cada execução gera uma carga diferente: vale a média de 30 simulações
        execucoes = 30 if p["computacao_mflop"][0] != p["computacao_mflop"][2] else 1
        for n in (2, 4, *p["workers_extra"]):
            modelo = MODELOS / f"{cenario}_{n}_workers.imsx"
            destino = RESULTADOS / modelo.stem
            rodar(jar, modelo, destino, execucoes)
            r[n] = ler_relatorio(destino)
            (destino / "metricas.json").write_text(json.dumps(r[n], indent=2, ensure_ascii=False), encoding="utf-8")
        t2, t4 = r[2]["tempo_total_simulado_s"], r[4]["tempo_total_simulado_s"]
        comparacao.append({
            "cenario": cenario, "execucoes": execucoes, "tarefas": p["tarefas"],
            "computacao_mflop": "/".join(map(str, p["computacao_mflop"])),
            "comunicacao_mbit": "/".join(map(str, p["comunicacao_mbit"])), "banda_mbps": p["banda_mbps"],
            "latencia_s": p["latencia_s"], "escalonador": p["escalonador"], "potencia_mflops": p["potencia_mflops"],
            "T2_s": round(t2, 2), "T4_s": round(t4, 2), "reducao_pct": round(100 * (t2 - t4) / t2, 2),
            "speedup_T2_T4": round(t2 / t4, 3),
            **{f"T{n}_s": round(r[n]["tempo_total_simulado_s"], 2) for n in p["workers_extra"]},
            **{f"ociosidade_proc_{n}_pct": round(r[n]["ociosidade_processamento_pct"], 3) for n in p["workers_extra"]},
            **{f"ociosidade_com_{n}_pct": round(r[n]["ociosidade_comunicacao_pct"], 3) for n in p["workers_extra"]},
            "processamento_total_2_s": round(sum(x["processamento"] for x in r[2]["recursos"]), 1),
            "processamento_total_4_s": round(sum(x["processamento"] for x in r[4]["recursos"]), 1),
            "ociosidade_proc_2_pct": round(r[2]["ociosidade_processamento_pct"], 3),
            "ociosidade_proc_4_pct": round(r[4]["ociosidade_processamento_pct"], 3),
            "ociosidade_com_2_pct": round(r[2]["ociosidade_comunicacao_pct"], 3),
            "ociosidade_com_4_pct": round(r[4]["ociosidade_comunicacao_pct"], 3),
        })
        print(f"{cenario:<18} T2 = {t2:9.2f} s | T4 = {t4:9.2f} s | redução {comparacao[-1]['reducao_pct']:6.2f}% | "
              f"T2/T4 = {comparacao[-1]['speedup_T2_T4']:.3f}")
    colunas = list(dict.fromkeys(k for c in comparacao for k in c))
    with open(RESULTADOS / "comparacao.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, delimiter=";", restval="")
        w.writeheader()
        w.writerows(comparacao)
    (RESULTADOS / "comparacao.json").write_text(json.dumps(comparacao, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
