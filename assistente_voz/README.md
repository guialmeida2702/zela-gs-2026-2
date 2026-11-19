# Zela por voz · Assistente de voz (NLP, Chatbots & Virtual Agents)

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

O cidadão fala a dúvida sobre zeladoria ("como peço a poda de uma árvore?") e ouve a resposta em português, baseada em páginas oficiais da Prefeitura de São Paulo. A conversa tem memória: "e quanto tempo demora?" é entendida como continuação.

**Persona:** Dona Cida, 67 anos, mora no Ipiranga, enxerga mal letras pequenas e não gosta de digitar no celular. Quer saber a quem pedir a poda da árvore que encosta nos fios da rua dela.

## Arquitetura

```
microfone (push-to-talk) ou arquivo de áudio
  └─> STT: faster-whisper "small", local, int8, com o vocabulário do tema (voz/stt.py) ── o áudio é apagado logo após a transcrição
        └─> LLM + base de conhecimento: Assistente Zela pela API (voz/cerebro.py)
              · system prompt com papel, tom e limites  · RAG com citações e abstenção  · memória dos últimos turnos
              └─> adaptação para fala (voz/fala.py): sem citações, listas, emojis e links; frases curtas;
                  números, valores, datas, siglas e telefones escritos como se falam
                    └─> TTS: Piper, voz sintética pt_BR "faber" (voz/tts.py)
                          └─> alto-falante + transcrição e texto na tela + latência de cada etapa
```

Cada etapa é um módulo trocável. A orquestração de um turno, com medição de latência, está em `voz/pipeline.py`; a interface, em `app.py`.

**Base de conhecimento: RAG, e não fine-tuning nem só prompt.** As regras de poda, calçada e chuvas mudam e precisam de fonte para o cidadão conferir. Com RAG, a base é atualizada sem treinar o modelo e cada resposta cita a página oficial; com fine-tuning, o modelo decoraria os textos sem dizer de onde vieram e precisaria de novo treino a cada mudança. O RAG é o mesmo do assistente de texto (relatório em `docs/relatorios/genai_avaliacao.md`).

## Modelos, versões e licenças

| Etapa | Modelo / biblioteca | Versão | Licença |
|---|---|---|---|
| STT | Whisper `small` e `tiny` via faster-whisper (CTranslate2, int8) | faster-whisper 1.2.1, pesos Systran/faster-whisper-small | MIT |
| LLM | Qwen2.5-1.5B-Instruct, GGUF Q4_K_M, via llama-cpp-python (servidor compatível com OpenAI) | llama-cpp-python 0.3.36 | Apache-2.0 (modelo), MIT (servidor) |
| Busca | BM25 (rank-bm25) + `paraphrase-multilingual-MiniLM-L12-v2` (fastembed) | 0.2.2 / 0.9.1 | Apache-2.0 |
| TTS | Piper, voz `pt_BR-faber-medium` (alternativa `pt_BR-cadu-medium`) | piper-tts 1.8.0 | GPL-3.0 (motor); voz treinada com base CC0 |
| Números por extenso | num2words | 0.5.14 | LGPL-2.1 |
| Interface | Streamlit (`st.audio_input` para o microfone) | 1.67.0 | Apache-2.0 |

Tudo roda localmente, sem GPU (testado em CPU de 2 núcleos) ou no Google Colab com T4.

## Como executar

```bash
# 1) API do Zela com o assistente (veja o README principal). LLM local, por exemplo:
python -m llama_cpp.server --model qwen2.5-1.5b-instruct-q4_k_m.gguf --port 8080 --n_ctx 4096 --chat_format chatml &
cd backend && LLM_PROVIDER=openai_compat LLM_BASE_URL=http://127.0.0.1:8080/v1 LLM_API_KEY=local \
  LLM_MODEL=qwen2.5-1.5b-instruct LLM_TIMEOUT_S=300 GESTOR_SENHA=troque JWT_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))") \
  uvicorn app.main:app --port 8000 &
# 2) assistente de voz
cd assistente_voz
pip install -r requirements.txt
ZELA_API_URL=http://localhost:8000 streamlit run app.py     # STT_MODELO=tiny para máquinas mais fracas
```

Na primeira execução, os modelos de fala são baixados do Hugging Face (cerca de 550 MB). A transcrição recebe uma lista curta de palavras do tema ("Sabesp", "PMSP", "bueiro", "subprefeitura"), o `initial_prompt` do Whisper; nas 20 gravações reais, isso baixou o erro de 10,7% para 9,1% (nos áudios sintéticos, de 19,3% para 13,2%) sem custo de tempo. Variáveis: `ZELA_API_URL`, `STT_MODELO` (`small` ou `tiny`), `TTS_VOZ` (`faber` ou `cadu`), `MODELOS_CACHE_DIR`.

## Ética e privacidade

- **Consentimento:** a primeira tela explica o que acontece com a voz e só libera o microfone depois do "Entendi e concordo".
- **Sem retenção de áudio:** a gravação vai para um arquivo temporário só durante a transcrição e é apagada em seguida. O histórico guarda apenas texto, com CPF e e-mail removidos, e some quando a página é fechada.
- **Fora do escopo:** saúde, questões jurídicas, financeiras e outros assuntos recebem recusa e indicação de procurar um profissional. Em risco, a resposta manda ligar 193 ou 199.
- **"Não sei":** se as fontes não têm a resposta, o assistente diz que não encontrou e indica o 156.
- **Clonagem de voz:** é proibido clonar a voz de uma pessoa real sem consentimento expresso e documentado. O projeto usa apenas vozes sintéticas prontas do Piper; nenhuma voz real foi clonada.

## Testes (pasta `avaliacao/`)

| Teste | Script | Material | Situação |
|---|---|---|---|
| STT: WER de 20 áudios gravados por pessoas (3 vozes ou mais, 5 com ruído); comparação `tiny` x `small` x `small` com vocabulário do tema | `avaliar_stt.py --pasta avaliacao/audios_reais` | `frases_stt.csv` (frases para ler), `audios_reais/manifesto.csv` | Linha de base com áudios sintéticos feita; **gravações reais pendentes** |
| LLM: 30 perguntas (20 diretas, 5 continuações, 5 fora do escopo) | `avaliar_llm.py` | `perguntas_llm.json` | Executado |
| TTS: 10 respostas, notas de 1 a 5 de 3 pessoas ou mais | `avaliar_tts.py` e `avaliar_tts.py --resumir` | `amostras_tts/`, `resultados/notas_tts.csv` | Áudios e latência prontos; **notas pendentes** |
| Ponta a ponta: 10 conversas de 3 turnos, latência por etapa | `avaliar_e2e.py` | conversas no próprio script | Executado com perguntas faladas por voz sintética |

Para gravar os áudios reais (o autor e pelo menos mais duas pessoas, com consentimento): cada pessoa lê as frases de `frases_stt.csv` (as 5 marcadas como `ruido` com TV, rua ou ventilador ligados), salva como WAV e preenche `audios_reais/manifesto.csv` (`arquivo;id;locutor;condicao`). Depois: `python avaliacao/avaliar_stt.py --pasta avaliacao/audios_reais`.

Resultados e análise: `docs/relatorios/pln_assistente_voz.md` (o PDF do relatório é gerado a partir dele).
