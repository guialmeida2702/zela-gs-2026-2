"""Jornada principal do cidadão: relatar -> revisar a análise da IA (human-in-the-loop) -> protocolo."""

import re

import streamlit as st

from features.minhas_solicitacoes import avaliacao
from providers import dados
from providers.api_client import ErroApi
from state import session
from ui import acessibilidade, components, theme, visao

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_relato(descricao: str, cep: str, numero: str = "", referencia: str = "") -> dict[str, str]:
    """Validação no front ANTES do envio (o back-end valida de novo com Pydantic)."""
    erros: dict[str, str] = {}
    texto = " ".join((descricao or "").split())
    if not texto:
        erros["descricao"] = "Descreva o problema: este campo é obrigatório."
    elif len(texto) < 20:
        erros["descricao"] = f"Conte um pouco mais: faltam {20 - len(texto)} caracteres (mínimo de 20)."
    elif len(texto) > 1000:
        erros["descricao"] = "O relato pode ter no máximo 1000 caracteres."
    elif sum(c.isalpha() for c in texto) < 10:
        erros["descricao"] = "Use palavras para descrever o problema."
    digitos = re.sub(r"\D", "", cep or "")
    if not digitos:
        erros["cep"] = "Informe o CEP do local: este campo é obrigatório."
    elif len(digitos) != 8:
        erros["cep"] = "O CEP deve ter 8 números (ex.: 01001-000)."
    if numero and len(numero.strip()) > 10:
        erros["numero"] = "O número pode ter no máximo 10 caracteres."
    if referencia and len(referencia.strip()) > 120:
        erros["referencia"] = "O ponto de referência pode ter no máximo 120 caracteres."
    return erros


def validar_contato(contato: str) -> str | None:
    contato = (contato or "").strip()
    if not contato:
        return None
    if _EMAIL.match(contato) or 10 <= len(re.sub(r"\D", "", contato)) <= 13:
        return None
    return "Informe um e-mail válido ou um telefone com DDD (ou deixe em branco)."


def tela() -> None:
    etapa = session.etapa()
    components.passos_jornada(etapa)
    if etapa == "revisar" and session.obter("analise"):
        _revisao()
    elif etapa == "concluido" and session.obter("ultimo_registro"):
        _sucesso()
    else:
        _formulario()


# ---------------- 1. formulário ----------------
def _formulario() -> None:
    st.subheader("Conte o que está acontecendo", anchor=False)
    st.caption("Use suas palavras. Diga **o que** é, **onde** fica e se existe **algum risco**. "
               "Não é preciso informar nome nem documentos.")
    opcoes = ["", *theme.CATEGORIAS]  # "" = "não sei" (None seria tratado como "sem seleção" pelo Streamlit)

    # Chaves estáveis + valor inicial no session_state (em vez de value=...): se o value mudasse entre
    # reruns, o Streamlit recriaria o widget e descartaria o que o cidadão acabou de digitar.
    v = session.obter("versao_form")
    anterior = session.obter("relato") or {}
    iniciais = {
        f"rel_descricao_{v}": anterior.get("descricao", ""),
        f"rel_cep_{v}": anterior.get("cep", ""),
        f"rel_numero_{v}": anterior.get("numero") or "",
        f"rel_referencia_{v}": anterior.get("ponto_referencia") or "",
        f"rel_categoria_{v}": anterior.get("categoria_sugerida") or "",
    }
    for chave, valor in iniciais.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor

    with st.form(f"form_relato_{v}", border=True):
        descricao = st.text_area(
            "Descreva o problema (obrigatório)",
            key=f"rel_descricao_{v}",
            max_chars=1000,
            height=150,
            placeholder="Ex.: Tem um buraco grande na rua, perto do ponto de ônibus. Ontem um motoqueiro quase caiu.",
            help="Mínimo de 20 caracteres. Evite colocar telefone ou CPF aqui — se colocar, removemos antes da análise.",
        )
        c1, c2, c3 = st.columns([1.1, 0.9, 2])
        cep = c1.text_input("CEP do local (obrigatório)", key=f"rel_cep_{v}", max_chars=9, placeholder="00000-000",
                            help="Com o CEP encontramos o endereço e a previsão de chuva da região.")
        numero = c2.text_input("Número próximo", key=f"rel_numero_{v}", max_chars=10, placeholder="Ex.: 120")
        referencia = c3.text_input("Ponto de referência", key=f"rel_referencia_{v}", max_chars=120,
                                   placeholder="Ex.: em frente à padaria")
        categoria = st.selectbox(
            "Você sabe o tipo de problema? (opcional)",
            opcoes,
            key=f"rel_categoria_{v}",
            format_func=lambda c: theme.nome_categoria(c) if c else "Não sei — deixar a IA sugerir",
            placeholder="Escolha uma opção",
        )
        foto = st.file_uploader(
            "Foto do problema (opcional)", type=["jpg", "jpeg", "png", "webp"], key=f"rel_foto_{v}",
            help="Para paredes, muros, viadutos e calçadas, a IA procura sinais de fissura na foto. "
                 "A foto não é guardada pelo serviço. Evite fotografar rostos e placas de carro.",
        )
        enviar = st.form_submit_button("Analisar meu relato", type="primary", icon="🔎", width="stretch")

    if not enviar:
        return
    erros = validar_relato(descricao, cep, numero, referencia)
    relato = {
        "descricao": " ".join(descricao.split()),
        "cep": re.sub(r"\D", "", cep),
        "numero": numero.strip() or None,
        "ponto_referencia": referencia.strip() or None,
        "categoria_sugerida": categoria or None,
    }
    session.guardar_relato(relato)  # o texto nunca se perde, mesmo com erro
    if erros:
        st.error("Faltam alguns ajustes antes de enviar:\n\n" + "\n".join(f"- {m}" for m in erros.values()), icon="✍️")
        return
    _analisar(relato, foto)


