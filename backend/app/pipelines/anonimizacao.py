"""Remoção de dados pessoais do relato ANTES de enviá-lo ao LLM e de salvá-lo (LGPD: minimização).

Os padrões são propositalmente conservadores: preferimos mascarar um número
a mais do que vazar um CPF ou telefone para um provedor externo.
"""

import re
from dataclasses import dataclass


def cpf_valido(numero: str) -> bool:
    """Confere os dígitos verificadores, para distinguir CPF de celular com 11 dígitos."""
    d = [int(c) for c in re.sub(r"\D", "", numero)]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(d[i] * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10 % 11) % 10 != d[tamanho]:
            return False
    return True


_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

_PADROES: list[tuple[str, str, re.Pattern[str]]] = [
    ("e-mail", "[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("CNPJ", "[CNPJ]", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
    (
        "telefone",
        "[TELEFONE]",
        re.compile(r"(?:\+?55\s?)?(?:\(?\d{2}\)?[\s-]?)?(?:9\s?)?\d{4}[\s-]?\d{4}\b"),
    ),
    ("placa de veículo", "[PLACA]", re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b", re.IGNORECASE)),
    (
        "nome próprio declarado",
        "[NOME]",
        re.compile(
            r"(?i:\b(?:meu nome é|me chamo|sou o|sou a)\s+)([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+){0,3})"
        ),
    ),
]


@dataclass
class ResultadoAnonimizacao:
    texto: str
    removidos: list[str]


def anonimizar(texto: str) -> ResultadoAnonimizacao:
    removidos: list[str] = []
    # CPF primeiro, mas só quando os dígitos verificadores batem (senão pode ser um celular)
    novo = _CPF.sub(lambda m: "[CPF]" if cpf_valido(m.group(0)) else m.group(0), texto)
    if novo != texto:
        removidos.append("CPF")
        texto = novo
    for nome, marcador, padrao in _PADROES:
        if padrao.groups:  # substitui só o grupo (ex.: o nome depois de "meu nome é")
            def _sub(m: re.Match[str], marcador: str = marcador) -> str:
                return m.group(0).replace(m.group(1), marcador)

            novo = padrao.sub(_sub, texto)
        else:
            novo = padrao.sub(marcador, texto)
        if novo != texto:
            removidos.append(nome)
            texto = novo
    return ResultadoAnonimizacao(texto=texto, removidos=removidos)
