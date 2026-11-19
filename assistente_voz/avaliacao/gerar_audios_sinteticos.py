"""Gera áudios SINTÉTICOS das 20 frases do teste de STT (3 vozes Piper, 5 frases com ruído).

Para que serve: validar o script de WER e comparar os modelos de STT antes das gravações reais.
Não substitui as gravações reais exigidas no enunciado (20 áudios de pessoas, 3 vozes ou mais, 5 com ruído):
voz sintética é mais limpa que voz humana, então o WER aqui tende a ser otimista.

Uso:  python avaliacao/gerar_audios_sinteticos.py
"""

import csv
import io
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz.tts import Sintetizador  # noqa: E402

AQUI = Path(__file__).parent
SAIDA = AQUI / "audios_sinteticos"
VOZES = ["faber", "cadu", "edresson"]
SNR_DB = 10.0


def _ruido_rua(n: int, rng: np.random.Generator, taxa: int) -> np.ndarray:
    """Ruído rosa (chiado) + ronco grave de trânsito + buzinas curtas esparsas."""
    branco = rng.standard_normal(n)
    espectro = np.fft.rfft(branco)
    freqs = np.fft.rfftfreq(n, 1 / taxa)
    espectro[1:] /= np.sqrt(freqs[1:])
    rosa = np.fft.irfft(espectro, n)
    t = np.arange(n) / taxa
    ronco = 0.6 * np.sin(2 * np.pi * 70 * t) * (1 + 0.5 * np.sin(2 * np.pi * 0.3 * t))
    buzina = np.zeros(n)
    for inicio in rng.integers(0, max(1, n - taxa // 4), size=2):
        trecho = np.arange(min(taxa // 4, n - inicio))
        buzina[inicio:inicio + len(trecho)] = 0.8 * np.sign(np.sin(2 * np.pi * 420 * trecho / taxa))
    total = rosa / np.std(rosa) + ronco + buzina
    return total / np.std(total)


def _para_16k(wav_bytes: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        taxa = w.getframerate()
        dados = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return resample_poly(dados, 16000, taxa).astype(np.float32)


def _salvar(caminho: Path, sinal: np.ndarray) -> None:
    pcm = (np.clip(sinal, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())


def main() -> None:
    import os
    cache = os.getenv("MODELOS_CACHE_DIR")
    SAIDA.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    vozes = {v: Sintetizador(v, cache=cache) for v in VOZES}
    with open(AQUI / "frases_stt.csv", encoding="utf-8") as f:
        frases = list(csv.DictReader(f, delimiter=";"))
    linhas = []
    for i, fr in enumerate(frases):
        voz = VOZES[i % len(VOZES)]
        wav, _, _ = vozes[voz].sintetizar(fr["frase"])
        sinal = _para_16k(wav)
        sinal = np.concatenate([np.zeros(4000, np.float32), sinal, np.zeros(4000, np.float32)])  # 0,25 s de silêncio
        if fr["condicao"] == "ruido":
            ruido = _ruido_rua(len(sinal), rng, 16000)
            potencia_voz = np.mean(sinal ** 2)
            ruido *= np.sqrt(potencia_voz / (10 ** (SNR_DB / 10)))
            sinal = sinal + ruido
        sinal = 0.9 * sinal / max(1e-6, np.max(np.abs(sinal)))
        nome = f"{fr['id']}_{voz}.wav"
        _salvar(SAIDA / nome, sinal)
        linhas.append({"arquivo": nome, "id": fr["id"], "locutor": f"sintetico-{voz}", "condicao": fr["condicao"]})
    with open(SAIDA / "manifesto.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["arquivo", "id", "locutor", "condicao"], delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} áudios em {SAIDA}")


if __name__ == "__main__":
    main()
