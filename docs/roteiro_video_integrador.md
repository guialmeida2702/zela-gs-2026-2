# Roteiro do vídeo integrador (Governança em IA & BA) · 6 min 30 s

Regras do enunciado: de 5 a 7 minutos, publicado no YouTube como **Não listado**, sem leitura extensa de documento. Mostre o sistema funcionando e fale com as próprias palavras; os textos abaixo são apoio, não para ler.

Antes de gravar: API com o LLM rodando, front aberto (perfil Cidadão), robô com dados de teste gerados, assistente de voz aberto em outra aba, captura do iSPD e PDF do documento à mão. Use uma foto de muro rachado e uma de calçada sem fissura.

| Tempo | Tela | O que mostrar e dizer |
|---|---|---|
| 0:00–0:35 | Painel da cidade | O problema: relatos de zeladoria chegam sem informação e sem prioridade; em São Paulo são cerca de 157 mil solicitações por mês no SP156. O Zela ajuda o cidadão a relatar e a prefeitura a priorizar, sempre com uma pessoa decidindo. |
| 0:35–1:50 | Relatar problema | Relato com foto de muro rachado. Mostrar as etapas na tela de espera, a revisão com as áreas marcadas na foto, o aviso de que a foto não mede gravidade e a confirmação pelo cidadão (corrigir a urgência, por exemplo). Protocolo gerado. **Front End + Visão Computacional.** |
| 1:50–2:40 | Tire dúvidas | Pergunta respondível com as fontes abertas; continuação ("e quanto tempo demora?"); pergunta sem resposta e a abstenção. Citar o número da avaliação (tabela do relatório). **Generative AI.** |
| 2:40–3:30 | Assistente de voz e ferramenta de corpus | Tela de consentimento; uma pergunta falada, a resposta em voz com a transcrição e a latência por etapa; um pedido fora do escopo e a recusa. Em 10 segundos, a ferramenta de corpus: envio de um PDF, o antes e depois da limpeza e os três corpora gerados. **NLP.** |
| 3:30–4:20 | Terminal + e-mail .eml + Gestor | Rodar `python robo.py --chuva-teste-mm 45`: log com as etapas, a planilha corrompida indo para revisão, casos de drenagem priorizados. Abrir a fila do gestor mostrando a nota "[robô]" e a aba Monitoramento por imagens. **RPA.** |
| 4:20–4:55 | Capturas do iSPD | 2 x 4 workers: 3.602 s x 1.801 s, ganho de 2; e o cenário em que mais máquinas não ajudam (rede saturada). **Cluster.** |
| 4:55–5:20 | Celular com o OuviAí | Campainha e batida reconhecidas ao vivo; resultado das 15 tentativas. Evolução: alerta de sirene. **IoT.** |
| 5:20–5:40 | Tabela do roteiro quântico | O gargalo real é despachar equipes; otimização quântica só entra se vencer o clássico; PQC desde já. **Quântica.** |
| 5:40–6:30 | Documento: quadros de inventário, riscos e integração | Governança: onde a IA sugere e quem decide; riscos e mitigações com evidência; LGPD (dados removidos antes do modelo, foto e áudio não guardados); indicadores; o que foi e o que não foi integrado, e por quê. Encerrar com o próximo passo do projeto. |

Dicas: grave a tela em 1080p, com o zoom do navegador em 110%; mantenha cada fala curta; se o LLM local demorar, corte a espera na edição e diga quanto tempo levou.
