"""Componentes visuais reutilizáveis.

`cartao_solicitacao` é o principal componente reutilizado: aparece na tela de
sucesso, em "Minhas solicitações" (modo cidadão) e na fila do gestor (modo
gestor), com parâmetros diferentes. Os selos de urgência/status e a linha de
indicadores também são usados em várias telas.

Todo texto vindo do usuário ou do LLM passa por `seguro()` antes de entrar em
HTML (evita injeção de HTML/markdown, como imagens externas de rastreio).
"""

import html
from datetime import datetime

import streamlit as st

from providers.api_client import ErroApi
from ui import theme

_MD_ESPECIAIS = str.maketrans({"[": "&#91;", "]": "&#93;", "`": "&#96;", "*": "&#42;", "_": "&#95;",
                               "#": "&#35;", "|": "&#124;", "~": "&#126;"})


def seguro(texto: object) -> str:
    return html.escape(str(texto or ""), quote=True).translate(_MD_ESPECIAIS)


def _html(conteudo: str) -> None:
    st.markdown(conteudo, unsafe_allow_html=True)


def data_br(valor: str | None) -> str:
    if not valor:
        return "—"
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(valor)


# ---------------- selos (cor + ícone + texto) ----------------
def selo_urgencia(codigo: str) -> str:
    """Cores vêm de classes CSS (ver theme.aplicar_estilo); ícone + texto garantem que a cor não esteja sozinha."""
    info = theme.URGENCIA.get(codigo)
    if not info:
        return ""
    return (
        f'<span class="zela-selo zela-urg-{codigo}" role="img" '
        f'aria-label="Urgência {info["nome"]}: {info["ajuda"]}">'
        f'<span aria-hidden="true">{info["icone"]}</span><span>Urgência {info["nome"]}</span></span>'
    )


def selo_status(codigo: str) -> str:
    info = theme.STATUS.get(codigo, {"nome": codigo, "icone": ""})
    return (f'<span class="zela-selo zela-selo-status"><span aria-hidden="true">{info["icone"]}</span>'
            f'<span>{info["nome"]}</span></span>')


def selo_categoria(codigo: str) -> str:
    info = theme.CATEGORIAS.get(codigo, {"nome": codigo, "icone": "📌"})
    return (f'<span class="zela-selo zela-selo-neutro"><span aria-hidden="true">{info["icone"]}</span>'
            f'<span>{seguro(info["nome"])}</span></span>')


# ---------------- estrutura ----------------
def cabecalho(subtitulo: str) -> None:
    _html(
        '<header class="zela-hero" role="banner">'
        '<h1><span aria-hidden="true">📍</span> Zela</h1>'
        f"<p>{seguro(subtitulo)}</p></header>"
    )


def passos_jornada(etapa_atual: str) -> None:
    passos = [("relatar", "1. Conte o problema"), ("revisar", "2. Confira a análise"), ("concluido", "3. Receba o protocolo")]
    ordem = [p[0] for p in passos]
    idx = ordem.index(etapa_atual) if etapa_atual in ordem else 0
    itens = []
    for i, (_chave, rotulo) in enumerate(passos):
        if i == idx:
            itens.append(f'<li aria-current="step">{rotulo}</li>')
        elif i < idx:
            itens.append(f'<li class="feito"><span aria-hidden="true">✓ </span>{rotulo}</li>')
        else:
            itens.append(f"<li>{rotulo}</li>")
    _html(f'<ol class="zela-passos" aria-label="Etapas do relato">{"".join(itens)}</ol>')


def aviso_emergencia(contatos: list[str] | None = None, compacto: bool = False) -> None:
    contatos = contatos or ["Bombeiros: 193", "Defesa Civil: 199", "SAMU: 192"]
    if compacto:
        _html(f'<div class="zela-emergencia" role="note"><strong>Emergência?</strong> {" · ".join(contatos)}</div>')
        return
    _html(
        '<div class="zela-emergencia" role="alert"><strong><span aria-hidden="true">🚨</span> '
        "Risco imediato: afaste-se do local e mantenha outras pessoas longe.</strong><br>"
        f"Ligue agora: <strong>{' · '.join(contatos)}</strong>. Registrar aqui não substitui o atendimento de emergência.</div>"
    )


