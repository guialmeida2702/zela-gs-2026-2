# Relatório da execução 1

- Início: 2026-11-12T17:31:56 · Fim: 2026-11-12T17:32:03 · Simulação: sim
- Notícias coletadas: 35 (relevantes: 21)
- Chuva prevista 72h: None mm · Alerta ativo: não
- OS aplicadas: 8 · Linhas para revisão humana: 9 · Arquivos ignorados (já processados): 0
- Casos de drenagem priorizados: 0
- Fotos com possível fissura: 8 de 16
- E-mail: salvo em boletim_20261112_173203.eml (sem credenciais SMTP ou modo simulação)

## Validação com dados de teste rotulados

```json
{
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

- [B-clima] previsão indisponível (HTTPStatusError); priorização usa só as notícias oficiais
- [D-planilhas] os_planilha_corrompida.csv ilegível: colunas obrigatórias ausentes: ['data_execucao', 'equipe', 'observacao', 'protocolo', 'status_os']; movido para revisão humana
- [F-visao] foto_corrompida.jpg: imagem inválida (UnidentifiedImageError); enviada para revisão humana
