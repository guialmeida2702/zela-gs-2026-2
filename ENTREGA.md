# Checklist de entrega · Global Solution 2026.2

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

Prazo de cada disciplina: **19/11/2026, 23h55**, no Portal do Aluno. O GitHub precisa estar com tudo **antes** da
entrega: em Governança, commit depois do prazo pode tirar nota.

Legenda: ✅ pronto no repositório · 🧑 só o autor consegue fazer (gravação, teste com pessoas, vídeo, envio)

A conferência item a item de cada enunciado está em [`docs/conformidade.md`](docs/conformidade.md).

## Para todas as disciplinas

- 🧑 Criar o repositório público no GitHub, subir tudo e colar o link no README (tabela do topo) e no tópico
  "Links" do documento ABNT.
- 🧑 Conferir no portal se algum enunciado mudou desde 12/11/2026.
- ✅ **PLN:** o professor confirmou (16/11) que a disciplina exige as duas entregas, o assistente de voz completo
  (`assistente_voz/`) e a ferramenta de corpus (`corpus_pln/`). O relatório de PLN cobre as duas, e o vídeo deve
  mostrar as duas.

## Por disciplina

| Disciplina | Pronto no repositório | Falta fazer (só o autor) |
|---|---|---|
| **Front End & Mobile** | ✅ código nas camadas exigidas, 132 testes (90 da API e 42 da interface), Docker Compose testado, avaliação da IA com ajuste de prompt, README completo | ✅ teste com 3 pessoas feito em 19/11 e ajuste publicado (`docs/validacao_usuarios.md`, README 8.5 a); 🧑 vídeo de até 5 min (`docs/roteiro_video.md`); 🧑 deploy público (opcional) |
| **Visão Computacional** | ✅ pipeline, modelo, métricas, análise de erros, latência e FPS, integração no protótipo, relatório em PDF | 🧑 vídeo de demonstração (roteiro no fim do relatório) |
| **Generative AI** | ✅ assistente com RAG integrado, corpus com URLs e datas, avaliação por componente e ponta a ponta, testes adversariais, relatório em PDF | 🧑 vídeo de até 5 min (roteiro no fim do relatório) |
| **NLP (assistente de voz)** | ✅ código modular, README com modelos e licenças, 30 perguntas com resposta esperada, 10 conversas com latência por etapa, comparação de três opções de STT, 20 gravações reais de 3 pessoas avaliadas (WER 9,1% com a opção adotada) e análise de viés, notas do TTS de 3 pessoas (5,00 de naturalidade e de clareza), planilha de avaliação, relatório em PDF | 🧑 vídeo com conversa real de 3 turnos, continuação e recusa |
| **NLP (ferramenta de corpus)** | ✅ interface e linha de comando, 9 formatos de entrada, limpeza com relatório, três corpora em JSONL com treino e validação, rastreabilidade e ficha do corpus, 13 testes, seção 8 do relatório de PLN | 🧑 cerca de 1 minuto no vídeo de PLN: envio de documentos, a limpeza e os corpora gerados |
| **AI for RPA** | ✅ robô com 6 temas, quadro de temas, validação medida, casos de falha, evidências | 🧑 (opcional) configurar SMTP com senha de app para envio real do boletim |
| **Cluster Computing** | ✅ modelos do iSPD, simulações, capturas da interface, relatório de 4 páginas | 🧑 (opcional) abrir os modelos no iSPD para conferir |
| **Computação Quântica** | ✅ documento (gargalo, capacidade, roteiro, ética, LGPD e ODS) | nada |
| **Cognitive IoT (OuviAí)** | ✅ 60 gravações conferidas (15/5 por classe), impulse MFE + CNN treinado no Edge Impulse (validação 90,1%), Classify all nos 15 arquivos de Test (76,1% por janela, 12 de 15 arquivos), cinco capturas, planilha e relatório preenchidos e teste ao vivo (10 de 15, 5 falsos positivos em ambiente) registrado na seção 6 | nada (vídeo do teste ao vivo na seção 6; ambiente_06 tem uma batida, documentado como limitação) |
| **Governança & BA** | ✅ documento ABNT (`docs/governanca/`), roteiro do vídeo integrador | 🧑 **escrever a Conclusão sem IA** (regra do enunciado), com até cerca de 20 linhas para o documento continuar em 15 páginas; preencher os links; 🧑 vídeo de 5 a 7 min no YouTube (não listado) |

## Como regerar os documentos

```bash
python backend/scripts/relatorio_assistente.py          # relatório do assistente (GenAI)
python assistente_voz/avaliacao/gerar_planilha.py       # planilha de avaliação do assistente de voz
(cd corpus_pln && python construir.py --entrada exemplos --saida saida \
   --escopo "zeladoria urbana, segurança em chuvas e uso do Zela" --registrar)   # corpora de exemplo e corpus_pln/resultados/
python assistente_voz/avaliacao/gerar_relatorio.py      # relatório de PLN (assistente de voz e ferramenta de corpus)
bash docs/relatorios/gerar_pdfs.sh                      # PDFs de todos os relatórios
python docs/governanca/gerar_documento.py               # documento ABNT (DOCX + PDF), lê os resultados medidos
```

O documento ABNT e os PDFs precisam do LibreOffice e do pandoc instalados. Para editar no Word, abra o `.docx`
gerado, edite e exporte para PDF.
