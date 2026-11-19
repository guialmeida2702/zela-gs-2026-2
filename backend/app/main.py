"""Ponto de entrada da API Zela (FastAPI)."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, get_settings
from app.core.dependencias import Container
from app.core.erros import ErroZela
from app.core.rate_limit import LimitadorTaxa
from app.core.seed import popular_dados_demo
from app.pipelines.assistente import Assistente
from app.pipelines.conhecimento import construir_trechos
from app.pipelines.triagem import PipelineTriagem
from app.providers.busca import IndiceBusca
from app.providers.clima import ProvedorClima
from app.providers.database import Repositorio
from app.providers.geo import ProvedorGeo
from app.providers.llm import criar_provedor_llm
from app.providers.llm.base import ProvedorLLM
from app.providers.visao import ProvedorVisao
from app.routers import gestor, inteligencia, relatos, sistema, solicitacoes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("zela.api")

_MENSAGENS_CAMPO = {
    "descricao": "Descreva o problema com pelo menos 20 caracteres (no máximo 1000).",
    "cep": "Informe um CEP válido, com 8 dígitos.",
    "numero": "O número deve ter no máximo 10 caracteres.",
    "ponto_referencia": "O ponto de referência deve ter no máximo 120 caracteres.",
    "categoria_sugerida": "Escolha uma categoria da lista.",
    "categoria_final": "Escolha uma categoria da lista.",
    "urgencia_final": "Escolha um nível de urgência da lista.",
    "consentimento_lgpd": "É preciso concordar com o uso dos dados para registrar a solicitação.",
    "contato": "Informe um e-mail válido ou um telefone com DDD.",
    "comentario_cidadao": "O comentário deve ter no máximo 300 caracteres.",
    "comentario": "O comentário deve ter no máximo 300 caracteres.",
    "analise_id": "Análise inválida. Envie o relato novamente.",
    "usuario": "Informe o usuário.",
    "senha": "Informe a senha.",
}


def _corpo_erro(codigo: str, mensagem: str, campos: dict[str, str] | None = None) -> dict:
    erro: dict = {"codigo": codigo, "mensagem": mensagem}
    if campos:
        erro["campos"] = campos
    return {"erro": erro}


def _registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroZela)
    async def _erro_zela(request: Request, exc: ErroZela) -> JSONResponse:
        nivel = logging.ERROR if exc.status_code >= 500 else logging.INFO
        log.log(nivel, "%s %s -> %s (%s)", request.method, request.url.path, exc.codigo, exc.detalhe_tecnico or "-")
        return JSONResponse(status_code=exc.status_code, content=_corpo_erro(exc.codigo, exc.mensagem_usuario))

    @app.exception_handler(RequestValidationError)
    async def _erro_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
        campos: dict[str, str] = {}
        for erro in exc.errors():
            loc = [str(p) for p in erro.get("loc", []) if p not in ("body", "query", "path")]
            campo = loc[0] if loc else "dados"
            msg = str(erro.get("msg", ""))
            if erro.get("type") == "value_error" and msg.startswith("Value error, "):
                texto = msg.removeprefix("Value error, ")
                texto = texto[0].upper() + texto[1:] + "."
            else:
                texto = _MENSAGENS_CAMPO.get(campo, "Confira este campo.")
            campos.setdefault(campo, texto)
        mensagem = "Alguns dados precisam de ajuste antes do envio."
        if list(campos) == ["dados"]:
            mensagem = "Não foi possível ler os dados enviados."
        return JSONResponse(status_code=422, content=_corpo_erro("ENTRADA_INVALIDA", mensagem, campos))

    @app.exception_handler(StarletteHTTPException)
    async def _erro_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mensagens = {404: "Recurso não encontrado.", 405: "Operação não permitida."}
        return JSONResponse(
            status_code=exc.status_code,
            content=_corpo_erro(f"HTTP_{exc.status_code}", mensagens.get(exc.status_code, "Requisição não atendida.")),
        )

    @app.exception_handler(Exception)
    async def _erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Erro inesperado em %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_corpo_erro(ErroZela.codigo, ErroZela.mensagem))


def create_app(
    settings: Settings | None = None,
    *,
    llm: ProvedorLLM | None = None,
    geo: ProvedorGeo | None = None,
    clima: ProvedorClima | None = None,
    repo: Repositorio | None = None,
    assistente: Assistente | None = None,
    visao: ProvedorVisao | None = None,
) -> FastAPI:
    """Fábrica da aplicação. Os parâmetros opcionais permitem injetar dublês nos testes."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = httpx.AsyncClient(headers={"Accept": "application/json"}, follow_redirects=True)
        _repo = repo or Repositorio(settings.database_path)
        _llm = llm or criar_provedor_llm(settings)
        _geo = geo or ProvedorGeo(
            http, timeout_s=settings.timeout_externo_s, user_agent=settings.nominatim_user_agent,
            habilitado=settings.usar_dados_externos,
        )
        _clima = clima or ProvedorClima(http, timeout_s=settings.timeout_externo_s, habilitado=settings.usar_dados_externos)
        if settings.seed_demo_data:
            inseridos = popular_dados_demo(_repo)
            if inseridos:
                log.info("Inseridos %d registros FICTÍCIOS de demonstração.", inseridos)
        _assistente = assistente or Assistente(
            _llm, IndiceBusca(construir_trechos(), modo=settings.busca_modo, cache_modelos=settings.modelos_cache_dir or None),
            k=settings.assistente_k)
        app.state.container = Container(
            settings=settings, http=http, llm=_llm, geo=_geo, clima=_clima, repo=_repo,
            triagem=PipelineTriagem(_llm, _geo, _clima, _repo),
            limitador=LimitadorTaxa(settings.rate_limit_por_min),
            assistente=_assistente,
            visao=visao or ProvedorVisao(),
        )
        log.info("Zela API pronta | IA=%s (%s) | CORS=%s", _llm.nome, _llm.modelo, settings.cors_origin_list)
        yield
        await http.aclose()
        if repo is None:
            _repo.fechar()

    app = FastAPI(
        title="Zela API — triagem cidadã de problemas urbanos",
        version=settings.app_versao,
        description="Back-end da POC CitizenTech: recebe relatos, analisa com LLM (saída Pydantic) e encaminha.",
        lifespan=lifespan,
        docs_url=None if settings.em_producao else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,  # lista explícita; "*" é recusado em produção (config.py)
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def _cabecalhos_seguranca(request: Request, call_next):
        resposta = await call_next(request)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        return resposta

    _registrar_handlers(app)
    for r in (sistema.router, relatos.router, solicitacoes.router, gestor.router_auth, gestor.router, inteligencia.router):
        app.include_router(r)
    return app


app = create_app()
