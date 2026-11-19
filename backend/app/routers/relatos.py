"""Etapa 1 da jornada: o cidadão envia o relato e recebe a análise da IA para revisar."""

from fastapi import APIRouter, Depends

from app.core.dependencias import Container, get_container, limitar_taxa
from app.schemas.analise import AnaliseResposta
from app.schemas.comum import ErroResposta
from app.schemas.relato import RelatoEntrada

router = APIRouter(prefix="/relatos", tags=["cidadão"])


@router.post(
    "/analisar",
    response_model=AnaliseResposta,
    dependencies=[Depends(limitar_taxa)],
    summary="Analisa o relato com IA (ainda NÃO registra a solicitação)",
    responses={
        422: {"model": ErroResposta, "description": "Entrada inválida"},
        429: {"model": ErroResposta, "description": "Muitos envios em pouco tempo"},
        502: {"model": ErroResposta, "description": "A IA devolveu uma resposta fora do formato"},
        503: {"model": ErroResposta, "description": "IA indisponível"},
        504: {"model": ErroResposta, "description": "Tempo esgotado na IA"},
    },
)
async def analisar_relato(entrada: RelatoEntrada, c: Container = Depends(get_container)) -> AnaliseResposta:
    return await c.triagem.analisar(entrada)
