"""Normalização de texto para o cálculo de WER (igual para referência e transcrição)."""

import re
import unicodedata

from num2words import num2words


def normalizar(texto: str) -> str:
    t = texto.lower()
    t = re.sub(r"\d+", lambda m: " " + num2words(int(m.group(0)), lang="pt_BR") + " ", t)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def contem_algum(texto: str, termos: list[str]) -> bool:
    base = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return any(unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode() in base for t in termos)
