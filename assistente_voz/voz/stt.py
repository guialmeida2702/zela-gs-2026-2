"""STT: transcrição de fala em português com faster-whisper (Whisper/OpenAI, licença MIT), executado localmente.

Local = sem custo por uso, funciona sem internet depois de baixar o modelo e a voz do cidadão
não sai da máquina (dado pessoal, possivelmente biométrico). O áudio temporário é apagado logo
depois da transcrição.
"""

import os
import shutil
import subprocess
import tempfile
import time
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from scipy.signal import resample_poly

TAXA = 16000
# Dica de vocabulário para o Whisper (initial_prompt): nomes próprios e siglas do domínio que o modelo
# costuma errar ("Sabesp" virava "sabés", "PMSP" virava "PMS Penela"). Comparado com e sem a dica em avaliar_stt.py.
VOCABULARIO = ("Conversa sobre zeladoria urbana em São Paulo: Zela, SP156, Sabesp, PMSP, Enel, CET, Defesa Civil, "
               "subprefeitura, bueiro, semáforo, poda de árvore, calçada, entulho, cata-bagulho.")


def carregar_audio(caminho: str | Path) -> np.ndarray:
    """Lê o áudio como float32 mono 16 kHz. WAV/FLAC/OGG/MP3 pelo libsndfile; outros formatos (m4a do
    celular) pelo ffmpeg, se instalado. Não depende do PyAV, cuja API mudou entre versões."""
    try:
        dados, taxa = sf.read(str(caminho), dtype="float32", always_2d=True)
    except (sf.LibsndfileError, RuntimeError) as exc:
        if not shutil.which("ffmpeg"):
            raise ValueError("Formato de áudio não suportado. Envie WAV, MP3 ou OGG.") from exc
        bruto = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(caminho), "-ac", "1", "-ar", str(TAXA),
                                "-f", "f32le", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(bruto, dtype=np.float32).copy()
    mono = dados.mean(axis=1)
    if taxa != TAXA:
        g = gcd(TAXA, taxa)
        mono = resample_poly(mono, TAXA // g, taxa // g).astype(np.float32)
    return mono


class Transcritor:
    def __init__(self, tamanho: str = "small", threads: int = 2, cache: str | None = None,
                 vocabulario: str | None = VOCABULARIO):
        self.tamanho = tamanho
        self.vocabulario = vocabulario
        self.modelo = WhisperModel(tamanho, device="cpu", compute_type="int8", cpu_threads=threads, download_root=cache)

    def transcrever_arquivo(self, caminho: str | Path) -> dict:
        inicio = time.perf_counter()
        audio = carregar_audio(caminho)
        segmentos, _ = self.modelo.transcribe(audio, language="pt", beam_size=1, vad_filter=True,
                                              condition_on_previous_text=False, initial_prompt=self.vocabulario)
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        return {"texto": texto, "segundos": round(time.perf_counter() - inicio, 2),
                "duracao_audio_s": round(len(audio) / TAXA, 2),
                "modelo": f"faster-whisper-{self.tamanho}" + ("+vocabulario" if self.vocabulario else "")}

    def transcrever_bytes(self, conteudo: bytes, sufixo: str = ".wav") -> dict:
        """Grava em arquivo temporário só durante a transcrição e apaga em seguida (retenção mínima)."""
        fd, caminho = tempfile.mkstemp(suffix=sufixo)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(conteudo)
            return self.transcrever_arquivo(caminho)
        finally:
            Path(caminho).unlink(missing_ok=True)
