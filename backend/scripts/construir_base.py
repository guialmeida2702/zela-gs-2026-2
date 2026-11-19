"""Constrói a base de conhecimento do Assistente Zela a partir de páginas OFICIAIS.

Para cada fonte: baixa o HTML, extrai o texto principal, normaliza e salva um
Markdown com cabeçalho de metadados (título, órgão, URL, data de consulta).
O manifesto `fontes.json` registra tudo para rastreabilidade.

Uso:  python scripts/construir_base.py            (grava em app/conhecimento/)
"""

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

DESTINO = Path(__file__).resolve().parent.parent / "app" / "conhecimento"

FONTES = [
    {"id": "dc-chuvas-excessivas", "orgao": "Prefeitura de São Paulo — Defesa Civil",
     "titulo": "Chuvas excessivas: saiba como agir",
     "url": "https://prefeitura.sp.gov.br/web/defesa_civil/w/cuidados_importantes/179951"},
    {"id": "poda-ipiranga", "orgao": "Prefeitura de São Paulo — Subprefeitura Ipiranga",
     "titulo": "Como solicitar poda e remoção de árvore",
     "url": "https://prefeitura.sp.gov.br/web/ipiranga/w/como-solicitar-poda-e-remo%C3%A7%C3%A3o-de-%C3%A1rvore-no-ipiranga"},
    {"id": "poda-butanta", "orgao": "Prefeitura de São Paulo — Subprefeitura Butantã",
     "titulo": "Saiba como solicitar serviços de poda e remoção de árvores",
     "url": "https://prefeitura.sp.gov.br/web/butanta/w/saiba-como-solicitar-nossos-servi%C3%A7os-de-poda-e-remo%C3%A7%C3%A3o-de-%C3%A1rvores"},
    {"id": "calcadas-responsabilidade", "orgao": "Prefeitura de São Paulo — Subprefeitura Ipiranga",
     "titulo": "Manutenção das calçadas é responsabilidade do proprietário do imóvel",
     "url": "https://prefeitura.sp.gov.br/web/ipiranga/w/a-responsabilidade-da-manuten%C3%A7%C3%A3o-das-cal%C3%A7adas-%C3%A9-de-responsabilidade-do-propriet%C3%A1rio"},
    {"id": "calcadas-fiscalizacao", "orgao": "Prefeitura de São Paulo — Secretaria das Subprefeituras",
     "titulo": "Calçadas: fiscalização e regras",
     "url": "https://prefeitura.sp.gov.br/subprefeituras/w/calcadas/37439"},
    {"id": "faq-subprefeitura", "orgao": "Prefeitura de São Paulo — Subprefeitura Vila Prudente",
     "titulo": "Perguntas frequentes da Subprefeitura (poda, poço de visita, sinalização, veículos)",
     "url": "https://prefeitura.sp.gov.br/web/vila_prudente/w/acesso_a_informacao/50102"},
]

CABECALHO = {"User-Agent": "Mozilla/5.0 (zela-citizentech; projeto academico FIAP)"}
_RUIDO = re.compile(r"(compartilhe:|collections|galeria de imagens|imprimir|voltar ao topo|acessibilidade|mapa do site|"
                    r"cookies|política de privacidade|hand talk)", re.I)
# Linhas descartadas sempre (widget de acessibilidade e rótulos soltos de menu)
_DESCARTE = re.compile(r"hand talk|^(quadro de serviços|clique aqui|controladoria|fale com a ouvidoria)$", re.I)


def extrair_texto(html: str) -> str:
    sopa = BeautifulSoup(html, "lxml")
    for tag in sopa(["script", "style", "nav", "header", "footer", "noscript", "form", "iframe", "svg"]):
        tag.decompose()
    candidatos = sopa.select("div.journal-content-article, article, main, div#content, div.portlet-body")
    alvo = max(candidatos, key=lambda c: len(c.get_text(" ", strip=True))) if candidatos else sopa.body or sopa
    linhas = []
    for bloco in alvo.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        texto = " ".join(bloco.get_text(" ", strip=True).split())
        link = bloco.find("a")
        if bloco.name == "li" and (link is not None and len(link.get_text(strip=True)) >= len(texto.replace(" ", "")) - 2
                                   or bloco.find("li") is not None):
            continue  # item de menu (só um link) ou lista aninhada de navegação
        if len(texto) < 3 or _RUIDO.search(texto) and len(texto) < 60 or _DESCARTE.search(texto.lstrip("- ")):
            continue
        if bloco.name in ("h1", "h2", "h3", "h4"):
            linhas.append(f"\n## {texto}\n")
        elif bloco.name == "li":
            linhas.append(f"- {texto}")
        else:
            linhas.append(texto)
    # remove repetições consecutivas (menus duplicados)
    saida, anterior = [], None
    for linha in linhas:
        if linha != anterior:
            saida.append(linha)
        anterior = linha
    return unicodedata.normalize("NFC", "\n".join(saida)).strip()


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    manifesto, falhas = [], []
    with httpx.Client(headers=CABECALHO, timeout=20, follow_redirects=True) as cliente:
        for fonte in FONTES:
            try:
                resp = cliente.get(fonte["url"])
                resp.raise_for_status()
                texto = extrair_texto(resp.text)
                if len(texto) < 200:
                    raise ValueError(f"texto muito curto ({len(texto)} caracteres)")
            except Exception as exc:  # fonte fora do ar não interrompe a construção da base
                falhas.append({"id": fonte["id"], "erro": str(exc)[:200]})
                print(f"[FALHA] {fonte['id']}: {exc}", file=sys.stderr)
                continue
            conteudo = (f"---\nid: {fonte['id']}\ntitulo: {fonte['titulo']}\norgao: {fonte['orgao']}\n"
                        f"url: {fonte['url']}\nconsultado_em: {hoje}\ntipo: oficial\n---\n\n# {fonte['titulo']}\n\n{texto}\n")
            (DESTINO / f"{fonte['id']}.md").write_text(conteudo, encoding="utf-8")
            manifesto.append(fonte | {"consultado_em": hoje, "caracteres": len(texto)})
            print(f"[OK] {fonte['id']}: {len(texto)} caracteres")
    (DESTINO / "fontes.json").write_text(json.dumps({"fontes": manifesto, "falhas": falhas}, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return 0 if manifesto else 1


if __name__ == "__main__":
    sys.exit(main())
