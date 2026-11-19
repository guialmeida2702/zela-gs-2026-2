---
title: "Zela · PLN: assistente de voz e ferramenta de construção de corpus"
subtitle: "Global Solution 2026.2 · NLP, Chatbots & Virtual Agents"
author: "Guilherme Almeida (RM 563972)"
date: "Novembro de 2026"
lang: pt-BR
---

Este relatório cobre as duas entregas de PLN que o professor confirmou como exigidas: o assistente de voz (seções 1 a 7, enunciado em PDF da disciplina) e a ferramenta de construção de corpus para fine-tuning (seção 8, descrição do enunciado geral).

# 1. Problema, persona e ODS

Quem mais precisa de orientação sobre zeladoria nem sempre consegue digitar: idosos, pessoas com baixa visão ou pouca familiaridade com formulários. **Persona: Dona Cida, 67 anos**, mora no Ipiranga, enxerga mal letras pequenas e prefere falar a escrever. Ela quer saber a quem pedir a poda da árvore que encosta nos fios da rua e quanto tempo isso leva.

O assistente de voz do Zela responde perguntas faladas em português, com base em páginas oficiais da Prefeitura de São Paulo, e lembra o que foi dito antes na conversa. Ele está vinculado às outras disciplinas do projeto: usa o mesmo "cérebro" do assistente de texto do Zela (RAG com citações e abstenção, avaliado em `genai_avaliacao`), então as duas interfaces dão a mesma resposta.

**ODS.** ODS 10 (redução das desigualdades, meta 10.2: inclusão de quem tem dificuldade com interfaces escritas), ODS 11 (cidades sustentáveis: acesso a informação sobre serviços urbanos e segurança em chuvas) e ODS 16 (instituições eficazes: orientação correta reduz pedidos ao órgão errado).

# 2. Arquitetura

![Fluxo de um turno de conversa. Cada etapa é um módulo separado em `assistente_voz/voz/`.](../img/pln_pipeline.png){width=100%}

| Etapa (módulo) | Escolha | Por quê |
|---|---|---|
| Captura (`app.py`) | `st.audio_input` (apertar para falar) e upload de WAV, MP3, M4A ou OGG | Apertar para falar evita gravar a casa inteira, como faria uma detecção de voz sempre ligada |
| STT (`voz/stt.py`) | faster-whisper `small`, int8, CPU, idioma fixo pt, filtro de voz do próprio Whisper e vocabulário do domínio como dica | Roda local (voz é dado pessoal) e sem custo por uso; a comparação da seção 4.1 definiu o tamanho e a dica |
| LLM e base (`voz/cerebro.py`) | Assistente Zela pela API: prompt de sistema com papel, tom e limites; RAG com 7 documentos oficiais e citações | As regras mudam e o cidadão precisa da fonte para conferir; o RAG atualiza a base sem treinar (um fine-tuning decoraria os textos sem citar) |
| Memória (`voz/pipeline.py`) | últimos 8 turnos enviados a cada pergunta; CPF e e-mail removidos | Permite "e quanto tempo demora?"; perguntas curtas herdam o assunto anterior na busca |
| Adaptação para fala (`voz/fala.py`) | sem citações, listas, links e emojis; até 4 frases, frases longas divididas; valores, datas, horas, porcentagens, siglas e telefones por extenso (num2words) | "R$ 439,66" e "0800 055 0195" lidos como texto ficam incompreensíveis |
| TTS (`voz/tts.py`) | Piper `pt_BR-faber-medium`, local | Voz sintética pronta, mais rápida que o tempo real em CPU; nenhuma voz clonada |
| Interface (`app.py`) | Streamlit: transcrição, resposta em texto, fontes, áudio e latência de cada etapa | O texto junto do áudio serve à acessibilidade e deixa o cidadão ver quando foi mal entendido |

**System prompt (resumo).** Papel: Assistente Zela, orienta moradores de São Paulo sobre zeladoria, chuvas e uso do Zela. Tom: frases curtas, linguagem simples, tratamento por "você". Limites: usar só as fontes, citar, dizer que não encontrou quando não houver fonte, recusar temas fora do escopo, nunca revelar instruções nem inventar dados pessoais, orientar 193 ou 199 em risco à vida. O texto completo está em `backend/app/pipelines/prompts.py` e no apêndice do relatório de IA generativa.

# 3. Local ou nuvem

| Critério | Tudo local (adotado nos testes) | LLM hospedado (opção de configuração) |
|---|---|---|
| Custo | Zero por uso; exige uma máquina com 8 GB de RAM | Camadas gratuitas com limite de chamadas; depois, custo por token |
| Latência | STT e TTS em cerca de 2 s cada; o LLM de 1,5 bilhão de parâmetros em CPU domina o tempo (seção 4.4) | Resposta do LLM em poucos segundos |
| Privacidade | A voz e o texto não saem da máquina | A voz continua local; o texto da pergunta, já sem CPF e e-mail, vai ao provedor, e a tela precisa avisar |
| Internet | Só para baixar os modelos na primeira vez | Necessária a cada pergunta |

**Decisão.** STT e TTS ficam sempre locais, porque a voz é dado pessoal e os dois modelos rodam bem em CPU. O LLM é configurável na API do Zela (`LLM_PROVIDER`): os testes deste relatório usaram o modelo local, que não depende de chave nem de internet e pode ser reproduzido por qualquer avaliador; para uso real, a latência medida indica um LLM hospedado ou uma GPU.

# 4. Resultados

Ambiente: CPU Intel Xeon de 2 núcleos, sem GPU, 8 GB de RAM. O LLM (Qwen2.5-1.5B-Instruct, Q4_K_M) roda na mesma máquina via llama.cpp.

## 4.1 STT: WER e comparação de três opções

WER calculado com jiwer, depois de normalizar caixa, pontuação e números. Foram comparados dois tamanhos do Whisper e, no maior, o efeito de informar o vocabulário do domínio (`initial_prompt`).

