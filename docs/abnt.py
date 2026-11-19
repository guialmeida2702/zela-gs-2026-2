"""Gerador de documentos no padrão ABNT/FIAP com python-docx + LibreOffice.

Faz duas passagens: na primeira gera o .docx com números de página provisórios, converte para PDF
e descobre em que página caiu cada título, figura e quadro; na segunda preenche sumário e listas.
Regras aplicadas (NBR 14724): A4, margens 3 cm (sup./esq.) e 2 cm (inf./dir.), Arial 12, espaçamento
1,5, recuo de 1,25 cm, legendas acima das ilustrações com fonte abaixo, páginas pré-textuais contadas
a partir da folha de rosto e numeração exibida a partir da Introdução, no canto superior direito.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONTE = "Arial"


@dataclass
class Trabalho:
    instituicao: str
    curso: str
    autores: list[str]
    titulo: str
    subtitulo: str
    natureza: str
    local: str
    ano: str
    blocos: list[tuple] = field(default_factory=list)   # conteúdo textual (ver Gerador._bloco)
    referencias: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- utilidades de baixo nível
def _fonte(run, tamanho=12, negrito=False, italico=False, cor=None):
    run.font.name = FONTE
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    run.font.size = Pt(tamanho)
    run.bold = negrito
    run.italic = italico
    if cor:
        run.font.color.rgb = RGBColor.from_string(cor)


def _formato(par, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25, espaco=1.5, antes=0, depois=0, manter=False):
    pf = par.paragraph_format
    par.alignment = alinhamento
    pf.first_line_indent = Cm(recuo) if recuo else None
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if espaco == 1.5 else WD_LINE_SPACING.SINGLE
    pf.space_before = Pt(antes)
    pf.space_after = Pt(depois)
    pf.keep_with_next = manter
    pf.widow_control = True


def _texto_rico(par, texto: str, tamanho=12):
    """**negrito** e *itálico* simples dentro do parágrafo."""
    for pedaco in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", texto):
        if not pedaco:
            continue
        if pedaco.startswith("**"):
            _fonte(par.add_run(pedaco[2:-2]), tamanho, negrito=True)
        elif pedaco.startswith("*"):
            _fonte(par.add_run(pedaco[1:-1]), tamanho, italico=True)
        else:
            _fonte(par.add_run(pedaco), tamanho)


def _campo_pagina(par):
    run = par.add_run()
    for tipo, texto in (("begin", None), (None, "PAGE"), ("separate", None), (None, None), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
            run._r.append(el)
        elif texto:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texto
            run._r.append(el)
    _fonte(run, 10)


def _inicio_numeracao(secao, inicio: int):
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), str(inicio))
    secao._sectPr.append(pg)


def _bordas_tabela(tabela):
    tbl = tabela._tbl
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "808080")
        borders.append(b)
    tbl.tblPr.append(borders)


def _sombrear(celula, cor="E8F2F2"):
    tcPr = celula._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), cor)
    tcPr.append(shd)


def _repetir_cabecalho(linha):
    trPr = linha._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


# ---------------------------------------------------------------- gerador
class Gerador:
    def __init__(self, trabalho: Trabalho, paginas: dict[str, int] | None = None):
        self.t = trabalho
        self.paginas = paginas or {}
        self.doc = Document()
        self.figuras: list[str] = []
        self.quadros: list[str] = []
        self.tabelas: list[str] = []
        self.titulos: list[tuple[int, str]] = []
        self._preparar()

    def _preparar(self):
        estilo = self.doc.styles["Normal"]
        estilo.font.name = FONTE
        estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
        estilo.font.size = Pt(12)
        s = self.doc.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.top_margin, s.left_margin, s.bottom_margin, s.right_margin = Cm(3), Cm(3), Cm(2), Cm(2)
        s.header_distance = Cm(2)

    # ---------- elementos
    def _par(self, texto="", **fmt):
        p = self.doc.add_paragraph()
        _formato(p, **fmt)
        if texto:
            _texto_rico(p, texto)
        return p

    def _centro(self, texto, negrito=False, tamanho=12, antes=0, depois=0, maiusculas=False):
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.CENTER, recuo=0, antes=antes, depois=depois)
        _fonte(p.add_run(texto.upper() if maiusculas else texto), tamanho, negrito)
        return p

    def _quebra(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _espaco(self, n=1):
        for _ in range(n):
            p = self.doc.add_paragraph()
            _formato(p, recuo=0)

    # ---------- pré-textuais
    def capa(self):
        self._centro(self.t.instituicao, negrito=True, maiusculas=True)
        self._centro(self.t.curso, maiusculas=True)
        self._espaco(3)
        for a in self.t.autores:
            self._centro(a, maiusculas=True)
        self._espaco(6)
        self._centro(self.t.titulo, negrito=True, maiusculas=True)
        self._centro(self.t.subtitulo)
        self._espaco(9)
        self._centro(self.t.local)
        self._centro(self.t.ano)

    def folha_de_rosto(self):
        for a in self.t.autores:
            self._centro(a, maiusculas=True)
        self._espaco(7)
        self._centro(self.t.titulo, negrito=True, maiusculas=True)
        self._centro(self.t.subtitulo)
        self._espaco(3)
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=0, espaco=1)
        p.paragraph_format.left_indent = Cm(8)
        _fonte(p.add_run(self.t.natureza), 10)
        self._espaco(8)
        self._centro(self.t.local)
        self._centro(self.t.ano)

    def _lista(self, titulo, itens, prefixo):
        self._centro(titulo, negrito=True, maiusculas=True, depois=12)
        for i, legenda in enumerate(itens, 1):
            chave = f"{prefixo} {i}"
            self._linha_indice(f"{chave} – {legenda}", self.paginas.get(chave, 0), recuo_esq=0)

    def _linha_indice(self, texto, pagina, recuo_esq=0.0, negrito=False):
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, espaco=1.5)
        p.paragraph_format.left_indent = Cm(recuo_esq)
        tabs = p.paragraph_format.tab_stops
        from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
        tabs.add_tab_stop(Cm(16), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        _fonte(p.add_run(f"{texto}\t{pagina:02d}" if pagina else f"{texto}\t##"), 12, negrito)

    def sumario(self):
        self._centro("SUMÁRIO", negrito=True, depois=12)
        for nivel, titulo in self.titulos:
            numero = titulo.split(" ", 1)[0]
            self._linha_indice(titulo if nivel == 1 else titulo, self.paginas.get(titulo, 0),
                               recuo_esq=0, negrito=(nivel == 1 and numero[0].isdigit()))

    # ---------- textuais
    def _titulo(self, nivel, texto, nova_pagina=False):
        if nova_pagina:
            self._quebra()
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, antes=0 if nova_pagina else 12, depois=12, manter=True)
        _fonte(p.add_run(texto.upper() if nivel == 1 else texto), 12, negrito=True)
        self.titulos.append((nivel, texto.upper() if nivel == 1 else texto))

    def _legenda(self, tipo, titulo):
        lista = {"Figura": self.figuras, "Quadro": self.quadros, "Tabela": self.tabelas}[tipo]
        lista.append(titulo)
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.CENTER, recuo=0, espaco=1, antes=6, depois=3, manter=True)
        _fonte(p.add_run(f"{tipo} {len(lista)} – {titulo}"), 10, negrito=True)

    def _fonte_ilustracao(self, texto):
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, espaco=1, antes=3, depois=9)
        _fonte(p.add_run(f"Fonte: {texto}"), 10)

    def _quadro(self, tipo, titulo, colunas, linhas, fonte, larguras=None):
        self._legenda(tipo, titulo)
        tab = self.doc.add_table(rows=1, cols=len(colunas))
        tab.alignment = WD_TABLE_ALIGNMENT.CENTER
        _bordas_tabela(tab)
        for c, texto in zip(tab.rows[0].cells, colunas, strict=True):
            c.text = ""
            par = c.paragraphs[0]
            _formato(par, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, espaco=1)
            _fonte(par.add_run(texto), 9, negrito=True)
            _sombrear(c)
        _repetir_cabecalho(tab.rows[0])
        for linha in linhas:
            cels = tab.add_row().cells
            for c, texto in zip(cels, linha, strict=True):
                c.text = ""
                par = c.paragraphs[0]
                _formato(par, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, espaco=1)
                _texto_rico(par, str(texto), tamanho=9)
        if larguras:
            tab.autofit = False
            tblW = tab._tbl.tblPr.find(qn("w:tblW"))
            if tblW is None:
                tblW = OxmlElement("w:tblW")
                tab._tbl.tblPr.append(tblW)
            tblW.set(qn("w:type"), "dxa")
            tblW.set(qn("w:w"), str(int(sum(larguras) * 567)))
            for col, w in zip(tab.columns, larguras, strict=True):
                col.width = Cm(w)
            for gc, w in zip(tab._tbl.tblGrid.findall(qn("w:gridCol")), larguras, strict=True):
                gc.set(qn("w:w"), str(int(w * 567)))
            for linha in tab.rows:
                for c, w in zip(linha.cells, larguras, strict=True):
                    c.width = Cm(w)
        self._fonte_ilustracao(fonte)

    def _figura(self, titulo, caminho, fonte, largura=16):
        self._legenda("Figura", titulo)
        p = self.doc.add_paragraph()
        _formato(p, WD_ALIGN_PARAGRAPH.CENTER, recuo=0, espaco=1, manter=True)
        p.add_run().add_picture(str(caminho), width=Cm(largura))
        self._fonte_ilustracao(fonte)

    def _bloco(self, b):
        tipo = b[0]
        if tipo == "h1":
            self._titulo(1, b[1], nova_pagina=b[2] if len(b) > 2 else True)
        elif tipo == "h2":
            self._titulo(2, b[1])
        elif tipo == "h3":
            self._titulo(3, b[1])
        elif tipo == "p":
            self._par(b[1])
        elif tipo == "itens":
            for item in b[1]:
                p = self._par("", recuo=0)
                p.paragraph_format.left_indent = Cm(1.25)
                p.paragraph_format.first_line_indent = Cm(-0.5)
                _texto_rico(p, "• " + item)
        elif tipo == "nota":
            p = self.doc.add_paragraph()
            _formato(p, WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=0, espaco=1, antes=6, depois=6)
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.right_indent = Cm(1)
            _fonte(p.add_run(b[1]), 11, italico=True, cor="5A5A5A")
        elif tipo in ("quadro", "tabela"):
            self._quadro("Quadro" if tipo == "quadro" else "Tabela", *b[1:])
        elif tipo == "figura":
            self._figura(*b[1:])
        else:
            raise ValueError(tipo)

    def referencias(self):
        self._titulo(1, "REFERÊNCIAS", nova_pagina=True)
        for ref in self.t.referencias:
            p = self.doc.add_paragraph()
            _formato(p, WD_ALIGN_PARAGRAPH.LEFT, recuo=0, espaco=1, depois=12)
            _texto_rico(p, ref)

    # ---------- montagem
    def montar(self) -> Document:
        # 1ª passagem "a seco" só para conhecer títulos e legendas (o sumário vem antes do texto)
        if not self.titulos:
            seco = Gerador(self.t, self.paginas)
            seco._corpo()
            self.titulos, self.figuras, self.quadros, self.tabelas = seco.titulos, seco.figuras, seco.quadros, seco.tabelas
        titulos, figuras, quadros, tabelas = self.titulos, self.figuras, self.quadros, self.tabelas
        self.capa()
        # seção 2: folha de rosto e pré-textuais (contadas a partir de 1, sem número visível)
        s2 = self.doc.add_section(WD_SECTION.NEW_PAGE)
        _inicio_numeracao(s2, 1)
        self.folha_de_rosto()
        self._quebra()
        # listas de ilustrações e de tabelas na mesma página, para caber no limite de páginas do enunciado
        primeira = True
        for titulo, itens, prefixo in (("Lista de figuras", figuras, "Figura"), ("Lista de quadros", quadros, "Quadro"),
                                       ("Lista de tabelas", tabelas, "Tabela")):
            if itens:
                if not primeira:
                    self._espaco(1)
                self._lista(titulo, itens, prefixo)
                primeira = False
        if not primeira:
            self._quebra()
        self.titulos = titulos
        self.sumario()
        # seção 3: texto, com número visível no canto superior direito
        s3 = self.doc.add_section(WD_SECTION.NEW_PAGE)
        for pg in s3._sectPr.findall(qn("w:pgNumType")):  # add_section copia o reinício da seção anterior
            s3._sectPr.remove(pg)
        s3.header.is_linked_to_previous = False
        cab = s3.header.paragraphs[0]
        cab.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _campo_pagina(cab)
        for s in self.doc.sections[:2]:
            s.header.is_linked_to_previous = False
        self.figuras, self.quadros, self.tabelas, self.titulos = [], [], [], []
        self._corpo(primeira_sem_quebra=True)
        return self.doc

    def _corpo(self, primeira_sem_quebra=False):
        primeiro = True
        for b in self.t.blocos:
            if b[0] == "h1" and primeiro and primeira_sem_quebra:
                self._titulo(1, b[1], nova_pagina=False)
            else:
                self._bloco(b)
            primeiro = False
        self.referencias()


# ---------------------------------------------------------------- PDF e paginação
def para_pdf(docx: Path, destino: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    with tempfile.TemporaryDirectory() as perfil:
        subprocess.run([soffice, f"-env:UserInstallation=file://{perfil}", "--headless", "--convert-to", "pdf",
                        "--outdir", str(destino), str(docx)], check=True, capture_output=True, timeout=300)
    return destino / (docx.stem + ".pdf")


def descobrir_paginas(pdf: Path, titulos: list[str], legendas: list[str]) -> dict[str, int]:
    """Página exibida (ABNT: física - 1, porque a capa não conta) de cada título e legenda, procurando
    só depois do sumário."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    textos = [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"], capture_output=True,
                             text=True).stdout for i in range(1, n + 1)]
    inicio = next(i for i, t in enumerate(textos) if "SUMÁRIO" in t) + 1
    achados: dict[str, int] = {}

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    for chave in [*titulos, *legendas]:
        alvo = norm(chave)[:60] + (" –" if re.fullmatch(r"(Figura|Quadro|Tabela) \d+", chave) else "")
        for i in range(inicio, n):
            linhas = [norm(linha) for linha in textos[i].splitlines()]
            if any(linha.startswith(alvo) for linha in linhas):
                achados[chave] = i  # índice 0-based = página física - 1 = página exibida
                break
    return achados


def gerar(trabalho: Trabalho, saida_docx: Path, saida_pdf_dir: Path) -> Path:
    g = Gerador(trabalho)
    g.montar().save(saida_docx)
    pdf = para_pdf(saida_docx, saida_pdf_dir)
    legendas = ([f"Figura {i}" for i in range(1, len(g.figuras) + 1)] + [f"Quadro {i}" for i in range(1, len(g.quadros) + 1)]
                + [f"Tabela {i}" for i in range(1, len(g.tabelas) + 1)])
    paginas = descobrir_paginas(pdf, [t for _, t in g.titulos], legendas)
    g2 = Gerador(trabalho, paginas)
    g2.montar().save(saida_docx)
    return para_pdf(saida_docx, saida_pdf_dir)
