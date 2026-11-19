"""Adaptação do texto para fala (etapa entre o LLM e o TTS).

O texto do assistente foi pensado para ler: tem citações [1], siglas, telefones, valores
e datas. Lido em voz alta sem ajuste, "0800 055 0195" vira "oitocentos..." e "[1]" vira
"um". Aqui o texto vira frases curtas, sem markdown e sem emojis, com números pronunciáveis.
"""

import re

from num2words import num2words

SIGLAS = {
    "SP156": "S P cento e cinquenta e seis", "PMSP": "pê eme esse pê", "CET": "cê é tê", "CEP": "cep", "CPF": "cê pê éfe",
    "SAMU": "samu", "LGPD": "éle gê pê dê", "ODS": "ó dê esse", "IA": "inteligência artificial", "SP": "São Paulo",
    "COMDEC": "comdec", "CGE": "cê gê é", "ONG": "ongue", "Enel": "Enél", "OS": "ordem de serviço",
}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]")
_DIGITOS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
# Endereços com ou sem "http": a pontuação que encerra a frase fica fora do link
_URL = re.compile(r"(?:https?://|www\.)[^\s<>]*[^\s<>.,;:!?)]|\b[\w-]+(?:\.[\w-]+)*\.(?:gov|com|org|sp)\.br(?:/[^\s<>]*[^\s<>.,;:!?)])?")


def _n(valor: int) -> str:
    return num2words(valor, lang="pt_BR")


def _telefone(m: re.Match) -> str:
    """Telefones são ditos em blocos de dígitos, como as pessoas falam: 'zero oitocentos...' vira dígito a dígito."""
    blocos = re.findall(r"\d+", m.group(0))
    return ", ".join(" ".join(_DIGITOS[int(d)] for d in b) for b in blocos)


def _dinheiro(m: re.Match) -> str:
    reais, centavos = int(m.group(1).replace(".", "")), int(m.group(2) or 0)
    texto = f"{_n(reais)} {'real' if reais == 1 else 'reais'}"
    if centavos:
        texto += f" e {_n(centavos)} {'centavo' if centavos == 1 else 'centavos'}"
    return texto


def _data(m: re.Match) -> str:
    dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mes <= 12:
        return m.group(0)
    return f"{'primeiro' if dia == 1 else _n(dia)} de {MESES[mes - 1]} de {_n(ano)}"


def _protocolo(m: re.Match) -> str:
    return ", ".join(" ".join(c if c.isalpha() else _DIGITOS[int(c)] for c in parte)
                                    for parte in m.group(0).split("-")[1:])


def adaptar_para_fala(texto: str, max_frases: int = 4) -> str:
    t = re.sub(r"\s*\[\d+\]", "", texto)                                   # citações [1]
    t = _URL.sub("o site oficial", t)                                      # links não se leem em voz alta
    t = re.sub(r"\b(site|portal|página|pagina|endereço|link)( d[aeo])? o site oficial", r"\1 oficial", t, flags=re.I)
    t = re.sub(r"[*_#`>|]+", "", t)                                      # markdown
    t = _EMOJI.sub("", t)
    t = re.sub(r"\bZL-\d{6}-[0-9A-F]{6}\b", _protocolo, t)
    t = re.sub(r"\bR\$\s?(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d{2}))?", _dinheiro, t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", _data, t)
    t = re.sub(r"\b0800[\s.-]?\d{2,3}[\s.-]?\d{2,4}(?:[\s.-]?\d{1,4})?\b|\(\d{2}\)\s?\d{4,5}-?\d{4}", _telefone, t)
    t = re.sub(r"\b(\d{1,3})\s?%", lambda m: f"{_n(int(m.group(1)))} por cento", t)
    t = re.sub(r"\b(\d{1,2})h(\d{2})?\b", lambda m: f"{_n(int(m.group(1)))} horas" + (f" e {_n(int(m.group(2)))}" if m.group(2) else ""), t)
    for sigla, falada in SIGLAS.items():
        t = re.sub(rf"\b{re.escape(sigla)}\b", falada, t)
    t = re.sub(r"\b(\d+),(\d+)\b", lambda m: f"{_n(int(m.group(1)))} vírgula {_n(int(m.group(2)))}", t)
    t = re.sub(r"\b\d{1,6}\b", lambda m: _n(int(m.group(0))), t)        # números restantes por extenso
    t = re.sub(r"\s*\n+\s*[-•]?\s*", ". ", t)                            # listas viram frases
    t = re.sub(r"\s*\(([^)]*)\)", r", \1,", t)                           # parênteses viram pausas
    t = re.sub(r",\s*([.!?])", r"\1", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" .")
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", t) if f.strip()]
    saida = []
    for f in frases[:max_frases]:
        partes = [f]
        if len(f) > 180:  # frases longas cansam quem ouve: quebra na vírgula mais próxima do meio
            meio = f.find(",", len(f) // 2 - 30)
            if 0 < meio < len(f) - 20:
                partes = [f[:meio].strip(), f[meio + 1:].strip()]
        for parte in partes:
            parte = parte[0].upper() + parte[1:]
            saida.append(parte if parte[-1] in ".!?" else parte + ".")
    return " ".join(saida)