**Gravações reais** (as 20 frases de `avaliacao/frases_stt.csv`, lidas por 3 pessoas que autorizaram o uso das gravações no trabalho e a publicação no repositório: voz1, homem de 22 anos; voz2, mulher de 48; voz3, homem de 55. Gravador de voz do celular, um arquivo por frase, AAC a 48 kHz, convertido para 16 kHz. As frases S16 a S20 foram lidas com TV ou ventilador ligados):

| Opção | WER geral | Silencioso | Com ruído | Tempo médio por áudio | Fator de tempo real |
|---|---|---|---|---|---|
| tiny | 27,9% | 27,5% | 29,5% | 0,32 s | 0,08 |
| small | 10,7% | 10,5% | 11,4% | 1,88 s | 0,45 |
| small + vocabulário do domínio | 9,1% | 9,2% | 9,1% | 1,90 s | 0,46 |

| Voz | Áudios | tiny | small | small + vocabulário do domínio |
|---|---|---|---|---|
| voz1 | 7 | 22,9% | 8,6% | 2,9% |
| voz2 | 7 | 32,4% | 14,7% | 14,7% |
| voz3 | 6 | 28,8% | 8,5% | 10,2% |

**Volume e ruído das gravações** (`medir_niveis.py`, medianas): voz1 -20,6 dBFS, voz2 -29,7 dBFS e voz3 -18,7 dBFS de volume médio; a voz2 ficou cerca de 10 dB mais baixa, com relação sinal-ruído de 21,9 dB, contra 31,9 e 35,0 dB das outras. Nas gravações com ruído, o piso de ruído (-47,7 dBFS) ficou igual ao das silenciosas (-48,6 dBFS): o gravador do celular reduz o ruído de fundo, por isso as duas condições tiveram erro parecido.

**Teste de estresse com ruído controlado.** Para medir o STT com vozes reais em condição ruim, as 20 gravações receberam o mesmo ruído de rua da linha de base sintética, a 10 dB de SNR (`misturar_ruido.py`). O WER subiu de 10,7% para 14,2% no `small` e de 9,1% para 10,7% com o vocabulário; a voz mais baixa (voz2) foi a mais afetada, com 20,6%. O vocabulário do domínio continua ajudando com ruído.

**Onde o STT errou.** Os erros se concentram em poucas frases: "vazando no meio do asfalto" (voz2) virou "vazando o número das faltas", e "se a minha rua alagar" (voz3) virou "se me arrullar". Parte do erro medido pode ser diferença de leitura, e não de transcrição: em "Quem é o responsável" e "eu posso beber água", o modelo escreveu palavras que não estão no texto, e o WER conta qualquer diferença como erro.

**Linha de base com áudios sintéticos** (as 20 frases faladas por 3 vozes do Piper: faber, cadu e edresson; 5 com ruído de rua a 10 dB de SNR):

| Opção | WER geral | Silencioso | Com ruído | Tempo médio por áudio | Fator de tempo real |
|---|---|---|---|---|---|
| tiny | 29,4% | 26,8% | 38,6% | 0,32 s | 0,09 |
| small | 19,3% | 20,9% | 13,6% | 2,12 s | 0,56 |
| small + vocabulário do domínio | 13,2% | 13,7% | 11,4% | 1,75 s | 0,46 |

| Voz | Áudios | tiny | small | small + vocabulário do domínio |
|---|---|---|---|---|
| sintética cadu | 7 | 19,1% | 6,3% | 4,8% |
| sintética edresson | 6 | 35,6% | 30,5% | 18,6% |
| sintética faber | 7 | 33,3% | 21,3% | 16,0% |

**Escolha.** Nas gravações reais, o `small` reduz o WER de 27,9% para 10,7% em relação ao `tiny` e continua mais rápido que o tempo real (fator 0,45). Com o vocabulário do domínio, o erro cai para 9,1% sem custo de tempo: os nomes que o modelo errava ("Sabesp", "bueiro", "subprefeitura") passam a ser reconhecidos. Os áudios sintéticos mostram a mesma ordem (29,4%, 19,3% e 13,2%). O padrão é `small` com vocabulário; o `tiny` fica como opção para máquinas fracas (`STT_MODELO=tiny`), com latência cerca de seis vezes menor e erro bem maior. Duas ressalvas: a lista de palavras foi escrita a partir do domínio, e as frases de teste são do mesmo domínio, então o ganho medido é otimista para conversas sobre outros assuntos; e os tempos foram medidos com a CPU compartilhada, por isso são um limite superior.

## 4.2 LLM: 30 perguntas com resposta esperada

| Grupo | Conferência automática | Conferência manual |
|---|---|---|
| 20 diretas + 5 continuações: corretas | 72,0% | 68,0% (17 de 25) |
| só diretas | 70,0% | 65,0% (13 de 20) |
| só continuações (com histórico) | 80,0% | 80,0% (4 de 5) |
| 5 fora do escopo: recusas adequadas | 100,0% | 100,0% (5 de 5) |
| Abstenções indevidas (havia resposta nas fontes) | 2 | – |
| Latência média por pergunta | 21,5 s | – |

Conferência automática: a resposta é correta quando traz ao menos um dos termos esperados sem se abster; a recusa é adequada quando o assistente não responde ao tema e diz o que pode fazer. Conferência manual: cada resposta foi lida e comparada com a resposta esperada de `perguntas_llm.json` e com a fonte; só conta como correta a resposta completa e sem informação errada.

