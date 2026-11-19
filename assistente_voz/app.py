"""Assistente de voz do Zela (PLN): fale com o serviço de zeladoria e ouça a resposta.

Executar:  streamlit run app.py   (com a API do Zela rodando; veja README.md)
"""

import os

import streamlit as st
from voz.cerebro import Cerebro
from voz.pipeline import AssistenteVoz
from voz.stt import Transcritor
from voz.tts import Sintetizador

API_URL = os.getenv("ZELA_API_URL", "http://localhost:8000")
MODELO_STT = os.getenv("STT_MODELO", "small")
VOZ_TTS = os.getenv("TTS_VOZ", "faber")
CACHE = os.getenv("MODELOS_CACHE_DIR") or None

st.set_page_config(page_title="Zela por voz", page_icon="🎙️", layout="centered")


@st.cache_resource(show_spinner="Carregando modelos de fala (só na primeira vez)...")
def _modelos(stt: str, voz: str):
    return Transcritor(stt, cache=CACHE), Sintetizador(voz, cache=CACHE)


def _assistente() -> AssistenteVoz:
    if "assistente_voz" not in st.session_state:
        transcritor, sintetizador = _modelos(MODELO_STT, VOZ_TTS)
        st.session_state.assistente_voz = AssistenteVoz(transcritor, Cerebro(API_URL), sintetizador)
        st.session_state.turnos = []
    return st.session_state.assistente_voz


st.title("🎙️ Zela por voz")
st.caption("Tire dúvidas sobre zeladoria urbana de São Paulo falando. As respostas vêm de páginas oficiais da Prefeitura.")

if not st.session_state.get("consentimento"):
    st.markdown(
        "**Antes de começar**\n\n"
        "- Sua voz é gravada só para ser transcrita aqui mesmo, neste computador. O áudio é apagado logo depois da transcrição.\n"
        "- O texto da conversa fica na memória só enquanto esta página estiver aberta.\n"
        "- A voz que responde é sintética. Ninguém teve a voz copiada.\n"
        "- Não diga CPF, telefone ou endereço completo. Se disser, o sistema remove antes de guardar o histórico.\n"
        "- O assistente não substitui atendimento de emergência: em risco, ligue 193 (Bombeiros) ou 199 (Defesa Civil)."
    )
    if st.button("Entendi e concordo", type="primary"):
        st.session_state.consentimento = True
        st.rerun()
    st.stop()

assistente = _assistente()

with st.sidebar:
    st.subheader("Configuração")
    st.write(f"STT: faster-whisper `{MODELO_STT}` · TTS: Piper `{VOZ_TTS}` · API: `{API_URL}`")
    if st.button("Nova conversa"):
        assistente.memoria.limpar()
        st.session_state.turnos = []
        st.rerun()

for turno in st.session_state.turnos:
    with st.chat_message("user", avatar="🧑"):
        st.write(turno["transcricao"] or "(não entendi o áudio)")
    with st.chat_message("assistant", avatar="🏙️"):
        st.write(turno["resposta_texto"])
        if turno["fontes"]:
            st.caption("Fontes: " + ", ".join(dict.fromkeys(turno["fontes"])))
        lat = turno["latencias"]
        st.caption(f"⏱ fala→texto {lat['stt_s']} s · resposta {lat['llm_s']} s · voz {lat['tts_s']} s · "
                   f"**até começar a falar {lat['ate_inicio_da_fala_s']} s**")

st.divider()
modo = st.radio("Como quer perguntar?", ["Falar no microfone", "Enviar arquivo de áudio"], horizontal=True,
                key="modo_entrada")
if modo == "Falar no microfone":
    audio = st.audio_input("Aperte, fale sua pergunta e aperte de novo para enviar", key=f"mic_{len(st.session_state.turnos)}")
    conteudo, sufixo = (audio.getvalue(), ".wav") if audio else (None, None)
else:
    arquivo = st.file_uploader("Áudio (wav, mp3, m4a, ogg)", type=["wav", "mp3", "m4a", "ogg"],
                               key=f"up_{len(st.session_state.turnos)}")
    conteudo, sufixo = (arquivo.getvalue(), "." + arquivo.name.rsplit(".", 1)[-1]) if arquivo else (None, None)

if conteudo:
    with st.spinner("Ouvindo e preparando a resposta..."):
        resultado = assistente.turno(conteudo, sufixo)
    del conteudo  # não guardamos o áudio do cidadão
    st.session_state.turnos.append({k: v for k, v in resultado.items() if k != "audio"})
    st.session_state.ultimo_audio = resultado["audio"]
    st.rerun()

if st.session_state.get("ultimo_audio"):
    st.audio(st.session_state.ultimo_audio, format="audio/wav", autoplay=True)
