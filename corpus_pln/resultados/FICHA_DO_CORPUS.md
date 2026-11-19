# Ficha do corpus

Gerado em 16/11/2026 11:18 pela ferramenta de construção de corpus do Zela.

## Documentos de origem

| Arquivo | Formato | Caracteres antes | Caracteres depois | Redução | Dados pessoais mascarados |
|---|---|---|---|---|---|
| calcadas-fiscalizacao.md | .md | 1859 | 1803 | 3.0% | nenhum |
| cartilha_chuvas_sintetica.pdf | .pdf | 2252 | 1725 | 23.4% | nenhum |
| dc-chuvas-excessivas.md | .md | 4271 | 4242 | 0.7% | nenhum |
| faq-subprefeitura.md | .md | 5342 | 5298 | 0.8% | nenhum |
| pagina_iluminacao_sintetica.html | .html | 691 | 593 | 14.2% | nenhum |
| perguntas_sobre_o_zela.csv | .csv | 0 | 0 | 0.0% | nenhum |
| poda-butanta.md | .md | 2723 | 2712 | 0.4% | nenhum |
| procedimento_poda_sintetico.docx | .docx | 898 | 832 | 7.3% | EMAIL: 1, TELEFONE: 1 |
| relatos_sinteticos.jsonl | .jsonl | 481 | 321 | 33.3% | EMAIL: 1, CPF: 2, TELEFONE: 2, PLACA: 1 |
| zela-guia-do-servico.md | .md | 2871 | 2786 | 3.0% | nenhum |

## Limpeza aplicada

- [x] Normalização Unicode (NFC), aspas e traços simples, sem caracteres invisíveis
- [x] Remoção de cabeçalho, rodapé e número de página repetidos (PDF)
- [x] Remoção de linhas de menu e botões de página web
- [x] Junção de linhas quebradas e de palavras hifenizadas no fim da linha
- [ ] Remoção de endereços (URL)
- [x] Mascaramento de CPF, e-mail pessoal, celular, RG e placa
- [x] Remoção de parágrafos duplicados entre os documentos
- [ ] Conversão para minúsculas
- Parágrafos com menos de 25 caracteres descartados

Contagem do que saiu: linhas cabecalho rodape: 9, linhas ruido: 3, hifens unidos: 5, linhas unidas: 54, urls removidas: 0, paragrafos duplicados: 2, paragrafos curtos: 0.

## Corpora gerados

| Corpus | Exemplos | Treino | Validação | Caracteres | Tokens (estimativa) | Origem dos exemplos |
|---|---|---|---|---|---|---|
| Texto puro | 33 | 28 | 5 | 20359 | 5090 | texto_limpo: 33 |
| Perguntas e respostas | 38 | 31 | 7 | 15864 | 3966 | derivada_do_titulo: 11, estruturada: 6, extraida: 15, titulo_interrogativo: 6 |
| Conversacional | 21 | 19 | 2 | 16676 | 4169 | pares_da_fonte: 16, recusa_modelo: 5 |

Configuração: trechos de até 1200 caracteres; até 3 turnos por conversa; validação de 10%; semente 42.

## Antes de usar

- Leia uma amostra de cada corpus. Perguntas de origem `derivada_do_titulo` são montadas por modelo fixo e servem de ponto de partida; as de origem `llm` foram escritas por um modelo e conferidas só por regra.
- O mascaramento de dados pessoais é uma heurística. Confira nomes de pessoas e outros dados que as regras não cobrem.
- Confira a licença e os termos de uso dos documentos de origem antes de publicar o corpus ou um modelo treinado com ele.
- O corpus reflete as fontes: se elas cobrem uma cidade ou um órgão, o modelo ajustado responderá com esse viés.
- A contagem de tokens é uma estimativa de 4 caracteres por token; meça com o tokenizador do modelo escolhido.
