"""Container de dependências criado no startup e injetado nas rotas via FastAPI Depends."""

from dataclasses import dataclass

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.core.erros import NaoAutorizado
from app.core.rate_limit import LimitadorTaxa
from app.core.seguranca import validar_token
from app.pipelines.assistente import Assistente
from app.pipelines.triagem import PipelineTriagem
from app.providers.clima import ProvedorClima
from app.providers.database import Repositorio
from app.providers.geo import ProvedorGeo
from app.providers.llm.base import ProvedorLLM
from app.providers.visao import ProvedorVisao


@dataclass
class Container:
    settings: Settings
    http: httpx.AsyncClient
    llm: ProvedorLLM
    geo: ProvedorGeo
    clima: ProvedorClima
    repo: Repositorio
    triagem: PipelineTriagem
    limitador: LimitadorTaxa
    assistente: Assistente
    visao: ProvedorVisao


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_repo(c: Container = Depends(get_container)) -> Repositorio:
    return c.repo


def limitar_taxa(request: Request, c: Container = Depends(get_container)) -> None:
    ip = request.client.host if request.client else "desconhecido"
    c.limitador.verificar(ip)


_bearer = HTTPBearer(auto_error=False)


def exigir_gestor(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    c: Container = Depends(get_container),
) -> str:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NaoAutorizado("Entre com o usuário de gestor para acessar esta área.")
    dados = validar_token(c.settings, credenciais.credentials)
    return dados["sub"]