def estado_vazio(icone: str, titulo: str, texto: str) -> None:
    _html(
        f'<div class="zela-vazio" role="status"><div class="icone" aria-hidden="true">{icone}</div>'
        f"<p><strong>{seguro(titulo)}</strong></p><p>{seguro(texto)}</p></div>"
    )


def mostrar_erro(erro: ErroApi, *, acao: str | None = None) -> None:
    """Mensagem clara para o cidadão. Nunca exibe stack trace nem detalhes técnicos."""
    icone = "📡" if erro.fora_do_ar else "⚠️"
    texto = erro.mensagem
    if acao:
        texto += f"\n\n{acao}"
    st.error(texto, icon=icone)
    if erro.campos:
        for msg in erro.campos.values():
            st.caption(f"• {msg}")


def linha_indicadores(itens: list[tuple[str, str, str | None]]) -> None:
    """Linha de métricas: [(rótulo, valor, ajuda), ...]. Reutilizada no painel público e no gestor."""
    colunas = st.columns(len(itens))
    for col, (rotulo, valor, ajuda) in zip(colunas, itens, strict=True):
        col.metric(rotulo, valor, help=ajuda, border=True)


def medidor_confianca(confianca: float) -> None:
    if confianca >= 0.8:
        nivel, dica = "alta", "A IA entendeu bem o relato. Mesmo assim, confira."
    elif confianca >= 0.6:
        nivel, dica = "média", "Confira com atenção a categoria e a urgência."
    else:
        nivel, dica = "baixa", "O relato ficou pouco claro para a IA. Revise a classificação ou detalhe melhor."
    st.progress(min(max(confianca, 0.0), 1.0), text=f"Certeza da IA: {nivel} ({confianca:.0%}). {dica}")


# ---------------- cartões ----------------
def cartao_analise(resposta: dict) -> None:
    """Resultado da IA apresentado como orientação útil (não como texto bruto)."""
    an = resposta["analise"]
    enc = resposta["encaminhamento"]
    ctx = resposta.get("contexto") or {}

    if an.get("risco_imediato"):
        aviso_emergencia(enc.get("contatos_emergencia"))

    with st.container(border=True):
        _html(f"{selo_urgencia(an['urgencia'])} &nbsp; {selo_categoria(an['categoria'])}")
        st.subheader(an["titulo"], anchor=False)
        if an.get("fora_do_escopo"):
            st.info("Este relato não parece ser um problema de zeladoria urbana. Veja as orientações abaixo "
                    "para procurar o serviço adequado.", icon="🧭")

        col1, col2 = st.columns([3, 2], gap="large")
        with col1:
            st.markdown("**O que você pode fazer agora**")
            for i, passo in enumerate(an["orientacoes"], start=1):
                st.markdown(f"{i}. {seguro(passo)}", unsafe_allow_html=True)
            st.markdown("**Por que essa prioridade?**")
            _html(f"<p>{seguro(an['justificativa'])}</p>")
            for ajuste in resposta.get("ajustes_de_seguranca", []):
                st.warning(ajuste, icon="🛡️")
        with col2:
            st.markdown("**Para onde vai o seu relato**")
            _html(
                f'<div class="zela-rotulo">Responsável</div><p>{seguro(enc["orgao"])}</p>'
                f'<div class="zela-rotulo">Canal oficial</div><p>{seguro(enc["canal"])}</p>'
                f'<div class="zela-rotulo">Prazo de referência</div><p>{seguro(enc["prazo_referencia"])}</p>'
            )
            endereco = ctx.get("endereco")
            if endereco:
                partes = [endereco.get("logradouro"), endereco.get("bairro"), f"{endereco['cidade']}/{endereco['uf']}"]
                _html(f'<div class="zela-rotulo">Local</div><p>{seguro(", ".join(p for p in partes if p))}</p>')
            if ctx.get("clima"):
                _html(f'<div class="zela-rotulo">Previsão do tempo</div><p><span aria-hidden="true">🌧️</span> '
                      f'{seguro(ctx["clima"]["resumo"])}</p>')

        if an.get("informacoes_faltantes"):
            st.info("**Informações que ajudariam a equipe:** " + "; ".join(seguro(i) for i in an["informacoes_faltantes"]),
                    icon="📝")
        medidor_confianca(an["confianca"])
        if resposta.get("dados_pessoais_removidos"):
            st.caption("🔒 Para proteger você, removemos do texto antes da análise: "
                       + ", ".join(resposta["dados_pessoais_removidos"]) + ".")
        for aviso in ctx.get("avisos", []):
            st.caption(f"ℹ️ {aviso}")
        fontes = ctx.get("fontes_consultadas") or []
        st.caption(
            f"Análise feita por IA ({resposta['modelo_ia']}) em {resposta['latencia_ms'] / 1000:.1f}s"
            + (f" · dados abertos: {', '.join(fontes)}" if fontes else "")
            + (" · resultado reaproveitado do cache" if resposta.get("em_cache") else "")
        )


