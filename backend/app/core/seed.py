"""Dados FICTÍCIOS de demonstração (marcados com demo=True e sinalizados na interface).

Servem apenas para o painel não começar vazio numa apresentação. Desative com SEED_DEMO_DATA=false.
"""

import random
from datetime import timedelta

from app.core.tempo import agora as hora_local
from app.pipelines.registro import gerar_protocolo
from app.pipelines.roteamento import rotear
from app.providers.database import Repositorio
from app.schemas.analise import Endereco
from app.schemas.comum import Categoria, Status, Urgencia

_BAIRROS = [
    ("Sé", -23.5505, -46.6333), ("Mooca", -23.5600, -46.5990), ("Santana", -23.5020, -46.6250),
    ("Butantã", -23.5710, -46.7080), ("Lapa", -23.5270, -46.7040), ("Itaquera", -23.5400, -46.4560),
    ("Capão Redondo", -23.6710, -46.7790), ("Penha", -23.5270, -46.5430), ("Pinheiros", -23.5670, -46.6930),
    ("Vila Mariana", -23.5890, -46.6340), ("Casa Verde", -23.5100, -46.6600), ("Sapopemba", -23.6000, -46.5100),
    ("Jabaquara", -23.6460, -46.6420), ("Campo Limpo", -23.6330, -46.7600), ("Tatuapé", -23.5400, -46.5760),
    ("Brasilândia", -23.4700, -46.6900), ("Grajaú", -23.7550, -46.6900), ("São Mateus", -23.6100, -46.4800),
]

_MODELOS: list[tuple[Categoria, str, str, Urgencia]] = [
    (Categoria.BURACO_VIA, "Buraco grande na faixa da direita", "Buraco fundo na rua, carros desviam em cima da hora.", Urgencia.ALTA),
    (Categoria.BURACO_VIA, "Asfalto afundado em frente ao mercado", "O asfalto cedeu e está afundando aos poucos.", Urgencia.MEDIA),
    (Categoria.ILUMINACAO, "Poste apagado há uma semana", "A lâmpada do poste está apagada e a rua fica muito escura à noite.", Urgencia.MEDIA),
    (Categoria.ILUMINACAO, "Lâmpada acesa durante o dia", "A luz do poste fica acesa o dia todo.", Urgencia.BAIXA),
    (Categoria.LIXO_ENTULHO, "Entulho na calçada", "Deixaram entulho de obra e um sofá velho na calçada.", Urgencia.MEDIA),
    (Categoria.LIXO_ENTULHO, "Coleta de lixo não passou", "O caminhão de lixo não passa há 4 dias e o lixo está acumulando.", Urgencia.MEDIA),
    (Categoria.ALAGAMENTO, "Bueiro entupido na esquina", "Toda chuva a esquina alaga porque o bueiro está entupido de folhas.", Urgencia.ALTA),
    (Categoria.ALAGAMENTO, "Boca de lobo sem tampa", "A boca de lobo está sem a grade, alguém pode cair.", Urgencia.ALTA),
    (Categoria.ARVORE, "Galhos encostando na fiação", "Os galhos da árvore estão encostando nos fios do poste.", Urgencia.ALTA),
    (Categoria.ARVORE, "Pedido de poda", "A árvore está muito grande e cobrindo a iluminação.", Urgencia.BAIXA),
    (Categoria.CALCADA, "Calçada quebrada perto da escola", "Calçada toda quebrada, cadeirante não consegue passar.", Urgencia.ALTA),
    (Categoria.CALCADA, "Rampa de acessibilidade danificada", "A rampa da esquina está quebrada.", Urgencia.MEDIA),
    (Categoria.SINALIZACAO, "Semáforo apagado em cruzamento", "O farol do cruzamento está desligado desde cedo.", Urgencia.ALTA),
    (Categoria.SINALIZACAO, "Faixa de pedestre apagada", "A pintura da faixa de pedestre sumiu.", Urgencia.BAIXA),
    (Categoria.AGUA_ESGOTO, "Vazamento de água na rua", "Tem água limpa jorrando do asfalto há dois dias.", Urgencia.MEDIA),
    (Categoria.AGUA_ESGOTO, "Esgoto a céu aberto", "Esgoto escorrendo pela sarjeta com mau cheiro.", Urgencia.ALTA),
    (Categoria.FIACAO, "Fio caído após a chuva", "Um fio grosso caiu na calçada depois do temporal.", Urgencia.CRITICA),
    (Categoria.FIACAO, "Fios soltos no poste", "Fios pendurados baixos no poste, quase na altura das pessoas.", Urgencia.ALTA),
]