def _analisar_foto(foto) -> dict | None:
    """Visão computacional antes da triagem. Se falhar, o relato segue sem a foto."""
    conteudo = foto.getvalue()
    try:
        resultado = dados.cliente().analisar_imagem(foto.name, conteudo, foto.type or "image/jpeg")
    except ErroApi as erro:
        st.write(f"📷 Não usamos a foto: {components.seguro(erro.mensagem)} O relato segue sem ela.")
        session.guardar_foto_analise(None)
        return None
    session.guardar_foto_analise(resultado, visao.sobrepor_blocos(conteudo, resultado))
    achou = resultado["classe"] == "com_fissura"
    st.write(f"📷 Foto analisada em {resultado['latencia_ms'] / 1000:.1f}s: "
             + ("sinais de fissura encontrados." if achou else "nenhum sinal de fissura."))
    return visao.evidencia_para_relato(resultado)


def _analisar(relato: dict, foto=None) -> None:
    """Design para latência: etapas reais visíveis + barra de progresso enquanto a IA trabalha."""
    with st.status("Analisando seu relato…", expanded=True) as status:
        barra = st.progress(10, text="Conferindo o endereço pelo CEP…")
        try:
            end = dados.endereco_por_cep(relato["cep"])
            local = ", ".join(p for p in (end.get("logradouro"), end.get("bairro"), f"{end['cidade']}/{end['uf']}") if p)
            st.write(f"📍 Endereço encontrado: {components.seguro(local)}")
        except ErroApi as erro:
            if erro.fora_do_ar:
                status.update(label="Serviço indisponível", state="error", expanded=True)
                components.mostrar_erro(erro, acao="Seu texto continua no formulário acima.")
                return
            st.write("📍 Não confirmamos o endereço pelo CEP — a análise segue mesmo assim.")
        if foto is not None:
            barra.progress(25, text="Procurando sinais de fissura na foto…")
            relato["evidencia_visual"] = _analisar_foto(foto)
            session.guardar_relato(relato)
        else:
            session.guardar_foto_analise(None)
        barra.progress(40, text="A IA está lendo seu relato… isso costuma levar de 3 a 15 segundos.")
        try:
            resposta = dados.cliente().analisar(relato)
        except ErroApi as erro:
            barra.empty()
            status.update(label="Não foi possível concluir a análise", state="error", expanded=True)
            components.mostrar_erro(erro, acao="Seu texto continua no formulário acima: é só tentar de novo.")
            return
        barra.progress(100, text="Pronto!")
        status.update(label="Análise concluída", state="complete", expanded=False)
    session.receber_analise(resposta)
    st.rerun()


