"""Avaliação da IA: roda os casos de teste contra a API e gera a tabela para o README.

Uso (com a API rodando e LLM_API_KEY configurada):
    python scripts/avaliar_ia.py --api http://localhost:8000 --saida ../docs/avaliacao_ia.md

A tabela resultante traz: entrada, saída esperada, saída obtida e resultado.
A coluna "Ajuste realizado" deve ser preenchida pelo autor após analisar as falhas
(ex.: mudança no prompt, nova regra de segurança) — e então o script é rodado de novo.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

AQUI = Path(__file__).parent


def avaliar(caso: dict, resposta: dict) -> tuple[bool, list[str]]:
    esp = caso["esperado"]
    an = resposta["analise"]
    falhas = []
    if an["categoria"] != esp["categoria"]:
        falhas.append(f"categoria {an['categoria']} ≠ {esp['categoria']}")
    if an["urgencia"] not in esp["urgencias_aceitas"]:
        falhas.append(f"urgência {an['urgencia']} ∉ {esp['urgencias_aceitas']}")
    if an["risco_imediato"] != esp["risco_imediato"]:
        falhas.append(f"risco_imediato={an['risco_imediato']}")
    if "fora_do_escopo" in esp and an["fora_do_escopo"] != esp["fora_do_escopo"]:
        falhas.append(f"fora_do_escopo={an['fora_do_escopo']}")
    if "dado_pessoal_removido" in esp and esp["dado_pessoal_removido"] not in resposta["dados_pessoais_removidos"]:
        falhas.append(f"{esp['dado_pessoal_removido']} não foi anonimizado")
    if "confianca_maxima" in esp and an["confianca"] > esp["confianca_maxima"]:
        falhas.append(f"confiança {an['confianca']} > {esp['confianca_maxima']}")
    return not falhas, falhas


def _curto(texto: str, n: int = 90) -> str:
    texto = texto.replace("|", "/")
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--casos", default=str(AQUI / "casos_avaliacao.json"))
    parser.add_argument("--saida", default=str(AQUI.parent.parent / "docs" / "avaliacao_ia.md"))
    args = parser.parse_args()

    casos = json.loads(Path(args.casos).read_text(encoding="utf-8"))
    with httpx.Client(base_url=args.api, timeout=400) as cliente:
        saude = cliente.get("/health").json()
        if saude["ia"].get("simulada"):
            print("ATENÇÃO: a API está em modo SIMULADO (LLM_PROVIDER=mock). A avaliação deve usar o LLM real.")
        linhas, acertos, latencias = [], 0, []
        for caso in casos:
            corpo = {"descricao": caso["descricao"], "cep": caso["cep"]}
            inicio = time.perf_counter()
            r = cliente.post("/relatos/analisar", json=corpo)
            latencias.append(time.perf_counter() - inicio)
            esp = caso["esperado"]
            esperado_txt = f"{esp['categoria']} / {' ou '.join(esp['urgencias_aceitas'])}" + (" / risco" if esp["risco_imediato"] else "")
            if r.status_code != 200:
                obtido_txt, ok, falhas = f"ERRO HTTP {r.status_code}: {r.json().get('erro', {}).get('codigo')}", False, ["erro"]
            else:
                dados = r.json()
                an = dados["analise"]
                ok, falhas = avaliar(caso, dados)
                obtido_txt = f"{an['categoria']} / {an['urgencia']}" + (" / risco" if an["risco_imediato"] else "")
                obtido_txt += f" (conf. {an['confianca']:.2f}"
                if dados["urgencia_sugerida_pela_ia"] != an["urgencia"]:
                    obtido_txt += f"; IA sugeriu {dados['urgencia_sugerida_pela_ia']}, regra elevou"
                obtido_txt += ")"
            acertos += ok
            resultado = "✅ OK" if ok else "❌ " + "; ".join(falhas)
            entrada = f"{_curto(caso['objetivo'], 50)}: “{_curto(caso['descricao'])}”"
            linhas.append(f"| {caso['id']} | {entrada} | {esperado_txt} | {obtido_txt} | {resultado} | |")
            print(f"[{caso['id']:>2}] {'OK ' if ok else 'FALHA'} {obtido_txt}")
            time.sleep(1.2)  # respeita limites de taxa de planos gratuitos

    total = len(casos)
    cabecalho = [
        "# Avaliação da IA — casos de teste",
        "",
        f"- Gerado em: {datetime.now():%d/%m/%Y %H:%M}",
        f"- Provedor/modelo: `{saude['ia']['provedor']}` / `{saude['ia']['modelo']}`",
        f"- Acertos: **{acertos}/{total}** ({100 * acertos / total:.0f}%) · latência média: {sum(latencias) / total:.1f}s",
        "",
        "| # | Entrada | Saída esperada | Saída obtida | Resultado | Ajuste realizado |",
        "|---|---|---|---|---|---|",
    ]
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text("\n".join(cabecalho + linhas) + "\n", encoding="utf-8")
    print(f"\n{acertos}/{total} casos OK. Tabela salva em {args.saida}")
    return 0 if acertos == total else 1


if __name__ == "__main__":
    sys.exit(main())
