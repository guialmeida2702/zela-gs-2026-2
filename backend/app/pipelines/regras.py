"""Regras determinísticas de segurança aplicadas DEPOIS do LLM.

Princípio: as regras só podem ELEVAR a urgência, nunca reduzir. Elas existem
para cobrir falhas do modelo em situações de risco (falso negativo é o erro
mais caro numa triagem). Cada ajuste vem com uma explicação para o cidadão.
"""

import re
import unicodedata

from app.pipelines.catalogo import CONTATOS_EMERGENCIA
from app.schemas.analise import AnaliseIA, Clima
from app.schemas.comum import Categoria, Urgencia

LIMIAR_CHUVA_MM_72H = 30.0
CATEGORIAS_SENSIVEIS_A_CHUVA = {Categoria.ALAGAMENTO, Categoria.ARVORE, Categoria.AGUA_ESGOTO}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


# Padrões aplicados sobre o texto normalizado (sem acentos, minúsculo)
_RISCO_IMEDIATO = [
    (re.compile(r"\bfios?\b.{0,30}\b(caid[oa]s?|partid[oa]s?|solt[oa]s?|arrebentad[oa]s?|no chao|soltando faisca)"), "fio elétrico caído ou solto"),
    (re.compile(r"\b(choque eletrico|levou choque|faisca|faiscando|soltando faisca)"), "risco de choque elétrico"),
    (re.compile(r"\b(desab(ou|ando|amento)|desmoron(ou|ando|amento)|deslizamento|barranco cedendo)"), "risco de desabamento ou deslizamento"),
    (
        re.compile(r"\barvore\b.{0,40}\b(caindo|vai cair|cai[ur] em cima|sobre (a|uma) casa|sobre (o|um) carro|tombando)"),
        "árvore com risco de queda sobre pessoas ou imóveis",
    ),
    (re.compile(r"\b(ilhad[oa]s?|correnteza|arrastad[oa]|agua (na|ate a) cintura|carro boiando)"), "pessoas ou veículos em área alagada"),
    (re.compile(r"\b(incendio|pegando fogo|em chamas)"), "fogo no local"),
    (re.compile(r"\b(ferid[oa]s?|machucad[oa]s?|atropelad[oa]s?|inconsciente)\b"), "pessoa ferida"),
    (re.compile(r"\bposte\b.{0,30}\b(caindo|tombando|vai cair|caiu)"), "poste com risco de queda"),
]

_ATENCAO = [
    (re.compile(r"\b(escola|creche|hospital|posto de saude|ubs)\b"), "fica perto de escola, creche ou unidade de saúde"),
    (re.compile(r"\b(cadeirante|cadeira de rodas|idos[oa]s?|deficiente visual|cego|muleta)"), "afeta pessoas com mobilidade reduzida"),
    (
        re.compile(
            r"\b(quase (caiu|bateu|foi atropelad[oa])|acidentes?|"
            r"(alguem|gente|pessoa|crianca|idos[oa]|moto|motoqueiro|motociclista|ciclista) (ja )?caiu)\b"
        ),
        "já causou acidente ou quase acidente",
    ),
    (re.compile(r"\bbueiro\b.{0,25}\b(sem tampa|aberto|destampado)"), "é um bueiro aberto, com risco de queda"),
    (re.compile(r"\bcratera\b"), "é uma cratera na via"),
]


# Perguntas ao assistente sobre situações em andamento ("tá alagando aqui") também contam como menção de risco
_RISCO_EM_PERGUNTA = re.compile(r"\b(alagando|alagou|esta alagad[oa]|enchente|inundacao|agua subindo|cheiro de gas)\b")


_SOBRE_ANTES_OU_DEPOIS = re.compile(r"\b(depois|apos|antes|prevenir|preparar)\b")


def menciona_risco(texto: str) -> bool:
    """A pergunta descreve um risco que está acontecendo? Perguntas sobre o antes ou o depois de uma enchente
    ("o que fazer depois de uma inundação?") não são emergência, a menos que tragam um sinal de risco imediato."""
    t = _normalizar(texto)
    if any(padrao.search(t) for padrao, _ in _RISCO_IMEDIATO):
        return True
    return bool(_RISCO_EM_PERGUNTA.search(t)) and not _SOBRE_ANTES_OU_DEPOIS.search(t)


def _elevar(urgencia: Urgencia, minimo: Urgencia) -> Urgencia:
    return urgencia if urgencia.nivel >= minimo.nivel else minimo


def aplicar_regras(
    analise: AnaliseIA, texto_relato: str, clima: Clima | None
) -> tuple[AnaliseIA, list[str]]:
    """Retorna (análise ajustada, lista de explicações dos ajustes)."""
    texto = _normalizar(texto_relato)
    ajustes: list[str] = []
    dados = analise.model_dump()
    urgencia = analise.urgencia

    # 1) Risco imediato detectado no texto
    motivos_risco = [motivo for padrao, motivo in _RISCO_IMEDIATO if padrao.search(texto)]
    if motivos_risco and not analise.fora_do_escopo:
        if not analise.risco_imediato or urgencia != Urgencia.CRITICA:
            ajustes.append(
                "Por segurança, marcamos como risco imediato porque o relato menciona: "
                + "; ".join(motivos_risco) + "."
            )
        dados["risco_imediato"] = True
        urgencia = Urgencia.CRITICA

    # 2) Se a IA já indicou risco imediato, a urgência tem que ser crítica
    if dados["risco_imediato"] and urgencia != Urgencia.CRITICA:
        ajustes.append("Situações com risco imediato são sempre tratadas como urgência crítica.")
        urgencia = Urgencia.CRITICA

    # 3) Fatores de atenção (vulneráveis, histórico de acidente) => no mínimo "alta"
    motivos_atencao = [motivo for padrao, motivo in _ATENCAO if padrao.search(texto)]
    if motivos_atencao and not analise.fora_do_escopo and urgencia.nivel < Urgencia.ALTA.nivel:
        ajustes.append("A prioridade subiu para alta porque o problema " + "; ".join(motivos_atencao) + ".")
        urgencia = _elevar(urgencia, Urgencia.ALTA)

    # 4) Cruzamento com previsão do tempo (dado aberto Open-Meteo)
    if (
        clima
        and clima.chuva_prevista_mm_72h >= LIMIAR_CHUVA_MM_72H
        and analise.categoria in CATEGORIAS_SENSIVEIS_A_CHUVA
        and urgencia.nivel < Urgencia.CRITICA.nivel
    ):
        nova = Urgencia.de_nivel(urgencia.nivel + 1)
        ajustes.append(
            f"A previsão indica cerca de {clima.chuva_prevista_mm_72h:.0f} mm de chuva nos próximos 3 dias, "
            f"o que pode agravar este problema. A prioridade passou de {urgencia.value} para {nova.value}."
        )
        urgencia = nova

    dados["urgencia"] = urgencia

    # 5) Em risco imediato, a primeira orientação é sempre de segurança
    if dados["risco_imediato"]:
        aviso = "Afaste-se do local e mantenha outras pessoas longe. Em perigo, ligue " + ", ".join(CONTATOS_EMERGENCIA) + "."
        orientacoes = [o for o in dados["orientacoes"] if "afaste" not in _normalizar(o)]
        dados["orientacoes"] = [aviso[:220], *orientacoes][:4]

    return AnaliseIA.model_validate(dados), ajustes
