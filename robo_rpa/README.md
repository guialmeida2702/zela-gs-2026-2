# Robô Zela · RPA (automação diária do gestor)

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

## Problema

Todo dia, a equipe de zeladoria de uma subprefeitura repete o mesmo trabalho manual: conferir se saiu alerta de chuva, abrir as planilhas de ordens de serviço (OS) que as equipes de campo mandam, atualizar uma a uma as solicitações no sistema, olhar as fotos de vistoria e mandar um resumo para os gestores. É lento, sujeito a erro de digitação e, em dia de temporal, atrasa justamente quando a prioridade mais importa.

O robô faz esse ciclo inteiro em uma execução, com registro de tudo num banco de auditoria e com um caminho seguro para cada falha previsível. Ele conversa com o Zela pela mesma API que o front usa.

## Quadro de temas

Seis temas da disciplina, cada um com função real no fluxo. A escolha partiu do trabalho manual descrito acima: cada tema substitui uma tarefa que hoje uma pessoa faz.

| # | Tema | Onde é usado no fluxo | O que resolve | Por que este tema |
|---|---|---|---|---|
| 1 | **Web scraping** | Etapa A, `etapas/coleta_web.py` | Lê as listagens de notícias da Prefeitura de SP e da Defesa Civil municipal, marca as relevantes para zeladoria e procura alertas recentes | Essas páginas não têm API; sem scraping alguém teria de abrir os sites todo dia |
| 2 | **Integração com APIs** | Etapas B, C, D e E, `etapas/integracoes.py` | Consulta a chuva prevista para 72 h (Open-Meteo) e conversa com a API do Zela (login de gestor, fila, atualização de solicitações) | É o que liga o robô ao protótipo: ele usa a mesma API do front, sem acesso direto ao banco do Zela |
| 3 | **Arquivos e dados (Pandas)** | Etapa D, `etapas/planilhas.py` | Lê CSV e XLSX de ordens de serviço das subprefeituras, valida linha a linha e separa o que pode ser aplicado | As equipes de campo trabalham com planilhas; digitar cada linha no sistema é a parte mais lenta e com mais erro |
| 4 | **E-mail automatizado** | Etapa G, `etapas/relatorio.py` | Envia aos gestores um boletim HTML com o resumo e as linhas rejeitadas em anexo CSV | O gestor precisa saber o que o robô fez e o que sobrou para revisão sem abrir o sistema |
| 5 | **Banco de dados (SQL)** | Todas as etapas, `etapas/infra.py` (SQLite) | Registra execuções, eventos, notícias e vistorias; evita processar o mesmo arquivo duas vezes (hash) | Auditoria e idempotência: cada decisão do robô fica rastreável |
| 6 | **IA (modelo de outra disciplina)** | Etapa F, `etapas/integracoes.py` | Classifica as fotos de vistoria com o modelo de fissuras treinado em Visão Computacional (ONNX) | Evita que alguém abra foto por foto para decidir quais precisam de inspeção; não usa LLM |
| + | Regra de decisão | Etapa E, `robo.py` | Com chuva prevista acima de 30 mm em 72 h ou alerta oficial recente, eleva para "alta" os casos de drenagem em aberto com urgência baixa ou média, com nota para revisão | Junta os temas 1 e 2 numa ação útil: bueiro entupido vira prioridade antes do temporal |

## Fluxo de uma execução

```
A. scraping de notícias ─┐
B. previsão de chuva ────┼─> gatilho de alerta ─> E. priorização de drenagem (API do Zela)
C. login + fila do Zela ─┘
D. planilhas de OS ─> validação ─> válidas: atualiza o Zela · inválidas: revisao_humana_<n>.csv
F. fotos de vistoria ─> modelo de fissuras ─> banco de auditoria
G. relatório da execução (JSON + Markdown) + e-mail aos gestores (ou .eml se não houver SMTP)
```

Cada etapa roda dentro de um bloco próprio: se uma falha, as outras continuam e a falha vai para o log, para o relatório e para o e-mail.

## Como executar

Ponto de entrada único: `robo.py`.

```bash
cd robo_rpa
pip install -r requirements.txt
# 1) a API do Zela precisa estar no ar (veja o README principal). Para testar sem LLM:
#    cd ../backend && LLM_PROVIDER=mock SEED_DEMO_DATA=true GESTOR_SENHA=demo123 uvicorn app.main:app --port 8000
# 2) a senha do gestor é a mesma da API (no Windows: set ZELA_GESTOR_SENHA=demo123)
export ZELA_GESTOR_SENHA=demo123
# 3) gere os dados de teste (planilhas com erros de propósito e gabarito)
python gerar_dados_teste.py
# 4) rode
python robo.py --simular                   # simulação: lê tudo, não altera o Zela, salva o e-mail como .eml
python robo.py                             # execução real
python robo.py --chuva-teste-mm 45         # teste da regra de alerta sem depender do Open-Meteo
python avaliar_relevancia.py               # mede o filtro de notícias na amostra rotulada
```

Saídas em `saida/`: `robo.log`, `robo.db`, `execucao_<n>.json` e `.md`, `revisao_humana_<n>.csv` e o boletim `.eml`.

**Execução automática, sem intervenção.** O robô não pede nenhuma entrada durante a execução, então pode ser agendado. Exemplo com cron (Linux), todo dia às 6h30:

```cron
30 6 * * * cd /caminho/zela/robo_rpa && /usr/bin/python3 robo.py >> saida/cron.log 2>&1
```