_CAMINHO = {
    Status.RECEBIDA: [],
    Status.EM_ANALISE: [Status.EM_ANALISE],
    Status.ENCAMINHADA: [Status.EM_ANALISE, Status.ENCAMINHADA],
    Status.RESOLVIDA: [Status.EM_ANALISE, Status.ENCAMINHADA, Status.RESOLVIDA],
    Status.RECUSADA: [Status.EM_ANALISE, Status.RECUSADA],
}

_PESOS_CATEGORIA = [9, 6, 8, 3, 6, 4, 7, 4, 4, 3, 5, 3, 4, 2, 4, 3, 2, 3]


def popular_dados_demo(repo: Repositorio, quantidade: int = 64, semente: int = 2026) -> int:
    if repo.contar_solicitacoes() > 0:
        return 0
    rnd = random.Random(semente)
    agora = hora_local()
    for _ in range(quantidade):
        categoria, titulo, descricao, urgencia = rnd.choices(_MODELOS, weights=_PESOS_CATEGORIA)[0]
        bairro, lat, lon = rnd.choice(_BAIRROS)
        lat += rnd.uniform(-0.012, 0.012)
        lon += rnd.uniform(-0.012, 0.012)
        criado = agora - timedelta(days=rnd.randint(0, 45), hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59))

        # ~85% de concordância: às vezes a IA errou e o cidadão corrigiu
        categoria_ia, urgencia_ia = categoria, urgencia
        corrigida = rnd.random() < 0.15
        if corrigida:
            if rnd.random() < 0.5:
                categoria_ia = rnd.choice([c for c in Categoria if c not in (categoria, Categoria.OUTROS)])
            else:
                delta = 1 if urgencia.nivel == 0 else -1 if urgencia.nivel == 3 else rnd.choice([-1, 1])
                urgencia_ia = Urgencia.de_nivel(urgencia.nivel + delta)

        idade_dias = (agora - criado).days
        if idade_dias > 20:
            status = rnd.choices([Status.RESOLVIDA, Status.ENCAMINHADA, Status.RECUSADA], [7, 2, 1])[0]
        elif idade_dias > 7:
            status = rnd.choices([Status.RESOLVIDA, Status.ENCAMINHADA, Status.EM_ANALISE], [4, 4, 2])[0]
        else:
            status = rnd.choices([Status.RECEBIDA, Status.EM_ANALISE, Status.ENCAMINHADA], [5, 3, 2])[0]

        historico = [{"status": Status.RECEBIDA.value, "em": criado.isoformat(), "nota": "Relato confirmado pelo cidadão."}]
        momento = criado
        for etapa in _CAMINHO[status]:
            momento = min(agora, momento + timedelta(hours=rnd.randint(4, 120)))
            historico.append({"status": etapa.value, "em": momento.isoformat(), "nota": "[gestor-demo] atualização"})

        endereco = Endereco(cep="00000000", bairro=bairro, cidade="São Paulo", uf="SP", latitude=lat, longitude=lon, fonte="demo")
        enc = rotear(categoria, endereco, urgencia == Urgencia.CRITICA)
        repo.criar_solicitacao({
            "protocolo": gerar_protocolo(repo),
            "analise_id": f"demo-{rnd.getrandbits(48):012x}",
            "criado_em": criado,
            "atualizado_em": momento,
            "status": status.value,
            "categoria_ia": categoria_ia.value,
            "urgencia_ia": urgencia_ia.value,
            "categoria_final": categoria.value,
            "urgencia_final": urgencia.value,
            "corrigida_pelo_cidadao": corrigida,
            "comentario_cidadao": "Ajustei a classificação." if corrigida else None,
            "titulo": titulo,
            "descricao": f"[DEMONSTRAÇÃO] {descricao}",
            "endereco_resumo": f"{bairro}, São Paulo/SP",
            "bairro": bairro,
            "cidade": "São Paulo",
            "uf": "SP",
            "latitude": lat,
            "longitude": lon,
            "orgao": enc.orgao,
            "canal": enc.canal,
            "prazo_referencia": enc.prazo_referencia,
            "orientacoes": ["Registro fictício de demonstração."],
            "risco_imediato": urgencia == Urgencia.CRITICA,
            "confianca_ia": round(rnd.uniform(0.55, 0.97), 2),
            "contato": None,
            "feedback_util": rnd.choice([True, True, True, False, None, None]),
            "feedback_comentario": None,
            "nota_gestor": None,
            "historico": historico,
            "demo": True,
        })
    return quantidade