def cartao_solicitacao(sol: dict, *, modo: str = "cidadao", mostrar_historico: bool = True) -> None:
    """Componente reutilizável. modo: 'cidadao' | 'gestor' | 'compacto'."""
    with st.container(border=True):
        cab1, cab2 = st.columns([3, 2])
        with cab1:
            _html(f'<div class="zela-rotulo">Protocolo</div><div class="zela-protocolo" style="font-size:1.15rem">'
                  f'{seguro(sol["protocolo"])}</div>')
            st.markdown(f"**{seguro(sol['titulo'])}**", unsafe_allow_html=True)
        with cab2:
            _html(f"{selo_urgencia(sol['urgencia'])}<br><br>{selo_status(sol['status'])}")

        local = sol.get("endereco_resumo") or ", ".join(p for p in (sol.get("bairro"), sol.get("cidade")) if p)
        st.caption(f"{theme.nome_categoria(sol['categoria'])} · {seguro(local) or 'local não informado'} · "
                   f"registrado em {data_br(sol['criado_em'])}")
        if sol.get("demo"):
            st.caption("🧪 Registro fictício de demonstração.")
        if modo == "compacto":
            return

        if modo in ("cidadao", "gestor") and sol.get("descricao"):
            _html(f'<div class="zela-rotulo">Relato (dados pessoais removidos)</div><p>{seguro(sol["descricao"])}</p>')
        if sol.get("orgao"):
            _html(f'<div class="zela-rotulo">Encaminhado para</div><p>{seguro(sol["orgao"])} — {seguro(sol.get("canal"))}</p>')

        if modo == "gestor":
            concorda_cat = sol["categoria_ia"] == sol["categoria"]
            concorda_urg = sol["urgencia_ia"] == sol["urgencia"]
            st.markdown(
                f"**Sugestão original da IA:** {theme.nome_categoria(sol['categoria_ia'])} "
                f"{'✓' if concorda_cat else '✗ (corrigida)'} · {theme.nome_urgencia(sol['urgencia_ia'])} "
                f"{'✓' if concorda_urg else '✗ (corrigida)'} · certeza {sol['confianca_ia']:.0%}"
            )
            if sol.get("comentario_cidadao"):
                _html(f"<p><em>Comentário do cidadão:</em> {seguro(sol['comentario_cidadao'])}</p>")
            if sol.get("contato"):
                _html(f"<p><em>Contato (autorizado pelo cidadão):</em> {seguro(sol['contato'])}</p>")
            if sol.get("feedback_util") is not None:
                st.caption("Avaliação do cidadão: " + ("👍 orientação útil" if sol["feedback_util"] else "👎 não ajudou"))

        if mostrar_historico and sol.get("historico"):
            with st.expander("Linha do tempo do atendimento"):
                for ev in sol["historico"]:
                    nota = f" — {seguro(ev['nota'])}" if ev.get("nota") else ""
                    st.markdown(f"- {theme.nome_status(ev['status'])} · {data_br(ev['em'])}{nota}", unsafe_allow_html=True)
