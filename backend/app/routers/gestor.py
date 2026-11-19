"""Visão do gestor público (protegida por token): fila, tratamento e indicadores."""

from fastapi import APIRouter, Depends, Query

from app.core.dependencias import Container, exigir_gestor, get_container, get_repo
from app.core.erros import NaoAutorizado
from app.core.seguranca import emitir_token, verificar_credenciais
from app.pipelines import registro
from app.providers.database import Repositorio
from app.schemas.auth import LoginEntrada, Token
from app.schemas.comum import Categoria, Status, Urgencia
from app.schemas.solicitacao import AtualizacaoGestor, Indicadores, SolicitacaoGestor

router_auth = APIRouter(prefix="/auth", tags=["gestor"])
router = APIRouter(prefix="/gestor", tags=["gestor"], dependencies=[Depends(exigir_gestor)])


@router_auth.post("/login", response_model=Token, summary="Login do gestor (retorna token JWT)")
def login(dados: LoginEntrada, c: Container = Depends(get_container)) -> Token:
    c.limitador.verificar(f"login:{dados.usuario}")  # dificulta tentativa e erro de senha
    if not verificar_credenciais(c.settings, dados.usuario, dados.senha):
        raise NaoAutorizado("Usuário ou senha incorretos.")
    token, expira = emitir_token(c.settings, dados.usuario)
    return Token(access_token=token, expira_em=expira)


@router.get("/solicitacoes", response_model=list[SolicitacaoGestor], summary="Fila completa de solicitações")
def listar(
    status: Status | None = None,
    categoria: Categoria | None = None,
    urgencia: Urgencia | None = None,
    limite: int = Query(default=500, ge=1, le=2000),
    repo: Repositorio = Depends(get_repo),
) -> list[SolicitacaoGestor]:
    sols = repo.listar_solicitacoes(
        status=status.value if status else None,
        categoria=categoria.value if categoria else None,
        urgencia=urgencia.value if urgencia else None,
        limite=limite,
    )
    return [registro.para_gestor(s) for s in sols]


@router.patch("/solicitacoes/{protocolo}", response_model=SolicitacaoGestor, summary="Atualiza status/classificação")
def atualizar(
    protocolo: str,
    mudanca: AtualizacaoGestor,
    usuario: str = Depends(exigir_gestor),
    repo: Repositorio = Depends(get_repo),
) -> SolicitacaoGestor:
    return registro.para_gestor(registro.atualizar_pelo_gestor(repo, protocolo, mudanca, usuario))


@router.get("/indicadores", response_model=Indicadores, summary="Indicadores operacionais e de qualidade da IA")
def indicadores(repo: Repositorio = Depends(get_repo)) -> Indicadores:
    return registro.calcular_indicadores(repo.listar_solicitacoes(limite=100_000))
