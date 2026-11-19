# Conformidade com os enunciados · Global Solution 2026.2

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

Este documento confere, item a item, cada enunciado e cada barema contra o repositório. Ele foi montado na
revisão em três rodadas pedida antes da entrega; o registro das rodadas está no fim.

Legenda: ✅ atendido no repositório · ⚠️ atendido com ressalva (explicada na linha) · 🧑 depende do autor
(gravação, teste com pessoas, vídeo, envio no portal).

## Itens comuns a todas as disciplinas

| Item | Onde está | Situação |
|---|---|---|
| Nome completo e RM do autor nos materiais | README de cada módulo, capas dos relatórios em PDF, capa e folha de rosto do documento ABNT | ✅ |
| Entrega individual permitida | Enunciado geral ("trio, dupla ou individualmente") e enunciados das disciplinas | ✅ |
| Repositório no GitHub com tudo antes do prazo (19/11/2026, 23h55) | `ENTREGA.md` explica o que subir | 🧑 publicar e colar o link no README e no tópico "Links" do documento ABNT |
| Chaves fora do código e do repositório | `.env.example` sem valores; `.gitignore` com `.env`; leitura por variável de ambiente | ✅ |
| Dados pessoais reais fora de APIs | Dados de teste sintéticos ou públicos; anonimização antes do LLM | ✅ |
| Vídeo pitch de até 7 min para o prêmio (opcional) | Roteiro em `docs/roteiro_video_integrador.md` | 🧑 |

## Front End & Mobile (Front-end em Sistemas de IA)

