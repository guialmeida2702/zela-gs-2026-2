"""Gera os modelos iSPD (.imsx) do estudo de cluster do Zela: cada cenário em versão com 2 e com 4 workers.

Dentro de cada par, tudo é igual (carga, capacidade de cada worker, escalonador, banda e latência);
só muda a quantidade de workers. O cenário "principal" é o pedido no enunciado; os outros três são
análises de sensibilidade usadas na discussão. Os valores vêm das medições do próprio Zela (veja o relatório).

Uso: python gerar_modelos.py   -> modelos/<cenario>_<n>_workers.imsx
"""

from pathlib import Path

SAIDA = Path(__file__).parent / "modelos"

BASE = {
    "potencia_mflops": 10_000,     # capacidade de cada máquina (MFlop/s), igual para mestre e workers
    "banda_mbps": 1_000,           # enlaces mestre-worker (Mbit/s), rede local do datacenter
    "latencia_s": 0.001,           # latência de cada enlace (s)
    "escalonador": "Workqueue",    # mesmo escalonador em todos os cenários
    "rede_compartilhada_mbps": None,  # None = cada worker tem enlace próprio com o mestre
    "workers_extra": (),           # quantidades além de 2 e 4, só para a discussão
    "tarefas": 240,                # relatos na hora de pico depois de um temporal
    # Cada tarefa = triagem de um relato (LLM local) + análise da foto + resposta do assistente.
    # 300.000 MFlop = 30 s numa máquina de 10 GFlop/s, a média medida no Zela.
    "computacao_mflop": (300_000, 300_000, 300_000),   # (mínimo, média, máximo)
    "comunicacao_mbit": (16, 16, 16),                  # texto + foto de 2 MB
}

CENARIOS = {
    "principal": {},
    "tarefas_variaveis": {"computacao_mflop": (50_000, 300_000, 600_000)},       # relatos de 5 s a 60 s
    # Relato com vídeo curto (12,5 MB = 100 Mbit) e workers ligados por um switch compartilhado de 10 Mbit/s.
    # Modelado com o ícone "cluster" do iSPD, em que todos os nós disputam a mesma banda. Tem também 8 workers.
    "rede_compartilhada": {"comunicacao_mbit": (100, 100, 100), "rede_compartilhada_mbps": 10, "latencia_s": 0.05,
                           "workers_extra": (8,)},
    "poucas_tarefas": {"tarefas": 6},                                            # madrugada: 6 relatos
}


def modelo_cluster(n_workers: int, p: dict) -> str:
    """Ícone "cluster" do iSPD: n nós iguais atrás de um switch com a banda informada (compartilhada)."""
    cmin, cmed, cmax = p["computacao_mflop"]
    mmin, mmed, mmax = p["comunicacao_mbit"]
    return "\n".join([
        '<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>', '<!DOCTYPE system SYSTEM "iSPD.dtd">',
        '<system version="2.1">', '<owner id="user1"/>',
        f'<cluster id="cluster_zela" nodes="{n_workers}" power="{p["potencia_mflops"]}" '
        f'bandwidth="{p["rede_compartilhada_mbps"]}" latency="{p["latencia_s"]}" scheduler="{p["escalonador"]}" '
        f'owner="user1" master="true"><position x="200" y="200"/><icon_id global="1" local="0"/></cluster>',
        f'<load><node application="zela" owner="user1" id_master="cluster_zela" tasks="{p["tarefas"]}">'
        f'<size type="computing" minimum="{cmin}" average="{cmed}" maximum="{cmax}" probability="0.0"/>'
        f'<size type="communication" minimum="{mmin}" average="{mmed}" maximum="{mmax}" probability="0.0"/>'
        f'</node></load>', "</system>"]) + "\n"


def modelo(n_workers: int, p: dict) -> str:
    if p["rede_compartilhada_mbps"]:
        return modelo_cluster(n_workers, p)
    # No iSPD as referências (escravos e enlaces) usam o número global do ícone; a carga usa o rótulo do mestre
    gid = {"mestre": 1, **{f"worker{i}": 1 + i for i in range(1, n_workers + 1)}}
    proximo = iter(range(len(gid) + 1, 1000))
    linhas = ['<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>',
              '<!DOCTYPE system SYSTEM "iSPD.dtd">', '<system version="2.1">', '<owner id="user1"/>']
    escravos = "".join(f'<slave id="{gid[f"worker{i}"]}"/>' for i in range(1, n_workers + 1))
    linhas.append(f'<machine id="mestre" power="{p["potencia_mflops"]}" load="0.0" owner="user1">'
                  f'<master scheduler="{p["escalonador"]}">{escravos}</master>'
                  f'<position x="{60 + 60 * n_workers}" y="60"/><icon_id global="1" local="0"/></machine>')
    for i in range(1, n_workers + 1):
        linhas.append(f'<machine id="worker{i}" power="{p["potencia_mflops"]}" load="0.0" owner="user1">'
                      f'<position x="{120 * i}" y="300"/><icon_id global="{gid[f"worker{i}"]}" local="{i}"/></machine>')
    pares = [(1, gid[f"worker{i}"], f"{i}") for i in range(1, n_workers + 1)]
    for origem, destino, rotulo in pares:
        for a, b, sufixo in ((origem, destino, "ida"), (destino, origem, "volta")):
            linhas.append(f'<link id="enlace_{sufixo}_{rotulo}" bandwidth="{p["banda_mbps"]}" load="0.0" '
                          f'latency="{p["latencia_s"]}"><connect origination="{a}" destination="{b}"/>'
                          f'<icon_id global="{next(proximo)}" local="{next(proximo)}"/></link>')
    cmin, cmed, cmax = p["computacao_mflop"]
    mmin, mmed, mmax = p["comunicacao_mbit"]
    linhas.append(f'<load><node application="zela" owner="user1" id_master="mestre" tasks="{p["tarefas"]}">'
                  f'<size type="computing" minimum="{cmin}" average="{cmed}" maximum="{cmax}" probability="0.0"/>'
                  f'<size type="communication" minimum="{mmin}" average="{mmed}" maximum="{mmax}" probability="0.0"/>'
                  f'</node></load>')
    linhas.append("</system>")
    return "\n".join(linhas) + "\n"


def parametros(cenario: str) -> dict:
    return BASE | CENARIOS[cenario]


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    for nome in CENARIOS:
        for n in (2, 4, *parametros(nome)["workers_extra"]):
            caminho = SAIDA / f"{nome}_{n}_workers.imsx"
            caminho.write_text(modelo(n, parametros(nome)), encoding="ISO-8859-1")
            print(caminho)
