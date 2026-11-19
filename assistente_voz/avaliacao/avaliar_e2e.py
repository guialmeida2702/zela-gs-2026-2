"""Teste ponta a ponta: 10 conversas de 3 turnos (áudio -> STT -> LLM -> adaptação -> TTS), com latência por etapa.

As perguntas são faladas por uma voz sintética diferente da voz do assistente (Piper "cadu"), para o teste
ser reproduzível. Para o vídeo e para o teste com pessoas, use o app (streamlit run app.py) e o microfone.

Uso:  python avaliacao/avaliar_e2e.py --api http://localhost:8000
"""

import argparse
import csv
import io
import json
import os
import statistics
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from avaliacao.normalizar import contem_algum  # noqa: E402
from voz.cerebro import Cerebro  # noqa: E402
from voz.pipeline import AssistenteVoz  # noqa: E402
from voz.stt import Transcritor  # noqa: E402
from voz.tts import Sintetizador  # noqa: E402

AQUI = Path(__file__).parent
RECUSA = ["fora do que eu consigo", "posso ajudar com"]
NAO_SEI = ["nao encontrei"]
CONVERSAS = [
    [("como eu peço a poda de uma árvore na calçada", ["156"]), ("e quanto tempo demora", ["120"]),
     ("e se não fizerem nesse prazo", ["156", "ouvidoria", "nao encontrei"])],
    [("de quem é a responsabilidade de consertar a calçada", ["propriet", "possuidor"]),
     ("e se o dono não arrumar", ["notific", "multa"]), ("qual o valor da multa", ["439", "quatrocentos"])],
    [("o que eu faço se a minha rua alagar", ["atravesse", "contato", "199", "193", "afaste"]),
     ("e depois que a água baixar", ["ferv", "filtr", "limp", "aliment"]), ("posso beber a água da torneira", ["ferv", "filtr"])],
    [("tem um fio caído soltando faísca na calçada", ["enel", "nao se aproxime", "193", "afaste"]),
     ("pra qual número eu ligo", ["0800", "193", "enel"]),
     ("e o zela resolve isso sozinho", ["nao substitui", "193", "emergencia", "nao"])],
    [("tem água limpa vazando no meio da rua", ["sabesp"]), ("qual é o telefone deles", ["0800"]),
     ("eles atendem pelo whatsapp", ["3388", "whatsapp"])],
    [("o semáforo da esquina está quebrado", ["cet"]), ("como eu faço o pedido", ["156", "portal"]),
     ("me indica um restaurante aqui perto", "RECUSA")],
    [("como eu registro um problema no zela", ["cep", "protocolo"]), ("o zela guarda o meu cpf", ["remov"]),
     ("e o prazo que aparece é garantido", ["referencia", "nao sao prazos oficiais", "nao promete"])],
    [("a tampa do bueiro afundou na minha rua", ["pmsp", "sabesp", "156"]), ("está escrito pmsp nela", ["156"]),
     ("e se fosse sabesp", ["sabesp"])],
    [("qual remédio é bom pra dor de cabeça", "RECUSA"), ("e sobre buraco na rua como eu faço", ["156", "zela", "relat"]),
     ("e quanto tempo demora pra tapar", "NAO_SEI")],
    [("tem um carro abandonado na minha rua", ["notifica", "abandon"]), ("depois de quantos dias ele é removido", ["cinco", "5"]),
     ("conta uma piada", "RECUSA")],
]


def _audio_pergunta(tts: Sintetizador, texto: str) -> bytes:
    wav, _, _ = tts.sintetizar(texto)
    with wave.open(io.BytesIO(wav), "rb") as w:
        taxa = w.getframerate()
        dados = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    dados = resample_poly(dados, 16000, taxa).astype(np.int16)
    saida = io.BytesIO()
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(dados.tobytes())
    return saida.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--stt", default="small")
    args = ap.parse_args()
    cache = os.getenv("MODELOS_CACHE_DIR")
    voz_cidadao = Sintetizador("cadu", cache=cache)
    assistente = AssistenteVoz(Transcritor(args.stt, cache=cache), Cerebro(args.api), Sintetizador("faber", cache=cache))
    assistente.tts.sintetizar("Aquecimento.")
    parcial = AQUI / "resultados" / "e2e_parcial.json"
    parcial.parent.mkdir(exist_ok=True)
    # retomada: conversas já concluídas numa execução interrompida não são refeitas
    linhas = json.loads(parcial.read_text(encoding="utf-8")) if parcial.exists() else []
    feitas = {linha["conversa"] for linha in linhas if linha["turno"] == 3}
    linhas = [linha for linha in linhas if linha["conversa"] in feitas]
    for c, conversa in enumerate(CONVERSAS, 1):
        if c in feitas:
            continue
        assistente.memoria.limpar()
        for t, (pergunta, esperado) in enumerate(conversa, 1):
            r = assistente.turno(_audio_pergunta(voz_cidadao, pergunta))
            if esperado == "RECUSA":
                ok, tipo = bool(r["fora_do_escopo"] or contem_algum(r["resposta_texto"], RECUSA)), "recusa"
            elif esperado == "NAO_SEI":
                ok, tipo = bool(r["sem_evidencia"] or contem_algum(r["resposta_texto"], NAO_SEI)), "nao_sei"
            else:
                ok, tipo = (not r["sem_evidencia"]) and contem_algum(r["resposta_texto"], esperado), "resposta"
            lat = r["latencias"]
            linhas.append({"conversa": c, "turno": t, "pergunta_dita": pergunta, "transcricao": r["transcricao"],
                           "resposta_texto": r["resposta_texto"], "resposta_falada": r["resposta_falada"], "tipo_esperado": tipo,
                           "adequada": ok, "bloqueios": ", ".join(r.get("bloqueios") or []) or (r.get("erro") or ""), **lat,
                           "duracao_resposta_s": r["duracao_resposta_s"]})
            parcial.write_text(json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
            print(f"C{c}T{t} {'OK ' if ok else 'ERR'} stt {lat['stt_s']}s llm {lat['llm_s']}s tts {lat['tts_s']}s "
                  f"total {lat['ate_inicio_da_fala_s']}s | {r['transcricao']} -> {r['resposta_texto'][:90]}")

    def estat(chave: str) -> dict:
        v = [linha[chave] for linha in linhas]
        return {"media": round(statistics.mean(v), 2), "mediana": round(statistics.median(v), 2),
                "p90": round(sorted(v)[int(0.9 * (len(v) - 1))], 2), "max": round(max(v), 2)}

    resumo = {"conversas": len(CONVERSAS), "turnos": len(linhas),
              "pct_turnos_adequados": round(100 * sum(linha["adequada"] for linha in linhas) / len(linhas), 1),
              "latencia_s": {k: estat(k) for k in ("stt_s", "llm_s", "adaptacao_s", "tts_s", "ate_inicio_da_fala_s")},
              "modelos": {"stt": f"faster-whisper-{args.stt}", "tts": assistente.tts.voz_nome}}
    saida = AQUI / "resultados"
    saida.mkdir(exist_ok=True)
    with open(saida / "e2e_10_conversas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    (saida / "e2e_10_conversas.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    parcial.unlink(missing_ok=True)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
