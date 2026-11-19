"""Um turno de conversa por voz: microfone -> STT -> LLM (Assistente Zela) -> adaptação -> TTS -> alto-falante.

Cada etapa é um módulo trocável (stt.py, cerebro.py, fala.py, tts.py). A latência de cada etapa é medida;
"ate_inicio_da_fala" = do fim da gravação até o áudio de resposta ficar pronto para tocar.
"""

import re
import time

from voz.cerebro import Cerebro, Memoria
from voz.fala import adaptar_para_fala
from voz.stt import Transcritor
from voz.tts import Sintetizador

_DADO_PESSOAL = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b[\w.+-]+@[\w-]+\.[\w.]+\b")


class AssistenteVoz:
    def __init__(self, transcritor: Transcritor, cerebro: Cerebro, sintetizador: Sintetizador):
        self.stt, self.cerebro, self.tts = transcritor, cerebro, sintetizador
        self.memoria = Memoria()

    def turno(self, audio: bytes, sufixo: str = ".wav") -> dict:
        t0 = time.perf_counter()
        trans = self.stt.transcrever_bytes(audio, sufixo)  # o áudio é apagado aqui
        pergunta = trans["texto"]
        if len(pergunta) < 3:
            resposta = {"resposta": "Não consegui entender. Pode repetir, falando um pouco mais perto do microfone?",
                        "fontes": [], "segundos": 0.0, "sem_evidencia": True, "fora_do_escopo": False}
        else:
            resposta = self.cerebro.responder(pergunta, self.memoria)
        t1 = time.perf_counter()
        fala = adaptar_para_fala(resposta["resposta"])
        t2 = time.perf_counter()
        audio_resposta, seg_tts, duracao = self.tts.sintetizar(fala)
        t3 = time.perf_counter()
        if len(pergunta) >= 3:
            self.memoria.adicionar("cidadao", _DADO_PESSOAL.sub("[dado removido]", pergunta))
            self.memoria.adicionar("assistente", resposta["resposta"])
        return {
            "transcricao": pergunta, "resposta_texto": resposta["resposta"], "resposta_falada": fala,
            "fontes": resposta.get("fontes", []), "sem_evidencia": resposta.get("sem_evidencia"),
            "fora_do_escopo": resposta.get("fora_do_escopo"), "bloqueios": resposta.get("bloqueios", []),
            "erro": resposta.get("erro"), "audio": audio_resposta, "duracao_resposta_s": duracao,
            "latencias": {"stt_s": trans["segundos"], "llm_s": resposta.get("segundos", round(t1 - t0 - trans["segundos"], 2)),
                          "adaptacao_s": round(t2 - t1, 3), "tts_s": seg_tts,
                          "ate_inicio_da_fala_s": round(t3 - t0, 2)},
            "modelos": {"stt": trans["modelo"], "llm": resposta.get("modelo"), "tts": self.tts.voz_nome},
        }