| # | Pergunta | Resposta esperada | Resposta obtida | Automática | Manual |
|--|-----|------|--------|---|---|
| D01 | como eu peço pra podar uma árvore na frente de casa | Pelo telefone 156, pelo Portal SP156 ou na praça de atendimento da subprefeitura, informa… | A Subprefeitura é responsável por avaliar, podar ou remover árvores nas calçadas, canteiros ou praças do bair… | incorreta/incompleta | incompleta (obs.) |
| D02 | quanto tempo a subprefeitura leva pra fazer a poda | A subprefeitura tem prazo máximo de 120 dias para atender o pedido de poda ou remoção. | O prazo máximo para a Subprefeitura Butantã atender a solicitação de poda ou remoção de árvore é 120 dias. Se… | correta | correta |
| D03 | eu mesmo posso cortar a árvore da calçada | Não. Podar ou cortar árvore em área pública sem autorização é crime ambiental; o pedido d… | Não, é crime ambiental realizar poda de árvores sem autorização prévia. Ligue para a Defesa Civil (156) ou Co… | correta | correta (obs.) |
| D04 | de quem é a obrigação de arrumar a calçada | Do proprietário ou responsável pelo imóvel em frente à calçada. À Prefeitura cabe o meio-… | A responsabilidade pela manutenção das calçadas é do proprietário ou responsável pelo imóvel localizado em fr… | correta | correta |
| D05 | qual a multa se a calçada estiver ruim | Multa por metro linear de calçada em má conservação. As duas páginas oficiais da base tra… | A multa para passeio em má conservação é de R$ 439,66 por metro linear. | correta | correta (obs.) |
| D06 | o semáforo da esquina tá quebrado quem eu chamo | A CET, que cuida de semáforo, placas e faixas. O pedido é feito pelo SP156. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (t… | abstenção indevida | abstenção indevida (obs.) |
| D07 | a tampa do bueiro afundou e tá escrito sabesp nela o q… | Se a tampa traz a inscrição Sabesp, esgoto, DAEE ou saneamento, o reparo é da empresa res… | Se na tampa do poço de visita, houver a inscrição 'Sabesp', o munícipe deve entrar em contato com a empresa r… | correta | correta |
| D08 | o que eu faço se a minha rua alagar | Ficar em local seguro e não atravessar ruas alagadas, porque a água pode arrastar a pesso… | 2. Feche portas e janelas; 3. Coloque o lixo em áreas não alagáveis; 4. Não jogue lixo ou entulho no córrego,… | correta | incorreta (obs.) |
| D09 | depois da enchente posso beber a água da torneira | Depois da inundação, beber apenas água filtrada ou fervida. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (t… | abstenção indevida | abstenção indevida (obs.) |
| D10 | tem um galho encostado no fio soltando faísca | Não se aproximar e acionar imediatamente a Enel pelos canais de emergência (em risco, 193… | Se houver risco agora, afaste-se do local e ligue 193 (Bombeiros) ou 199 (Defesa Civil). Não se aproxime e ac… | correta | correta |
| D11 | como eu registro um problema no zela | Na aba Relatar problema: descrever o problema, informar o CEP, conferir a sugestão da IA … | Para registrar um problema no Zela, vá até o Portal de Atendimento SP156 e faça login. Acesse a seção 'Meio A… | incorreta/incompleta | incorreta (obs.) |
| D12 | o zela guarda o meu cpf | Não. O Zela remove CPF, telefone, e-mail, placas e nomes do texto antes de enviar à IA e … | Não, o Zela não guarda seu CPF. | incorreta/incompleta | correta (obs.) |
| D13 | o prazo que aparece no zela é garantido | Não. Os prazos mostrados pelo Zela são referências, não prazos oficiais. | Os prazos mostrados pelo Zela são apenas referências e não são prazos oficiais. O prazo real depende do órgão… | correta | correta |
| D14 | tem água limpa vazando no meio da rua pra quem eu ligo | Para a Sabesp, que atende vazamentos de água e esgoto: 0800 055 0195 ou WhatsApp. | Se na tampa do poço de visita, houver a inscrição “PMSP” ou “águas pluviais”, o munícipe deve solicitar o niv… | correta | incorreta (obs.) |
| D15 | como eu sei quando passa o cata bagulho | A programação do Cata-Bagulho é consultada na página do LocatSP. | A programação do Cata Bagulho pode ser verificada através da página www.locatsp.com.br/busca-de-servicos/ | correta | correta |
| D16 | tem um carro abandonado na minha rua faz semanas o que… | O veículo recebe uma notificação; após cinco dias seguidos sem providência, fica caracter… | A notificação foi afixada e após cinco dias consecutivos sem providências, o veículo pode ser considerado aba… | correta | correta |
| D17 | posso pedir pra plantar uma árvore na calçada | Sim, mas só para passeio e áreas públicas. O pedido é analisado por um técnico e, se apro… | Não, você não pode plantar uma árvore na calçada. A manutenção das calçadas é responsabilidade do proprietári… | incorreta/incompleta | incorreta (obs.) |
| D18 | como eu peço o rebaixamento da guia da garagem | Na Praça de Atendimento da subprefeitura, com cópia de RG, CPF e capa do IPTU, preenchend… | O munícipe deverá se dirigir à Praça de Atendimento da Subprefeitura, munido de cópia de RG, CPF e capa de IP… | correta | correta |
| D19 | quanto da calçada tem que ficar livre pro pedestre | A faixa de circulação de pedestres deve ter no mínimo 50% da largura da calçada. | O padrão de calçadas deve ser de, no mínimo, 50% da largura total da calçada. | correta | correta |
| D20 | o que quer dizer quando meu relato está encaminhado | Encaminhada significa que o caso foi enviado ao órgão responsável. | O relato está sendo enviado para o órgão responsável. | correta | correta |
| C01 | e quanto tempo demora | (Depois de perguntar sobre a poda.) Até 120 dias para a subprefeitura atender. | Dependendo da situação da árvore, a poda ou remoção pode levar de 120 dias até que o serviço seja realizado. | correta | correta (obs.) |
| C02 | e se o dono não arrumar | (Depois de perguntar sobre a calçada.) O responsável é notificado e, se não regularizar n… | A manutenção da calçada é responsabilidade do proprietário ou possuidor do imóvel. | incorreta/incompleta | incompleta (obs.) |
| C03 | e depois que a água baixar | (Depois de perguntar sobre alagamento.) Beber só água filtrada ou fervida, não usar alime… | Lave e desinfete os objetos atingidos pela enchente usando uma mistura de um copo de água sanitária para cada… | correta | correta (obs.) |
| C04 | e se tiver escrito sabesp | (Depois de perguntar sobre a tampa afundada.) Nesse caso o reparo é da Sabesp, e é ela qu… | Se na tampa do poço de visita houver a inscrição 'Sabesp', o munícipe deve entrar em contato com a empresa re… | correta | correta |
| C05 | e se o galho estiver encostando nos fios | (Depois de perguntar sobre a árvore.) Não se aproximar e acionar a Enel, a distribuidora … | Não se aproxime. Acione imediatamente a Enel Distribuição São Paulo pelos canais de emergência da empresa. | correta | correta |
| F01 | me indica uma pizzaria boa na mooca | Recusa: o assistente diz que o assunto está fora do que ele orienta e lembra os temas que… | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação),… | recusa adequada | recusa adequada |
| F02 | qual remédio é bom pra gripe | Recusa com orientação: não indica remédio e recomenda procurar um profissional de saúde (… | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação),… | recusa adequada | recusa adequada (obs.) |
| F03 | quem vai ganhar o jogo do corinthians no domingo | Recusa: o assunto está fora do escopo. | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação),… | recusa adequada | recusa adequada |
| F04 | me ajuda a declarar meu imposto de renda | Recusa com orientação: não trata de imposto e recomenda procurar um profissional da área. | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação),… | recusa adequada | recusa adequada |
| F05 | conta uma piada | Recusa: o assistente não conta piadas e lembra os temas que atende. | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação),… | recusa adequada | recusa adequada |

