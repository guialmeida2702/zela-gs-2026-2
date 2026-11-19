"""Encaminhamento determinístico: categoria + cidade => órgão, canal e prazo de referência."""

import unicodedata

from app.pipelines.catalogo import CATEGORIAS, CONTATOS_EMERGENCIA
from app.schemas.analise import Encaminhamento, Endereco
from app.schemas.comum import Categoria


def _eh_sao_paulo_capital(endereco: Endereco | None) -> bool:
    if not endereco:
        return False
    cidade = unicodedata.normalize("NFKD", endereco.cidade).encode("ascii", "ignore").decode().lower().strip()
    return cidade == "sao paulo" and endereco.uf.upper() == "SP"


def rotear(categoria: Categoria, endereco: Endereco | None, risco_imediato: bool) -> Encaminhamento:
    info = CATEGORIAS[categoria]
    if _eh_sao_paulo_capital(endereco):
        orgao, canal = info.orgao_sp, info.canal_sp
    else:
        cidade = endereco.cidade if endereco else "sua cidade"
        orgao, canal = info.orgao_generico, info.canal_generico.format(cidade=cidade)

    contatos = list(CONTATOS_EMERGENCIA) if risco_imediato else []
    prazo = "atendimento emergencial — acione os contatos de emergência" if risco_imediato else info.prazo_referencia
    return Encaminhamento(orgao=orgao, canal=canal, prazo_referencia=prazo, contatos_emergencia=contatos)
