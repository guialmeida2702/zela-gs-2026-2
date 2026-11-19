"""Estado centralizado da sessão (st.session_state).

Toda leitura/escrita de estado passa por aqui, com nomes explícitos, para que
as telas (features/) não espalhem chaves mágicas pelo código.
"""

import copy
from datetime import UTC, datetime
from typing import Any

import streamlit as st

_PADROES: dict[str, Any] = {
    # jornada do cidadão
    "etapa": "relatar",            # relatar -> revisar -> concluido
    "relato": None,                # último relato enviado (dict) — mantém o texto se der erro
    "analise": None,               # resposta da IA aguardando revisão humana
    "ultimo_registro": None,       # solicitação recém-criada (para a tela de sucesso)
    "historico": [],               # solicitações registradas nesta sessão (alimenta lista e gráficos)
    "analises_feitas": 0,          # quantas análises a IA fez nesta sessão
    "versao_form": 0,              # muda para limpar o formulário
    "feedbacks": {},               # protocolo -> bool (avaliação já enviada)
    "foto_analise": None,          # resultado da visão computacional + foto marcada (só nesta sessão)
    "conversa": [],                # mensagens do Assistente Zela (cidadão e assistente)
    # gestor
    "token_gestor": None,
    "usuario_gestor": None,
    "token_expira": None,
    # acessibilidade
    "alto_contraste": False,
    "tamanho_fonte": "Padrão",
}


def iniciar() -> None:
    for chave, valor in _PADROES.items():
        if chave not in st.session_state:
            st.session_state[chave] = copy.deepcopy(valor)


def obter(chave: str) -> Any:
    return st.session_state.get(chave, _PADROES.get(chave))


# ---------------- jornada do cidadão ----------------
def etapa() -> str:
    return st.session_state.etapa


def guardar_relato(relato: dict) -> None:
    st.session_state.relato = relato


def receber_analise(analise: dict) -> None:
    st.session_state.analise = analise
    st.session_state.etapa = "revisar"
    st.session_state.analises_feitas += 1


def descartar_analise() -> None:
    """Volta ao formulário mantendo o texto para o cidadão editar."""
    st.session_state.analise = None
    st.session_state.etapa = "relatar"


def concluir_registro(solicitacao: dict) -> None:
    st.session_state.ultimo_registro = solicitacao
    st.session_state.etapa = "concluido"
    adicionar_ao_historico(solicitacao)


def novo_relato() -> None:
    st.session_state.analise = None
    st.session_state.relato = None
    st.session_state.ultimo_registro = None
    st.session_state.foto_analise = None
    st.session_state.etapa = "relatar"
    st.session_state.versao_form += 1


def guardar_foto_analise(resultado: dict | None, sobreposicao: bytes | None = None) -> None:
    st.session_state.foto_analise = {"resultado": resultado, "imagem": sobreposicao} if resultado else None


# ---------------- assistente ----------------
def conversa() -> list[dict]:
    return st.session_state.conversa


def adicionar_mensagem(papel: str, texto: str, resposta: dict | None = None) -> None:
    st.session_state.conversa.append({"papel": papel, "texto": texto, "resposta": resposta})


def limpar_conversa() -> None:
    st.session_state.conversa = []


# ---------------- histórico ----------------
def historico() -> list[dict]:
    return st.session_state.historico


def adicionar_ao_historico(solicitacao: dict) -> None:
    hist = [s for s in st.session_state.historico if s["protocolo"] != solicitacao["protocolo"]]
    st.session_state.historico = [solicitacao, *hist]


def atualizar_no_historico(solicitacao: dict) -> None:
    st.session_state.historico = [
        solicitacao if s["protocolo"] == solicitacao["protocolo"] else s for s in st.session_state.historico
    ]


# ---------------- gestor ----------------
def entrar_gestor(token: str, usuario: str, expira_em: str) -> None:
    st.session_state.token_gestor = token
    st.session_state.usuario_gestor = usuario
    st.session_state.token_expira = expira_em


def sair_gestor() -> None:
    st.session_state.token_gestor = None
    st.session_state.usuario_gestor = None
    st.session_state.token_expira = None


def token_gestor() -> str | None:
    token, expira = st.session_state.token_gestor, st.session_state.token_expira
    if not token or not expira:
        return None
    try:
        if datetime.fromisoformat(str(expira).replace("Z", "+00:00")) <= datetime.now(UTC):
            sair_gestor()
            return None
    except ValueError:
        return None
    return token


# ---------------- feedback do cidadão ----------------
def feedback_enviado(protocolo: str) -> bool | None:
    return st.session_state.feedbacks.get(protocolo)


def marcar_feedback(protocolo: str, util: bool) -> None:
    st.session_state.feedbacks = {**st.session_state.feedbacks, protocolo: util}