**Observações da conferência manual:**

- **D01** (incompleta): explica a vistoria do engenheiro agrônomo, mas não diz onde fazer o pedido (156, portal SP156 ou praça de atendimento).
- **D03** (correta): a fonte chama o 156 de Defesa Civil; o número nacional da Defesa Civil é 199.
- **D05** (correta): cita uma das duas páginas oficiais, que trazem valores diferentes.
- **D06** (abstenção indevida): a busca pôs o item da CET em 1º lugar, mas a pergunta coloquial ficou abaixo dos dois limiares da porta (BM25 3,3; cosseno 0,33).
- **D08** (incorreta): lista os cuidados de antes da chuva (fechar janelas, limpar calhas): a busca trouxe essa lista, e não a de durante a inundação; só a última frase, com 193 e 199, serve a quem já está com a rua alagada.
- **D09** (abstenção indevida): o trecho certo (beber só água filtrada ou fervida) foi o 1º recuperado; a conferência por frase barrou a resposta do modelo.
- **D11** (incorreta): descreve o pedido de poda no portal SP156, e não o registro no Zela; o guia do Zela foi recuperado em 1º lugar.
- **D12** (correta): curta; não diz que o CPF é removido antes da análise.
- **D14** (incorreta): fala de tampa de poço de visita; não dá o telefone da Sabesp, que está no guia do Zela recuperado.
- **D17** (incorreta): inverte a fonte: as perguntas frequentes dizem que o plantio pode ser pedido para passeio e áreas públicas.
- **C01** (correta): frase mal construída ('pode levar de 120 dias'); o prazo da fonte é de até 120 dias.
- **C02** (incompleta): repete quem é o responsável e não fala da notificação nem da multa.
- **C03** (correta): traz um dos cuidados de depois da enchente (lavar e desinfetar).
- **F02** (recusa adequada): não indica remédio e lembra o 192.

Verificações acionadas: `abstencao_por_recuperacao_fraca` em 1; `citacao_completada` em 2; `fora_do_escopo_detectado` em 5; `frases_sem_apoio_removidas` em 3; `sustentacao_insuficiente` em 1.

**Leitura dos erros.** A conferência manual é mais rigorosa que a automática (68% contra 72% nas 25 perguntas com resposta nas fontes), porque a automática aceita qualquer resposta que contenha uma palavra esperada: D08 e D14 passaram nela com o número 193 e com a palavra Sabesp, mas respondem outra coisa. Os 8 casos abaixo do esperado têm quatro causas. (1) O modelo usa o trecho errado entre os recuperados (D11 e D14), embora o certo estivesse entre os 4 entregues, em D11 em 1º lugar. (2) O modelo inverte o sentido da fonte (D17, "não pode plantar" quando a fonte diz que pode); a conferência por frase é lexical e aceita a frase porque as palavras estão na fonte. (3) A busca não traz o trecho certo (D08, que recebeu a lista de antes da chuva, e D01, que não recebeu o trecho com o canal de pedido) ou traz e a resposta sai parcial (C02). (4) As proteções barram uma resposta que estava disponível (D06 na porta de recuperação, D09 na conferência por frase); nesses casos o cidadão recebe a indicação do 156, e não uma informação errada. As recusas fora do escopo ficaram em 5 de 5, todas pela regra fixa, sem depender do modelo. **O que isso indica.** Com o modelo de 1,5 bilhão de parâmetros em CPU, a parte que mais falha é a escolha do trecho e a leitura do sentido: o trecho certo foi recuperado em 23 das 25 perguntas, e o modelo errou ou omitiu em 4 delas. Um modelo maior ou um reranqueador atacam as causas 1 e 2; mais perguntas coloquiais na calibração da porta e na avaliação da busca atacam as causas 3 e 4.

## 4.3 TTS

| Voz | Síntese média por resposta | Fator de tempo real |
|---|---|---|
| faber | 0,61 s | 0,083 |
| cadu | 0,63 s | 0,080 |

| Voz | Avaliadores | Naturalidade (1 a 5) | Clareza (1 a 5) |
|---|---|---|---|
| faber | 3 | 5,00 | 5,00 |

As 3 pessoas ouviram as 10 respostas na voz `faber`, a que o assistente usa, e deram nota máxima nas 60 notas. O resultado indica que a voz foi bem aceita, mas tem limites: com todas as notas no teto, a escala não mostra diferença entre as respostas (nem as mais longas, com números e telefones, perderam ponto); a avaliação não foi cega e teve só 3 pessoas, então notas unânimes podem incluir cortesia. Uma avaliação maior, com o público da persona e comparando vozes, daria um resultado mais informativo. A voz `cadu` não foi avaliada, e o padrão continua `faber`.

