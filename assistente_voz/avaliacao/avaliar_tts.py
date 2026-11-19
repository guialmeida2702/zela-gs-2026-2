"""Teste de TTS: gera 10 respostas faladas em duas vozes Piper, mede latência e prepara a planilha de notas.

Passo 1 (gera áudios e planilha em branco):  python avaliacao/avaliar_tts.py
Passo 2 (pelo menos 3 pessoas ouvem e dão notas de 1 a 5 em naturalidade e clareza na planilha)
Passo 3 (resume as notas):                   python avaliacao/avaliar_tts.py --resumir
"""

import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz.fala import adaptar_para_fala  # noqa: E402

AQUI = Path(__file__).parent
PASTA = AQUI / "amostras_tts"
PLANILHA = AQUI / "resultados" / "notas_tts.csv"
VOZES = ["faber", "cadu"]
AVALIADORES = ["Avaliador 1", "Avaliador 2", "Avaliador 3"]

# Respostas típicas do assistente (texto original, antes da adaptação para fala)
RESPOSTAS = [
    "Você pode pedir a vistoria da árvore pelo telefone 156, pelo portal SP156 ou na Praça de Atendimento da Subprefeitura [1].",
    "Depois da abertura do chamado, a Subprefeitura tem até 120 dias para realizar a poda [1].",
    "A manutenção da calçada é responsabilidade do proprietário ou possuidor do imóvel [1].",
    "O valor da multa para passeio em má conservação é de R$ 439,66 por metro linear [1].",
    "Não se aproxime do fio. Ligue para a Enel São Paulo no 0800 72 72 196 e, se houver risco, para os Bombeiros no 193 [1].",
    "Não atravesse áreas alagadas e evite contato com a água. Se precisar de ajuda, ligue 199 para a Defesa Civil [1].",
    "Vazamentos de água são atendidos pela Sabesp, no 0800 055 0195 ou pelo WhatsApp (11) 3388-8000 [1].",
    "Semáforos, faixas de pedestre e placas de trânsito são de responsabilidade da CET [1].",
    "Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 156).",
    "Posso ajudar com problemas de zeladoria urbana. Para dúvidas de saúde, procure um profissional da área.",
]


def gerar() -> None:
    from voz.tts import Sintetizador
    PASTA.mkdir(exist_ok=True)
    PLANILHA.parent.mkdir(exist_ok=True)
    cache = os.getenv("MODELOS_CACHE_DIR")
    medicoes = []
    for voz in VOZES:
        tts = Sintetizador(voz, cache=cache)
        tts.sintetizar("Aquecimento.")  # a primeira chamada inclui inicialização
        for i, texto in enumerate(RESPOSTAS, 1):
            fala = adaptar_para_fala(texto)
            wav, seg, dur = tts.sintetizar(fala)
            nome = f"R{i:02d}_{voz}.wav"
            (PASTA / nome).write_bytes(wav)
            medicoes.append({"amostra": f"R{i:02d}", "voz": voz, "texto_falado": fala, "sintese_s": seg, "duracao_s": dur,
                             "fator_tempo_real": round(seg / dur, 3)})
            print(f"{nome}: {seg}s para {dur}s de áudio | {fala}")
    with open(AQUI / "resultados" / "tts_latencia.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(medicoes[0]), delimiter=";")
        w.writeheader()
        w.writerows(medicoes)
    resumo = {v: {"sintese_media_s": round(statistics.mean(m["sintese_s"] for m in medicoes if m["voz"] == v), 3),
                  "fator_tempo_real_medio": round(statistics.mean(m["fator_tempo_real"] for m in medicoes if m["voz"] == v), 3)}
              for v in VOZES}
    (AQUI / "resultados" / "tts_latencia.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    if not PLANILHA.exists():
        with open(PLANILHA, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["avaliador", "amostra", "voz", "arquivo", "naturalidade_1a5", "clareza_1a5", "comentario"])
            for av in AVALIADORES:
                for i in range(1, len(RESPOSTAS) + 1):
                    for voz in VOZES:
                        w.writerow([av, f"R{i:02d}", voz, f"amostras_tts/R{i:02d}_{voz}.wav", "", "", ""])
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


def _notas_do_xlsx() -> list[dict]:
    """Notas preenchidas na aba TTS de planilha_avaliacao.xlsx (alternativa ao CSV)."""
    xlsx = AQUI / "planilha_avaliacao.xlsx"
    if not xlsx.exists():
        return []
    from openpyxl import load_workbook
    ws = load_workbook(xlsx, read_only=True)["TTS"]
    linhas = list(ws.iter_rows(min_row=2, max_col=8, values_only=True))
    return [{"avaliador": av, "amostra": am, "voz": voz, "naturalidade_1a5": nat, "clareza_1a5": cla}
            for av, am, voz, _arq, _txt, nat, cla, _com in linhas if nat and cla]


def resumir() -> None:
    with open(PLANILHA, encoding="utf-8") as f:
        notas = [r for r in csv.DictReader(f, delimiter=";") if r["naturalidade_1a5"] and r["clareza_1a5"]]
    notas = notas or _notas_do_xlsx()
    if not notas:
        print("Ainda não há notas em resultados/notas_tts.csv nem na aba TTS de planilha_avaliacao.xlsx.")
        return
    resumo = {}
    for voz in VOZES:
        sel = [r for r in notas if r["voz"] == voz]
        if sel:
            resumo[voz] = {"avaliadores": len({r["avaliador"] for r in sel}), "notas": len(sel),
                           "naturalidade_media": round(statistics.mean(float(r["naturalidade_1a5"]) for r in sel), 2),
                           "clareza_media": round(statistics.mean(float(r["clareza_1a5"]) for r in sel), 2)}
    (AQUI / "resultados" / "tts_notas_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumir", action="store_true")
    resumir() if ap.parse_args().resumir else gerar()