# ---------------- 2. revisão humana ----------------
def _revisao() -> None:
    resposta = session.obter("analise")
    an = resposta["analise"]
    st.subheader("Confira o que a IA entendeu", anchor=False)
    st.caption("A IA sugere; **você decide**. Nada é enviado à prefeitura antes da sua confirmação.")
    components.cartao_analise(resposta)
    _foto_analisada()
    acessibilidade.botao_ouvir(acessibilidade.texto_para_leitura(resposta))

    categorias = theme.opcoes_categoria(an["categoria"])
    with st.form("form_confirmacao", border=True):
        st.markdown("#### Está correto?")
        c1, c2 = st.columns(2)
        categoria_final = c1.selectbox("Tipo de problema", categorias, index=categorias.index(an["categoria"]),
                                       format_func=theme.nome_categoria,
                                       help="Se a IA errou o tipo, escolha o correto. O encaminhamento é recalculado.")
        urgencia_final = c2.selectbox(
            "Urgência", theme.ORDEM_URGENCIA, index=theme.ORDEM_URGENCIA.index(an["urgencia"]),
            format_func=lambda u: f"{theme.nome_urgencia(u)} — {theme.URGENCIA[u]['ajuda']}",
        )
        comentario = st.text_input("Quer explicar a correção? (opcional)", max_chars=300,
                                   placeholder="Ex.: na verdade o problema é a calçada, não a rua")
        contato = st.text_input("E-mail ou telefone para retorno (opcional)", max_chars=120,
                                help="Só a equipe responsável verá. Não aparece no painel público.")
        consentimento = st.checkbox(
            "Autorizo o uso destas informações apenas para tratar esta solicitação (LGPD). (obrigatório)"
        )
        b1, b2 = st.columns(2)
        confirmar = b1.form_submit_button("Confirmar e registrar", type="primary", icon="✅", width="stretch")
        voltar = b2.form_submit_button("Voltar e editar o relato", icon="✏️", width="stretch")

    if voltar:
        session.descartar_analise()
        st.rerun()
    if not confirmar:
        return

    problemas = []
    if not consentimento:
        problemas.append("Marque a autorização de uso dos dados para registrar.")
    if (msg := validar_contato(contato)) is not None:
        problemas.append(msg)
    if problemas:
        st.error("\n\n".join(problemas), icon="✍️")
        return
    if an.get("risco_imediato") and theme.ORDEM_URGENCIA.index(urgencia_final) > 0:
        st.warning("Você reduziu a urgência de um caso com risco imediato. Se houver perigo, ligue 193 ou 199.", icon="🚨")

    with st.spinner("Registrando sua solicitação…"):
        try:
            sol = dados.cliente().registrar({
                "analise_id": resposta["analise_id"],
                "categoria_final": categoria_final,
                "urgencia_final": urgencia_final,
                "comentario_cidadao": comentario.strip() or None,
                "contato": contato.strip() or None,
                "consentimento_lgpd": True,
            })
        except ErroApi as erro:
            components.mostrar_erro(erro, acao="Nada foi perdido: confira e tente confirmar de novo.")
            return
    dados.limpar_cache_dados()
    session.concluir_registro(sol)
    st.rerun()


def _foto_analisada() -> None:
    foto = session.obter("foto_analise")
    if not foto:
        return
    with st.container(border=True):
        st.markdown("**📷 O que a IA viu na sua foto**")
        c1, c2 = st.columns([2, 3], gap="large")
        c1.image(foto["imagem"], caption="Áreas marcadas em vermelho: possíveis fissuras", width="stretch")
        with c2:
            st.markdown(visao.resumo(foto["resultado"]))
            st.caption(f"Modelo {foto['resultado']['modelo']} · limiar {foto['resultado']['limiar']:.2f} · "
                       f"{foto['resultado']['latencia_ms'] / 1000:.2f}s. A equipe técnica decide se é preciso vistoria.")


# ---------------- 3. protocolo ----------------
def _sucesso() -> None:
    sol = session.obter("ultimo_registro")
    st.success("Pronto! Seu relato foi registrado e encaminhado.", icon="✅")
    st.markdown(f'<div class="zela-rotulo">Seu protocolo</div><div class="zela-protocolo" aria-live="polite">'
                f'{components.seguro(sol["protocolo"])}</div>', unsafe_allow_html=True)
    st.caption("Anote ou copie o número abaixo para acompanhar o andamento na aba “Minhas solicitações”.")
    st.code(sol["protocolo"], language=None)
    components.cartao_solicitacao(sol, modo="cidadao", mostrar_historico=False)
    avaliacao(sol, chave="sucesso")
    if sol.get("risco_imediato"):
        components.aviso_emergencia()
    if st.button("Relatar outro problema", icon="➕", type="primary"):
        session.novo_relato()
        st.rerun()
