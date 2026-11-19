# Relatório da execução 3

- Início: 2026-11-12T17:33:08 · Fim: 2026-11-12T17:33:09 · Simulação: não
- Notícias coletadas: 35 (relevantes: 21)
- Chuva prevista 72h: 45.0 mm · Alerta ativo: sim
- OS aplicadas: 8 · Linhas para revisão humana: 9 · Arquivos ignorados (já processados): 0
- Casos de drenagem priorizados: 2
- Fotos com possível fissura: 8 de 16
- E-mail: salvo em boletim_20261112_173309.eml (sem credenciais SMTP ou modo simulação)

## Validação com dados de teste rotulados

```json
{
  "priorizacao": {
    "casos_avaliados": 3,
    "acertos": 3,
    "erros": []
  },
  "planilhas": {
    "linhas_avaliadas": 17,
    "acertos": 17,
    "acuracia": 1.0,
    "erros": []
  },
  "fotos": {
    "avaliadas": 16,
    "acertos": 16,
    "acuracia": 1.0,
    "falsos_negativos": 0,
    "falsos_positivos": 0,
    "verdadeiros_positivos": 8
  }
}
```

## Falhas tratadas

- [D-planilhas] os_planilha_corrompida.csv ilegível: colunas obrigatórias ausentes: ['data_execucao', 'equipe', 'observacao', 'protocolo', 'status_os']; movido para revisão humana
- [F-visao] foto_corrompida.jpg: imagem inválida (UnidentifiedImageError); enviada para revisão humana
