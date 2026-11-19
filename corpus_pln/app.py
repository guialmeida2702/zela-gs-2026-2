"""Interface da ferramenta de construção de corpus (Streamlit).

    streamlit run app.py

Fluxo: enviar documentos -> escolher a limpeza -> conferir antes e depois -> gerar os três corpora ->
baixar os arquivos de treino e validação com a ficha do corpus.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from corpus import (
    FORMATOS,
    SISTEMA_PADRAO,
    Configuracao,
    ErroLeitura,
    OpcoesLimpeza,
    construir,
    ler_bytes,
    ler_texto_colado,
    pacote_zip,
    texto_limpo,
)
from corpus.exportacao import CORPORA, NOMES, arquivos, linha_de_treino

st.set_page_config(page_title="Corpus Zela · construção de corpus para fine-tuning", page_icon="📚", layout="wide")

DESCRICAO = {
    "texto_puro": "Trechos de texto corrido. Servem para adaptar o modelo ao vocabulário e ao estilo do domínio.",
    "perguntas_respostas": "Pares de pergunta e resposta. Servem para o ajuste por instrução (instruction tuning).",
    "conversacional": "Diálogos com papéis (system, user, assistant). Servem para ajustar modelos de chat.",
}
ORIGENS = {
    "texto_limpo": "texto limpo do documento", "estruturada": "colunas de pergunta e resposta do arquivo",
    "extraida": "pergunta escrita no próprio documento", "titulo_interrogativo": "título da seção em forma de pergunta",
    "derivada_do_titulo": "pergunta montada a partir do título (conferir)", "llm": "gerada por LLM e conferida por regra",
    "pares_da_fonte": "pares do mesmo documento em sequência", "recusa_modelo": "recusa fora do escopo (modelo fixo)",
}


@st.cache_data(show_spinner=False, max_entries=64)
def ler(nome: str, dados: bytes):
    """A leitura de PDF e DOCX é a parte lenta: o cache evita repeti-la a cada interação."""
    return ler_bytes(nome, dados)


def barra_lateral() -> tuple[OpcoesLimpeza, Configuracao]:
    with st.sidebar:
        st.header("Limpeza", anchor=False)
        op = OpcoesLimpeza(
            normalizar_unicode=st.checkbox("Normalizar caracteres (aspas, traços, espaços invisíveis)", True),
            remover_cabecalho_rodape=st.checkbox("Tirar cabeçalho, rodapé e número de página (PDF)", True),
            remover_ruido_web=st.checkbox("Tirar menus e botões de páginas web", True),
            juntar_linhas_quebradas=st.checkbox("Juntar linhas e palavras quebradas", True),
            mascarar_dados_pessoais=st.checkbox("Mascarar dados pessoais (CPF, e-mail, celular, RG, placa)", True,
                                                help="Deixe ligado sempre que os documentos tiverem relatos de pessoas."),
            remover_duplicados=st.checkbox("Tirar parágrafos repetidos entre documentos", True),
            remover_urls=st.checkbox("Tirar endereços de sites", False),
            minusculas=st.checkbox("Converter para minúsculas", False,
                                   help="Em geral não é recomendado para LLMs: maiúsculas carregam informação."),
            min_caracteres=st.number_input("Descartar parágrafos com menos de (caracteres)", 0, 400, 25, step=5),
        )
        preservar = st.text_input("Não mascarar (separe por ponto e vírgula)", placeholder="ex.: (11) 99999-0000; contato@orgao.gov.br",
                                  help="Contatos públicos que devem continuar no texto.")
        op.preservar = tuple(p.strip() for p in preservar.split(";") if p.strip())

        st.header("Corpora", anchor=False)
        cfg = Configuracao(
            tamanho_trecho=st.slider("Tamanho máximo do trecho de texto puro (caracteres)", 300, 3000, 1200, step=100),
            derivar_perguntas=st.checkbox("Montar perguntas a partir dos títulos das seções", True,
                                          help="Útil quando o documento não tem perguntas escritas. Confira o resultado."),
            turnos=st.slider("Pares por conversa", 1, 5, 3),
            incluir_recusas=st.checkbox("Incluir conversas de recusa fora do escopo", True),
            fracao_validacao=st.slider("Fração para validação", 0.0, 0.3, 0.1, step=0.05),
            semente=int(st.number_input("Semente do sorteio", 0, 10_000, 42)),
        )
        cfg.escopo = st.text_input("Assuntos que o assistente atende", "zeladoria urbana, segurança em chuvas e uso do Zela")
        cfg.sistema = st.text_area("Mensagem de sistema do corpus conversacional", SISTEMA_PADRAO, height=110)
    return op, cfg


def entrada() -> tuple[list, list[tuple[str, str]]]:
    st.subheader("1. Envie os documentos", anchor=False)
    enviados = st.file_uploader("Documentos (" + ", ".join(FORMATOS) + ")", type=[f.lstrip(".") for f in FORMATOS],
                                accept_multiple_files=True,
                                help="PDF com texto selecionável, DOCX, HTML, TXT, MD, CSV, JSON ou JSONL. Em CSV e JSON, "
                                     "colunas 'pergunta' e 'resposta' viram pares prontos.")
    colado = st.text_area("Ou cole um texto", height=100, placeholder="Cole aqui o texto de uma página ou documento.")
    documentos, erros = [], []
    for arquivo in enviados or []:
        try:
            documentos.append(ler(arquivo.name, arquivo.getvalue()))
        except ErroLeitura as exc:
            erros.append((arquivo.name, str(exc)))
    if colado.strip():
        try:
            documentos.append(ler_texto_colado(colado))
        except ErroLeitura as exc:
            erros.append(("texto colado", str(exc)))
    for nome, mensagem in erros:
        st.warning(f"**{nome}** não entrou no corpus: {mensagem}", icon="⚠️")
    return documentos, erros


def mostrar_limpeza(resultado) -> None:
    st.subheader("2. Confira a limpeza", anchor=False)
    linhas = []
    for d in resultado.documentos:
        r = d["relatorio"]
        linhas.append({"Documento": d["nome"], "Formato": d["formato"], "Caracteres antes": r.caracteres_antes,
                       "Caracteres depois": r.caracteres_depois, "Redução (%)": r.reducao_pct,
                       "Cabeçalho/rodapé": r.linhas_cabecalho_rodape, "Menus": r.linhas_ruido,
                       "Repetidos": r.paragrafos_duplicados, "Dados pessoais": sum(r.dados_pessoais.values()),
                       "Pares prontos": d["pares_estruturados"]})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    nomes = [d["nome"] for d in resultado.documentos]
    escolhido = st.selectbox("Ver antes e depois de", nomes)
    doc = next(x for x in st.session_state.documentos if x.nome == escolhido)
    antes, depois = st.columns(2)
    antes.markdown("**Antes**")
    antes.text_area("Texto original", doc.texto[:6000], height=320, disabled=True, label_visibility="collapsed")
    depois.markdown("**Depois**")
    depois.text_area("Texto limpo", texto_limpo(resultado.blocos[escolhido])[:6000], height=320, disabled=True,
                     label_visibility="collapsed")


def mostrar_corpora(resultado) -> None:
    st.subheader("3. Corpora gerados", anchor=False)
    colunas = st.columns(3)
    for coluna, corpus in zip(colunas, CORPORA, strict=True):
        e = resultado.estatisticas[corpus]
        coluna.metric(NOMES[corpus], f"{e['exemplos']} exemplos", f"{e['treino']} treino · {e['validacao']} validação",
                      delta_color="off", help=f"Cerca de {e['tokens_estimados']} tokens (estimativa de 4 caracteres por token).")
    abas = st.tabs([NOMES[c] for c in CORPORA])
    for aba, corpus in zip(abas, CORPORA, strict=True):
        with aba:
            st.caption(DESCRICAO[corpus])
            exemplos = resultado.corpora[corpus]
            if not exemplos:
                st.info("Nenhum exemplo foi gerado para este corpus com os documentos e as opções atuais.", icon="ℹ️")
                continue
            origem = pd.Series([ORIGENS.get(e["origem"], e["origem"]) for e in exemplos]).value_counts()
            st.markdown("**Origem dos exemplos:** " + " · ".join(f"{k}: {v}" for k, v in origem.items()))
            for e in exemplos[:6]:
                with st.expander(f"{e['fonte']} · {e.get('secao') or 'sem seção'} ({ORIGENS.get(e['origem'], e['origem'])})"):
                    st.code(json.dumps(linha_de_treino(corpus, e), ensure_ascii=False, indent=2), language="json", wrap_lines=True)
            if len(exemplos) > 6:
                st.caption(f"Mostrando 6 de {len(exemplos)} exemplos. Todos estão no pacote para baixar.")


def mostrar_downloads(resultado) -> None:
    st.subheader("4. Baixe os arquivos", anchor=False)
    st.download_button("Baixar tudo (.zip)", pacote_zip(resultado), "corpus_zela.zip", "application/zip", type="primary",
                       icon="📦")
    saida = arquivos(resultado)
    with st.expander("Arquivos individuais e ficha do corpus"):
        for nome, conteudo in saida.items():
            st.download_button(nome, conteudo.encode("utf-8"), nome, key=f"baixar_{nome}")
        st.markdown(saida["FICHA_DO_CORPUS.md"])


def main() -> None:
    st.title("📚 Construção de corpus para fine-tuning", anchor=False)
    st.caption("Envie documentos, confira a limpeza e baixe três corpora prontos para ajustar um LLM de pequeno porte: "
               "texto puro, perguntas e respostas e conversacional.")
    op, cfg = barra_lateral()
    documentos, erros = entrada()
    st.session_state.documentos = documentos
    if not documentos:
        st.info("Envie pelo menos um documento ou cole um texto para começar. A pasta `exemplos/` do projeto tem "
                "arquivos de teste em todos os formatos aceitos.", icon="📄")
        return
    with st.spinner("Limpando os documentos e montando os corpora..."):
        resultado = construir(documentos, op, cfg, erros=erros)
    mostrar_limpeza(resultado)
    mostrar_corpora(resultado)
    mostrar_downloads(resultado)
    st.caption("Antes de usar: leia uma amostra de cada corpus, confira se restou algum dado pessoal e verifique a "
               "licença dos documentos de origem.")


main()
