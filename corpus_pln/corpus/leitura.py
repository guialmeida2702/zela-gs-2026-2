"""Leitura de documentos de vários formatos (TXT, MD, HTML, PDF, DOCX, CSV, JSON, JSONL).

Cada leitor devolve um `Documento` com o texto bruto. Títulos são marcados no padrão do
Markdown ("# Título"), para que a limpeza e a segmentação tratem todos os formatos da mesma forma.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

FORMATOS = (".txt", ".md", ".html", ".htm", ".pdf", ".docx", ".csv", ".json", ".jsonl")

# Nomes de coluna ou de campo aceitos para perguntas, respostas e texto corrido
_CAMPOS_PERGUNTA = ("pergunta", "question", "duvida", "dúvida", "instruction", "prompt", "entrada")
_CAMPOS_RESPOSTA = ("resposta", "answer", "output", "completion", "saida", "saída")
_CAMPOS_TEXTO = ("texto", "text", "conteudo", "conteúdo", "content", "descricao", "descrição", "corpo")


class ErroLeitura(Exception):
    """Arquivo que não pôde ser lido. A mensagem pode ser mostrada a quem enviou o arquivo."""


@dataclass
class Documento:
    nome: str
    formato: str
    texto: str
    pares: list[tuple[str, str]] = field(default_factory=list)  # perguntas e respostas já estruturadas na origem
    paginas: list[str] = field(default_factory=list)            # PDF: uma entrada por página
    metadados: dict[str, str] = field(default_factory=dict)

    @property
    def titulo(self) -> str:
        return self.metadados.get("titulo") or Path(self.nome).stem.replace("_", " ").replace("-", " ")


def _decodificar(dados: bytes) -> str:
    for codificacao in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1", errors="replace")


def _separar_cabecalho(texto: str) -> tuple[dict[str, str], str]:
    """Cabeçalho no início do arquivo, entre linhas '---', com pares 'chave: valor' (fonte, URL, data da consulta)."""
    achado = re.match(r"^---\n(.*?)\n---\n", texto, flags=re.S)
    if not achado:
        return {}, texto
    metadados = {}
    for linha in achado.group(1).splitlines():
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            metadados[chave.strip().lower()] = valor.strip()
    return metadados, texto[achado.end():]


class _TextoDeHtml(HTMLParser):
    """Extrai o texto visível de uma página e descarta menus, rodapés, scripts e formulários."""

    _IGNORAR = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "button", "iframe"}
    _BLOCO = {"p", "div", "section", "article", "tr", "table", "ul", "ol", "br", "blockquote", "main", "dd", "dt"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self.titulo_pagina = ""
        self._ignorando = 0
        self._em_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._IGNORAR:
            self._ignorando += 1
        elif tag == "title":
            self._em_title = True
        elif self._ignorando:
            return
        elif re.fullmatch(r"h[1-6]", tag):
            self.partes.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.partes.append("\n- ")
        elif tag in self._BLOCO:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self._IGNORAR:
            self._ignorando = max(0, self._ignorando - 1)
        elif tag == "title":
            self._em_title = False
        elif not self._ignorando and (re.fullmatch(r"h[1-6]", tag) or tag in {"p", "div", "li", "tr", "table", "ul", "ol"}):
            self.partes.append("\n")

    def handle_data(self, dados):
        if self._em_title:
            self.titulo_pagina += dados.strip()
        elif not self._ignorando:
            self.partes.append(dados)


def _ler_html(texto: str) -> tuple[str, dict[str, str]]:
    leitor = _TextoDeHtml()
    leitor.feed(texto)
    corpo = "".join(leitor.partes)
    return corpo, ({"titulo": leitor.titulo_pagina} if leitor.titulo_pagina else {})


def _ler_pdf(dados: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depende da instalação
        raise ErroLeitura("Para ler PDF, instale o pacote pypdf.") from exc
    try:
        leitor = PdfReader(io.BytesIO(dados))
        paginas = [(pagina.extract_text() or "") for pagina in leitor.pages]
    except Exception as exc:
        raise ErroLeitura(f"O PDF não pôde ser lido ({type(exc).__name__}).") from exc
    if not any(p.strip() for p in paginas):
        raise ErroLeitura("O PDF não tem texto selecionável (parece ser uma imagem digitalizada).")
    return paginas


def _ler_docx(dados: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - depende da instalação
        raise ErroLeitura("Para ler DOCX, instale o pacote python-docx.") from exc
    try:
        documento = Document(io.BytesIO(dados))
    except Exception as exc:
        raise ErroLeitura(f"O DOCX não pôde ser lido ({type(exc).__name__}).") from exc
    linhas = []
    for paragrafo in documento.paragraphs:
        texto = paragrafo.text.strip()
        if not texto:
            linhas.append("")
            continue
        estilo = (paragrafo.style.name or "").lower() if paragrafo.style is not None else ""
        nivel = re.search(r"(?:heading|t[ií]tulo)\s*(\d)", estilo)
        if nivel:
            linhas += ["", "#" * int(nivel.group(1)) + " " + texto, ""]
        elif estilo.startswith("title") or estilo == "título":
            linhas += ["", "# " + texto, ""]
        elif "list" in estilo or "lista" in estilo:
            linhas.append("- " + texto)
        else:
            linhas += [texto, ""]
    for tabela in documento.tables:
        linhas.append("")
        for linha in tabela.rows:
            celulas = [c.text.strip() for c in linha.cells if c.text.strip()]
            if celulas:
                linhas.append(" | ".join(celulas))
        linhas.append("")
    return "\n".join(linhas)


def _campo(registro: dict, nomes: tuple[str, ...]) -> str:
    for chave, valor in registro.items():
        if str(chave).strip().lower() in nomes and valor is not None and str(valor).strip():
            return str(valor).strip()
    return ""


def _de_registros(registros: list[dict]) -> tuple[str, list[tuple[str, str]]]:
    """Registros tabulares: pares pergunta/resposta quando as colunas existem; senão, texto corrido."""
    pares, textos = [], []
    for registro in registros:
        if not isinstance(registro, dict):
            textos.append(str(registro))
            continue
        pergunta, resposta = _campo(registro, _CAMPOS_PERGUNTA), _campo(registro, _CAMPOS_RESPOSTA)
        if pergunta and resposta:
            pares.append((pergunta, resposta))
            continue
        texto = _campo(registro, _CAMPOS_TEXTO)
        if texto:
            textos.append(texto)
        else:
            textos.append("; ".join(f"{k}: {v}" for k, v in registro.items() if v not in (None, "")))
    return "\n\n".join(t for t in textos if t), pares


def _ler_csv(texto: str) -> tuple[str, list[tuple[str, str]]]:
    amostra = texto[:4000]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
    except csv.Error:
        dialeto = csv.excel
        dialeto.delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
    return _de_registros(list(csv.DictReader(io.StringIO(texto), dialect=dialeto)))


def _ler_json(texto: str, linhas: bool) -> tuple[str, list[tuple[str, str]]]:
    if linhas:
        dados = []
        for numero, linha in enumerate(texto.splitlines(), start=1):
            if not linha.strip():
                continue
            try:
                dados.append(json.loads(linha))
            except json.JSONDecodeError as exc:
                raise ErroLeitura(f"JSON inválido (linha {numero}).") from exc
    else:
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ErroLeitura(f"JSON inválido (linha {exc.lineno}).") from exc
    if isinstance(dados, dict):
        # formatos comuns: {"perguntas": [...]}, {"data": [...]} ou um único registro
        listas = [v for v in dados.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        dados = listas[0] if listas else [dados]
    if not isinstance(dados, list):
        dados = [dados]
    return _de_registros(dados)


def ler_bytes(nome: str, dados: bytes) -> Documento:
    """Lê um arquivo enviado (nome + conteúdo). Levanta ErroLeitura com mensagem clara se não conseguir."""
    formato = Path(nome).suffix.lower()
    if formato not in FORMATOS:
        raise ErroLeitura(f"Formato {formato or '(sem extensão)'} não aceito. Use: {', '.join(FORMATOS)}.")
    if not dados.strip():
        raise ErroLeitura("O arquivo está vazio.")
    pares: list[tuple[str, str]] = []
    paginas: list[str] = []
    metadados: dict[str, str] = {}
    if formato == ".pdf":
        paginas = _ler_pdf(dados)
        texto = "\n\n".join(paginas)
    elif formato == ".docx":
        texto = _ler_docx(dados)
    else:
        bruto = _decodificar(dados).replace("\r\n", "\n").replace("\r", "\n")
        if formato in (".html", ".htm"):
            texto, metadados = _ler_html(bruto)
        elif formato == ".csv":
            texto, pares = _ler_csv(bruto)
        elif formato in (".json", ".jsonl"):
            texto, pares = _ler_json(bruto, linhas=formato == ".jsonl")
        else:
            metadados, texto = _separar_cabecalho(bruto)
    if not texto.strip() and not pares:
        raise ErroLeitura("Não encontrei texto neste arquivo.")
    return Documento(nome=Path(nome).name, formato=formato, texto=texto, pares=pares, paginas=paginas, metadados=metadados)


def ler_arquivo(caminho: str | Path) -> Documento:
    caminho = Path(caminho)
    return ler_bytes(caminho.name, caminho.read_bytes())


def ler_texto_colado(texto: str, nome: str = "texto_colado.txt") -> Documento:
    return ler_bytes(nome, texto.encode("utf-8"))