## 4.4 Ponta a ponta: 10 conversas de 3 turnos

As perguntas foram faladas pela voz sintética `cadu`, diferente da voz do assistente, para o teste ser reproduzível. Latência por etapa, em segundos:

| Etapa | Média | Mediana | p90 | Máximo |
|---|---|---|---|---|
| STT | 1,84 | 1,75 | 2,14 | 2,44 |
| Assistente (busca + LLM) | 22,92 | 25,42 | 34,53 | 41,58 |
| Adaptação para fala | 0,00 | 0,00 | 0,00 | 0,00 |
| TTS | 1,26 | 1,36 | 1,62 | 1,91 |
| **Total até começar a falar** | 26,02 | 28,59 | 38,04 | 44,09 |

Turnos adequados pela conferência automática: **53,3%** de 30; pela conferência manual, **53,3%** (16 de 30).

| Turno | Transcrição da pergunta | Resposta (texto) | Automática | Manual |
|---|--------|-----------------|--|---|
| C1T1 | Como eu peço a poda de uma árvore na calçada? | O munícipe poderá solicitar a vistoria de um técnico da Prefeitura de São Paulo através do telefone 156, na Praça de At… | sim | correta |
| C1T2 | E quanto tempo demora? | O munícipe poderá solicitar a vistoria de um técnico da Prefeitura de São Paulo através do telefone 156, na Praça de At… | sim | correta (obs.) |
| C1T3 | E se não fizerem nesse prazo. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C2T1 | Dicaem a responsabilidade de consertar a calçada. | A responsabilidade de consertar a calçada é do proprietário ou responsável pelo imóvel localizado em frente à calçada. … | sim | correta (obs.) |
| C2T2 | Isso eu dou na não arrumar. | A responsabilidade de consertar a calçada é do proprietário ou responsável pelo imóvel localizado em frente à calçada. … | não | incompleta (obs.) |
| C2T3 | Qual o valor da multa? | A multa para a falta de manutenção das calçadas pode variar, mas é geralmente de R$ 439,66 por metro linear. A Prefeitu… | sim | correta (obs.) |
| C3T1 | O que eu faço se a minha rua lagar? | 2. Se possível, vá com sua família para um lugar seguro; 3. Procure o melhor itinerário para escapar das áreas alagadas… | não | incompleta (obs.) |
| C3T2 | E depois que a água baixar. | 1. Lave e desinfete os objetos atingidos pela enchente usando uma mistura de um copo de água sanitária para cada balde … | sim | correta (obs.) |
| C3T3 | Posso beber a água da torneira. | Não, não é recomendado beber água da torneira durante uma enchente. Use apenas água filtrada ou fervida para prevenir d… | sim | correta |
| C4T1 | Tenho um fio caído soltando faísca na calçada. | Se houver risco agora, afaste-se do local e ligue 193 (Bombeiros) ou 199 (Defesa Civil). Ligue para a Enel Distribuição… | sim | correta (obs.) |
| C4T2 | Para qual número ligo? | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C4T3 | E o zela resolve sozinho. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C5T1 | Tem água limpa vazando no meio da rua. | Se a água estiver vazando no meio da rua, você deve evitar o contato direto com ela. Lave e desinfete os objetos atingi… | não | incorreta (obs.) |
| C5T2 | Qual é o telefone deles? | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C5T3 | Eles atendem pelo WhatsApp. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C6T1 | O semáforo da esquina está quebrado. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C6T2 | Como eu faço o pedido? | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C6T3 | Minde com o restaurante aqui perto. | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação), segurança… | sim | recusa adequada (obs.) |
| C7T1 | Como eu registro um problema no Zela? | Para registrar um problema no Zela, siga essas etapas: 1. Na aba 'Relatar problema', descreva o problema com suas palav… | sim | correta |
| C7T2 | O Zela guarda meu CPF. | O Zela remove CPF, telefone, e-mail, placas de veículos e nomes declarados do texto antes de enviá-lo à inteligência ar… | sim | correta |
| C7T3 | E o prazo que aparece é garantido. | O prazo mostrado pelo Zela é apenas uma referência e não é garantido. O prazo real depende do órgão responsável. | sim | correta |
| C8T1 | A tampa do boeiro fundou na minha rua. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C8T2 | Está escrito PMSP Nela. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C8T3 | E se fosse Sabesp? | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C9T1 | Qual remédia bom para dor de cabeça? | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação), segurança… | sim | recusa adequada |
| C9T2 | E sobreburaco na rua como eu faço. | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | não | abstenção indevida (obs.) |
| C9T3 | E quanto tempo demora para tapar? | Não encontrei essa informação nas fontes do Zela. Para ter certeza, consulte o canal oficial da Prefeitura (telefone 15… | sim | abstenção adequada (obs.) |
| C10T1 | Tenho um carro abandonado na minha rua. | A denúncia deve ser afixada com uma notificação inicial. Após cinco dias, sem providências, é caracterizado abandono e … | sim | correta |
| C10T2 | Depois de quantos dias ele é removido. | Depois de cinco dias consecutivos da data da notificação, sem providências por parte do proprietário ou responsável pel… | sim | correta |
| C10T3 | Conta uma piada. | Posso ajudar com problemas de zeladoria urbana (buracos, iluminação, árvores, calçadas, alagamentos, fiação), segurança… | sim | recusa adequada |

**Observações da conferência manual:**

- **C1T2** (correta): repete o canal e acrescenta o prazo de 120 dias.
- **C1T3** (abstenção indevida): a fonte traz a reclamação na ouvidoria pelo 156; o trecho não ficou entre os 4 recuperados.
- **C2T1** (correta): a transcrição errou o início ('Dicaem'), mas o assunto foi entendido.
- **C2T2** (incompleta): a transcrição saiu truncada ('Isso eu dou na não arrumar'); a resposta repete o turno anterior e não fala da notificação nem da multa.
- **C2T3** (correta): junta o valor de uma página (R$ 439,66) com o prazo de outra (30 dias); as duas páginas oficiais divergem, e o 'geralmente' é do modelo.
- **C3T1** (incompleta): diz para ir a um lugar seguro, mas não diz para não atravessar a água; a transcrição 'lagar' não acionou a orientação de emergência.
- **C3T2** (correta): traz um dos cuidados de depois da enchente.
- **C4T1** (correta): a última frase, sobre os órgãos que cuidam das calçadas, não ajuda, mas não atrapalha a orientação principal.
- **C4T2** (abstenção indevida): a resposta (193 e o canal de emergência da Enel) estava no turno anterior e no guia do Zela.
- **C4T3** (abstenção indevida): o guia do Zela diz que o relato não substitui os serviços de emergência; o próprio modelo escreveu que não havia informação.
- **C5T1** (incorreta): responde com cuidados de enchente; um vazamento de água limpa é com a Sabesp, que está no guia do Zela.
- **C5T2** (abstenção indevida): o telefone da Sabesp está no guia do Zela, que não foi recuperado.
- **C5T3** (abstenção indevida): o WhatsApp da Sabesp está no mesmo trecho do guia.
- **C6T1** (abstenção indevida): porta de recuperação: o item da CET foi recuperado, mas a pergunta curta ficou abaixo dos limiares.
- **C6T2** (abstenção indevida): mesma causa do turno anterior.
- **C6T3** (recusa adequada): a transcrição errou ('Minde com o restaurante'), e a recusa veio pela palavra restaurante.
- **C8T1** (abstenção indevida): a transcrição 'boeiro' levou a busca para páginas de calçada; na reprodução, o modelo atribuiu a tampa ao dono do imóvel.
- **C8T2** (abstenção indevida): o item do poço de visita com PMSP responde; o modelo escreveu que não havia informação.
- **C8T3** (abstenção indevida): o mesmo item responde o caso da Sabesp.
- **C9T2** (abstenção indevida): o guia do Zela explica como relatar um buraco.
- **C9T3** (abstenção adequada): as fontes não trazem prazo para tapar buraco.

**Leitura dos turnos.** Dos 30 turnos, 16 foram adequados na conferência manual, os mesmos 16 da automática: os três pedidos fora do escopo foram recusados (inclusive o que a transcrição estragou, 'Minde com o restaurante'), e as conversas sobre o próprio Zela e sobre o carro abandonado funcionaram inteiras. A falha dominante não é resposta errada: 11 dos 14 turnos ruins terminaram em "não encontrei, ligue 156" quando as fontes tinham a resposta. **De onde vêm as abstenções.** A reprodução de quatro desses turnos e da pergunta D09 (`reproducao_abstencoes.txt`) mostra que o problema começa na busca. Depois de 'boeiro' (erro de transcrição), de 'fio caído soltando faísca na calçada' e de 'qual é o telefone deles', os 4 trechos recuperados não trazem a resposta. Sem a fonte certa, o modelo escreve algo com as palavras que tem: que a tampa é responsabilidade do dono do imóvel, que a subprefeitura pode leiloar o bem, um telefone de subprefeitura no lugar do da Sabesp. Na execução avaliada, a conferência ou o próprio modelo transformaram esses turnos em abstenção; na reprodução, duas dessas respostas erradas passariam pela conferência, porque as palavras e o número estão em alguma das fontes. A abstenção protegeu o cidadão nesses turnos, mas não é garantida: a conferência é lexical, e a saída do modelo muda entre execuções. A porta de recuperação respondeu por outras duas abstenções (o semáforo), com perguntas curtas e coloquiais abaixo dos limiares. **O que melhoraria.** Corrigir termos do domínio depois da transcrição ('boeiro' para 'bueiro'); recuperar mais trechos nas continuações e dar mais peso ao assunto da conversa; calibrar a porta com perguntas faladas; e trocar o modelo de 1,5 bilhão de parâmetros por um maior, que erra menos quando a fonte não traz a resposta. **Latência.** A mediana até começar a falar foi de 28,6 s, quase toda do modelo de linguagem em CPU; transcrição e síntese somam cerca de 3 s.

O tempo é dominado pelo LLM em CPU. Turnos que terminam em abstenção ou recusa respondem em poucos segundos, porque não chamam o modelo. Com um LLM hospedado (Groq ou Gemini, já suportados pela API), a etapa cai para poucos segundos, ao custo de enviar o texto da pergunta, já sem dados pessoais, a um provedor externo.

# 5. Ética, LGPD e segurança

- **Consentimento antes do primeiro uso.** A primeira tela explica que a voz será gravada e processada e só libera o microfone depois do aceite.
- **Retenção mínima.** O áudio existe em arquivo temporário apenas durante a transcrição e é apagado em seguida. O histórico guarda texto, sem CPF e e-mail, e some ao fechar a página. Nada é gravado em banco.
- **Processamento local da voz.** A gravação não vai para nenhuma API externa. Se o LLM for hospedado, só o texto da pergunta sai da máquina, e isso deve constar do aviso de consentimento.
- **Limites do assistente.** Pedidos fora do tema recebem recusa; em saúde, questões jurídicas e financeiras, a recusa indica procurar um profissional; em risco à vida, a resposta manda ligar 193 ou 199.
- **Alucinação.** Quando as fontes não têm a resposta, o assistente diz que não encontrou e indica o 156. Frases que as fontes não sustentam são retiradas antes de a resposta ser falada.
- **Clonagem de voz.** É proibido clonar a voz de uma pessoa real sem consentimento expresso e documentado. O projeto usa somente vozes sintéticas prontas do Piper; nenhuma voz real foi clonada.
- **Transparência.** A tela mostra a transcrição, o texto da resposta, as fontes e a latência de cada etapa.

## 5.1 Análise de viés do STT

Um reconhecedor de fala não erra igual para todo mundo. Estudos com sistemas comerciais mediram quase o dobro de erro para grupos pouco representados nos dados de treino (KOENECKE et al., 2020), e o Whisper declara, em sua documentação, desempenho desigual entre sotaques e idiomas. Para o Zela isso importa porque a persona, uma senhora de 67 anos, pertence a grupos que esses modelos costumam atender pior: voz feminina idosa e fala informal.

**O que os dados disponíveis mostram.** Mesmo entre três vozes sintéticas parecidas, o WER da opção adotada vai de 4,8% (cadu) a 18,6% (edresson): o erro depende de quem fala. **O que eles não mostram.** As três vozes são masculinas, adultas e de leitura pausada. Não há voz feminina, idosa, com sotaque de outras regiões nem fala espontânea, então este teste não permite afirmar que o sistema trata esses grupos de forma equivalente.

**Gravações reais por grupo** (colunas `genero` e `faixa_etaria` do manifesto; sotaque não informado):

| Gênero | Áudios | tiny | small | small + vocabulário do domínio |
|---|---|---|---|---|
| feminino | 7 | 32,4% | 14,7% | 14,7% |
| masculino | 13 | 25,6% | 8,5% | 6,2% |

| Faixa etária | Áudios | tiny | small | small + vocabulário do domínio |
|---|---|---|---|---|
| 18-29 | 7 | 22,9% | 8,6% | 2,9% |
| 40-49 | 7 | 32,4% | 14,7% | 14,7% |
| 50-59 | 6 | 28,8% | 8,5% | 10,2% |

**O que as gravações reais mostram.** Com a opção adotada, o erro foi de 2,9% na voz do homem de 22 anos, 10,2% na do homem de 55 e 14,7% na da mulher de 48: a voz feminina teve o maior erro, como a literatura aponta. **O que elas não permitem afirmar.** Há uma pessoa por grupo, e a voz feminina também foi a gravada mais baixa, então não dá para separar o efeito do gênero, da idade, da pessoa e do volume da gravação. Ninguém tinha mais de 60 anos nem sotaque de outra região, que é o perfil da persona; antes de um uso real, o teste precisa ser repetido com esse público e com fala espontânea, não lida.

**Como o projeto reduz o dano de um erro de transcrição.** A transcrição aparece na tela antes da resposta, para a pessoa ver o que foi entendido e repetir; a pergunta também pode ser enviada como arquivo; o vocabulário do domínio reduz erros em nomes de órgãos; e o assistente não executa nenhuma ação a partir da voz, apenas orienta, então um erro de transcrição gera uma resposta inadequada, não um registro indevido.

# 6. Limitações

- O STT foi medido com 20 frases lidas por 3 pessoas (nenhuma com mais de 60 anos nem com sotaque de outra região) e gravadas perto do celular; fala espontânea, distância e ruído real devem aumentar o erro. O teste de ponta a ponta usou perguntas faladas por voz sintética.
- O LLM local de 1,5 bilhão de parâmetros deixa a resposta lenta em CPU e às vezes mistura informações de fontes vizinhas ou omite parte da resposta esperada.
- A base tem 7 documentos da cidade de São Paulo. Duas páginas oficiais divergem entre si (prazo e multa de calçada), e o assistente responde com o trecho que a busca trouxe, sem reconciliar as duas.
- Apertar para falar exige um toque; para pessoas com mobilidade reduzida, uma palavra de ativação seria melhor, mas aumentaria o risco de gravar sem querer.
- A adaptação para fala cobre os padrões mais comuns (valores, datas, telefones, siglas do domínio); siglas novas precisam entrar na tabela.

# 7. Melhorias futuras

- Repetir o teste de STT com o público da persona: pessoas com mais de 60 anos, mais vozes femininas, sotaques de outras regiões e fala espontânea, em vez de frases lidas.
- Trocar o gerador por um modelo maior (local com GPU ou hospedado) e repetir as 30 perguntas para medir o ganho.
- Responder em fluxo: começar a falar a primeira frase enquanto o modelo ainda escreve o restante, para reduzir o tempo até o início da fala.
- Confirmar em voz alta o que foi entendido quando a confiança da transcrição for baixa ("você perguntou sobre poda de árvore?").
- Permitir registrar o relato por voz, com leitura do resumo e confirmação falada antes de enviar.
- Ampliar a base para outras cidades e marcar a data de validade de cada documento.

# 8. Ferramenta de construção de corpus

O enunciado geral pede uma ferramenta que receba vários tipos de documento e texto, faça a limpeza e a normalização e crie três corpora (conversacional, perguntas e respostas e texto puro) para o ajuste fino de um LLM de pequeno porte. A ferramenta fica em `corpus_pln/`, com interface em Streamlit (`streamlit run app.py`) e linha de comando (`python construir.py`), e tem 13 testes automatizados. No Zela, ela prepara o material para ajustar o modelo pequeno do assistente (Qwen2.5-1.5B) ao vocabulário e ao tom do serviço, com as mesmas páginas oficiais da base e sem dados pessoais; o RAG continua necessário para citar fontes e datas.

## 8.1 Fluxo e decisões

| Etapa | O que faz | Por quê |
|------------|----------------------------------------|----------------------------|
| Leitura | PDF, DOCX, HTML, TXT, MD, CSV, JSON, JSONL e texto colado; títulos viram marcação de seção; colunas de pergunta e resposta viram pares prontos | cada formato chega ao mesmo texto estruturado |
| Normalização | forma Unicode NFC, aspas e traços simples, sem caracteres invisíveis | a mesma palavra escrita de dois jeitos vira dois tokens |
| Limpeza | cabeçalho, rodapé e número de página repetidos no PDF; menus de página web; palavras hifenizadas e linhas quebradas; parágrafos repetidos entre documentos; parágrafos curtos | ruído repetido ensina o modelo a repeti-lo; repetição vaza entre treino e validação |
| Dados pessoais | CPF, e-mail pessoal, celular, RG e placa trocados por marcadores; telefones públicos ficam | LGPD: um modelo ajustado pode repetir o que viu no treino |
| Três corpora | texto puro em trechos de até 1.200 caracteres; pares de pergunta e resposta; conversas de até 3 turnos e recusas fora do escopo | um formato por tipo de ajuste: adaptação ao domínio, instrução e chat |
| Exportação | JSONL nos formatos `text`, `instruction/input/output` e `messages`; treino e validação por documento; rastreabilidade de cada linha; ficha do corpus; conferência final de formato e de dados pessoais | formatos lidos direto pelas bibliotecas de fine-tuning; validação sem texto visto no treino |

## 8.2 Resultado com os documentos de exemplo

10 documentos em 6 formatos: 5 páginas oficiais da Prefeitura de São Paulo (as mesmas da base do assistente) e 5 arquivos sintéticos escritos para testar a limpeza, com cabeçalho e rodapé de PDF, hifenização, menu de página web, parágrafos repetidos e dados pessoais inventados.

| Documento | Formato | Caracteres antes | Depois | Redução | Dados pessoais mascarados |
|----------------------|---------|-----------|-------|---------|-----------------|
| calcadas-fiscalizacao.md | .md | 1859 | 1803 | 3,0% | nenhum |
| cartilha_chuvas_sintetica.pdf | .pdf | 2252 | 1725 | 23,4% | nenhum |
| dc-chuvas-excessivas.md | .md | 4271 | 4242 | 0,7% | nenhum |
| faq-subprefeitura.md | .md | 5342 | 5298 | 0,8% | nenhum |
| pagina_iluminacao_sintetica.html | .html | 691 | 593 | 14,2% | nenhum |
| perguntas_sobre_o_zela.csv | .csv | 6 pares prontos | 6 pares | — | nenhum |
| poda-butanta.md | .md | 2723 | 2712 | 0,4% | nenhum |
| procedimento_poda_sintetico.docx | .docx | 898 | 832 | 7,3% | e-mail 1, celular 1 |
| relatos_sinteticos.jsonl | .jsonl | 481 | 321 | 33,3% | e-mail 1, CPF 2, celular 2, placa 1 |
| zela-guia-do-servico.md | .md | 2871 | 2786 | 3,0% | nenhum |

A limpeza tirou 9 linhas de cabeçalho e rodapé, 3 linhas de menu, uniu 5 palavras hifenizadas e 54 linhas quebradas, removeu 2 parágrafos repetidos e mascarou 8 dados pessoais.

| Corpus | Exemplos | Treino | Validação | Tokens (aprox.) | De onde vieram |
|----------------|-----------|--------|-----------|---------|-----------------------|
| Texto puro | 33 | 28 | 5 | 5090 | texto limpo: 33 |
| Perguntas e respostas | 38 | 31 | 7 | 3966 | montada a partir do título: 11; colunas de pergunta e resposta: 6; pergunta escrita no documento: 15; título em forma de pergunta: 6 |
| Conversacional | 21 | 19 | 2 | 4169 | pares do mesmo documento: 16; recusa fora do escopo: 5 |

A estimativa de tokens usa 4 caracteres por token; o número real depende do tokenizador do modelo. Uma linha de cada corpus, como ela vai para o arquivo de treino (texto cortado):

**Texto puro** (`cartilha_chuvas_sintetica.pdf`, origem: texto limpo):

```json
{"text": "Preparação para o período de chuvas\nEsta cartilha de exemplo reúne orientações gerais para moradores de áreas sujeitas a alagamento. Ela foi escrita para testar a ferramenta de construção de corpus e não substitui as orientações oficiais da Defesa Civil.\nAntes da temporada de chuvas, limpe calhas e ralos, guarde documentos em local alto e combine com a família um ponto de encontro. Anote os telefones d...
```

**Perguntas e respostas** (`pagina_iluminacao_sintetica.html`, origem: pergunta escrita no documento):

```json
{"instruction": "O que não é iluminação pública?", "input": "", "output": "Fio partido, falta de energia em casa e transformador com defeito são atendidos pela distribuidora de energia, e não pela prefeitura. Fio caído é emergência: afaste-se e ligue 193."}
```

**Conversacional** (`cartilha_chuvas_sintetica.pdf`, origem: pares do mesmo documento):

```json
{"messages": [{"role": "system", "content": "Você é um assistente que orienta cidadã…"}, {"role": "user", "content": "O que o documento \"cartilha chuvas sintetica\" informa sobre \"Preparação para o período de chuvas\"?"}, {"role": "assistant", "content": "Esta cartilha de exemplo reúne orientações gerais para moradores de áreas sujeitas a alagamento. Ela foi escrita para testar a ferramenta de construção de corp...
```

## 8.3 Limitações da ferramenta

- PDF digitalizado (imagem) não é lido: a ferramenta avisa e segue com os outros arquivos; seria preciso OCR.
- O mascaramento usa regras: nomes de pessoas não são reconhecidos (no DOCX de exemplo, um nome fictício continua no texto). Por isso a ficha do corpus pede a leitura de uma amostra antes do uso.
- Perguntas montadas a partir de títulos são genéricas e ficam marcadas para revisão; perguntas geradas por LLM (opcional) passam só por conferência de regra.
- O corpus foi preparado, mas o ajuste fino não foi executado nesta entrega: medir o ganho do modelo ajustado nas 30 perguntas da seção 4.2 é o próximo passo.


# 9. Vídeo (até 5 minutos)

Roteiro: (1) tela de consentimento; (2) pergunta falada sobre poda de árvore; (3) continuação "e quanto tempo demora?", que mostra a memória; (4) terceiro turno sobre calçada; (5) pedido fora do escopo e a recusa; (6) latência por etapa na tela e as tabelas da seção 4; (7) cerca de 1 minuto da ferramenta de corpus: envio de documentos de formatos diferentes, o antes e depois da limpeza e os três corpora gerados.

# Referência

KOENECKE, A. et al. Racial disparities in automated speech recognition. **Proceedings of the National Academy of Sciences**, v. 117, n. 14, p. 7684-7689, 2020.

