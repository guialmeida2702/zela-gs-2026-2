# Relatório da execução 5

- Início: 2026-11-12T17:33:16 · Fim: 2026-11-12T17:33:24 · Simulação: sim
- Notícias coletadas: 35 (relevantes: 21)
- Chuva prevista 72h: None mm · Alerta ativo: não
- OS aplicadas: 0 · Linhas para revisão humana: 0 · Arquivos ignorados (já processados): 2
- Casos de drenagem priorizados: 0
- Fotos com possível fissura: 8 de 16
- E-mail: salvo em boletim_20261112_173324.eml (sem credenciais SMTP ou modo simulação)

## Validação com dados de teste rotulados

```json
{
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
- [C-api] API do Zela indisponível (ConnectError: [Errno 111] Connection refused); atualizações ficam pendentes
- [D-planilhas] os_planilha_corrompida.csv ilegível: colunas obrigatórias ausentes: ['data_execucao', 'equipe', 'observacao', 'protocolo', 'status_os']; movido para revisão humana
- [F-visao] foto_corrompida.jpg: imagem inválida (UnidentifiedImageError); enviada para revisão humana
