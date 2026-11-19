"""Provedor SIMULADO, baseado em palavras-chave.

Serve para (1) testes automatizados sem custo e sem rede e (2) demonstração
offline quando não há chave de API. A interface exibe um aviso claro quando
este modo está ativo — ele NÃO substitui o LLM na solução real.
"""

import asyncio
import unicodedata

from app.pipelines.catalogo import CATEGORIAS
from app.providers.llm.base import M
from app.schemas.analise import AnaliseIA
from app.schemas.comum import Categoria, Urgencia

_PALAVRAS: list[tuple[Categoria, tuple[str, ...], Urgencia]] = [
    (Categoria.FIACAO, ("fio", "fiacao", "poste de energia", "transformador", "faisca"), Urgencia.ALTA),
    (Categoria.ALAGAMENTO, ("alag", "bueiro", "boca de lobo", "enchente", "inund", "corrego"), Urgencia.ALTA),
    (Categoria.ARVORE, ("arvore", "galho", "poda", "tronco"), Urgencia.MEDIA),
    (Categoria.AGUA_ESGOTO, ("vazamento", "esgoto", "cano", "agua jorrando", "falta d'agua", "falta de agua"), Urgencia.MEDIA),
    (Categoria.ILUMINACAO, ("lampada", "iluminacao", "poste apagado", "luz do poste", "rua escura", "apagad"), Urgencia.MEDIA),
    (Categoria.SINALIZACAO, ("semaforo", "farol", "placa", "faixa de pedestre", "sinalizacao"), Urgencia.ALTA),
    (Categoria.ESTRUTURA, ("fissura", "rachadura", "trinca", "viaduto", "muro rachado"), Urgencia.MEDIA),
    (Categoria.BURACO_VIA, ("buraco", "asfalto", "cratera", "pavimento"), Urgencia.MEDIA),
    (Categoria.CALCADA, ("calcada", "rampa", "cadeirante", "passeio"), Urgencia.MEDIA),
    (Categoria.LIXO_ENTULHO, ("lixo", "entulho", "descarte", "sofa", "coleta", "sujeira"), Urgencia.BAIXA),
]


def _norm(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def classificar_por_palavras(texto: str) -> AnaliseIA:
    t = _norm(texto.split("<relato>")[-1])
    for categoria, palavras, urgencia in _PALAVRAS:
        if any(p in t for p in palavras):
            return AnaliseIA(
                categoria=categoria,
                titulo=f"Relato: {CATEGORIAS[categoria].nome.lower()}",
                urgencia=urgencia,
                risco_imediato=False,
                justificativa="Classificação simulada por palavras-chave (modo demonstração, sem IA real).",
                orientacoes=[
                    "Se for seguro, tire uma foto do problema sem se colocar em risco.",
                    "Guarde o número do protocolo para acompanhar o atendimento.",
                ],
                informacoes_faltantes=[],
                confianca=0.55,
            )
    return AnaliseIA(
        categoria=Categoria.OUTROS,
        titulo="Relato não classificado",
        urgencia=Urgencia.BAIXA,
        risco_imediato=False,
        justificativa="Não identificamos o tipo de problema (modo demonstração, sem IA real).",
        orientacoes=["Descreva com mais detalhes o que está acontecendo e onde."],
        informacoes_faltantes=["Tipo de problema", "Há quanto tempo acontece"],
        confianca=0.3,
    )


def responder_extrativo(usuario: str) -> dict:
    """Gerador extrativo (sem LLM): devolve as duas primeiras frases da fonte 1 com citação.
    Serve de linha de base e para testes automatizados do assistente."""
    import re

    m = re.search(r'<fonte n="1"[^>]*>\n(.*?)\n</fonte>', usuario, re.S)
    if not m:
        return {"resposta": "Não encontrei essa informação nas fontes.", "citacoes": [], "sem_evidencia": True}
    frases = re.split(r"(?<=[.!?])\s+", m.group(1).strip())
    return {"resposta": " ".join(frases[:2])[:600] + " [1]", "citacoes": [1], "sem_evidencia": False}


class ProvedorSimulado:
    nome = "mock"
    modelo = "simulado-palavras-chave"

    def __init__(self, atraso_s: float = 0.6):
        self.atraso_s = atraso_s

    async def gerar_estruturado(self, system: str, usuario: str, schema: type[M]) -> M:
        await asyncio.sleep(self.atraso_s)  # simula latência para exercitar o "design para latência"
        if schema.__name__ == "SaidaLLMAssistente":
            return schema.model_validate(responder_extrativo(usuario))
        return schema.model_validate(classificar_por_palavras(usuario).model_dump())
