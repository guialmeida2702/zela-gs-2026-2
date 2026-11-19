"""Etapas 2 e 3: confirmação humana (gera protocolo), consulta, feedback e painel público."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencias import get_repo
from app.core.tempo import agora
from app.pipelines import registro
from app.providers.database import Repositorio
from app.schemas.solicitacao import FeedbackEntrada, SolicitacaoCidadao, SolicitacaoCriar, SolicitacaoPublica

router = APIRouter(prefix="/solicitacoes", tags=["cidadão"])


@router.post(
    "",
    response_model=SolicitacaoCidadao,
    status_code=status.HTTP_201_CREATED,
    summary="Registra a solicitação após o cidadão confirmar ou corrigir a análise da IA",
)
def registrar(dados: SolicitacaoCriar, repo: Repositorio = Depends(get_repo)) -> SolicitacaoCidadao:
    return registro.para_cidadao(registro.registrar_solicitacao(repo, dados))


@router.get("/publicas", response_model=list[SolicitacaoPublica], summary="Dados anônimos para o painel da cidade")
def listar_publicas(
    dias: int = Query(default=90, ge=1, le=365),
    repo: Repositorio = Depends(get_repo),
) -> list[SolicitacaoPublica]:
    desde = agora() - timedelta(days=dias)
    return [registro.para_publica(s) for s in repo.listar_solicitacoes(desde=desde)]


@router.get("/{protocolo}", response_model=SolicitacaoCidadao, summary="Consulta o andamento pelo protocolo")
def consultar(protocolo: str, repo: Repositorio = Depends(get_repo)) -> SolicitacaoCidadao:
    return registro.para_cidadao(registro.obter_ou_404(repo, protocolo))


@router.post("/{protocolo}/feedback", response_model=SolicitacaoCidadao, summary="Cidadão avalia se a orientação foi útil")
def avaliar(protocolo: str, dados: FeedbackEntrada, repo: Repositorio = Depends(get_repo)) -> SolicitacaoCidadao:
    return registro.para_cidadao(registro.registrar_feedback(repo, protocolo, dados.util, dados.comentario))
