"""TTS: síntese de voz em português do Brasil com Piper (vozes sintéticas prontas, execução local).

Não há clonagem de voz: são usadas apenas vozes publicadas no repositório rhasspy/piper-voices.
"""

import io
import time
import wave
from pathlib import Path

from huggingface_hub import hf_hub_download
from piper import PiperVoice

VOZES = {
    "faber": "pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
    "cadu": "pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx",
    "edresson": "pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx",
}


class Sintetizador:
    def __init__(self, voz: str = "faber", cache: str | None = None):
        caminho = VOZES[voz]
        modelo = hf_hub_download("rhasspy/piper-voices", caminho, cache_dir=cache)
        config = hf_hub_download("rhasspy/piper-voices", caminho + ".json", cache_dir=cache)
        self.voz_nome = f"piper-{Path(caminho).stem}"
        self.voz = PiperVoice.load(modelo, config_path=config)

    def sintetizar(self, texto: str) -> tuple[bytes, float, float]:
        """Devolve (wav, segundos de processamento, duração do áudio em segundos)."""
        inicio = time.perf_counter()
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            self.voz.synthesize_wav(texto, wav)
        dados = buffer.getvalue()
        with wave.open(io.BytesIO(dados), "rb") as w:
            duracao = w.getnframes() / w.getframerate()
        return dados, round(time.perf_counter() - inicio, 2), round(duracao, 2)
