"""Testes da ferramenta de construção de corpus (leitura, limpeza, geração, exportação e interface)."""

import io
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from corpus import (  # noqa: E402
    Configuracao,
    ErroLeitura,
    OpcoesLimpeza,
    construir,
    exportar,
    gerar_pares_com_llm,
    ler_bytes,
    limpar,
    validar_pasta,
)
from corpus.geradores import pares_no_texto  # noqa: E402
from corpus.limpeza import mascarar_dados_pessoais  # noqa: E402

EXEMPLOS = RAIZ / "exemplos"


# ---------------------------------------------------------------- leitura
def test_formato_nao_aceito_e_arquivo_vazio_tem_mensagem_clara():
    with pytest.raises(ErroLeitura, match="não aceito"):
        ler_bytes("planilha.xlsx", b"qualquer coisa")
    with pytest.raises(ErroLeitura, match="vazio"):
        ler_bytes("nota.txt", b"   ")


def test_pdf_sem_texto_selecionavel_e_recusado():
    from reportlab.pdfgen import canvas

    memoria = io.BytesIO()
    pdf = canvas.Canvas(memoria)
    pdf.rect(50, 50, 100, 100)  # só um desenho, nenhum texto
    pdf.save()
    with pytest.raises(ErroLeitura, match="selecionável"):
        ler_bytes("digitalizado.pdf", memoria.getvalue())


def test_csv_com_colunas_de_pergunta_e_resposta_vira_pares_prontos():
    dados = "pergunta;resposta\nComo peço a poda?;Pelo telefone 156 ou pelo portal SP156.\n".encode()
    doc = ler_bytes("faq.csv", dados)
    assert doc.pares == [("Como peço a poda?", "Pelo telefone 156 ou pelo portal SP156.")]


def test_html_perde_menu_script_e_rodape_e_guarda_os_titulos():
    html = ("<html><head><title>Página</title><script>alert(1)</script></head><body><nav>Início Serviços</nav>"
            "<h1>Iluminação</h1><p>Informe o endereço do poste apagado.</p><footer>Todos os direitos</footer></body></html>")
    doc = ler_bytes("pagina.html", html.encode())
    assert "# Iluminação" in doc.texto and "endereço do poste" in doc.texto
    assert "alert" not in doc.texto and "Início Serviços" not in doc.texto and "direitos" not in doc.texto
    assert doc.metadados["titulo"] == "Página"


def test_jsonl_invalido_aponta_a_linha():
    with pytest.raises(ErroLeitura, match="linha 2"):
        ler_bytes("dados.jsonl", b'{"texto": "ok"}\n{quebrado\n')


# ---------------------------------------------------------------- limpeza
def test_mascara_dados_pessoais_e_preserva_contatos_publicos():
    texto = ("Meu CPF é 123.456.789-09, celular (11) 98765-4321, e-mail ana.souza@exemplo.com e placa ABC1D23. "
             "Sabesp: 0800 055 0195. Escreva para ouvidoria@prefeitura.sp.gov.br. Emergência: 193.")
    limpo, contagem = mascarar_dados_pessoais(texto)
    assert mascarar_dados_pessoais("O CPF dele é 123.456.789-09.")[0] == "O CPF dele é [CPF]."  # ponto final logo depois
    assert "[CPF]" in limpo and "[TELEFONE]" in limpo and "[EMAIL]" in limpo and "[PLACA]" in limpo
    assert "0800 055 0195" in limpo and "ouvidoria@prefeitura.sp.gov.br" in limpo and "193" in limpo
    assert contagem == {"EMAIL": 1, "CPF": 1, "TELEFONE": 1, "PLACA": 1}
    preservado, _ = mascarar_dados_pessoais("Plantão: (11) 99999-0000.", preservar=("(11) 99999-0000",))
    assert "(11) 99999-0000" in preservado


def test_pdf_perde_cabecalho_rodape_e_hifenizacao():
    doc = ler_bytes("cartilha.pdf", (EXEMPLOS / "cartilha_chuvas_sintetica.pdf").read_bytes())
    blocos, rel = limpar(doc, OpcoesLimpeza())
    texto = " ".join(b.texto for b in blocos)
    assert "Cartilha de exemplo - Zela" not in texto and "Página 1 de 3" not in texto
    assert rel.linhas_cabecalho_rodape >= 6 and rel.hifens_unidos >= 1
    assert "-\n" not in texto
    assert any(b.tipo == "titulo" and b.texto == "O que fazer durante um alagamento" for b in blocos)


def test_paragrafo_repetido_em_outro_documento_sai_uma_vez():
    a = ler_bytes("a.txt", "Primeiro documento com um parágrafo bem longo sobre limpeza de bueiros.\n".encode())
    b = ler_bytes("b.txt", "Primeiro documento com um parágrafo bem longo sobre limpeza de bueiros.\n".encode())
    vistos: set[str] = set()
    blocos_a, _ = limpar(a, OpcoesLimpeza(), vistos)
    blocos_b, rel_b = limpar(b, OpcoesLimpeza(), vistos)
    assert len(blocos_a) == 1 and blocos_b == [] and rel_b.paragrafos_duplicados == 1


