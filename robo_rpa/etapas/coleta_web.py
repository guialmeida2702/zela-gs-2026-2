"""Tema 1 — Web scraping: notícias oficiais da Prefeitura de São Paulo e da Defesa Civil municipal.

Coleta títulos, datas e links das listagens públicas e marca como RELEVANTES os que tratam de
chuva, alagamento, alerta, árvore, deslizamento ou zeladoria. Notícias relevantes recentes compõem
o boletim do gestor e funcionam como gatilho de alerta (junto com a previsão de chuva).
"""

import re
import unicodedata
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

FONTES = {
    "Prefeitura de SP (notícias)": "https://prefeitura.sp.gov.br/noticias",
    "Defesa Civil municipal (notícias)": "https://prefeitura.sp.gov.br/web/defesa_civil/noticias",
}
# v2 (depois da avaliação em dados/teste/noticias_rotuladas.csv): saiu "defesa civil", que marcava toda notícia
# do órgão (cursos, doações); "piscin" virou "piscinao" (marcava piscina de clube); entraram tempestade, raio,
# área de risco, encosta, vistoria e interdição. "arvore" exige contexto de queda, poda ou remoção.
PALAVRAS_RELEVANTES = re.compile(
    r"chuva|alag|enchente|inunda|temporal|tempestade|\braios?\b|alerta|estado de aten|deslizamento|desabamento|"
    r"area de risco|areas de risco|risco geolog|encosta|vistori|interdit|queda de arvore|arvores? ca|poda|remocao de arvore|"
    r"zeladoria|bueiro|drenagem|piscinao|buraco|tapa-buraco|calcada", re.I)
PALAVRAS_ALERTA = re.compile(r"alerta|estado de aten|temporal|chuva forte|alag|enchente", re.I)
_MESES = {m: i for i, m in enumerate(["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto",
                                     "setembro", "outubro", "novembro", "dezembro"], start=1)}


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def extrair_data(texto: str) -> date | None:
    n = _norm(texto)
    m = re.search(r"(\d{1,2}) de ([a-z]+) de (\d{4})", n)
    if m and m.group(2) in _MESES:
        return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", n)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def analisar_listagem(html: str, fonte: str, base: str = "https://prefeitura.sp.gov.br") -> list[dict]:
    """Extrai notícias de uma listagem (função pura: testável com HTML salvo)."""
    sopa = BeautifulSoup(html, "lxml")
    vistas, noticias = set(), []
    for a in sopa.find_all("a", href=True):
        href, texto = a["href"], " ".join(a.get_text(" ", strip=True).split())
        if "/w/" not in href or len(texto) < 25:
            continue
        url = href if href.startswith("http") else base + href
        if url in vistas:
            continue
        vistas.add(url)
        titulo = re.sub(r"^(imagem de notícia|segunda|terça|quarta|quinta|sexta|sábado|domingo)[^0-9]*", "", texto,
                        flags=re.I).strip()
        titulo = re.sub(r"^\d{1,2} de \w+ de \d{4}\s*|^\d{2}/\d{2}/\d{4}\s*", "", titulo).strip()
        data_noticia = extrair_data(texto)
        noticias.append({
            "fonte": fonte, "url": url, "titulo": titulo[:200],
            "data": data_noticia.isoformat() if data_noticia else None,
            "relevante": bool(PALAVRAS_RELEVANTES.search(_norm(texto))),
            "alerta": bool(PALAVRAS_ALERTA.search(_norm(texto))),
        })
    return noticias


def coletar(cliente: httpx.Client, url: str, fonte: str) -> list[dict]:
    resp = cliente.get(url)
    resp.raise_for_status()
    if len(resp.text) < 5000:
        raise ValueError("página sem conteúdo útil (possível bloqueio ou manutenção)")
    return analisar_listagem(resp.text, fonte)


def alerta_recente(noticias: list[dict], hoje: date | None = None, dias: int = 2) -> list[dict]:
    hoje = hoje or datetime.now().date()
    return [n for n in noticias if n["alerta"] and n["data"] and (hoje - date.fromisoformat(n["data"])).days <= dias]
