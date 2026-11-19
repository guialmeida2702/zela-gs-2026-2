"""Identidade visual e tokens de cor do Zela.

Urgência usa uma paleta de STATUS (fixa, com significado reservado) e SEMPRE vem
acompanhada de ícone + texto: a cor nunca carrega a informação sozinha.
Os pares texto/fundo dos selos passam de 4.5:1 (WCAG AA); no modo alto
contraste, passam de 7:1 (AAA). Ver tests/test_contraste.py.
"""

import streamlit as st

MARCA = {
    "primaria": "#0F5C63",
    "primaria_escura": "#0A3F44",
    "destaque": "#F2A541",
    "fundo": "#FBFAF7",
    "superficie": "#FFFFFF",
    "texto": "#14211F",
    "texto_secundario": "#4A5654",
    "borda": "#D9E2E0",
    "serie": "#2a78d6",  # cor única para séries nominais (ex.: contagem por categoria)
}

URGENCIA: dict[str, dict] = {
    "critica": {"nome": "Crítica", "icone": "🚨", "cor": "#d03b3b", "fundo": "#FBE9E9", "texto": "#7A1414",
                "hc_fundo": "#7F0000", "hc_texto": "#FFFFFF", "ajuda": "risco imediato à vida ou à segurança"},
    "alta": {"nome": "Alta", "icone": "⚠️", "cor": "#ec835a", "fundo": "#FDEEE6", "texto": "#7A3300",
             "hc_fundo": "#8A3B00", "hc_texto": "#FFFFFF", "ajuda": "risco de acidente ou dano em breve"},
    "media": {"nome": "Média", "icone": "⏳", "cor": "#fab219", "fundo": "#FEF6E0", "texto": "#5E4300",
              "hc_fundo": "#FFE14D", "hc_texto": "#000000", "ajuda": "atrapalha o dia a dia e pode piorar"},
    "baixa": {"nome": "Baixa", "icone": "ℹ️", "cor": "#0ca30c", "fundo": "#E6F5E6", "texto": "#145214",
              "hc_fundo": "#00522B", "hc_texto": "#FFFFFF", "ajuda": "incômodo sem risco imediato"},
}
ORDEM_URGENCIA = ["critica", "alta", "media", "baixa"]

STATUS: dict[str, dict] = {
    "recebida": {"nome": "Recebida", "icone": "📥"},
    "em_analise": {"nome": "Em análise", "icone": "🔎"},
    "encaminhada": {"nome": "Encaminhada", "icone": "📤"},
    "resolvida": {"nome": "Resolvida", "icone": "✅"},
    "recusada": {"nome": "Recusada", "icone": "⛔"},
}
ORDEM_STATUS = ["recebida", "em_analise", "encaminhada", "resolvida", "recusada"]

# Espelho local do catálogo da API: mantém a interface legível mesmo se a API cair
CATEGORIAS: dict[str, dict] = {
    "buraco_via": {"nome": "Buraco ou asfalto danificado", "icone": "🕳️"},
    "iluminacao_publica": {"nome": "Iluminação pública", "icone": "💡"},
    "lixo_entulho": {"nome": "Lixo, entulho ou descarte irregular", "icone": "🗑️"},
    "alagamento_drenagem": {"nome": "Alagamento, bueiro ou drenagem", "icone": "🌊"},
    "arvore_poda": {"nome": "Árvore: poda, queda ou risco", "icone": "🌳"},
    "calcada_acessibilidade": {"nome": "Calçada e acessibilidade", "icone": "♿"},
    "sinalizacao_semaforo": {"nome": "Sinalização ou semáforo", "icone": "🚦"},
    "agua_esgoto": {"nome": "Vazamento de água ou esgoto", "icone": "🚰"},
    "fiacao_energia": {"nome": "Fiação ou rede elétrica", "icone": "⚡"},
    "estrutura_fissura": {"nome": "Fissura ou dano em estrutura", "icone": "🧱"},
    "outros": {"nome": "Outro problema urbano", "icone": "📌"},
}

TAMANHOS_FONTE = {"Padrão": 16, "Grande": 19, "Muito grande": 22}


def opcoes_categoria(atual: str | None = None) -> list[str]:
    """Categorias para caixas de seleção. Uma categoria nova na API entra na lista em vez de quebrar a tela."""
    opcoes = list(CATEGORIAS)
    if atual and atual not in opcoes:
        opcoes.append(atual)
    return opcoes


def nome_categoria(codigo: str, com_icone: bool = True) -> str:
    info = CATEGORIAS.get(codigo, {"nome": codigo, "icone": "📌"})
    return f"{info['icone']} {info['nome']}" if com_icone else info["nome"]


def nome_urgencia(codigo: str, com_icone: bool = True) -> str:
    info = URGENCIA.get(codigo, {"nome": codigo, "icone": ""})
    return f"{info['icone']} {info['nome']}" if com_icone else info["nome"]


def nome_status(codigo: str, com_icone: bool = True) -> str:
    info = STATUS.get(codigo, {"nome": codigo, "icone": ""})
    return f"{info['icone']} {info['nome']}" if com_icone else info["nome"]


