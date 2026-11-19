"""Pipeline pós-IA: consolida a decisão humana (cidadão/gestor) com a sugestão da IA.

Guarda SEMPRE a classificação original da IA ao lado da final, para medir
concordância e auditar erros do modelo (human-in-the-loop mensurável).
"""

import secrets
from collections import Counter
from datetime import datetime

from app.core.erros import ErroZela, NaoEncontrado
from app.core.tempo import agora
from app.pipelines.catalogo import CATEGORIAS
from app.pipelines.roteamento import rotear
from app.providers.database import Repositorio
from app.schemas.analise import AnaliseResposta
from app.schemas.comum import Status, Urgencia
from app.schemas.solicitacao import (
    AtualizacaoGestor,
    Indicadores,
    SolicitacaoCidadao,
    SolicitacaoCriar,
    SolicitacaoGestor,
    SolicitacaoPublica,
)

STATUS_ABERTOS = {Status.RECEBIDA.value, Status.EM_ANALISE.value, Status.ENCAMINHADA.value}


class AnaliseExpirada(ErroZela):
    status_code = 404
    codigo = "ANALISE_NAO_ENCONTRADA"
    mensagem = "Esta análise expirou ou não foi encontrada. Envie o relato novamente."


def _agora() -> datetime:
    return agora()


def gerar_protocolo(repo: Repositorio) -> str:
    while True:
        protocolo = f"ZL-{_agora():%y%m%d}-{secrets.token_hex(3).upper()}"
        if not repo.existe_protocolo(protocolo):
            return protocolo


def registrar_solicitacao(repo: Repositorio, dados: SolicitacaoCriar) -> dict:
    # Idempotente: confirmar duas vezes a mesma análise devolve o mesmo protocolo
    existente = repo.obter_por_analise(dados.analise_id)
    if existente:
        return existente

    salvo = repo.obter_analise(dados.analise_id)
    if not salvo:
        raise AnaliseExpirada()
    resposta = AnaliseResposta.model_validate(salvo["resposta"])
    entrada = salvo["entrada"]
    ia = resposta.analise
    endereco = resposta.contexto.endereco

    corrigida = dados.categoria_final != ia.categoria or dados.urgencia_final != ia.urgencia
    # Se o cidadão mudou a categoria, o encaminhamento é recalculado pela tabela
    risco = ia.risco_imediato or dados.urgencia_final == Urgencia.CRITICA
    encaminhamento = rotear(dados.categoria_final, endereco, risco)
    agora = _agora()
    registro = {
        "protocolo": gerar_protocolo(repo),
        "analise_id": dados.analise_id,
        "criado_em": agora,
        "atualizado_em": agora,
        "status": Status.RECEBIDA.value,
        "categoria_ia": ia.categoria.value,
        "urgencia_ia": ia.urgencia.value,
        "categoria_final": dados.categoria_final.value,
        "urgencia_final": dados.urgencia_final.value,
        "corrigida_pelo_cidadao": corrigida,
        "comentario_cidadao": dados.comentario_cidadao,
        # Se a categoria foi corrigida, o título gerado pela IA pode estar errado: usa o nome da categoria
        "titulo": ia.titulo if dados.categoria_final == ia.categoria else CATEGORIAS[dados.categoria_final].nome,
        "descricao": entrada["descricao"],
        "endereco_resumo": endereco.resumo if endereco else None,
        "bairro": endereco.bairro if endereco else None,
        "cidade": endereco.cidade if endereco else None,
        "uf": endereco.uf if endereco else None,
        "latitude": endereco.latitude if endereco else None,
        "longitude": endereco.longitude if endereco else None,
        "orgao": encaminhamento.orgao,
        "canal": encaminhamento.canal,
        "prazo_referencia": encaminhamento.prazo_referencia,
        "orientacoes": ia.orientacoes,
        "risco_imediato": risco,
        "confianca_ia": ia.confianca,
        "contato": dados.contato,
        "historico": [{"status": Status.RECEBIDA.value, "em": agora.isoformat(), "nota": "Relato confirmado pelo cidadão."}],
        "demo": False,
        "visao": entrada.get("evidencia_visual"),
    }
    repo.criar_solicitacao(registro)
    return repo.obter_solicitacao(registro["protocolo"])  # type: ignore[return-value]


def obter_ou_404(repo: Repositorio, protocolo: str) -> dict:
    sol = repo.obter_solicitacao(protocolo.strip().upper())
    if not sol:
        raise NaoEncontrado("Não encontramos esse protocolo. Confira se digitou corretamente (ex.: ZL-261111-A1B2C3).")
    return sol


def registrar_feedback(repo: Repositorio, protocolo: str, util: bool, comentario: str | None) -> dict:
    sol = obter_ou_404(repo, protocolo)
    repo.atualizar_solicitacao(
        sol["protocolo"],
        {"feedback_util": util, "feedback_comentario": comentario, "atualizado_em": _agora()},
    )
    return repo.obter_solicitacao(sol["protocolo"])  # type: ignore[return-value]


