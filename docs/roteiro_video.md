# Roteiro do vídeo (até 5 minutos)

Grave a tela em 1080p com o app rodando com o **LLM real** (não o modo simulado). Deixe abertos antes de gravar:
o navegador no app, o VS Code no repositório e um terminal. Ensaie uma vez com cronômetro.

| Tempo | O que mostrar | O que falar (resumo) | Item do enunciado |
|---|---|---|---|
| 0:00–0:35 | Tela inicial do Zela | Problema: canais confusos e relatos mal descritos atrasam a zeladoria (dados da Câmara/Prefeitura no README). Público: moradores, em especial idosos, PcD e áreas de alagamento; e gestores. ODS 11 e 16. | Problema, público e ODS |
| 0:35–1:05 | Relatar: digitar um caso com telefone no texto (ex.: bueiro entupido) | Validação no front (mostrar o erro de “faltam N caracteres”), depois envio. | Entrada com validação |
| 1:05–1:30 | Barra de progresso e etapas | Design para latência: CEP → endereço → IA. | Latência |
| 1:30–2:05 | Cartão de resultado | Selo de urgência com ícone + texto, encaminhamento vindo da tabela (não da IA), previsão de chuva cruzada, dado pessoal removido, “Ouvir em voz alta”. | Resposta útil, acessibilidade |
| 2:05–2:30 | Corrigir a urgência e confirmar | Human-in-the-loop: nada vai sem confirmação; a correção é registrada. Protocolo gerado. Avaliar com 👍. | HITL |
| 2:30–2:55 | Painel da cidade | Mapa Plotly com zoom/hover, filtros de período, tipo e urgência mudando os gráficos; “ver em tabela”. | Plotly + 2 filtros |
| 2:55–3:15 | Gestor: login → fila → tratar → indicadores (matriz IA × decisão final) | RBAC; o gestor confirma/corrige; métricas de concordância da IA. | Diferencial RBAC |
| 3:15–3:35 | Terminal: `docker compose stop api` → tentar enviar no app → `docker compose start api` | Erro tratado: mensagem clara, texto preservado, sem stack trace. | Cenário de erro |
| 3:35–4:25 | VS Code | Pastas `features/ ui/ state/ providers/` e `routers/ schemas/ pipelines/ providers/`. Chamada ao LLM: `backend/app/providers/llm/openai_compat.py` (`_chamar`) orquestrada em `pipelines/triagem.py`; saída `schemas/analise.py` (`AnaliseIA`). Estado: `frontend/state/session.py`. Cache: `frontend/providers/dados.py` (`@st.cache_data`/`@st.cache_resource`) e cache por conteúdo em `triagem.py`. Chave: `.env` + `backend/app/config.py`; mostrar `git check-ignore .env` e o `.env.example`. | Explicar o código / autoria |
| 4:25–5:00 | `docs/avaliacao_ia.md`, ficha de validação e `pytest` passando | Resultados dos testes com pessoas, o ajuste feito, tabela de casos da IA (e comparação com a linha de base por palavras-chave). | Evidências de validação |

Dicas:
- Use um relato **já testado** para não depender da sorte ao vivo; tenha um segundo pronto.
- Se o plano gratuito do LLM limitar requisições, espere 1 minuto entre tomadas.
- Termine mostrando a URL do deploy (se houver) e o link do repositório.