| Requisito (seção do enunciado) | Onde está | Situação |
|---|---|---|
| 3.1 Entrada com validação de obrigatórios, tamanho e formato antes do envio | `frontend/features/relatar.py` (`validar_relato`, `validar_contato`); testes em `frontend/tests/test_validacao_e_contraste.py` | ✅ |
| 3.1 Front não chama o LLM; chamada no FastAPI com saída Pydantic | `backend/app/providers/llm/`, `backend/app/schemas/analise.py` (`AnaliseIA`), `pipelines/triagem.py` | ✅ |
| 3.1 Resultado útil (classificação, orientação, encaminhamento, protocolo) | Cartão de análise, tela de revisão e protocolo (`frontend/ui/components.py`) | ✅ |
| 3.2 Front e back separados, por HTTP, nas camadas exigidas | `frontend/{features,ui,state,providers}`, `backend/app/{routers,schemas,pipelines,providers}` | ✅ |
| 3.3 `st.session_state`, `@st.cache_data` e `@st.cache_resource` sem chamadas repetidas | `frontend/state/session.py`, `frontend/providers/dados.py`; histórico alimenta "Minhas solicitações" e os gráficos | ✅ |
| 3.4 API fora do ar, timeout, erro do LLM e resposta inválida com mensagem clara | `frontend/providers/api_client.py` (`ErroApi`), `backend/app/core/erros.py`; testes `test_app_abre_mesmo_com_api_fora_do_ar`, `test_falha_da_ia_mostra_mensagem_amigavel_e_mantem_texto` | ✅ |
| 3.4 Segredos em variáveis de ambiente e `.env.example` | `.env.example` na raiz | ✅ |
| 3.4 Validação Pydantic no back e CORS restritivo | `backend/app/schemas/`, `backend/app/main.py` (lista de origens; `*` recusado em produção); teste de CORS | ✅ |
| 3.5 Tabs, colunas e sidebar, linguagem simples | `frontend/app.py`, abas do cidadão e do gestor | ✅ |
| 3.5 Design para latência e estados vazio e de erro | spinner e barra de progresso na análise; estados vazios nas listas e gráficos | ✅ |
| 3.5 Cores semânticas com texto e ícone, contraste, rótulos | `frontend/ui/theme.py`; teste automático de contraste WCAG (`test_selos_passam_wcag_aa`) | ✅ |
| 3.5 README lista os cuidados de acessibilidade | README, seção 9 | ✅ |
| 3.5 Human-in-the-loop | Cidadão confirma ou corrige tipo e urgência antes do registro; gestor revisa; botão "útil/não útil" | ✅ |
| 3.6 Plotly interativo com dados da solução + 2 filtros | `frontend/ui/charts.py` (mapa, barras, linha do tempo, matriz IA × gestor), `frontend/ui/filters.py` (período, tipo, urgência, situação) | ✅ |
| 3.6 Componente reutilizável | `components.cartao_solicitacao` (modo cidadão e gestor), `filters.painel_filtros` e `charts.exibir` (usados em várias telas com parâmetros diferentes) | ✅ |
| 3.7 Docker (opção B): `docker compose up` sobe tudo | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`; testado em 12/11 (25/25 pela API e 12/12 no navegador) | ✅ |
| 3.7 Deploy em plataforma (opção A, opcional se houver Docker) | `render.yaml` pronto | 🧑 opcional |
| 3.8 Problema e público com fonte | README, seções 1 e 8.1 (dados do SP156) | ✅ |
| 3.8 ODS com justificativa | README, seção 8.2 (ODS 11 e 16) | ✅ |
| 3.8 Decisões técnicas (Streamlit, prompt, formato, deploy) | README, seção 8.3 | ✅ |
| 3.8 Ética e limites da IA | README, seção 8.4 | ✅ |
| 3.8 (a) Teste com 3 pessoas, roteiro, observações e um ajuste | Roteiro em `docs/validacao_usuarios.md`; README 8.5 (a) com a tabela a preencher | 🧑 aplicar o teste e preencher |
| 3.8 (b) Tabela com ao menos 3 casos de teste da IA | README 8.5 (b) e `docs/avaliacao_ia.md` (10 casos, prompt v3 x v4, ajustes) | ✅ |
| 4 `requirements.txt` de cada serviço e README completo | `backend/requirements.txt`, `frontend/requirements.txt`, README | ✅ |
| 4 Vídeo de até 5 min | Roteiro em `docs/roteiro_video.md` | 🧑 |
| Diferenciais: Docker + deploy, dados abertos, RBAC do gestor, modelo próprio, testes, acessibilidade avançada | README, seção 11 | ✅ (deploy público 🧑) |

## Visão Computacional

| Requisito | Onde está | Situação |
|---|---|---|
| Base sugerida, exame das imagens, redimensionamento e normalização | Concrete Crack Images for Classification (Mendeley, DOI 10.17632/5y9wdsg2zt); `visao_computacional/pipeline.py` | ✅ |
| Treino, validação e teste sem misturar recortes da mesma imagem | Relatório, seção de dados: divisão por blocos de 50 arquivos consecutivos (a base não informa a foto de origem, e recortes vizinhos vêm da mesma foto), com semente fixa | ⚠️ aproximação documentada no relatório |
| CNN com transferência de aprendizado e amostra dos dados | MobileNetV3-Small pré-treinada, 5.800 imagens | ✅ |
| Precisão, recall, F1 e matriz de confusão | `visao_computacional/resultados/metricas.json`, matriz no relatório (teste: P 0,990, R 0,999, F1 0,994 no limiar 0,15) | ✅ |
| Acertos e erros com sombras, texturas, iluminação | Relatório, análise de erros e teste de perturbações | ✅ |
| Funcionalidade no protótipo com resultado visual e confiança | Relato com foto (áreas marcadas e confiança), `POST /visao/analisar` | ✅ |
| Vídeo curto ou sequência de imagens | Aba "Monitoramento por imagens" do gestor (`POST /visao/lote`) e `resultados/monitoramento_simulado.mp4` | ✅ |
| Latência média, FPS, equipamento e resolução | Relatório, seção de desempenho (CPU Xeon de 2 threads, 227×227 por recorte e foto de 12 MP) | ✅ |
| Justificativa de arquitetura, pré-processamento e limiar | Relatório | ✅ |
| Gravidade não é inferida da presença de fissura | Texto da interface e do relatório | ✅ |
| Notebook ou código executável, relatório breve | `visao_computacional/pipeline.py`, `docs/relatorios/pdf/visao_computacional.pdf` | ✅ |
| Vídeo de demonstração | Roteiro no fim do relatório | 🧑 |

## Generative AI & Advanced Nets

| Requisito | Onde está | Situação |
|---|---|---|
| Assistente integrado ao protótipo | Aba "💬 Tire dúvidas", `POST /assistente/perguntar`, consulta pelo protocolo | ✅ |
| Base pertinente e identificável (fontes, URLs, datas) | `backend/app/conhecimento/` e `fontes.json`; tabela na seção 1 do relatório | ✅ |
| Chunking justificado, tamanho, overlap, metadados, comparação | Relatório, seções 1 e 2 (blocos fixos x estrutura x estrutura com subtítulos; evid@4) | ✅ |
| Retriever justificado: lexical, denso, híbrido, embeddings, top-k, filtros, reranking | Relatório, seções 1 e 2 | ✅ |
| Generator: modelo, prompt (papel, instruções, contexto, formato, abstenção), parâmetros | Relatório, seção 1 e apêndice B (prompt completo) | ✅ |
| Avaliação separada de recuperação e geração, e do fluxo completo | Relatório, seções 2, 3 e 4 | ✅ |
| Pelo menos 10 perguntas: respondíveis, sem resposta, ambíguas, desvio do propósito | 22 perguntas ponta a ponta + 4 adversariais (`backend/scripts/avaliar_assistente.py`) | ✅ |
| Contexto recuperado, resposta e julgamento de cada pergunta | Relatório, seção 4 e apêndice A | ✅ |
| Taxa de respostas não sustentadas | Relatório, seção 4 ("Fundamentação"), a partir da conferência manual | ✅ |
| Pelo menos dois testes adversariais | 4 testes (injeção direta, revelar prompt, injeção por documento, dados pessoais) | ✅ |
| Mitigação de respostas não sustentadas, injeção e exposição de dados | Relatório, seções 5, 6 e 7; testes em `backend/tests/test_inteligencia.py` | ✅ |
| Interpretação dos resultados e impacto para o cidadão | Relatório, seção 8 | ✅ |
| Código, dependências e instruções | `backend/requirements.txt`, relatório, seção 10 | ✅ |
| Credenciais e dados pessoais não expostos | `.env.example`; anonimização da pergunta | ✅ |
| Vídeo de até 5 min | Roteiro no fim do relatório | 🧑 |

## NLP, Chatbots & Virtual Agents

O enunciado em PDF da disciplina pede um assistente de voz; o slide do enunciado geral descreve uma ferramenta de
construção de corpus. O professor confirmou em 16/11/2026 que as duas entregas são exigidas, e as duas estão no
repositório; o relatório de PLN cobre as duas (seções 1 a 7 e seção 8).

**Assistente de voz (`assistente_voz/`)**

| Requisito | Onde está | Situação |
|---|---|---|
| Persona, problema e ODS | `docs/relatorios/pln_assistente_voz.md`, seção 1 | ✅ |
| Nuvem ou local, justificado (custo, latência, privacidade, internet) | Relatório, seção 3 | ✅ |
| Módulos separados: microfone, STT, LLM, TTS, alto-falante | `assistente_voz/voz/` (`stt.py`, `cerebro.py`, `fala.py`, `tts.py`, `pipeline.py`) | ✅ |
| Gravação pelo microfone e upload de arquivo | `assistente_voz/app.py` (`st.audio_input` e `st.file_uploader`) | ✅ |
| System prompt com papel, tom e limites; memória da conversa | Assistente Zela (prompt no apêndice B do relatório de GenAI); histórico enviado a cada turno | ✅ |
| Base de conhecimento por RAG, justificada | Relatório, seção 2 | ✅ |
| Adaptação para fala (sem markdown, números, siglas, datas) | `assistente_voz/voz/fala.py`; 9 testes | ✅ |
| TTS em português com voz natural | Piper (vozes faber e cadu) | ✅ |
| Interface mostra transcrição e resposta em texto | `assistente_voz/app.py` | ✅ |
| Latência por etapa e total | Registrada em cada turno e na avaliação de ponta a ponta | ✅ |
| Consentimento, retenção mínima, limites, sem clonagem de voz | Tela de consentimento, áudio descartado após a transcrição, recusas fixas, só vozes prontas | ✅ |
| STT: 20 áudios gravados, 3 vozes, 5 com ruído, WER (jiwer) | 20 gravações de 3 pessoas (homem 22, mulher 48, homem 55), 5 com TV ou ventilador, em `avaliacao/audios_reais/`: WER 27,9% (tiny), 10,7% (small) e 9,1% (small com vocabulário); teste extra com ruído de rua a 10 dB: 10,7% | ✅ |
| LLM: 30 perguntas com resposta esperada (5 continuações, 5 fora do escopo) | `avaliacao/perguntas_llm.json`, `resultados/llm_30_perguntas.csv` | ✅ |
| TTS: 10 respostas avaliadas por 3 pessoas (1 a 5) | 3 pessoas, 10 respostas na voz `faber`: naturalidade 5,00 e clareza 5,00 (aba TTS e `resultados/notas_tts.csv`); limites da nota unânime discutidos no relatório, seção 4.3 | ✅ |
| Ponta a ponta: 10 conversas de 3 turnos com latência | `resultados/e2e_10_conversas.csv` | ✅ |
| Comparação de duas opções num componente | STT: tiny x small x small com vocabulário do tema (WER e tempo) | ✅ |
| Análise de viés do STT | Relatório, seção 5.1: WER por gênero e faixa etária nas gravações reais (feminina 14,7%, masculinas 2,9% e 10,2%), volume de cada gravação e limites da comparação | ✅ |
| README com arquitetura, modelos com versão e licença, execução, nome completo | `assistente_voz/README.md` | ✅ |
| Material de teste: áudios, perguntas com respostas esperadas, planilhas | `avaliacao/audios_sinteticos/`, `perguntas_llm.json`, `planilha_avaliacao.xlsx` | ✅ |
| Relatório em PDF | `docs/relatorios/pdf/pln_assistente_voz.pdf` | ✅ |
| Vídeo de até 5 min com conversa real de 3 turnos, continuação e recusa | Roteiro no relatório, seção 9 | 🧑 |

**Ferramenta de construção de corpus (`corpus_pln/`), conforme o enunciado geral**

| Requisito | Onde está | Situação |
|---|---|---|
| Subir diversos tipos de documentos e textos | Interface (`streamlit run app.py`) e linha de comando; PDF, DOCX, HTML, TXT, MD, CSV, JSON, JSONL e texto colado | ✅ |
| Limpeza e normalização | `corpus/limpeza.py`: Unicode, cabeçalho e rodapé, menus, quebras, dados pessoais, repetidos; antes e depois na interface | ✅ |
| Três corpora: conversacional, perguntas e respostas, texto puro | `corpus/geradores.py`; JSONL nos formatos `messages`, `instruction/output` e `text` | ✅ |
| Uso em fine-tuning de LLM pequeno | Treino e validação por documento, rastreabilidade, estatísticas e ficha do corpus | ✅ |
| Testes | `corpus_pln/tests/` (13 testes) | ✅ |
| Documentação | `corpus_pln/README.md` e seção 8 do relatório de PLN, com os números da execução registrada em `corpus_pln/resultados/` | ✅ |
| Vídeo | parte final do vídeo de PLN (cerca de 1 min) | 🧑 |

## AI for RPA

| Requisito | Onde está | Situação |
|---|---|---|
| Pelo menos 3 temas com função real e justificativa | `robo_rpa/README.md`, quadro de temas (6 temas e uma regra de decisão) | ✅ |
| IA onde agrega; LLM opcional | Modelo de fissuras de Visão Computacional e regras; o robô não usa LLM | ✅ |
| Falhas previsíveis com log e caminho seguro | Tabela "Casos de falha" do README; `robo_rpa/evidencias/` | ✅ |
| Ferramentas gratuitas e dados sintéticos ou públicos | Open-Meteo, páginas públicas, planilhas e fotos de teste | ✅ |
| Chaves fora do código | Variáveis de ambiente (`ZELA_*`, `SMTP_*`) | ✅ |
| Ponto de entrada claro e README que permite rodar sem ajuda | `robo.py`, README "Como executar" | ✅ |
| README: integrantes, problema, execução, chaves | `robo_rpa/README.md` | ✅ |
| Evidências: dados de teste, resultado medido, caso de falha | 17/17 linhas, 16/16 fotos, 3/3 priorizações, filtro de notícias 0,62 → 0,93 de precisão | ✅ |
| Parágrafo de proteção de dados, ética e ODS | `robo_rpa/README.md`, seção final | ✅ |
| Diferenciais: execução sem intervenção, timeout, retry com espera, idempotência, relatório, revisão humana | README e código | ✅ |

## Cluster Computing, Computação Neuromórfica e Supercomputadores

| Requisito | Onde está | Situação |
|---|---|---|
| Demanda do CitizenTech ligada à função de IA, com carga justificada | `docs/relatorios/cluster.md`, seção 1 (fila de triagem após um temporal) | ✅ |
| Dois cenários no iSPD: 2 e 4 workers, só o número de workers muda | `cluster/modelos/*.imsx`, `cluster/gerar_modelos.py` | ✅ |
| Parâmetros e unidades | Relatório, seção 2 | ✅ |
| Total Simulated Time e distribuição na aba Resources, com capturas legíveis | Relatório, seção 3; `cluster/capturas/` | ✅ (T2 = 3.602,27 s; T4 = 1.801,16 s) |
| Redução percentual e T2/T4 | Relatório (50,0% e 2,00) | ✅ |
| Gargalos, limitações e limites de extrapolar para o protótipo | Relatório, seções 4 e 5 | ✅ |
| Relatório de 2 a 4 páginas com projeto e integrante | `docs/relatorios/pdf/cluster.pdf` (4 páginas) | ✅ |
| Reprodução | Arquivos `.imsx`, `cluster/simular.py` e seção "Como reproduzir" | ✅ |

## Computação Quântica & IA

| Requisito | Onde está | Situação |
|---|---|---|
| Gargalo real quando o número de cidadãos cresce | `docs/relatorios/quantica.md`, seção 1 | ✅ |
| Capacidade quântica escolhida e justificada | Seção 2 (otimização do despacho e criptografia pós-quântica) | ✅ |
| Roteiro realista: IA clássica hoje, quântico no futuro | Seção 3 | ✅ |
| Ética, LGPD e ODS | Seção 4 | ✅ |
| Não precisa programar algoritmo quântico | Nenhum código quântico, como permitido | ✅ |

## Physical Computing, Robotics & Cognitive IoT (OuviAí)

| Requisito | Onde está | Situação |
|---|---|---|
| Capa com título, nome e RM | `iot_ouviai/relatorio_ouviai.md` | ✅ |
| Problema, público e ODS | Relatório, seção 1 | ✅ |
| Arquitetura microfone → MFE → CNN → resultado no celular | Relatório, seção 2 e `arquitetura.png` | ✅ |
| 20 gravações de 5 s por classe (15 treino, 5 teste), 16 kHz mono | 60 gravações no Edge Impulse (17/11), divisão ajustada para 15/5 por classe, conferência da forma de onda na aba `Gravacoes` | ✅ |
| MFE + CNN, parâmetros, validação e matriz de confusão | Relatório, seção 4: janela 1.000 ms, passo 500 ms, MFE padrão, CNN 1D, validação 90,1% (int8) | ✅ |
| Classify all com 5 arquivos de teste por classe | Relatório, seção 5 e aba `Teste_arquivos`: 76,1% por janela, 12 de 15 arquivos, matrizes e discussão dos erros | ✅ |
| Run this model no celular, 15 tentativas ao vivo, percentual de acertos | Relatório, seção 6 e aba `Teste_ao_vivo`: 10 de 15 (66,7%), 5 falsos positivos em ambiente | ✅ (vídeo: https://youtube.com/shorts/BKm9vIrK8n4) |
| Capturas de Data acquisition, Impulse design, Generate features, Classifier e Model testing | `iot_ouviai/capturas/`, no relatório | ✅ |
| Três avaliações diferenciadas e "probabilidade não é acurácia" | Relatório, seção 7 | ✅ |
| Evolução para alertas acessíveis; privacidade; caráter educacional | Relatório, seções 8 e 9 | ✅ |

## Governança em IA & Business Analysis

| Requisito | Onde está | Situação |
|---|---|---|
| Documento ABNT/FIAP de 10 a 15 páginas | `docs/governanca/Zela_documentacao_integrada.pdf` (gerado por `gerar_documento.py`): 15 páginas com capa, folha de rosto, listas, sumário e referências | ✅ (a conclusão precisa caber na página 13) |
| Capa e folha de rosto com o nome do integrante | Documento ABNT | ✅ |
| Listas e sumário | Listas de figuras, quadros e tabelas e sumário gerados automaticamente; inventário dos ativos de IA no quadro da seção 2.9.1 | ✅ |
| Introdução | Seção 1 | ✅ |
| Desenvolvimento com um tópico por disciplina, terminando em Governança, com o que foi ou não integrado | Seções 2.1 a 2.9 e quadro 2.9.5 | ✅ |
| Conclusão escrita pelo autor, sem IA na redação | Seção 3 com aviso e roteiro | 🧑 escrever |
| Tópico "Links" | Seção 4 | 🧑 colar os links |
| Vídeo de 5 a 7 min no YouTube, não listado, sem leitura de texto | `docs/roteiro_video_integrador.md` | 🧑 |
| GitHub sem commits depois da entrega | `ENTREGA.md` | 🧑 |
| Sem excesso de jargões de IA | Texto revisado (frases diretas, sem hipérboles nem travessões em excesso) | ✅ |

## Registro das três rodadas de revisão

Cada rodada releu todos os enunciados e baremas, executou o projeto e corrigiu o que apareceu.

### Rodada 1 (12 e 13/11/2026): releitura completa e teste de ponta a ponta

O que foi feito: releitura dos nove enunciados e baremas; execução de todos os testes automatizados; subida da
pilha pelo Docker Compose e percurso completo pela API (25 verificações) e pelo navegador (12 etapas); nova execução
das avaliações com o modelo local (assistente, 30 perguntas e 10 conversas por voz).

Defeitos encontrados e corrigidos:

| # | Onde | O que acontecia | Correção | Como foi confirmado |
|---|---|---|---|---|
| 1 | Todos os materiais | A autoria ainda citava grupo e tinha lugares para outros nomes | Autoria individual em todos os arquivos; texto em primeira pessoa do singular ou impessoal | Busca por "grupo", "integrantes" e verbos no plural |
| 2 | Docker | O `.env` com `MODELOS_CACHE_DIR=` vazio anulava o caminho do modelo de embeddings na imagem, e a busca do assistente caía para só BM25 | Caminho definido no `docker-compose.yml`; variável comentada no `.env.example` | `/health` do contêiner passou a informar busca `hibrido` |
| 3 | Front | A categoria "fissura ou dano em estrutura" faltava no espelho local do front; a tela de revisão e o formulário do gestor quebravam em relatos com foto de rachadura | Categoria incluída; caixas de seleção aceitam categoria nova sem quebrar | Teste que compara o espelho do front com os tipos da API; 12/12 no navegador |
| 4 | API | Em contêiner ou nuvem (relógio em UTC), protocolo e datas saíam 3 horas adiantados | Relógio do serviço com fuso configurável (`FUSO_HORARIO`, padrão Brasília) | Teste com `TZ=UTC` |
| 5 | Assistente | Resposta com conselho inventado no meio de frases corretas passava pela média de sustentação | Conferência frase a frase, com uma fonte por vez; frase sem apoio sai | Testes de regressão; rodadas 3 a 6 do relatório de GenAI |
| 6 | Assistente | Número certo citado do trecho vizinho virava abstenção; número inventado junto de um certo passava | Número precisa estar na mesma fonte da frase, como número inteiro; a citação é completada com a fonte certa | Rodada 6: A2 e M3 corretos |
| 7 | Assistente | Terceiro turno da conversa perdia o assunto; pergunta sem assunto recebia resposta montada; pedido de revelar o prompt chegava ao modelo | Continuação herda o assunto da conversa; pedido de esclarecimento; recusa fixa sem chamar o modelo | Conversa de 3 turnos 3/3; S2 aprovado |
| 8 | Assistente de voz | Nomes do domínio ("Sabesp", "PMSP", "bueiro") eram mal transcritos | Vocabulário do tema informado ao Whisper | WER de 19,3% para 13,2% nos mesmos 20 áudios |
| 9 | Assistente de voz | Endereço de site lido letra a letra; perguntas sem resposta esperada escrita | Endereço vira "site oficial"; 30 perguntas com resposta esperada; planilha de avaliação | Testes de adaptação para fala |
| 10 | PLN | O enunciado geral descreve uma ferramenta de corpus que não existia | Ferramenta `corpus_pln/` com interface, linha de comando e 13 testes | Execução com 10 documentos de exemplo em 6 formatos |
| 11 | Cluster | Faltavam unidades na tabela, limites de extrapolar para o protótipo e capturas legíveis | Relatório refeito em 4 páginas | Leitura do PDF |
| 12 | IoT | Relatório sem a estrutura pedida | Capa, seções do enunciado, planilha com fórmulas, verificador de áudio | Leitura do PDF e da planilha |

Resultados da nova execução com o modelo local (13/11/2026): assistente 20 de 22 perguntas pelo critério automático,
taxa de respostas não sustentadas de 12,5% (2 de 16) na conferência manual e 4 de 4 testes adversariais; teste de
voz com 72% de acerto automático e 68% na conferência manual nas 25 perguntas com resposta, 5 de 5 recusas e 16 de
30 turnos adequados nas conversas; fluxo completo no navegador com o modelo real, 12 de 12 etapas.

Mantido como limitação documentada (não corrigido): o assistente ainda copia o item vizinho das perguntas
frequentes em duas perguntas (A6 e U4); no teste de voz, a maior parte das falhas é abstenção quando a busca não traz
o trecho certo, e a reprodução desses turnos mostra que a conferência por frase nem sempre barra a resposta errada
(`assistente_voz/avaliacao/resultados/reproducao_abstencoes.txt`). Três versões de verificação de pertinência foram testadas e descartadas
porque barravam respostas certas; a evidência está em `avaliacao/genai/`.

### Rodada 2 (13/11/2026): o pacote entregue, numa pasta nova, seguindo só os READMEs

O que foi feito: o zip da rodada 1 foi extraído numa pasta vazia e instalado num ambiente virtual novo, com os
`requirements` de cada módulo; os testes rodaram ali (90 da API, 42 da interface, 13 da ferramenta de corpus e 9 da
adaptação para fala); a pilha subiu pelo Docker Compose a partir dessa cópia e passou pelo teste de fumaça (25 de 25)
e pelo fluxo no navegador; o robô, a ferramenta de corpus, a interface de voz (com envio de arquivo de áudio) e o
estudo do iSPD foram executados pelos comandos dos READMEs.

| # | Onde | O que acontecia | Correção |
|---|---|---|---|
| 1 | Robô RPA | O README não dizia para definir a senha do gestor antes de `gerar_dados_teste.py`, que falhava com um erro técnico; o README também dizia que o robô lia um `.env`, o que não era verdade | Passo com `ZELA_GESTOR_SENHA` no README; leitura de `robo_rpa/.env` sem sobrescrever o ambiente; `robo_rpa/.env.example`; mensagens claras quando a API não responde ou o login é recusado |
| 2 | Área do gestor | Com a fila cheia, o relato recém-criado ficava fora das linhas visíveis (a fila é ordenada por urgência e antiguidade), e o fluxo no navegador falhou numa repetição | Campo "Buscar protocolo" na fila; o teste no navegador passou a usá-lo e passou duas vezes seguidas |
| 3 | Cluster | Repetindo as simulações, o cenário de poucas tarefas variou de 1,41 a 1,49 em T2/T4, mais que o informado | Variação registrada no relatório (que continua com 4 páginas) |
| 4 | Relatórios de GenAI e PLN | As observações da conferência manual ficavam numa coluna estreita e esticavam as tabelas (o relatório de PLN tinha 21 páginas) | Observações listadas abaixo de cada tabela; relatório de PLN com 14 páginas |
| 5 | Matriz de conformidade | A linha da divisão treino/validação/teste de Visão Computacional estava imprecisa | Texto corrigido: divisão por blocos de arquivos consecutivos, como aproximação documentada |
| 6 | Script de PDFs | Caminhos passados a partir da raiz do repositório não funcionavam | O script aceita caminhos relativos à pasta de onde é chamado |

Sem defeito encontrado: instalação dos `requirements` sem conflito (`pip check`), testes, ferramenta de corpus pela linha
de comando, filtro de notícias do robô (precisão 0,93), Docker Compose com busca híbrida dentro do contêiner e
horário de Brasília com o contêiner em UTC.

### Rodada 3 (13/11/2026): conferência final do pacote, item a item

O que foi feito: cada linha desta matriz foi conferida contra o zip final extraído numa pasta nova; os testes rodaram
de novo a partir dele; o pacote foi revisado para chaves de API, e-mails pessoais, bancos de dados e arquivos `.env`
(nenhum encontrado); as páginas dos PDFs foram contadas (documento ABNT com 15 páginas; relatório de Cluster com 4); e
o texto do documento ABNT foi revisado para expressões vagas ou de efeito.

Correções desta rodada: uma expressão de efeito no documento ABNT foi trocada por texto direto. Nenhum defeito de
funcionamento apareceu.

O que continua com o autor, por depender de pessoas, gravações ou contas: teste de usabilidade com 3 pessoas
(Front End), conclusão do documento
ABNT escrita sem IA, vídeos, publicação no GitHub antes do prazo e as duas partes do vídeo de PLN (o professor confirmou
que as duas entregas são exigidas). A lista completa, com os comandos para regerar os documentos depois, está em `ENTREGA.md`.
