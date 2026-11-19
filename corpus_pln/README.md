# Corpus Zela · ferramenta de construção de corpus para fine-tuning (PLN)

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

Ferramenta que recebe documentos de vários formatos, limpa e normaliza o texto e monta **três corpora** para o
ajuste fino (fine-tuning) de um LLM de pequeno porte: **conversacional**, **perguntas e respostas** e **texto
puro**. Atende à descrição da disciplina de Processamento de Linguagem Natural no enunciado geral da Global
Solution 2026.2.

> O professor confirmou (16/11/2026) que PLN exige as duas entregas: esta ferramenta e o assistente de voz do
> enunciado em PDF, que está em [`assistente_voz/`](../assistente_voz/). O relatório de PLN
> (`docs/relatorios/pdf/pln_assistente_voz.pdf`, seção 8) descreve esta ferramenta e os resultados com os exemplos.

## Para que serve no Zela

O Assistente Zela responde dúvidas de zeladoria com base em páginas oficiais da Prefeitura. Hoje ele usa um modelo
genérico com RAG. Esta ferramenta prepara o material para o passo seguinte: ajustar um modelo pequeno (por exemplo,
Qwen2.5-0.5B ou 1.5B, o mesmo que já roda no projeto) ao vocabulário e ao tom do serviço, com as mesmas fontes
oficiais e sem dados pessoais de cidadãos.

## Fluxo

```
documentos (PDF, DOCX, HTML, TXT, MD, CSV, JSON, JSONL) ou texto colado
   │  leitura.py   extrai o texto; títulos viram "# Título"; CSV/JSON com pergunta e resposta viram pares prontos
   ▼
limpeza.py         Unicode, cabeçalho e rodapé de PDF, menus de página web, linhas e palavras quebradas,
   │               dados pessoais, parágrafos repetidos entre documentos, parágrafos curtos
   ▼
blocos e seções    título > subtítulo > parágrafos e itens (o caminho da seção vai para cada exemplo)
   │
   ├── texto puro             trechos de até 1.200 caracteres, fechados em fim de frase
   ├── perguntas e respostas  pares prontos, perguntas escritas no texto, títulos em forma de pergunta,
   │                          perguntas montadas a partir dos títulos e, se quiser, perguntas geradas por LLM
   └── conversacional         pares do mesmo documento em conversas de até 3 turnos + recusas fora do escopo
   ▼
exportacao.py      treino e validação (por documento), JSONL, rastreabilidade, estatísticas e ficha do corpus,
                   e uma conferência final de formato e de dados pessoais
```

## Como executar

```bash
cd corpus_pln
pip install -r requirements.txt

# interface (envio de arquivos, opções de limpeza, antes e depois, prévia e download)
streamlit run app.py

# linha de comando
python exemplos/gerar_exemplos.py                      # cria os exemplos em PDF, DOCX, HTML, CSV e JSONL
python construir.py --entrada exemplos --saida saida --escopo "zeladoria urbana, segurança em chuvas e uso do Zela"
# com --registrar, guarda estatísticas, limpeza, ficha e uma amostra de cada corpus em resultados/ (lido pelo relatório de PLN)

# opcional: mais perguntas geradas por um LLM local (llama.cpp, Ollama) ou de nuvem (API compatível com a da OpenAI)
python construir.py --entrada exemplos --saida saida --llm http://127.0.0.1:8080/v1 --modelo qwen2.5-1.5b-instruct

python -m pytest -q tests                              # 13 testes
```

A linha de comando sai com código 0 quando a conferência final não encontra problemas. Opções úteis:
`--sem-derivadas` (sem perguntas montadas a partir dos títulos), `--sem-recusas`, `--turnos 2`,
`--validacao 0.2`, `--preservar "(11) 99999-0000"` (contato público que não deve ser mascarado),
`--remover-urls`, `--minusculas`.

## Arquivos gerados

| Arquivo | Conteúdo | Formato de cada linha |
|---|---|---|
| `texto_puro_treino.jsonl`, `_validacao.jsonl` | trechos de texto limpo | `{"text": ...}` |
| `perguntas_respostas_treino.jsonl`, `_validacao.jsonl` | pares | `{"instruction": pergunta, "input": "", "output": resposta}` |
| `conversacional_treino.jsonl`, `_validacao.jsonl` | diálogos | `{"messages": [{"role": "system" \| "user" \| "assistant", "content": ...}]}` |
| `texto_puro.txt` | o corpus de texto puro em um arquivo só | trechos separados por linha em branco |
| `rastreabilidade.csv` | de onde veio cada linha de cada arquivo | corpus, divisão, linha, arquivo, seção, origem |
| `estatisticas.json` | exemplos, caracteres, tokens estimados, origem e fonte | |
| `FICHA_DO_CORPUS.md` | ficha do corpus: documentos, limpeza aplicada, contagens e cuidados antes do uso | |

Os três formatos JSONL são os que as bibliotecas de fine-tuning mais usadas leem direto (por exemplo, o
`SFTTrainer` da biblioteca TRL aceita `text` e `messages`; o formato `instruction/input/output` é o do Alpaca).

**Divisão em treino e validação.** Com 5 documentos ou mais, a validação recebe documentos inteiros: o mesmo texto
não aparece nos dois lados, e a validação mede generalização em vez de memória. Com menos documentos, a divisão é
por exemplo. A semente fixa (42) torna a divisão reproduzível.