# ---------------------------------------------------------------- geração
def test_pergunta_no_meio_do_texto_vira_par_e_pergunta_retorica_nao():
    texto = ("A Subprefeitura cuida de 162 mil árvores. Tá afim de ajudar? Saiba mais. Quanto tempo leva o serviço? "
             "Após a solicitação a Subprefeitura tem o prazo máximo de 120 dias.")
    assert pares_no_texto(texto) == [("Quanto tempo leva o serviço?", "Após a solicitação a Subprefeitura tem o prazo máximo de 120 dias.")]


def test_exemplos_geram_os_tres_corpora_com_rastreabilidade(tmp_path):
    from corpus import ler_arquivo

    documentos = [ler_arquivo(p) for p in sorted(EXEMPLOS.iterdir()) if p.suffix != ".py"]
    resultado = construir(documentos, OpcoesLimpeza(), Configuracao(escopo="zeladoria urbana"))
    for corpus in ("texto_puro", "perguntas_respostas", "conversacional"):
        assert resultado.corpora[corpus], corpus
    origens = {e["origem"] for e in resultado.corpora["perguntas_respostas"]}
    assert {"estruturada", "extraida"} <= origens
    pares = {e["pergunta"]: e["resposta"] for e in resultado.corpora["perguntas_respostas"]}
    assert "120 dias" in pares["Feita a solicitação, quanto tempo leva até a realização do serviço?"]
    # dados pessoais fictícios dos relatos e do DOCX não chegam ao corpus
    tudo = json.dumps(resultado.corpora, ensure_ascii=False)
    assert "123.456.789-09" not in tudo and "98765-4321" not in tudo and "joao.ficticio@exemplo.com" not in tudo
    # divisão por documento: nenhum arquivo aparece no treino e na validação ao mesmo tempo
    treino, validacao = resultado.divisoes["texto_puro"]
    assert validacao and not ({e["fonte"] for e in treino} & {e["fonte"] for e in validacao})

    exportar(resultado, tmp_path)
    assert validar_pasta(tmp_path) == []
    linha = json.loads((tmp_path / "conversacional_treino.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [m["role"] for m in linha["messages"]][:3] == ["system", "user", "assistant"]
    assert (tmp_path / "rastreabilidade.csv").read_text(encoding="utf-8").startswith("corpus;divisao;linha;fonte")
    assert "Ficha do corpus" in (tmp_path / "FICHA_DO_CORPUS.md").read_text(encoding="utf-8")


def test_conferencia_acha_dado_pessoal_e_conversa_mal_formada(tmp_path):
    for corpus in ("texto_puro", "perguntas_respostas", "conversacional"):
        for divisao in ("treino", "validacao"):
            (tmp_path / f"{corpus}_{divisao}.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "texto_puro_treino.jsonl").write_text(json.dumps({"text": "Meu CPF é 123.456.789-09."}) + "\n", encoding="utf-8")
    (tmp_path / "conversacional_treino.jsonl").write_text(
        json.dumps({"messages": [{"role": "assistant", "content": "Olá"}]}) + "\n", encoding="utf-8")
    problemas = validar_pasta(tmp_path)
    assert any("CPF" in p for p in problemas) and any("papéis" in p for p in problemas)


class _RespostaFalsa:
    def __init__(self, conteudo: str):
        self.conteudo = conteudo

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.conteudo}}]}


class _ClienteFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)

    def post(self, *args, **kwargs):
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return _RespostaFalsa(resposta)


def test_pares_do_llm_sao_conferidos_e_falha_nao_interrompe():
    trechos = [{"text": "A subprefeitura tem o prazo máximo de 120 dias para atender o pedido de poda.", "fonte": "a", "secao": ""},
               {"text": "Outro trecho qualquer sobre calçadas.", "fonte": "b", "secao": ""},
               {"text": "Terceiro trecho.", "fonte": "c", "secao": ""}]
    respostas = [
        json.dumps([{"pergunta": "Qual o prazo para a poda?", "resposta": "A subprefeitura tem até 120 dias para atender o pedido."},
                    {"pergunta": "Quem fabrica as motosserras?", "resposta": "Uma empresa sueca fundada em 1689 em Huskvarna."}]),
        TimeoutError("sem resposta"),
        "isto não é JSON",
    ]
    pares, resumo = gerar_pares_com_llm(trechos, "http://teste/v1", "modelo", cliente=_ClienteFalso(respostas))
    assert [p["pergunta"] for p in pares] == ["Qual o prazo para a poda?"]
    assert resumo == {"trechos": 3, "pares_aceitos": 1, "pares_rejeitados": 1, "chamadas_com_falha": 2}


# ---------------------------------------------------------------- interface
def test_interface_abre_e_mostra_os_tres_corpora_com_um_texto_colado():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert any("Envie pelo menos um documento" in i.value for i in at.info)
    at.text_area[0].input("# Poda\n\nComo peço a poda de uma árvore?\n\nPelo telefone 156 ou pelo portal SP156, "
                          "informando o endereço. Meu celular é (11) 98765-4321.").run()
    assert not at.exception
    assert [m.label for m in at.metric] == ["Texto puro", "Perguntas e respostas", "Conversacional"]
    assert "98765-4321" not in str(at.text_area[-1].value)