No Windows, o mesmo comando entra no Agendador de Tarefas. Rodar duas vezes no mesmo dia é seguro: arquivos já processados são ignorados.

## Como configurar chaves e senhas

Nada sensível fica no código nem no repositório. O robô lê variáveis de ambiente ou o arquivo `robo_rpa/.env` (copie de `robo_rpa/.env.example`; o `.env` está no `.gitignore`):

| Variável | Para quê |
|---|---|
| `ZELA_API_URL` | Endereço da API do Zela (padrão `http://localhost:8000`) |
| `ZELA_GESTOR_USUARIO`, `ZELA_GESTOR_SENHA` | Login de gestor na API do Zela |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_DESTINO` | Envio real do boletim. Sem elas, o e-mail vira arquivo `.eml` |

O Open-Meteo não pede chave. O scraping usa só páginas públicas.

## Validação com dados de teste

`gerar_dados_teste.py` cria entradas com resposta conhecida (`dados/entrada/gabarito.json`): duas planilhas de OS com 17 linhas (8 corretas e 9 com erros de propósito: protocolo inválido, inexistente, status desconhecido, data ausente, data futura, linha duplicada e telefone na observação), uma planilha corrompida, 16 fotos rotuladas mais uma foto corrompida e 3 casos de drenagem (2 que devem subir de prioridade e 1 que já é alta). Resultados medidos em 12/11/2026 (`evidencias/`):

| O que foi medido | Resultado |
|---|---|
| Decisão por linha de planilha (aplicar ou mandar para revisão) | 17 de 17 corretas |
| Classificação das fotos de vistoria | 16 de 16 corretas (8 com fissura, 0 falsos positivos, 0 falsos negativos) |
| Regra de priorização com alerta de chuva (teste com 45 mm) | 3 de 3 corretas (2 elevadas, 1 mantida) |
| Idempotência | 2ª execução com os mesmos arquivos: 2 planilhas ignoradas, nenhuma atualização em dobro |
| Filtro de notícias relevantes (35 notícias rotuladas à mão) | v1: precisão 0,62, recall 0,87 · v2: precisão 0,93, recall 0,87 |

As fotos de teste vêm da mesma base usada no treino do modelo (outras imagens, não as mesmas), por isso 16 de 16 é otimista para fotos reais de campo.

## Casos de falha

**Falhas previsíveis tratadas (o robô não para):**

| Falha | O que acontece | Evidência |
|---|---|---|
| Open-Meteo fora do ar (no ambiente de teste a API foi bloqueada) | 3 tentativas com espera crescente; segue só com o alerta das notícias | `evidencias/execucao_1.md` |
| API do Zela fora do ar | 3 tentativas; atualizações ficam pendentes; fotos, notícias e e-mail continuam | `evidencias/execucao_5.md` |
| Planilha corrompida (colunas erradas) | Arquivo vai inteiro para revisão humana | todas as execuções |
| Linha inválida | Linha vai para `revisao_humana_<n>.csv` com o motivo; as outras são aplicadas | `evidencias/revisao_humana_3.csv` |
| Foto corrompida | Registrada como inválida e enviada para revisão | todas as execuções |
| Sem SMTP | Boletim salvo como `.eml` | `evidencias/boletim_execucao_3.eml` |
| Arquivo já processado | Ignorado pelo hash (não aplica duas vezes) | `evidencias/execucao_4.md` |

**Falha real encontrada e corrigida: o filtro de notícias.** Na primeira versão, a palavra "defesa civil" marcava como relevante toda notícia do órgão, inclusive doação de cestas básicas e cursos para professores, e "piscin" (pensado para piscinão) marcou a reforma de uma piscina de clube. Ao mesmo tempo, uma notícia sobre proteção contra raios em tempestades passou despercebida. As 35 notícias coletadas foram rotuladas à mão (`dados/teste/noticias_rotuladas.csv`): precisão 0,62 e recall 0,87. Com as palavras-chave ajustadas, a precisão subiu para 0,93 com o mesmo recall. Ainda erram: dois textos sobre "redução de riscos" (falso negativo) e um curso de geólogas que cita área de risco (falso positivo). Como o ajuste foi feito olhando para a mesma amostra, o número da v2 é otimista; o certo é medir de novo numa coleta nova.

**Limitação observada:** a listagem de notícias da Defesa Civil municipal tem itens de 2020 a 2023, então o gatilho por notícia recente quase nunca dispara. Na prática, o alerta depende da previsão de chuva. Uma fonte melhor seria o boletim do CGE (Centro de Gerenciamento de Emergências).

## Ética, dados e ODS

O robô usa apenas dados públicos (notícias e previsão do tempo) e dados sintéticos de teste (planilhas e casos de drenagem gerados pelo script). O telefone que aparece numa das planilhas de teste é fictício e está lá para testar a rejeição. Nenhum dado pessoal real entra em API externa: a única chamada externa com dado do Zela é para a própria API do Zela. Se uma observação de OS contém telefone, CPF ou e-mail, a linha não é aplicada e o texto não é copiado para o relatório de revisão, que só mostra o motivo. Chaves e senhas ficam em variáveis de ambiente. O robô nunca fecha uma solicitação por conta própria a partir de uma suposição: toda priorização vem com nota "[robô]... Revisar" e tudo fica no banco de auditoria, para que o gestor possa conferir e desfazer. A automação contribui para o ODS 11 (cidades mais resilientes a chuvas, com resposta mais rápida em drenagem e estruturas) e para o ODS 16 (instituições eficazes e transparentes, com rastro de cada decisão).
