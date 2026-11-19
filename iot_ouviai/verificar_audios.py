"""Confere (e, se pedido, converte) as gravações do OuviAí antes do envio ao Edge Impulse.

Regras do enunciado: WAV PCM 16 bits, mono, 16 kHz, cerca de 5 s, pelo menos 20 por classe (15 Training + 5 Test).
Nomeie os arquivos como <classe>_<nn>.wav (ex.: campainha_01.wav) dentro de uma pasta.

Uso:
  python verificar_audios.py gravacoes/              # só confere
  python verificar_audios.py gravacoes/ --converter  # converte para gravacoes_16k/ (precisa do ffmpeg)
"""

import argparse
import shutil
import subprocess
import sys
import wave
from collections import Counter
from pathlib import Path

CLASSES = ("campainha", "batida_porta", "ambiente")


def conferir(arquivo: Path) -> list[str]:
    problemas = []
    try:
        with wave.open(str(arquivo), "rb") as w:
            if w.getnchannels() != 1:
                problemas.append(f"{w.getnchannels()} canais (precisa ser mono)")
            if w.getframerate() != 16000:
                problemas.append(f"{w.getframerate()} Hz (precisa ser 16000)")
            if w.getsampwidth() != 2:
                problemas.append(f"{8 * w.getsampwidth()} bits (precisa ser 16)")
            duracao = w.getnframes() / w.getframerate()
            if not 4.5 <= duracao <= 5.5:
                problemas.append(f"{duracao:.1f} s (o combinado é cerca de 5 s)")
    except (wave.Error, EOFError) as exc:
        problemas.append(f"não é WAV PCM válido ({exc})")
    return problemas


def converter(origem: Path, destino: Path) -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg não encontrado. Instale (https://ffmpeg.org) ou grave direto pelo Edge Impulse no celular.")
    destino.mkdir(exist_ok=True)
    for arq in sorted(origem.iterdir()):
        if arq.suffix.lower() in (".wav", ".m4a", ".mp3", ".ogg", ".aac", ".3gp"):
            saida = destino / (arq.stem + ".wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(arq), "-ac", "1", "-ar", "16000",
                            "-sample_fmt", "s16", "-t", "5", str(saida)], check=True)
    print(f"Convertidos para {destino}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--converter", action="store_true")
    a = ap.parse_args()
    pasta = Path(a.pasta)
    if a.converter:
        destino = pasta.parent / (pasta.name + "_16k")
        converter(pasta, destino)
        pasta = destino
    contagem, ruins = Counter(), 0
    for arq in sorted(pasta.glob("*.wav")):
        classe = next((c for c in CLASSES if arq.stem.startswith(c)), None)
        problemas = conferir(arq) + ([] if classe else ["nome não começa com uma classe conhecida"])
        contagem[classe] += 1
        if problemas:
            ruins += 1
            print(f"✗ {arq.name}: " + "; ".join(problemas))
    for c in CLASSES:
        print(f"{c:<13} {contagem[c]:>3} arquivos " + ("✓" if contagem[c] >= 20 else "✗ faltam " + str(20 - contagem[c])))
    print("Tudo certo para enviar." if ruins == 0 and all(contagem[c] >= 20 for c in CLASSES) else "Corrija os itens acima.")


if __name__ == "__main__":
    main()
