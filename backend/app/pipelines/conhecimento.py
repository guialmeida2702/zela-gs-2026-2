"""Base de conhecimento do Assistente Zela: leitura dos documentos e fatiamento (chunking).

Duas estratégias, comparadas na avaliação:
- "fixo_400": janelas de 400 caracteres sem olhar a estrutura do texto, sem sobreposição (linha de base);
- "estrutura_700_120" (padrão): respeita as seções (## títulos) do documento oficial, agrupa frases inteiras
  até ~700 caracteres e repete ~120 caracteres entre trechos vizinhos para não cortar uma orientação ao meio.
  Cada trecho carrega título, órgão, seção, URL e data de consulta (metadados para citação).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

PASTA_PADRAO = Path(__file__).resolve().parent.parent / "conhecimento"
_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.S)
# Fim de frase ou de item de lista. O número de um item ("8. Coloque o lixo...") não é fim de frase:
# sem a exceção, o "8." ficava no fim de um trecho e o texto do item no trecho seguinte.
_FRASE = re.compile(r"(?<=[.!?;:])(?<!\s\d\.)(?<!\s\d\d\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-])")


@dataclass
class Documento:
    id: str
    titulo: str
    orgao: str
    url: str
    consultado_em: str
    tipo: str
    texto: str


@dataclass
class Trecho:
    id: str
    doc_id: str
    titulo: str
    orgao: str
    url: str
    consultado_em: str
    tipo: str
    secao: str
    texto: str
    meta: dict = field(default_factory=dict)

    @property
    def texto_indexado(self) -> str:
        """Texto usado na busca: inclui título e seção (contexto que a frase sozinha não tem)."""
        return f"{self.titulo}. {self.secao}. {self.texto}"


def carregar_documentos(pasta: Path = PASTA_PADRAO) -> list[Documento]:
    docs = []
    for arquivo in sorted(pasta.glob("*.md")):
        bruto = arquivo.read_text(encoding="utf-8")
        m = _FRONT.match(bruto)
        meta = dict(linha.split(": ", 1) for linha in m.group(1).splitlines() if ": " in linha) if m else {}
        corpo = bruto[m.end():] if m else bruto
        docs.append(Documento(
            id=meta.get("id", arquivo.stem), titulo=meta.get("titulo", arquivo.stem), orgao=meta.get("orgao", ""),
            url=meta.get("url", ""), consultado_em=meta.get("consultado_em", ""), tipo=meta.get("tipo", "oficial"),
            texto=corpo.strip(),
        ))
    return docs


def _limpar(texto: str) -> str:
    texto = re.sub(r"^#\s.*$", "", texto, flags=re.M)  # título principal já vai nos metadados
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _secoes(texto: str) -> list[tuple[str, str]]:
    partes = re.split(r"^##\s+(.+)$", _limpar(texto), flags=re.M)
    saida = [("Introdução", partes[0].strip())] if partes[0].strip() else []
    for i in range(1, len(partes), 2):
        corpo = partes[i + 1].strip() if i + 1 < len(partes) else ""
        if corpo:
            saida.append((partes[i].strip(), corpo))
    return saida


def _novo(doc: Documento, n: int, secao: str, texto: str, estrategia: str) -> Trecho:
    return Trecho(id=f"{doc.id}#{n}", doc_id=doc.id, titulo=doc.titulo, orgao=doc.orgao, url=doc.url,
                  consultado_em=doc.consultado_em, tipo=doc.tipo, secao=secao, texto=texto.strip(),
                  meta={"estrategia": estrategia})


def fatiar_fixo(docs: list[Documento], tamanho: int = 400) -> list[Trecho]:
    trechos = []
    for doc in docs:
        texto = " ".join(_limpar(doc.texto).replace("## ", "").split())
        inicio, n = 0, 0
        while inicio < len(texto):
            fim = min(len(texto), inicio + tamanho)
            if fim < len(texto):
                espaco = texto.rfind(" ", inicio, fim)
                fim = espaco if espaco > inicio else fim
            trechos.append(_novo(doc, n, "", texto[inicio:fim], "fixo_400"))
            inicio, n = fim + 1, n + 1
    return trechos


_ITEM_FAQ = re.compile(r"^\s*\d{1,2}\s*[-–]\s*", re.M)


def _blocos(corpo: str) -> list[str]:
    """Separa itens numerados de perguntas frequentes ("5 - Quando há um poço...") em blocos próprios.
    Sem isso, duas perguntas diferentes caíam no mesmo trecho e o modelo misturava as respostas
    (na avaliação, o semáforo recebeu a resposta do poço de visita)."""
    inicios = [m.start() for m in _ITEM_FAQ.finditer(corpo)]
    if len(inicios) < 2:
        return [corpo]
    partes = [corpo[: inicios[0]], *[corpo[a:b] for a, b in zip(inicios, [*inicios[1:], len(corpo)], strict=True)]]
    return [p for p in partes if p.strip()]


# Subtítulo de lista escrito no meio do texto corrido ("O que fazer depois da inundação: 1. Beba apenas...").
_SUBTITULO_LISTA = re.compile(r"(?:^|(?<=[.;!?]\s)|(?<=\d\.\s))\s*((?:Cuidados|O que fazer|Como agir|Como proceder)[^.;:!?\n]{3,60}):",
                              re.M)


def _sublistas(secao: str, corpo: str) -> list[tuple[str, str]]:
    """Separa as listas que têm subtítulo próprio dentro de uma seção e usa o subtítulo como nome da seção.
    Sem isso, o subtítulo ficava no fim de um trecho e a lista no trecho seguinte: na avaliação, a pergunta
    "o que fazer depois de uma inundação?" recebeu os itens de antes e durante a enchente."""
    achados = list(_SUBTITULO_LISTA.finditer(corpo))
    if not achados:
        return [(secao, corpo)]
    partes = [(secao, corpo[: achados[0].start(1)])] if corpo[: achados[0].start(1)].strip() else []
    for m, proximo in zip(achados, [*achados[1:], None], strict=True):
        fim = proximo.start(1) if proximo else len(corpo)
        partes.append((m.group(1).strip(), corpo[m.start(1):fim]))
    # um "1." solto antes do subtítulo seguinte pertence à lista seguinte, não a esta
    return [(nome, re.sub(r"\s*\d{1,2}\.\s*$", "", texto)) for nome, texto in partes if texto.strip()]


def fatiar_estrutural(docs: list[Documento], alvo: int = 700, sobreposicao: int = 120,
                      subtitulos: bool = True) -> list[Trecho]:
    trechos = []
    for doc in docs:
        n = 0
        secoes = _secoes(doc.texto)
        if subtitulos:
            secoes = [parte for secao, corpo in secoes for parte in _sublistas(secao, corpo)]
        for secao, corpo_secao in secoes:
            for corpo in _blocos(corpo_secao):
                frases = [f.strip() for f in _FRASE.split(" ".join(corpo.split())) if f.strip()]
                atual: list[str] = []
                for frase in frases:
                    if atual and len(" ".join(atual)) + len(frase) > alvo:
                        trechos.append(_novo(doc, n, secao, " ".join(atual), "estrutura_700_120"))
                        n += 1
                        # sobreposição: carrega as últimas frases até ~120 caracteres
                        carry: list[str] = []
                        for f in reversed(atual):
                            if len(" ".join(carry)) + len(f) > sobreposicao:
                                break
                            carry.insert(0, f)
                        atual = carry
                    atual.append(frase)
                if atual:
                    trechos.append(_novo(doc, n, secao, " ".join(atual), "estrutura_700_120"))
                    n += 1
    return trechos


def fatiar_estrutural_sem_subtitulos(docs: list[Documento]) -> list[Trecho]:
    """Versão anterior da divisão por estrutura, mantida só para a comparação da avaliação."""
    return fatiar_estrutural(docs, subtitulos=False)


ESTRATEGIAS = {"fixo_400": fatiar_fixo, "estrutura_sem_subtitulos": fatiar_estrutural_sem_subtitulos,
               "estrutura_700_120": fatiar_estrutural}


def construir_trechos(estrategia: str = "estrutura_700_120", pasta: Path = PASTA_PADRAO) -> list[Trecho]:
    return ESTRATEGIAS[estrategia](carregar_documentos(pasta))
