# Cluster Computing · 2 x 4 workers no iSPD

Estudo de capacidade da fila de processamento de relatos do Zela num pico após um temporal.

- Relatório (4 páginas): [`docs/relatorios/cluster.md`](../docs/relatorios/cluster.md) (PDF em `docs/relatorios/pdf/cluster.pdf`)
- Modelos icônicos do iSPD (abrem na interface): `modelos/principal_2_workers.imsx` e `modelos/principal_4_workers.imsx`, mais os cenários de sensibilidade
- Capturas da interface (aba Global e Resources): `capturas/`
- Relatórios HTML do próprio iSPD e tabela comparativa: `resultados/`

| Cenário principal | Total Simulated Time | Redução | T₂/T₄ |
|---|---|---|---|
| 2 workers | 3.602,27 s | | |
| 4 workers | 1.801,16 s | 50,00% | 2,00 |

```bash
python gerar_modelos.py                      # gera os .imsx
python simular.py --ispd /caminho/iSPD.jar   # roda todos no modo terminal (em servidor sem tela, instale xvfb)
```

iSPD: https://www.dcce.ibilce.unesp.br/spd/downloads/iSPD.jar (GSPD/UNESP, GPL-2.0). Testado com Java 21.
