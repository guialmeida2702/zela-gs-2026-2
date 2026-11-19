"""Módulos de IA integrados ao Zela: visão computacional (fotos) e assistente conversacional (RAG)."""

import time

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.dependencias import Container, get_container, limitar_taxa
from app.core.erros import ErroZela
from app.pipelines.assistente import trecho_do_protocolo
from app.providers.visao import ImagemInvalida
from app.schemas.assistente import PerguntaAssistente, RespostaAssistente

router = APIRouter(tags=["inteligência"])

TIPOS_ACEITOS = {"image/jpeg", "image/png", "image/webp"}
TAMANHO_MAXIMO = 8 * 1024 * 1024


class VisaoIndisponivel(ErroZela):
    status_code = 503
    codigo = "VISAO_INDISPONIVEL"
    mensagem = "A análise de fotos está indisponível no momento. Você pode continuar o relato sem a foto."


class ImagemRecusada(ErroZela):
    status_code = 422
    codigo = "IMAGEM_INVALIDA"
    mensagem = "Não conseguimos usar essa imagem. Envie uma foto JPG ou PNG de até 8 MB."


async def _ler_imagem(c: Container, arquivo: UploadFile):
    if not c.visao.disponivel:
        raise VisaoIndisponivel()
    if arquivo.content_type not in TIPOS_ACEITOS:
        raise ImagemRecusada(detalhe_tecnico=f"tipo {arquivo.content_type}")
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ImagemRecusada("A imagem passa de 8 MB. Envie uma foto menor.")
    try:
        return c.visao.abrir(conteudo)
    except ImagemInvalida as exc:
        raise ImagemRecusada(str(exc)) from exc


@router.post("/visao/analisar", dependencies=[Depends(limitar_taxa)],
             summary="Sinaliza possíveis fissuras em uma foto (a imagem não é armazenada)")
async def analisar_imagem(arquivo: UploadFile = File(...), c: Container = Depends(get_container)) -> dict:
    return c.visao.analisar(await _ler_imagem(c, arquivo))


@router.post("/visao/lote", summary="Processa uma sequência de imagens (simulação de monitoramento)")
async def analisar_lote(arquivos: list[UploadFile] = File(...), c: Container = Depends(get_container)) -> dict:
    if len(arquivos) > 40:
        raise ImagemRecusada("Envie no máximo 40 imagens por vez.")
    inicio = time.perf_counter()
    resultados = []
    for arq in arquivos:
        try:
            r = c.visao.analisar(await _ler_imagem(c, arq))
            r.pop("blocos", None)
            resultados.append({"arquivo": arq.filename, **r})
        except ImagemRecusada as exc:  # uma imagem ruim não derruba o lote
            resultados.append({"arquivo": arq.filename, "erro": exc.mensagem_usuario})
    total = time.perf_counter() - inicio
    validos = [r for r in resultados if "erro" not in r]
    return {"resultados": resultados, "imagens": len(arquivos), "tempo_total_s": round(total, 3),
            "imagens_por_segundo": round(len(validos) / total, 2) if total else None,
            "com_fissura": sum(r["classe"] == "com_fissura" for r in validos)}


@router.post("/assistente/perguntar", response_model=RespostaAssistente, dependencies=[Depends(limitar_taxa)],
             summary="Assistente Zela: responde com base em fontes oficiais, citando-as, ou se abstém")
async def perguntar(entrada: PerguntaAssistente, c: Container = Depends(get_container)) -> RespostaAssistente:
    contexto = None
    if entrada.protocolo:
        sol = c.repo.obter_solicitacao(entrada.protocolo.strip().upper())
        if sol:
            contexto = trecho_do_protocolo(sol)
    return await c.assistente.responder(entrada, contexto)