def atualizar_pelo_gestor(repo: Repositorio, protocolo: str, mudanca: AtualizacaoGestor, usuario: str) -> dict:
    sol = obter_ou_404(repo, protocolo)
    agora = _agora()
    campos: dict = {"atualizado_em": agora}
    partes_nota = []
    if mudanca.categoria_final and mudanca.categoria_final.value != sol["categoria_final"]:
        campos["categoria_final"] = mudanca.categoria_final.value
        partes_nota.append(f"categoria ajustada para {CATEGORIAS[mudanca.categoria_final].nome}")
    if mudanca.urgencia_final and mudanca.urgencia_final.value != sol["urgencia_final"]:
        campos["urgencia_final"] = mudanca.urgencia_final.value
        partes_nota.append(f"urgência ajustada para {mudanca.urgencia_final.value}")
    if mudanca.nota:
        campos["nota_gestor"] = mudanca.nota
        partes_nota.append(mudanca.nota)
    novo_status = mudanca.status.value if mudanca.status else sol["status"]
    if mudanca.status or partes_nota:
        campos["status"] = novo_status
        historico = list(sol["historico"])
        historico.append({"status": novo_status, "em": agora.isoformat(),
                          "nota": f"[{usuario}] " + ("; ".join(partes_nota) or "status atualizado")})
        campos["historico"] = historico
    repo.atualizar_solicitacao(sol["protocolo"], campos)
    return repo.obter_solicitacao(sol["protocolo"])  # type: ignore[return-value]


# ---------------- visões (cada perfil vê só o que precisa) ----------------
def _base_publica(sol: dict) -> dict:
    return {
        "protocolo": sol["protocolo"],
        "criado_em": sol["criado_em"],
        "atualizado_em": sol["atualizado_em"],
        "status": sol["status"],
        "categoria": sol["categoria_final"],
        "urgencia": sol["urgencia_final"],
        "titulo": sol["titulo"],
        "bairro": sol["bairro"],
        "cidade": sol["cidade"],
        "uf": sol["uf"],
        "demo": sol["demo"],
    }


def para_publica(sol: dict) -> SolicitacaoPublica:
    dados = _base_publica(sol)
    # Coordenadas arredondadas (~100 m) para não expor o endereço exato de quem relatou
    dados["latitude"] = round(sol["latitude"], 3) if sol["latitude"] is not None else None
    dados["longitude"] = round(sol["longitude"], 3) if sol["longitude"] is not None else None
    return SolicitacaoPublica.model_validate(dados)


def para_cidadao(sol: dict) -> SolicitacaoCidadao:
    dados = _base_publica(sol) | {
        "latitude": sol["latitude"],
        "longitude": sol["longitude"],
        "descricao": sol["descricao"],
        "endereco_resumo": sol["endereco_resumo"],
        "orgao": sol["orgao"],
        "canal": sol["canal"],
        "prazo_referencia": sol["prazo_referencia"],
        "orientacoes": sol["orientacoes"],
        "risco_imediato": sol["risco_imediato"],
        "feedback_util": sol["feedback_util"],
        "historico": sol["historico"],
    }
    return SolicitacaoCidadao.model_validate(dados)


def para_gestor(sol: dict) -> SolicitacaoGestor:
    dados = para_cidadao(sol).model_dump() | {
        "categoria_ia": sol["categoria_ia"],
        "urgencia_ia": sol["urgencia_ia"],
        "corrigida_pelo_cidadao": sol["corrigida_pelo_cidadao"],
        "comentario_cidadao": sol["comentario_cidadao"],
        "confianca_ia": sol["confianca_ia"],
        "contato": sol["contato"],
        "nota_gestor": sol["nota_gestor"],
        "feedback_comentario": sol["feedback_comentario"],
        "visao": sol.get("visao"),
    }
    return SolicitacaoGestor.model_validate(dados)


def calcular_indicadores(sols: list[dict]) -> Indicadores:
    total = len(sols)
    abertas = [s for s in sols if s["status"] in STATUS_ABERTOS]
    com_feedback = [s for s in sols if s["feedback_util"] is not None]

    def pct(parte: int, todo: int) -> float | None:
        return round(100 * parte / todo, 1) if todo else None

    tempos = []
    for s in sols:
        if s["status"] == Status.RESOLVIDA.value:
            fim = next((h["em"] for h in reversed(s["historico"]) if h["status"] == Status.RESOLVIDA.value), None)
            if fim:
                delta = datetime.fromisoformat(fim) - datetime.fromisoformat(str(s["criado_em"]))
                tempos.append(delta.total_seconds() / 3600)

    return Indicadores(
        total=total,
        abertas=len(abertas),
        criticas_abertas=sum(1 for s in abertas if s["urgencia_final"] == Urgencia.CRITICA.value),
        por_status=dict(Counter(s["status"] for s in sols)),
        por_categoria=dict(Counter(s["categoria_final"] for s in sols)),
        por_urgencia=dict(Counter(s["urgencia_final"] for s in sols)),
        concordancia_categoria_pct=pct(sum(s["categoria_ia"] == s["categoria_final"] for s in sols), total),
        concordancia_urgencia_pct=pct(sum(s["urgencia_ia"] == s["urgencia_final"] for s in sols), total),
        feedback_util_pct=pct(sum(1 for s in com_feedback if s["feedback_util"]), len(com_feedback)),
        total_com_feedback=len(com_feedback),
        tempo_medio_resolucao_h=round(sum(tempos) / len(tempos), 1) if tempos else None,
    )


def catalogo_categorias() -> list[dict]:
    return [
        {"codigo": c.value, "nome": i.nome, "icone": i.icone, "descricao": i.descricao, "orgao_padrao": i.orgao_sp}
        for c, i in CATEGORIAS.items()
    ]