## Decisões de limpeza e por quê

| Etapa | O que faz | Por que |
|---|---|---|
| Unicode | forma NFC; aspas, traços e reticências simples; tira espaços invisíveis e caracteres de controle | a mesma palavra escrita de dois jeitos vira dois tokens diferentes para o modelo |
| Cabeçalho e rodapé (PDF) | tira linhas que se repetem nas bordas de 60% das páginas ou mais, e números de página | repetidas a cada página, ensinariam o modelo a escrevê-las no meio das respostas |
| Menus de páginas web | tira "Compartilhe", "Imprimir", "Voltar ao topo", redes sociais | ruído de navegação, sem conteúdo |
| Linhas quebradas | junta palavra hifenizada no fim da linha ("vi-\nas" → "vias") e linhas do mesmo parágrafo | PDF quebra o texto pela largura da página, não pelo sentido |
| Dados pessoais | troca CPF, e-mail pessoal, celular, RG e placa por `[CPF]`, `[EMAIL]` etc.; mantém 0800, telefones fixos, 156, 193 e e-mails institucionais | LGPD: um modelo ajustado pode repetir o que viu no treino |
| Repetidos | tira parágrafos iguais, também entre documentos diferentes | repetição pesa mais no treino e vaza entre treino e validação |
| Curtos | descarta parágrafos com menos de 25 caracteres | restos de formatação ("Saiba mais", "Leia também") |
| URLs e minúsculas | desligadas por padrão | endereços oficiais são informação útil; maiúsculas carregam sentido (siglas, nomes de órgãos) |

## Resultado com os exemplos

A pasta `exemplos/` tem 5 páginas oficiais da Prefeitura de São Paulo (as mesmas da base do Assistente Zela, com URL e
data da consulta no cabeçalho) e 5 arquivos sintéticos, escritos para testar a limpeza: um PDF de 3 páginas com
cabeçalho, rodapé e palavras hifenizadas, um DOCX com títulos, lista e um contato fictício, um HTML com menu, script e
rodapé, um CSV de perguntas e respostas e um JSONL de relatos com dados pessoais inventados e um relato repetido.

Execução registrada em [`resultados/`](resultados) (`python construir.py --entrada exemplos --saida saida --escopo ... --registrar`;
os números são os mesmos da execução de 13/11/2026):

| Corpus | Exemplos | Treino | Validação | Tokens (estimativa) | Origem |
|---|---|---|---|---|---|
| Texto puro | 33 | 28 | 5 | 5.090 | texto limpo |
| Perguntas e respostas | 38 | 31 | 7 | 3.966 | 15 escritas no documento, 6 do CSV, 6 de títulos em forma de pergunta, 11 montadas a partir de títulos |
| Conversacional | 21 | 19 | 2 | 4.169 | 16 com pares do mesmo documento, 5 recusas |

A limpeza tirou 9 linhas de cabeçalho e rodapé do PDF (23% do texto dele), 3 linhas de menu, uniu 5 palavras
hifenizadas e 54 linhas quebradas, removeu 2 parágrafos repetidos e mascarou 8 dados pessoais (2 CPFs, 3 celulares,
2 e-mails e 1 placa nos relatos e no DOCX). A conferência final não achou problemas de formato nem dados pessoais
restantes.

**O que a conferência por regra não pega.** No DOCX de exemplo, o nome "Maria Fictícia" continua no texto: nomes de
pessoas não são reconhecidos pelas regras. Por isso a ficha do corpus pede a leitura de uma amostra antes do uso, e a
interface mostra o antes e o depois de cada documento.

## Perguntas geradas por LLM (opcional)

Com `--llm`, cada trecho de texto puro vai para o modelo com o pedido de 2 perguntas que o trecho responde. A saída só
entra no corpus se for JSON válido, se a pergunta terminar em "?" e se pelo menos 60% das palavras de conteúdo da
resposta estiverem no trecho. Falha de rede ou resposta fora do formato não interrompe a geração: o trecho é pulado e
contado. Esses pares ficam marcados com origem `llm` na rastreabilidade.

## Limitações

- PDF digitalizado (imagem) não é lido: a ferramenta avisa e segue com os outros arquivos. Seria preciso OCR.
- Tabelas de PDF viram texto corrido; tabelas de DOCX viram linhas com colunas separadas por "|".
- Perguntas montadas a partir de títulos ("O que o documento X informa sobre Y?") são genéricas. Servem de ponto de
  partida e estão marcadas para revisão.
- Os pares de perguntas e respostas extraídos dependem de o documento ter perguntas escritas ou títulos claros.
- A estimativa de tokens usa 4 caracteres por token; o número real depende do tokenizador do modelo.

## Ética e dados

Os documentos de exemplo são públicos (páginas oficiais) ou sintéticos. Dados pessoais são mascarados antes de
entrarem no corpus, e a conferência final procura o que tenha restado. A ferramenta roda localmente e não envia nada a
serviços externos, exceto quando a geração por LLM é ligada com um endereço de nuvem; nesse caso, use só documentos
públicos. Antes de publicar um corpus ou um modelo treinado com ele, confira a licença das fontes.
