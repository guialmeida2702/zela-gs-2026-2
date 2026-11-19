"""Conhecimento de domínio: categorias, critérios de urgência e tabela de encaminhamento.

O encaminhamento (órgão, canal, prazo) é determinístico e vem DAQUI, não do LLM.
Assim a IA classifica, mas não inventa telefones, órgãos ou prazos.
Contatos verificados em nov/2026 — revise periodicamente.
"""

from dataclasses import dataclass

from app.schemas.comum import Categoria, Urgencia


@dataclass(frozen=True)
class InfoCategoria:
    nome: str
    icone: str
    descricao: str
    orgao_sp: str
    canal_sp: str
    orgao_generico: str
    canal_generico: str
    prazo_referencia: str


_SP156 = "SP156 — app SP156, site sp156.prefeitura.sp.gov.br ou telefone 156"
_156_GENERICO = "Central 156 / Ouvidoria da prefeitura de {cidade}"

CATEGORIAS: dict[Categoria, InfoCategoria] = {
    Categoria.BURACO_VIA: InfoCategoria(
        "Buraco ou asfalto danificado", "🕳️",
        "Buracos, crateras, asfalto afundado ou desgastado em ruas e avenidas.",
        "Subprefeitura da região (serviço tapa-buraco)", _SP156,
        "Secretaria de Obras / Serviços Urbanos", _156_GENERICO, "até 30 dias (referência)",
    ),
    Categoria.ILUMINACAO: InfoCategoria(
        "Iluminação pública", "💡",
        "Lâmpada de poste apagada, piscando, acesa de dia ou poste de iluminação danificado.",
        "Ilume — Departamento de Iluminação Pública", _SP156,
        "Setor de iluminação pública da prefeitura", _156_GENERICO, "até 7 dias (referência)",
    ),
    Categoria.LIXO_ENTULHO: InfoCategoria(
        "Lixo, entulho ou descarte irregular", "🗑️",
        "Lixo acumulado, entulho, móveis abandonados, coleta não realizada.",
        "Subprefeitura da região / Limpeza urbana (SP Regula)", _SP156,
        "Serviço de limpeza urbana da prefeitura", _156_GENERICO, "até 7 dias (referência)",
    ),
    Categoria.ALAGAMENTO: InfoCategoria(
        "Alagamento, bueiro ou drenagem", "🌊",
        "Rua alagada, bueiro entupido ou sem tampa, boca de lobo obstruída, córrego transbordando.",
        "Subprefeitura da região (limpeza de bueiros) / CGE em eventos de chuva", _SP156,
        "Secretaria de Obras / Defesa Civil municipal", _156_GENERICO, "até 15 dias (referência)",
    ),
    Categoria.ARVORE: InfoCategoria(
        "Árvore: poda, queda ou risco", "🌳",
        "Árvore caída, com risco de queda, galhos sobre fios ou pedido de poda/remoção.",
        "Subprefeitura da região (manejo arbóreo)", _SP156,
        "Secretaria de Meio Ambiente / Parques", _156_GENERICO, "até 30 dias (referência)",
    ),
    Categoria.CALCADA: InfoCategoria(
        "Calçada e acessibilidade", "♿",
        "Calçada quebrada, rampa de acessibilidade danificada, obstáculos para pedestres e cadeirantes.",
        "Subprefeitura da região (fiscalização/reforma de calçadas)", _SP156,
        "Secretaria de Obras / Mobilidade", _156_GENERICO, "até 30 dias (referência)",
    ),
    Categoria.SINALIZACAO: InfoCategoria(
        "Sinalização ou semáforo", "🚦",
        "Semáforo apagado ou com defeito, placa caída, faixa de pedestre apagada.",
        "CET — Companhia de Engenharia de Tráfego", _SP156,
        "Departamento de trânsito municipal", _156_GENERICO, "até 7 dias (referência)",
    ),
    Categoria.AGUA_ESGOTO: InfoCategoria(
        "Vazamento de água ou esgoto", "🚰",
        "Vazamento de água na rua, esgoto a céu aberto ou retornando, falta d'água na região.",
        "Sabesp — 0800 055 0195 ou WhatsApp (11) 3388-8000", "Canais da Sabesp (concessionária)",
        "Companhia de saneamento da sua cidade", "Canais da concessionária de água e esgoto",
        "conforme a concessionária",
    ),
    Categoria.FIACAO: InfoCategoria(
        "Fiação ou rede elétrica", "⚡",
        "Fio partido ou caído, poste de energia danificado, faíscas, transformador com problema.",
        "Distribuidora de energia (Enel SP — emergência 0800 72 72 196)", "Central de emergência da distribuidora",
        "Distribuidora de energia da sua cidade", "Central de emergência da distribuidora de energia",
        "atendimento emergencial",
    ),
    Categoria.ESTRUTURA: InfoCategoria(
        "Fissura ou dano em estrutura", "🧱",
        "Fissuras, trincas ou rachaduras em muros, pontes, viadutos, escadarias ou prédios públicos.",
        "Defesa Civil municipal (vistoria técnica) / Subprefeitura da região", _SP156,
        "Defesa Civil municipal (vistoria técnica)", _156_GENERICO, "conforme vistoria técnica",
    ),
    Categoria.OUTROS: InfoCategoria(
        "Outro problema urbano", "📌",
        "Problemas urbanos que não se encaixam nas demais categorias.",
        "Central SP156 (triagem)", _SP156,
        "Ouvidoria da prefeitura", _156_GENERICO, "conforme o serviço",
    ),
}

URGENCIAS: dict[Urgencia, tuple[str, str]] = {
    Urgencia.BAIXA: ("Baixa", "Incômodo sem risco: estética, desgaste leve, pedido de melhoria."),
    Urgencia.MEDIA: ("Média", "Atrapalha o dia a dia ou pode piorar: lâmpada apagada, lixo acumulado, buraco pequeno."),
    Urgencia.ALTA: (
        "Alta",
        "Risco de acidente ou dano em breve: buraco grande em via movimentada, bueiro sem tampa, árvore inclinada.",
    ),
    Urgencia.CRITICA: (
        "Crítica",
        "Risco imediato à vida: fio energizado caído, árvore caindo sobre casa, desabamento, pessoas ilhadas.",
    ),
}

CONTATOS_EMERGENCIA = [
    "Bombeiros: 193",
    "Defesa Civil: 199",
    "SAMU: 192",
]
