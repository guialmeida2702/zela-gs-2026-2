"""Endpoints de apoio: saúde da API, catálogo de categorias/urgências e consulta de CEP."""

from fastapi import APIRouter, Depends, Path

from app.core.dependencias import Container, get_container
from app.core.erros import NaoEncontrado
from app.pipelines.catalogo import URGENCIAS
from app.pipelines.registro import catalogo_categorias
from app.schemas.analise import Endereco
from app.schemas.catalogo import CategoriaInfo, UrgenciaInfo

router = APIRouter(tags=["sistema"])


@router.get("/health", summary="Verifica se a API está no ar")
def health(c: Container = Depends(get_container)) -> dict:
    return {
        "status": "ok",
        "versao": c.settings.app_versao,
        "ia": {
            "provedor": c.llm.nome,
            "modelo": c.llm.modelo,
            "simulada": c.llm.nome == "mock",
            "configurada": c.llm.nome != "nao_configurado",
        },
        "dados_externos": c.settings.usar_dados_externos,
        "modulos": {
            "visao_computacional": c.visao.disponivel,
            "assistente_busca": c.assistente.indice.modo,
            "assistente_trechos": len(c.assistente.indice.trechos),
        },
    }


@router.get("/categorias", response_model=list[CategoriaInfo], summary="Categorias de problemas urbanos")
def listar_categorias() -> list[dict]:
    return catalogo_categorias()


@router.get("/urgencias", response_model=list[UrgenciaInfo], summary="Níveis de urgência e seus critérios")
def listar_urgencias() -> list[UrgenciaInfo]:
    return [UrgenciaInfo(codigo=u.value, nome=nome, descricao=desc) for u, (nome, desc) in URGENCIAS.items()]


@router.get("/enderecos/{cep}", response_model=Endereco, summary="Consulta endereço pelo CEP (BrasilAPI/ViaCEP)")
async def consultar_cep(
    cep: str = Path(pattern=r"^\d{5}-?\d{3}$", description="CEP com 8 dígitos"),
    c: Container = Depends(get_container),
) -> Endereco:
    endereco = await c.geo.buscar_cep(cep.replace("-", ""))
    if not endereco:
        raise NaoEncontrado("Não encontramos esse CEP. Confira os números ou informe um ponto de referência.")
    return endereco
