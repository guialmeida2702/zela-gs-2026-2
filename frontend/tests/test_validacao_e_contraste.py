"""Validação no front e verificação automática de contraste (WCAG 2.1) dos selos de urgência."""

import re
from pathlib import Path

import pytest

from features.relatar import validar_contato, validar_relato
from ui import theme


# ---------------- validação ----------------
def test_relato_valido():
    assert validar_relato("Buraco grande na rua perto da escola municipal", "01001-000") == {}


@pytest.mark.parametrize(
    "descricao, cep, campo",
    [
        ("", "01001000", "descricao"),
        ("buraco", "01001000", "descricao"),
        ("x" * 1001, "01001000", "descricao"),
        ("12345 67890 12345 67890 123", "01001000", "descricao"),
        ("Buraco grande na rua perto da escola", "", "cep"),
        ("Buraco grande na rua perto da escola", "1234", "cep"),
    ],
)
def test_relato_invalido(descricao, cep, campo):
    assert campo in validar_relato(descricao, cep)


def test_mensagem_diz_quantos_caracteres_faltam():
    assert "faltam 14" in validar_relato("buraco", "01001000")["descricao"]


@pytest.mark.parametrize("contato, ok", [("", True), ("a@b.com", True), ("(11) 98765-4321", True),
                                         ("abc", False), ("123", False)])
def test_contato(contato, ok):
    assert (validar_contato(contato) is None) == ok


# ---------------- contraste ----------------
def _luminancia(hex_cor: str) -> float:
    hex_cor = hex_cor.lstrip("#")
    canais = [int(hex_cor[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("codigo", theme.ORDEM_URGENCIA)
def test_selos_passam_wcag_aa(codigo):
    u = theme.URGENCIA[codigo]
    assert contraste(u["texto"], u["fundo"]) >= 4.5


@pytest.mark.parametrize("codigo", theme.ORDEM_URGENCIA)
def test_selos_alto_contraste_passam_wcag_aaa(codigo):
    u = theme.URGENCIA[codigo]
    assert contraste(u["hc_texto"], u["hc_fundo"]) >= 7.0


def test_texto_principal_e_botao_primario():
    assert contraste(theme.MARCA["texto"], theme.MARCA["fundo"]) >= 7.0
    assert contraste("#FFFFFF", theme.MARCA["primaria"]) >= 4.5
    assert contraste(theme.MARCA["texto_secundario"], theme.MARCA["fundo"]) >= 4.5


def test_urgencia_nunca_depende_so_da_cor():
    for u in theme.URGENCIA.values():
        assert u["icone"] and u["nome"]
    assert len({u["icone"] for u in theme.URGENCIA.values()}) == len(theme.URGENCIA)


# ---------- o espelho local do catálogo precisa acompanhar a API ----------
_ENUMS_DA_API = Path(__file__).resolve().parents[2] / "backend" / "app" / "schemas" / "comum.py"


def _valores_do_enum(nome: str) -> list[str]:
    fonte = _ENUMS_DA_API.read_text(encoding="utf-8")
    bloco = re.search(rf"class {nome}\(.*?\):\n(.*?)(?:\n\n|\Z)", fonte, flags=re.S).group(1)
    return re.findall(r'=\s*"([a-z_]+)"', bloco)


@pytest.mark.skipif(not _ENUMS_DA_API.exists(), reason="backend não está neste checkout")
@pytest.mark.parametrize(
    "enum, espelho",
    [("Categoria", list(theme.CATEGORIAS)), ("Urgencia", theme.ORDEM_URGENCIA), ("Status", theme.ORDEM_STATUS)],
)
def test_espelho_local_tem_os_mesmos_codigos_da_api(enum, espelho):
    assert sorted(_valores_do_enum(enum)) == sorted(espelho)