def css_tema(alto_contraste: bool = False, tamanho_fonte: str = "Padrão") -> str:
    """Gera UM único bloco <style> (sem indentação, para o Markdown não confundir com código)."""
    px = TAMANHOS_FONTE.get(tamanho_fonte, 16)
    m = MARCA
    regras = [
        f"html {{ font-size: {px}px; }}",
        f".stApp {{ background: {m['fundo']}; }}",
        # foco sempre visível para quem navega pelo teclado
        f"*:focus-visible {{ outline: 3px solid {m['destaque']} !important; outline-offset: 2px !important; }}",
        f".zela-hero {{ background: linear-gradient(120deg, {m['primaria_escura']} 0%, {m['primaria']} 100%);"
        " color: #fff; border-radius: 14px; padding: 1.1rem 1.4rem; margin-bottom: .8rem; }",
        ".zela-hero h1 { color: #fff; font-size: 1.7rem; margin: 0; padding: 0; }",
        ".zela-hero p { color: #E8F1F0; margin: .25rem 0 0 0; font-size: 1.02rem; }",
        ".zela-selo { display: inline-flex; align-items: center; gap: .35rem; border-radius: 999px;"
        " padding: .18rem .7rem; font-weight: 700; font-size: .92rem; border: 2px solid; }",
        *(f".zela-urg-{c} {{ background: {u['fundo']}; color: {u['texto']}; border-color: {u['cor']}; }}"
          for c, u in URGENCIA.items()),
        f".zela-selo-status {{ background: #EEF3F2; color: {m['texto']}; border-color: #8FA7A4; }}",
        f".zela-selo-neutro {{ background: #FFFFFF; color: {m['texto']}; border-color: {m['borda']}; }}",
        f".zela-rotulo {{ color: {m['texto_secundario']}; font-size: .85rem; text-transform: uppercase;"
        " letter-spacing: .04em; font-weight: 600; margin-bottom: .1rem; }",
        ".zela-passos { display: flex; gap: .5rem; flex-wrap: wrap; margin: .2rem 0 1rem 0; padding: 0; list-style: none; }",
        f".zela-passos li {{ border-radius: 999px; padding: .25rem .8rem; font-size: .9rem; border: 1px solid {m['borda']};"
        f" color: {m['texto_secundario']}; background: {m['superficie']}; }}",
        f'.zela-passos li[aria-current="step"] {{ background: {m["primaria"]}; color: #fff; border-color: {m["primaria"]};'
        " font-weight: 700; }",
        f".zela-passos li.feito {{ color: {m['primaria']}; border-color: {m['primaria']}; }}",
        ".zela-protocolo { font-family: ui-monospace, monospace; font-size: 1.6rem; font-weight: 800;"
        f" letter-spacing: .06em; color: {m['primaria_escura']}; }}",
        ".zela-emergencia { background: #FBE9E9; border: 2px solid #d03b3b; color: #5C0E0E; border-radius: 12px;"
        " padding: .8rem 1rem; margin: .4rem 0 .8rem 0; }",
        ".zela-emergencia strong { color: #5C0E0E; }",
        f".zela-vazio {{ text-align: center; padding: 2rem 1rem; border: 2px dashed {m['borda']}; border-radius: 12px;"
        f" color: {m['texto_secundario']}; }}",
        ".zela-vazio .icone { font-size: 2.4rem; }",
    ]
    if alto_contraste:
        regras += [
            '.stApp, .stApp [data-testid="stSidebar"] { background: #FFFFFF !important; }',
            ".stApp p, .stApp li, .stApp label, .stApp span, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4,"
            ' .stApp small, .stApp [data-testid="stMarkdownContainer"] { color: #000000 !important; }',
            '.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {'
            " border: 2px solid #000 !important; background: #FFF !important; color: #000 !important; }",
            ".stApp button { border: 2px solid #000 !important; }",
            ".stApp a { color: #00007A !important; text-decoration: underline !important; }",
            ".stApp .zela-hero { background: #000 !important; }",
            ".stApp .zela-hero, .stApp .zela-hero * { color: #FFFFFF !important; }",
            ".stApp .zela-cartao { border: 2px solid #000 !important; }",
            ".stApp .zela-selo-status, .stApp .zela-selo-neutro { border-color: #000 !important; }",
            '.stApp .zela-passos li[aria-current="step"], .stApp .zela-passos li[aria-current="step"] *'
            " { background: #000 !important; color: #FFF !important; }",
            "*:focus-visible { outline: 4px solid #000 !important; }",
            *(f".stApp .zela-selo.zela-urg-{c}, .stApp .zela-selo.zela-urg-{c} * {{ background: {u['hc_fundo']} !important;"
              f" color: {u['hc_texto']} !important; border-color: #000 !important; }}" for c, u in URGENCIA.items()),
        ]
    return "<style>" + " ".join(regras) + "</style>"


def aplicar_estilo(alto_contraste: bool = False, tamanho_fonte: str = "Padrão") -> None:
    st.markdown(css_tema(alto_contraste, tamanho_fonte), unsafe_allow_html=True)
