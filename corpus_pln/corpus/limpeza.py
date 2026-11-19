"""Limpeza e normalização do texto antes de montar os corpora.

Cada etapa pode ser ligada ou desligada e deixa uma contagem no relatório, para que a pessoa
veja o que saiu do texto. Nada é removido em silêncio.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from .leitura import Documento


@dataclass
class OpcoesLimpeza:
    normalizar_unicode: bool = True
    remover_cabecalho_rodape: bool = True
    remover_ruido_web: bool = True
    juntar_linhas_quebradas: bool = True
    remover_urls: bool = False
    mascarar_dados_pessoais: bool = True
    remover_duplicados: bool = True
    minusculas: bool = False
    min_caracteres: int = 25
    # Trechos que nunca são mascarados (por exemplo, o celular de plantão de um órgão público)
    preservar: tuple[str, ...] = ()


@dataclass
class RelatorioLimpeza:
    caracteres_antes: int = 0
    caracteres_depois: int = 0
    linhas_cabecalho_rodape: int = 0
    linhas_ruido: int = 0
    hifens_unidos: int = 0
    linhas_unidas: int = 0
    urls_removidas: int = 0
    dados_pessoais: dict[str, int] = field(default_factory=dict)
    paragrafos_duplicados: int = 0
    paragrafos_curtos: int = 0

    @property
    def reducao_pct(self) -> float:
        if not self.caracteres_antes:
            return 0.0
        return round(100 * (1 - self.caracteres_depois / self.caracteres_antes), 1)


@dataclass
class Bloco:
    tipo: str  # "titulo", "paragrafo" ou "item"
    texto: str
    nivel: int = 0


# ---------------------------------------------------------------- unicode
_TROCAS = str.maketrans({
    " ": " ", " ": " ", " ": " ", " ": " ", "​": "", "‌": "", "‍": "",
    "﻿": "", "­": "", "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "−": "-",
    "…": "...", "ﬁ": "fi", "ﬂ": "fl", "•": "-", "●": "-", "▪": "-", "◦": "-", "‣": "-", "\t": " ", "\f": "\n",
})
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalizar_unicode(texto: str) -> str:
    """Forma NFC, aspas e traços simples, sem caracteres invisíveis ou de controle."""
    texto = unicodedata.normalize("NFC", texto).translate(_TROCAS)
    return _CONTROLE.sub("", texto)


# ---------------------------------------------------------------- cabeçalho, rodapé e ruído de página web
_NUMERO_DE_PAGINA = re.compile(r"^(?:p[aá]gina|p[aá]g\.?|page)?\s*\d{1,4}\s*(?:(?:de|/|of)\s*\d{1,4})?$", re.I)
_RUIDO_WEB = re.compile(
    r"^(?:compartilh\w*|imprimir|voltar ao topo|ir para o conte[uú]do|pular para o conte[uú]do|menu|buscar|pesquisar|"
    r"aceit\w+ (?:os |todos os )?cookies.*|siga-nos.*|leia mais|saiba mais|mapa do site|acessibilidade|alto contraste|"
    r"facebook|twitter|instagram|whatsapp|youtube|linkedin|copiar link|tamanho da fonte.*|a\+|a-|fechar|"
    r"todos os direitos reservados.*|©.*)$", re.I)


def _assinatura(linha: str) -> str:
    return re.sub(r"\d+", "#", linha.strip().lower())


def linhas_repetidas(paginas: list[str]) -> set[str]:
    """Linhas que aparecem nas bordas de pelo menos 60% das páginas: cabeçalho ou rodapé."""
    if len(paginas) < 3:
        return set()
    contagem: Counter[str] = Counter()
    for pagina in paginas:
        linhas = [linha for linha in pagina.splitlines() if linha.strip()]
        for assinatura in {_assinatura(linha) for linha in linhas[:3] + linhas[-3:]}:
            contagem[assinatura] += 1
    minimo = max(3, round(0.6 * len(paginas)))
    return {assinatura for assinatura, n in contagem.items() if n >= minimo}


# ---------------------------------------------------------------- dados pessoais
_EMAIL_INSTITUCIONAL = re.compile(
    r"^(?:contato|atendimento|ouvidoria|sac|faleconosco|fale\.conosco|imprensa|suporte|comunicacao|protocolo|gabinete|"
    r"secretaria|defesacivil|central)\b", re.I)
_DADOS_PESSOAIS = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    # não pode estar colado a outro número; o ponto final da frase logo depois do CPF é permitido
    ("CPF", re.compile(r"(?<!\d)(?<!\d\.)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)(?!\.\d)")),
    ("TELEFONE", re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9\s?\d{4}[-\s.]?\d{4}(?!\d)")),  # celular com DDD
    ("RG", re.compile(r"\bRG\s*(?:n[ºo.]*\s*)?:?\s*\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]\b", re.I)),
    ("PLACA", re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b")),
]
_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"']*[^\s<>\"'.,;:!?)]")


def mascarar_dados_pessoais(texto: str, preservar: tuple[str, ...] = ()) -> tuple[str, dict[str, int]]:
    """Troca CPF, e-mail pessoal, celular, RG e placa por marcadores. Telefones fixos, 0800 e números de serviço
    (156, 193) ficam, porque são informação pública útil. É uma heurística: a lista de `preservar` e a revisão
    humana do resultado cobrem o que ela erra."""
    guardados: dict[str, str] = {}
    for i, trecho in enumerate(t for t in preservar if t):
        chave = f"\x00{i}\x00"
        guardados[chave] = trecho
        texto = texto.replace(trecho, chave)
    contagem: dict[str, int] = {}

    def trocar(tipo: str):
        def _trocar(achado: re.Match) -> str:
            if tipo == "EMAIL" and _EMAIL_INSTITUCIONAL.match(achado.group(0)):
                return achado.group(0)
            contagem[tipo] = contagem.get(tipo, 0) + 1
            return f"[{tipo}]"
        return _trocar

    for tipo, padrao in _DADOS_PESSOAIS:
        texto = padrao.sub(trocar(tipo), texto)
    for chave, trecho in guardados.items():
        texto = texto.replace(chave, trecho)
    return texto, contagem


# ---------------------------------------------------------------- blocos
_ITEM = re.compile(r"^(?:[-*+]\s+|\d{1,2}[.)]\s+)")
_TITULO_MD = re.compile(r"^(#{1,6})\s+(.*\S)\s*#*$")
_TITULO_NUMERADO = re.compile(r"^\d{1,2}(?:\.\d{1,2})*[.)]?\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]")
_FIM_DE_FRASE = re.compile(r"[.!?:;]$")


def _em_caixa_alta(linha: str) -> bool:
    letras = [c for c in linha if c.isalpha()]
    return len(letras) >= 4 and len(linha) <= 90 and all(c.isupper() for c in letras) and not re.search(r"[.;,]$", linha)


def _eh_titulo_solto(linha: str) -> bool:
    """Linha sozinha no bloco que funciona como título em texto sem marcação (TXT e PDF)."""
    if len(linha) > 90 or len(linha) < 3:
        return False
    if linha.endswith("?"):
        return True
    if re.search(r"[.;:,]$", linha):
        return False
    if _em_caixa_alta(linha):
        return True
    return bool(_TITULO_NUMERADO.match(linha)) and len(linha) <= 70


def _texto_de_titulo(linha: str) -> str:
    """Tira a numeração ("2.1 ") e passa títulos em caixa alta para a forma de frase."""
    texto = re.sub(r"^\d{1,2}(?:\.\d{1,2})*[.)]?\s+", "", linha).strip()
    return texto.capitalize() if _em_caixa_alta(texto) else texto


def _fechar_paragrafo(blocos: list[Bloco], linhas: list[str]) -> None:
    if linhas:
        blocos.append(Bloco("paragrafo", " ".join(linhas)))
        linhas.clear()


def _blocos(texto: str, estruturado: bool, juntar: bool, rel: RelatorioLimpeza) -> list[Bloco]:
    blocos: list[Bloco] = []
    for trecho in re.split(r"\n\s*\n", texto):
        linhas = [re.sub(r"\s+", " ", linha).strip() for linha in trecho.splitlines()]
        linhas = [linha for linha in linhas if linha]
        if not linhas:
            continue
        if len(linhas) == 1 and not _TITULO_MD.match(linhas[0]) and not estruturado and _eh_titulo_solto(linhas[0]):
            blocos.append(Bloco("titulo", _texto_de_titulo(linhas[0]), 3 if linhas[0].endswith("?") else 2))
            continue
        atual: list[str] = []
        for linha in linhas:
            titulo = _TITULO_MD.match(linha)
            if titulo:
                _fechar_paragrafo(blocos, atual)
                blocos.append(Bloco("titulo", titulo.group(2).strip(), len(titulo.group(1))))
            elif not estruturado and _em_caixa_alta(linha):
                # PDF e TXT: título em maiúsculas colado no parágrafo seguinte, sem linha em branco
                _fechar_paragrafo(blocos, atual)
                blocos.append(Bloco("titulo", _texto_de_titulo(linha), 2))
            elif _ITEM.match(linha):
                _fechar_paragrafo(blocos, atual)
                blocos.append(Bloco("item", _ITEM.sub("", linha).strip()))
            elif blocos and blocos[-1].tipo == "item" and not atual and juntar and linha[0].islower():
                blocos[-1].texto += " " + linha  # continuação de um item quebrado em duas linhas
                rel.linhas_unidas += 1
            elif not atual:
                atual.append(linha)
            elif estruturado or (juntar and not (_FIM_DE_FRASE.search(atual[-1]) and linha[0].isupper())):
                atual.append(linha)
                rel.linhas_unidas += 1
            else:
                _fechar_paragrafo(blocos, atual)
                atual.append(linha)
        _fechar_paragrafo(blocos, atual)
    return [b for b in blocos if b.texto]


def _chave_duplicado(texto: str) -> str:
    return re.sub(r"\W+", " ", texto.lower()).strip()


def limpar(doc: Documento, opcoes: OpcoesLimpeza | None = None, vistos: set[str] | None = None) -> tuple[list[Bloco], RelatorioLimpeza]:
    """Aplica as etapas escolhidas e devolve os blocos limpos (títulos, parágrafos e itens) com o relatório.

    `vistos` guarda os parágrafos já aceitos em outros documentos, para a remoção de duplicados valer
    para o conjunto todo e não só dentro de um arquivo.
    """
    op = opcoes or OpcoesLimpeza()
    vistos = vistos if vistos is not None else set()
    rel = RelatorioLimpeza(caracteres_antes=len(doc.texto))
    texto = doc.texto

    if op.remover_cabecalho_rodape and doc.paginas:
        repetidas = linhas_repetidas(doc.paginas)
        paginas = []
        for pagina in doc.paginas:
            mantidas = []
            for linha in pagina.splitlines():
                if linha.strip() and (_assinatura(linha) in repetidas or _NUMERO_DE_PAGINA.match(linha.strip())):
                    rel.linhas_cabecalho_rodape += 1
                else:
                    mantidas.append(linha)
            paginas.append("\n".join(mantidas))
        texto = "\n".join(paginas)  # o parágrafo pode continuar na página seguinte

    if op.normalizar_unicode:
        texto = normalizar_unicode(texto)

    if op.remover_ruido_web:
        mantidas = []
        for linha in texto.splitlines():
            if _RUIDO_WEB.match(linha.strip()):
                rel.linhas_ruido += 1
            else:
                mantidas.append(linha)
        texto = "\n".join(mantidas)

    if op.juntar_linhas_quebradas:
        texto, rel.hifens_unidos = re.subn(r"(?<=[a-zà-ÿ])-\n(?=[a-zà-ÿ])", "", texto)

    if op.remover_urls:
        texto, rel.urls_removidas = _URL.subn("", texto)

    if op.mascarar_dados_pessoais:
        texto, rel.dados_pessoais = mascarar_dados_pessoais(texto, op.preservar)

    estruturado = doc.formato in (".md", ".html", ".htm", ".docx")
    blocos = _blocos(texto, estruturado, op.juntar_linhas_quebradas, rel)

    limpos: list[Bloco] = []
    for bloco in blocos:
        if bloco.tipo == "paragrafo":
            if len(bloco.texto) < op.min_caracteres and not bloco.texto.endswith(":"):
                rel.paragrafos_curtos += 1
                continue
            if op.remover_duplicados:
                chave = _chave_duplicado(bloco.texto)
                if chave in vistos:
                    rel.paragrafos_duplicados += 1
                    continue
                vistos.add(chave)
        if op.minusculas and bloco.tipo != "titulo":
            bloco.texto = re.sub(r"\[[A-Z]+\]|[^\[]+", lambda m: m.group(0) if m.group(0).startswith("[") else m.group(0).lower(), bloco.texto)
        limpos.append(bloco)

    # títulos que ficaram sem conteúdo (seção inteira removida) não vão para o corpus
    com_conteudo: list[Bloco] = []
    for i, bloco in enumerate(limpos):
        if bloco.tipo == "titulo" and not bloco.texto.endswith("?"):
            proximo = limpos[i + 1] if i + 1 < len(limpos) else None
            if proximo is None or (proximo.tipo == "titulo" and proximo.nivel <= bloco.nivel):
                continue
        com_conteudo.append(bloco)
    rel.caracteres_depois = sum(len(b.texto) for b in com_conteudo)
    return com_conteudo, rel


def texto_limpo(blocos: list[Bloco]) -> str:
    """Texto final de um documento, com os títulos marcados e uma linha em branco entre os blocos."""
    partes = []
    for bloco in blocos:
        if bloco.tipo == "titulo":
            partes.append("#" * max(1, bloco.nivel) + " " + bloco.texto)
        elif bloco.tipo == "item":
            partes.append("- " + bloco.texto)
        else:
            partes.append(bloco.texto)
    return "\n\n".join(partes)
