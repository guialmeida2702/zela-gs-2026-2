# ruff: noqa: E501  (linhas longas são tabelas Markdown do relatório)
"""Gera o relatório do assistente de voz (Markdown -> PDF via docs/relatorios/gerar_pdfs.sh) a partir dos resultados.

Os números vêm dos arquivos em avaliacao/resultados/. A conferência manual das respostas fica em
avaliacao/resultados/revisao_manual.json (um veredito por pergunta e a análise escrita), para que
o relatório nunca traga uma análise que não corresponda à última execução.

Uso: python avaliacao/gerar_relatorio.py   -> docs/relatorios/pln_assistente_voz.md
"""

import csv
import json
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[1]
RES = AQUI / "resultados"
SAIDA = RAIZ / "docs" / "relatorios" / "pln_assistente_voz.md"

OPCOES_STT = [("tiny", "tiny"), ("small", "small"), ("small+vocab", "small + vocabulário do domínio")]
VEREDITOS_BONS = {"correta", "recusa adequada", "abstenção adequada"}



def observacoes(a, itens: list[tuple[str, dict]]) -> None:
    """Observações da conferência manual fora da tabela, para a coluna do veredito continuar estreita."""
    com_obs = [(rotulo, v) for rotulo, v in itens if v.get("obs")]
    if com_obs:
        a("**Observações da conferência manual:**\n")
        for rotulo, v in com_obs:
            a(f"- **{rotulo}** ({v['veredito']}): {v['obs']}.")
        a("")

def ler(nome):
    p = RES / nome
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def ler_csv(nome) -> list[dict]:
    p = RES / nome
    return list(csv.DictReader(p.open(encoding="utf-8"), delimiter=";")) if p.exists() else []


def br(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",") if isinstance(x, (int, float)) else str(x)


def pct(x) -> str:
    return br(100 * x) + "%"


def curto(t, n=150):
    t = " ".join(str(t).split()).replace("|", "/")
    return t if len(t) <= n else t[: n - 1] + "…"


def tabela_stt(a, dados: dict) -> None:
    a("| Opção | WER geral | Silencioso | Com ruído | Tempo médio por áudio | Fator de tempo real |\n|---|---|---|---|---|---|")
    for chave, nome in OPCOES_STT:
        r = dados.get(chave)
        if r:
            cond = r["wer_por_condicao"]
            a(f"| {nome} | {pct(r['wer_geral'])} | {pct(cond.get('silencioso', 0))} | {pct(cond.get('ruido', 0))} | "
              f"{br(r['tempo_medio_s'], 2)} s | {br(r['fator_tempo_real'], 2)} |")
    a("")


def tabela_grupos(a, dados: dict, campo: str, titulo: str) -> bool:
    """WER por grupo (locutor, gênero, faixa etária, sotaque) nas três opções. Devolve False se não há dados."""
    grupos = sorted({g for chave, _ in OPCOES_STT for g in (dados.get(chave, {}).get(campo) or {})})
    if not grupos or grupos == ["nao_informado"]:
        return False
    a(f"| {titulo} | Áudios | " + " | ".join(nome for _, nome in OPCOES_STT if _ in dados) + " |")
    a("|---|---|" + "---|" * sum(1 for chave, _ in OPCOES_STT if chave in dados))
    for g in grupos:
        celulas, n = [], 0
        for chave, _ in OPCOES_STT:
            if chave in dados:
                r = (dados[chave].get(campo) or {}).get(g)
                celulas.append(pct(r["wer"]) if r else "–")
                n = r["audios"] if r else n
        a(f"| {g.replace('sintetico-', 'sintética ')} | {n} | " + " | ".join(celulas) + " |")
    a("")
    return True



CORPUS = RAIZ / "corpus_pln" / "resultados"
NOMES_CORPUS = {"texto_puro": "Texto puro", "perguntas_respostas": "Perguntas e respostas", "conversacional": "Conversacional"}
ORIGENS = {"texto_limpo": "texto limpo", "estruturada": "colunas de pergunta e resposta", "extraida": "pergunta escrita no documento",
           "titulo_interrogativo": "título em forma de pergunta", "derivada_do_titulo": "montada a partir do título",
           "llm": "gerada por LLM", "pares_da_fonte": "pares do mesmo documento", "recusa_modelo": "recusa fora do escopo"}


def secao_corpus(a) -> None:
    """Seção 8: a ferramenta de construção de corpus, com os números da execução registrada em corpus_pln/resultados/."""
    a("\n# 8. Ferramenta de construção de corpus\n")
    a("O enunciado geral pede uma ferramenta que receba vários tipos de documento e texto, faça a limpeza e a "
      "normalização e crie três corpora (conversacional, perguntas e respostas e texto puro) para o ajuste fino de um "
      "LLM de pequeno porte. A ferramenta fica em `corpus_pln/`, com interface em Streamlit (`streamlit run app.py`) e "
      "linha de comando (`python construir.py`), e tem 13 testes automatizados. No Zela, ela prepara o material para "
      "ajustar o modelo pequeno do assistente (Qwen2.5-1.5B) ao vocabulário e ao tom do serviço, com as mesmas páginas "
      "oficiais da base e sem dados pessoais; o RAG continua necessário para citar fontes e datas.\n")
    a("## 8.1 Fluxo e decisões\n")
    a("| Etapa | O que faz | Por quê |\n|------------|----------------------------------------|----------------------------|")
    for linha in (
        ("Leitura", "PDF, DOCX, HTML, TXT, MD, CSV, JSON, JSONL e texto colado; títulos viram marcação de seção; colunas de "
         "pergunta e resposta viram pares prontos", "cada formato chega ao mesmo texto estruturado"),
        ("Normalização", "forma Unicode NFC, aspas e traços simples, sem caracteres invisíveis", "a mesma palavra escrita de "
         "dois jeitos vira dois tokens"),
        ("Limpeza", "cabeçalho, rodapé e número de página repetidos no PDF; menus de página web; palavras hifenizadas e "
         "linhas quebradas; parágrafos repetidos entre documentos; parágrafos curtos", "ruído repetido ensina o modelo a "
         "repeti-lo; repetição vaza entre treino e validação"),
        ("Dados pessoais", "CPF, e-mail pessoal, celular, RG e placa trocados por marcadores; telefones públicos ficam",
         "LGPD: um modelo ajustado pode repetir o que viu no treino"),
        ("Três corpora", "texto puro em trechos de até 1.200 caracteres; pares de pergunta e resposta; conversas de até 3 "
         "turnos e recusas fora do escopo", "um formato por tipo de ajuste: adaptação ao domínio, instrução e chat"),
        ("Exportação", "JSONL nos formatos `text`, `instruction/input/output` e `messages`; treino e validação por "
         "documento; rastreabilidade de cada linha; ficha do corpus; conferência final de formato e de dados pessoais",
         "formatos lidos direto pelas bibliotecas de fine-tuning; validação sem texto visto no treino"),
    ):
        a("| " + " | ".join(linha) + " |")
    limpeza = ler_json_corpus("limpeza.json")
    stats = ler_json_corpus("estatisticas.json")
    amostras = ler_json_corpus("amostras.json")
    if not (limpeza and stats):
        a("\n> **Pendente:** rodar `python construir.py --entrada exemplos --saida saida --registrar` em `corpus_pln/`.\n")
        return
    a("\n## 8.2 Resultado com os documentos de exemplo\n")
    a(f"{len(limpeza)} documentos em {len({d['formato'] for d in limpeza})} formatos: 5 páginas oficiais da Prefeitura de São "
      "Paulo (as mesmas da base do assistente) e 5 arquivos sintéticos escritos para testar a limpeza, com cabeçalho e "
      "rodapé de PDF, hifenização, menu de página web, parágrafos repetidos e dados pessoais inventados.\n")
    a("| Documento | Formato | Caracteres antes | Depois | Redução | Dados pessoais mascarados |\n"
      "|----------------------|---------|-----------|-------|---------|-----------------|")
    nomes_pii = {"EMAIL": "e-mail", "TELEFONE": "celular", "CPF": "CPF", "RG": "RG", "PLACA": "placa"}
    for d in limpeza:
        pii = ", ".join(f"{nomes_pii.get(k, k)} {v}" for k, v in d["dados_pessoais"].items()) or "nenhum"
        if d["pares_estruturados"] and not d["caracteres_antes"]:
            a(f"| {d['nome']} | {d['formato']} | {d['pares_estruturados']} pares prontos | {d['pares_estruturados']} pares | — | {pii} |")
        else:
            a(f"| {d['nome']} | {d['formato']} | {d['caracteres_antes']} | {d['caracteres_depois']} | {br(d['reducao_pct'])}% | {pii} |")
    soma = {c: sum(d[c] for d in limpeza)
            for c in ("linhas_cabecalho_rodape", "linhas_ruido", "hifens_unidos", "linhas_unidas", "paragrafos_duplicados")}
    pii_total = sum(sum(d["dados_pessoais"].values()) for d in limpeza)
    a(f"\nA limpeza tirou {soma['linhas_cabecalho_rodape']} linhas de cabeçalho e rodapé, {soma['linhas_ruido']} linhas de "
      f"menu, uniu {soma['hifens_unidos']} palavras hifenizadas e {soma['linhas_unidas']} linhas quebradas, removeu {soma['paragrafos_duplicados']} parágrafos repetidos "
      f"e mascarou {pii_total} dados pessoais.\n")
    a("| Corpus | Exemplos | Treino | Validação | Tokens (aprox.) | De onde vieram |\n"
      "|----------------|-----------|--------|-----------|---------|-----------------------|")
    for c, nome in NOMES_CORPUS.items():
        s = stats[c]
        origem = "; ".join(f"{ORIGENS.get(k, k)}: {v}" for k, v in s["por_origem"].items())
        a(f"| {nome} | {s['exemplos']} | {s['treino']} | {s['validacao']} | {s['tokens_estimados']} | {origem} |")
    a("\nA estimativa de tokens usa 4 caracteres por token; o número real depende do tokenizador do modelo. Uma linha de "
      "cada corpus, como ela vai para o arquivo de treino (texto cortado):\n")
    for c, nome in NOMES_CORPUS.items():
        x = (amostras or {}).get(c)
        if x:
            mostrar = dict(x["linha"])
            if "messages" in mostrar:  # a instrução de sistema é igual em todas as linhas: encurtada para mostrar os turnos
                mostrar["messages"] = [{**m, "content": curto(m["content"], 40)} if m["role"] == "system" else m
                                       for m in mostrar["messages"]]
            linha = json.dumps(mostrar, ensure_ascii=False)
            a(f"**{nome}** (`{x['fonte']}`, origem: {ORIGENS.get(x['origem'], x['origem'])}):\n")
            a("```json\n" + (linha if len(linha) <= 420 else linha[:417] + "...") + "\n```\n")
    a("## 8.3 Limitações da ferramenta\n")
    for item in (
        "PDF digitalizado (imagem) não é lido: a ferramenta avisa e segue com os outros arquivos; seria preciso OCR.",
        "O mascaramento usa regras: nomes de pessoas não são reconhecidos (no DOCX de exemplo, um nome fictício continua no "
        "texto). Por isso a ficha do corpus pede a leitura de uma amostra antes do uso.",
        "Perguntas montadas a partir de títulos são genéricas e ficam marcadas para revisão; perguntas geradas por LLM "
        "(opcional) passam só por conferência de regra.",
        "O corpus foi preparado, mas o ajuste fino não foi executado nesta entrega: medir o ganho do modelo ajustado nas 30 "
        "perguntas da seção 4.2 é o próximo passo.",
    ):
        a(f"- {item}")
    a("")


def ler_json_corpus(nome: str):
    caminho = CORPUS / nome
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None

def main() -> None:
    stt_s, stt_r = ler("stt_audios_sinteticos.json"), ler("stt_audios_reais.json")
    stt_rr, niveis = ler("stt_audios_reais_ruido10db.json"), ler("niveis_audios_reais.json")
    llm, e2e, tts, notas = ler("llm_30_perguntas.json"), ler("e2e_10_conversas.json"), ler("tts_latencia.json"), ler("tts_notas_resumo.json")
    revisao = ler("revisao_manual.json") or {}
    L: list[str] = []
    a = L.append
    a("---\ntitle: \"Zela · PLN: assistente de voz e ferramenta de construção de corpus\"\n"
      "subtitle: \"Global Solution 2026.2 · NLP, Chatbots & Virtual Agents\"\n"
      "author: \"Guilherme Almeida (RM 563972)\"\n"
      "date: \"Novembro de 2026\"\nlang: pt-BR\n---\n")

    a("Este relatório cobre as duas entregas de PLN que o professor confirmou como exigidas: o assistente de voz "
      "(seções 1 a 7, enunciado em PDF da disciplina) e a ferramenta de construção de corpus para fine-tuning "
      "(seção 8, descrição do enunciado geral).\n")
    a("# 1. Problema, persona e ODS\n")
    a("Quem mais precisa de orientação sobre zeladoria nem sempre consegue digitar: idosos, pessoas com baixa visão ou pouca "
      "familiaridade com formulários. **Persona: Dona Cida, 67 anos**, mora no Ipiranga, enxerga mal letras pequenas e prefere "
      "falar a escrever. Ela quer saber a quem pedir a poda da árvore que encosta nos fios da rua e quanto tempo isso leva.\n")
    a("O assistente de voz do Zela responde perguntas faladas em português, com base em páginas oficiais da Prefeitura de "
      "São Paulo, e lembra o que foi dito antes na conversa. Ele está vinculado às outras disciplinas do projeto: usa o "
      "mesmo \"cérebro\" do assistente de texto do Zela (RAG com citações e abstenção, avaliado em `genai_avaliacao`), "
      "então as duas interfaces dão a mesma resposta.\n")
    a("**ODS.** ODS 10 (redução das desigualdades, meta 10.2: inclusão de quem tem dificuldade com interfaces escritas), "
      "ODS 11 (cidades sustentáveis: acesso a informação sobre serviços urbanos e segurança em chuvas) e ODS 16 "
      "(instituições eficazes: orientação correta reduz pedidos ao órgão errado).\n")

    a("# 2. Arquitetura\n")
    a("![Fluxo de um turno de conversa. Cada etapa é um módulo separado em `assistente_voz/voz/`.](../img/pln_pipeline.png){width=100%}\n")
    a("| Etapa (módulo) | Escolha | Por quê |\n|---|---|---|")
    a("| Captura (`app.py`) | `st.audio_input` (apertar para falar) e upload de WAV, MP3, M4A ou OGG | Apertar para falar evita gravar a casa inteira, como faria uma detecção de voz sempre ligada |")
    a("| STT (`voz/stt.py`) | faster-whisper `small`, int8, CPU, idioma fixo pt, filtro de voz do próprio Whisper e vocabulário do domínio como dica | Roda local (voz é dado pessoal) e sem custo por uso; a comparação da seção 4.1 definiu o tamanho e a dica |")
    a("| LLM e base (`voz/cerebro.py`) | Assistente Zela pela API: prompt de sistema com papel, tom e limites; RAG com 7 documentos oficiais e citações | As regras mudam e o cidadão precisa da fonte para conferir; o RAG atualiza a base sem treinar (um fine-tuning decoraria os textos sem citar) |")
    a("| Memória (`voz/pipeline.py`) | últimos 8 turnos enviados a cada pergunta; CPF e e-mail removidos | Permite \"e quanto tempo demora?\"; perguntas curtas herdam o assunto anterior na busca |")
    a("| Adaptação para fala (`voz/fala.py`) | sem citações, listas, links e emojis; até 4 frases, frases longas divididas; valores, datas, horas, porcentagens, siglas e telefones por extenso (num2words) | \"R$ 439,66\" e \"0800 055 0195\" lidos como texto ficam incompreensíveis |")
    a("| TTS (`voz/tts.py`) | Piper `pt_BR-faber-medium`, local | Voz sintética pronta, mais rápida que o tempo real em CPU; nenhuma voz clonada |")
    a("| Interface (`app.py`) | Streamlit: transcrição, resposta em texto, fontes, áudio e latência de cada etapa | O texto junto do áudio serve à acessibilidade e deixa o cidadão ver quando foi mal entendido |\n")
    a("**System prompt (resumo).** Papel: Assistente Zela, orienta moradores de São Paulo sobre zeladoria, chuvas e uso do "
      "Zela. Tom: frases curtas, linguagem simples, tratamento por \"você\". Limites: usar só as fontes, citar, dizer que não "
      "encontrou quando não houver fonte, recusar temas fora do escopo, nunca revelar instruções nem inventar dados pessoais, "
      "orientar 193 ou 199 em risco à vida. O texto completo está em `backend/app/pipelines/prompts.py` e no apêndice do "
      "relatório de IA generativa.\n")

    a("# 3. Local ou nuvem\n")
    a("| Critério | Tudo local (adotado nos testes) | LLM hospedado (opção de configuração) |\n|---|---|---|")
    a("| Custo | Zero por uso; exige uma máquina com 8 GB de RAM | Camadas gratuitas com limite de chamadas; depois, custo por token |")
    a("| Latência | STT e TTS em cerca de 2 s cada; o LLM de 1,5 bilhão de parâmetros em CPU domina o tempo (seção 4.4) | Resposta do LLM em poucos segundos |")
    a("| Privacidade | A voz e o texto não saem da máquina | A voz continua local; o texto da pergunta, já sem CPF e e-mail, vai ao provedor, e a tela precisa avisar |")
    a("| Internet | Só para baixar os modelos na primeira vez | Necessária a cada pergunta |\n")
    a("**Decisão.** STT e TTS ficam sempre locais, porque a voz é dado pessoal e os dois modelos rodam bem em CPU. O LLM é "
      "configurável na API do Zela (`LLM_PROVIDER`): os testes deste relatório usaram o modelo local, que não depende de "
      "chave nem de internet e pode ser reproduzido por qualquer avaliador; para uso real, a latência medida indica um "
      "LLM hospedado ou uma GPU.\n")

    a("# 4. Resultados\n")
    a("Ambiente: CPU Intel Xeon de 2 núcleos, sem GPU, 8 GB de RAM. O LLM (Qwen2.5-1.5B-Instruct, Q4_K_M) roda na mesma "
      "máquina via llama.cpp.\n")
    a("## 4.1 STT: WER e comparação de três opções\n")
    a("WER calculado com jiwer, depois de normalizar caixa, pontuação e números. Foram comparados dois tamanhos do "
      "Whisper e, no maior, o efeito de informar o vocabulário do domínio (`initial_prompt`).\n")
    if stt_r:
        a("**Gravações reais** (as 20 frases de `avaliacao/frases_stt.csv`, lidas por 3 pessoas que autorizaram o uso das gravações no trabalho e a publicação no repositório: "
          "voz1, homem de 22 anos; voz2, mulher de 48; voz3, homem de 55. Gravador de voz do celular, um arquivo por frase, "
          "AAC a 48 kHz, convertido para 16 kHz. As frases S16 a S20 foram lidas com TV ou ventilador ligados):\n")
        tabela_stt(a, stt_r)
        tabela_grupos(a, stt_r, "wer_por_locutor", "Voz")
        if niveis:
            nl, nc = niveis["por_locutor"], niveis["por_condicao"]
            a(f"**Volume e ruído das gravações** (`medir_niveis.py`, medianas): voz1 {br(nl['voz1']['volume_dbfs'])} dBFS, "
              f"voz2 {br(nl['voz2']['volume_dbfs'])} dBFS e voz3 {br(nl['voz3']['volume_dbfs'])} dBFS de volume médio; a voz2 "
              f"ficou cerca de 10 dB mais baixa, com relação sinal-ruído de {br(nl['voz2']['snr_db'])} dB, contra "
              f"{br(nl['voz1']['snr_db'])} e {br(nl['voz3']['snr_db'])} dB das outras. Nas gravações com ruído, o piso de "
              f"ruído ({br(nc['ruido']['piso_ruido_dbfs'])} dBFS) ficou igual ao das silenciosas "
              f"({br(nc['silencioso']['piso_ruido_dbfs'])} dBFS): o gravador do celular reduz o ruído de fundo, por isso as "
              "duas condições tiveram erro parecido.\n")
        if stt_rr:
            v_rr, v_r = stt_rr.get("small+vocab"), stt_r.get("small+vocab")
            s_rr, s_r = stt_rr.get("small"), stt_r.get("small")
            if v_rr and v_r and s_rr and s_r:
                voz2 = v_rr["wer_por_locutor"].get("voz2", {}).get("wer")
                a("**Teste de estresse com ruído controlado.** Para medir o STT com vozes reais em condição ruim, as 20 "
                  "gravações receberam o mesmo ruído de rua da linha de base sintética, a 10 dB de SNR "
                  f"(`misturar_ruido.py`). O WER subiu de {pct(s_r['wer_geral'])} para {pct(s_rr['wer_geral'])} no `small` e de "
                  f"{pct(v_r['wer_geral'])} para {pct(v_rr['wer_geral'])} com o vocabulário"
                  + (f"; a voz mais baixa (voz2) foi a mais afetada, com {pct(voz2)}" if voz2 is not None else "")
                  + ". O vocabulário do domínio continua ajudando com ruído.\n")
        a("**Onde o STT errou.** Os erros se concentram em poucas frases: \"vazando no meio do asfalto\" (voz2) virou "
          "\"vazando o número das faltas\", e \"se a minha rua alagar\" (voz3) virou \"se me arrullar\". Parte do erro "
          "medido pode ser diferença de leitura, e não de transcrição: em \"Quem é o responsável\" e \"eu posso beber "
          "água\", o modelo escreveu palavras que não estão no texto, e o WER conta qualquer diferença como erro.\n")
    else:
        a("> **Pendente:** as 20 gravações com vozes reais (3 vozes ou mais, 5 com ruído). O roteiro está em "
          "`assistente_voz/avaliacao/audios_reais/LEIA-ME.md`. Até lá, as tabelas usam áudios sintéticos, que validam o "
          "método e a comparação entre opções, mas não substituem o teste com pessoas.\n")
    if stt_s:
        a("**Linha de base com áudios sintéticos** (as 20 frases faladas por 3 vozes do Piper: faber, cadu e edresson; "
          "5 com ruído de rua a 10 dB de SNR):\n")
        tabela_stt(a, stt_s)
        tabela_grupos(a, stt_s, "wer_por_locutor", "Voz")
        base = stt_r or stt_s
        t, s, v = base.get("tiny"), base.get("small"), base.get("small+vocab")
        if t and s and v:
            origem = "Nas gravações reais" if stt_r else "Nos áudios sintéticos"
            confirma = (f" Os áudios sintéticos mostram a mesma ordem ({pct(stt_s['tiny']['wer_geral'])}, "
                        f"{pct(stt_s['small']['wer_geral'])} e {pct(stt_s['small+vocab']['wer_geral'])})." if stt_r else "")
            a(f"**Escolha.** {origem}, o `small` reduz o WER de {pct(t['wer_geral'])} para "
              f"{pct(s['wer_geral'])} em relação ao `tiny` e continua mais rápido que o tempo real (fator "
              f"{br(s['fator_tempo_real'], 2)}). Com o vocabulário do domínio, o erro cai para {pct(v['wer_geral'])} sem "
              "custo de tempo: os nomes que o modelo errava (\"Sabesp\", \"bueiro\", \"subprefeitura\") passam a ser "
              f"reconhecidos.{confirma} O padrão é `small` com vocabulário; o `tiny` fica como opção "
              "para máquinas fracas (`STT_MODELO=tiny`), com latência cerca de seis vezes menor e erro bem maior. Duas "
              "ressalvas: a lista de palavras foi escrita a partir do domínio, e as frases de teste são do mesmo domínio, "
              "então o ganho medido é otimista para conversas sobre outros assuntos; e os tempos foram medidos com a CPU "
              "compartilhada, por isso são um limite superior.\n")

    a("## 4.2 LLM: 30 perguntas com resposta esperada\n")
    linhas_llm = ler_csv("llm_30_perguntas.csv")
    if llm and linhas_llm:
        rev = revisao.get("llm", {})
        a(f"| Grupo | Conferência automática |{' Conferência manual |' if rev else ''}\n|---|---|{'---|' if rev else ''}")

        def humano(tipos: list[str]) -> str:
            sel = [x for x in linhas_llm if x["tipo"] in tipos]
            bons = sum(rev.get(x["id"], {}).get("veredito") in VEREDITOS_BONS for x in sel)
            return f" {br(100 * bons / len(sel))}% ({bons} de {len(sel)}) |"

        a(f"| 20 diretas + 5 continuações: corretas | {br(llm['pct_corretas_total'])}% |{humano(['direta', 'continuacao']) if rev else ''}")
        a(f"| só diretas | {br(llm['pct_corretas_diretas'])}% |{humano(['direta']) if rev else ''}")
        a(f"| só continuações (com histórico) | {br(llm['pct_corretas_continuacao'])}% |{humano(['continuacao']) if rev else ''}")
        a(f"| 5 fora do escopo: recusas adequadas | {br(llm['pct_recusas_adequadas'])}% |{humano(['fora_do_escopo']) if rev else ''}")
        a(f"| Abstenções indevidas (havia resposta nas fontes) | {llm['abstencoes_indevidas']} |{' – |' if rev else ''}")
        a(f"| Latência média por pergunta | {br(llm['latencia_media_s'])} s |{' – |' if rev else ''}\n")
        a("Conferência automática: a resposta é correta quando traz ao menos um dos termos esperados sem se abster; a "
          "recusa é adequada quando o assistente não responde ao tema e diz o que pode fazer. Conferência manual: cada "
          "resposta foi lida e comparada com a resposta esperada de `perguntas_llm.json` e com a fonte; só conta como "
          "correta a resposta completa e sem informação errada.\n")
        a("| # | Pergunta | Resposta esperada | Resposta obtida | Automática | Manual |\n|--|-----|------|--------|---|---|")
        for x in linhas_llm:
            v = rev.get(x["id"], {})
            a(f"| {x['id']} | {curto(x['pergunta'], 55)} | {curto(x.get('resposta_esperada', ''), 90)} | {curto(x['resposta'], 110)} | "
              f"{x['julgamento']} | {v.get('veredito', '–')}{' (obs.)' if v.get('obs') else ''} |")
        a("")
        observacoes(a, [(x["id"], rev.get(x["id"], {})) for x in linhas_llm])
        bloq: dict[str, int] = {}
        for x in linhas_llm:
            for b in filter(None, x["bloqueios"].split(",")):
                chave = b.split(":")[0].strip()
                bloq[chave] = bloq.get(chave, 0) + 1
        if bloq:
            a("Verificações acionadas: " + "; ".join(f"`{k}` em {v}" for k, v in sorted(bloq.items())) + ".\n")
        if revisao.get("analise_llm"):
            a(revisao["analise_llm"].strip() + "\n")
    else:
        a("> **Pendente:** executar `python avaliacao/avaliar_llm.py`.\n")

    a("## 4.3 TTS\n")
    if tts:
        a("| Voz | Síntese média por resposta | Fator de tempo real |\n|---|---|---|")
        for voz, r in tts.items():
            a(f"| {voz} | {br(r['sintese_media_s'], 2)} s | {br(r['fator_tempo_real_medio'], 3)} |")
        a("")
    if notas:
        a("| Voz | Avaliadores | Naturalidade (1 a 5) | Clareza (1 a 5) |\n|---|---|---|---|")
        for voz, r in notas.items():
            a(f"| {voz} | {r['avaliadores']} | {br(r['naturalidade_media'], 2)} | {br(r['clareza_media'], 2)} |")
        a("")
        faber = notas.get("faber")
        if faber and faber["naturalidade_media"] == 5 and faber["clareza_media"] == 5:
            a(f"As {faber['avaliadores']} pessoas ouviram as 10 respostas na voz `faber`, a que o assistente usa, e deram nota "
              f"máxima nas {faber['notas'] * 2} notas. O resultado indica que a voz foi bem aceita, mas tem limites: com todas "
              "as notas no teto, a escala não mostra diferença entre as respostas (nem as mais longas, com números e "
              "telefones, perderam ponto); a avaliação não foi cega e teve só 3 pessoas, então notas unânimes podem incluir "
              "cortesia. Uma avaliação maior, com o público da persona e comparando vozes, daria um resultado mais "
              "informativo." + ("" if "cadu" in notas else " A voz `cadu` não foi avaliada, e o padrão continua `faber`.")
              + "\n")
    else:
        a("> **Pendente:** 3 pessoas ou mais ouvem as 10 respostas de `avaliacao/amostras_tts/` nas duas vozes e dão notas "
          "de 1 a 5 de naturalidade e de clareza em `avaliacao/planilha_avaliacao.xlsx` (aba TTS) ou em "
          "`resultados/notas_tts.csv`; depois, `python avaliacao/avaliar_tts.py --resumir`. As duas vozes sintetizam uma "
          "resposta em menos de 1 s, então a escolha entre elas depende só dessas notas.\n")

    a("## 4.4 Ponta a ponta: 10 conversas de 3 turnos\n")
    linhas_e2e = ler_csv("e2e_10_conversas.csv")
    if e2e and linhas_e2e:
        lat = e2e["latencia_s"]
        a("As perguntas foram faladas pela voz sintética `cadu`, diferente da voz do assistente, para o teste ser "
          "reproduzível. Latência por etapa, em segundos:\n")
        a("| Etapa | Média | Mediana | p90 | Máximo |\n|---|---|---|---|---|")
        for k, nome in (("stt_s", "STT"), ("llm_s", "Assistente (busca + LLM)"), ("adaptacao_s", "Adaptação para fala"),
                        ("tts_s", "TTS"), ("ate_inicio_da_fala_s", "**Total até começar a falar**")):
            r = lat[k]
            a(f"| {nome} | {br(r['media'], 2)} | {br(r['mediana'], 2)} | {br(r['p90'], 2)} | {br(r['max'], 2)} |")
        rev = revisao.get("e2e", {})
        bons = sum(rev.get(f"{x['conversa']}.{x['turno']}", {}).get("veredito") in VEREDITOS_BONS for x in linhas_e2e)
        a(f"\nTurnos adequados pela conferência automática: **{br(e2e['pct_turnos_adequados'])}%** de {e2e['turnos']}"
          + (f"; pela conferência manual, **{br(100 * bons / len(linhas_e2e))}%** ({bons} de {len(linhas_e2e)})." if rev else ".") + "\n")
        a("| Turno | Transcrição da pergunta | Resposta (texto) | Automática | Manual |\n|---|--------|-----------------|--|---|")
        for x in linhas_e2e:
            v = rev.get(f"{x['conversa']}.{x['turno']}", {})
            a(f"| C{x['conversa']}T{x['turno']} | {curto(x['transcricao'], 55)} | {curto(x['resposta_texto'], 120)} | "
              f"{'sim' if x['adequada'] == 'True' else 'não'} | {v.get('veredito', '–')}{' (obs.)' if v.get('obs') else ''} |")
        a("")
        observacoes(a, [(f"C{x['conversa']}T{x['turno']}", rev.get(f"{x['conversa']}.{x['turno']}", {})) for x in linhas_e2e])
        if revisao.get("analise_e2e"):
            a(revisao["analise_e2e"].strip() + "\n")
        a("O tempo é dominado pelo LLM em CPU. Turnos que terminam em abstenção ou recusa respondem em poucos segundos, "
          "porque não chamam o modelo. Com um LLM hospedado (Groq ou Gemini, já suportados pela API), a etapa cai para "
          "poucos segundos, ao custo de enviar o texto da pergunta, já sem dados pessoais, a um provedor externo.\n")
    else:
        a("> **Pendente:** executar `python avaliacao/avaliar_e2e.py`.\n")

    a("# 5. Ética, LGPD e segurança\n")
    for item in [
        "**Consentimento antes do primeiro uso.** A primeira tela explica que a voz será gravada e processada e só libera "
        "o microfone depois do aceite.",
        "**Retenção mínima.** O áudio existe em arquivo temporário apenas durante a transcrição e é apagado em seguida. O "
        "histórico guarda texto, sem CPF e e-mail, e some ao fechar a página. Nada é gravado em banco.",
        "**Processamento local da voz.** A gravação não vai para nenhuma API externa. Se o LLM for hospedado, só o texto "
        "da pergunta sai da máquina, e isso deve constar do aviso de consentimento.",
        "**Limites do assistente.** Pedidos fora do tema recebem recusa; em saúde, questões jurídicas e financeiras, a "
        "recusa indica procurar um profissional; em risco à vida, a resposta manda ligar 193 ou 199.",
        "**Alucinação.** Quando as fontes não têm a resposta, o assistente diz que não encontrou e indica o 156. Frases "
        "que as fontes não sustentam são retiradas antes de a resposta ser falada.",
        "**Clonagem de voz.** É proibido clonar a voz de uma pessoa real sem consentimento expresso e documentado. O "
        "projeto usa somente vozes sintéticas prontas do Piper; nenhuma voz real foi clonada.",
        "**Transparência.** A tela mostra a transcrição, o texto da resposta, as fontes e a latência de cada etapa.",
    ]:
        a(f"- {item}")
    a("\n## 5.1 Análise de viés do STT\n")
    a("Um reconhecedor de fala não erra igual para todo mundo. Estudos com sistemas comerciais mediram quase o dobro de "
      "erro para grupos pouco representados nos dados de treino (KOENECKE et al., 2020), e o Whisper declara, em sua "
      "documentação, desempenho desigual entre sotaques e idiomas. Para o Zela isso importa porque a persona, uma "
      "senhora de 67 anos, pertence a grupos que esses modelos costumam atender pior: voz feminina idosa e fala informal.\n")
    if stt_s:
        loc = (stt_s.get("small+vocab") or stt_s.get("small") or {}).get("wer_por_locutor") or {}
        if loc:
            menor, maior = min(loc.items(), key=lambda kv: kv[1]["wer"]), max(loc.items(), key=lambda kv: kv[1]["wer"])
            a(f"**O que os dados disponíveis mostram.** Mesmo entre três vozes sintéticas parecidas, o WER da opção adotada "
              f"vai de {pct(menor[1]['wer'])} ({menor[0].replace('sintetico-', '')}) a {pct(maior[1]['wer'])} "
              f"({maior[0].replace('sintetico-', '')}): o erro depende de quem fala. **O que eles não mostram.** As três "
              "vozes são masculinas, adultas e de leitura pausada. Não há voz feminina, idosa, com sotaque de outras "
              "regiões nem fala espontânea, então este teste não permite afirmar que o sistema trata esses grupos de forma "
              "equivalente.\n")
    grupos_reais = False
    if stt_r:
        a("**Gravações reais por grupo** (colunas `genero` e `faixa_etaria` do manifesto; sotaque não informado):\n")
        for campo, titulo in (("wer_por_genero", "Gênero"), ("wer_por_faixa_etaria", "Faixa etária"), ("wer_por_sotaque", "Sotaque")):
            grupos_reais = tabela_grupos(a, stt_r, campo, titulo) or grupos_reais
        loc = (stt_r.get("small+vocab") or {}).get("wer_por_locutor") or {}
        if {"voz1", "voz2", "voz3"} <= loc.keys():
            a(f"**O que as gravações reais mostram.** Com a opção adotada, o erro foi de {pct(loc['voz1']['wer'])} na voz do "
              f"homem de 22 anos, {pct(loc['voz3']['wer'])} na do homem de 55 e {pct(loc['voz2']['wer'])} na da mulher de 48: "
              "a voz feminina teve o maior erro, como a literatura aponta. **O que elas não permitem afirmar.** Há uma pessoa "
              "por grupo, e a voz feminina também foi a gravada mais baixa, então não dá para separar o efeito do gênero, da "
              "idade, da pessoa e do volume da gravação. Ninguém tinha mais de 60 anos nem sotaque de outra região, que é o "
              "perfil da persona; antes de um uso real, o teste precisa ser repetido com esse público e com fala espontânea, "
              "não lida.\n")
        if revisao.get("analise_vies"):
            a(revisao["analise_vies"].strip() + "\n")
    if not grupos_reais:
        a("**Como o viés será medido.** O manifesto das gravações reais (`audios_reais/manifesto.csv`) tem as colunas "
          "`genero`, `faixa_etaria` e `sotaque`, e `avaliar_stt.py` calcula o WER de cada grupo. As gravações devem incluir "
          "pelo menos uma voz feminina e uma pessoa com mais de 60 anos, que é o perfil da persona. Com 20 áudios, a "
          "comparação indica tendências, não diferenças estatisticamente seguras.\n")
    a("**Como o projeto reduz o dano de um erro de transcrição.** A transcrição aparece na tela antes da resposta, para a "
      "pessoa ver o que foi entendido e repetir; a pergunta também pode ser enviada como arquivo; o vocabulário do "
      "domínio reduz erros em nomes de órgãos; e o assistente não executa nenhuma ação a partir da voz, apenas orienta, "
      "então um erro de transcrição gera uma resposta inadequada, não um registro indevido.\n")

    a("# 6. Limitações\n")
    for item in [
        ("O STT foi medido com 20 frases lidas por 3 pessoas (nenhuma com mais de 60 anos nem com sotaque de outra "
         "região) e gravadas perto do celular; fala espontânea, distância e ruído real devem aumentar o erro. O teste de "
         "ponta a ponta usou perguntas faladas por voz sintética." if stt_r else
         "Os testes de STT, TTS e ponta a ponta usam vozes sintéticas enquanto as gravações reais não são feitas; vozes "
         "reais, sotaques e ambientes ruidosos devem aumentar o WER."),
        "O LLM local de 1,5 bilhão de parâmetros deixa a resposta lenta em CPU e às vezes mistura informações de fontes "
        "vizinhas ou omite parte da resposta esperada.",
        "A base tem 7 documentos da cidade de São Paulo. Duas páginas oficiais divergem entre si (prazo e multa de "
        "calçada), e o assistente responde com o trecho que a busca trouxe, sem reconciliar as duas.",
        "Apertar para falar exige um toque; para pessoas com mobilidade reduzida, uma palavra de ativação seria melhor, "
        "mas aumentaria o risco de gravar sem querer.",
        "A adaptação para fala cobre os padrões mais comuns (valores, datas, telefones, siglas do domínio); siglas novas "
        "precisam entrar na tabela.",
    ]:
        a(f"- {item}")
    a("\n# 7. Melhorias futuras\n")
    for item in [
        ("Repetir o teste de STT com o público da persona: pessoas com mais de 60 anos, mais vozes femininas, sotaques de "
         "outras regiões e fala espontânea, em vez de frases lidas." if stt_r else
         "Fazer as gravações reais com pelo menos três pessoas de perfis diferentes e repetir as avaliações de STT e de viés."),
        "Trocar o gerador por um modelo maior (local com GPU ou hospedado) e repetir as 30 perguntas para medir o ganho.",
        "Responder em fluxo: começar a falar a primeira frase enquanto o modelo ainda escreve o restante, para reduzir o "
        "tempo até o início da fala.",
        "Confirmar em voz alta o que foi entendido quando a confiança da transcrição for baixa (\"você perguntou sobre "
        "poda de árvore?\").",
        "Permitir registrar o relato por voz, com leitura do resumo e confirmação falada antes de enviar.",
        "Ampliar a base para outras cidades e marcar a data de validade de cada documento.",
    ]:
        a(f"- {item}")
    secao_corpus(a)
    a("\n# 9. Vídeo (até 5 minutos)\n")
    a("Roteiro: (1) tela de consentimento; (2) pergunta falada sobre poda de árvore; (3) continuação \"e quanto tempo "
      "demora?\", que mostra a memória; (4) terceiro turno sobre calçada; (5) pedido fora do escopo e a recusa; "
      "(6) latência por etapa na tela e as tabelas da seção 4; (7) cerca de 1 minuto da ferramenta de corpus: envio "
      "de documentos de formatos diferentes, o antes e depois da limpeza e os três corpora gerados.\n")
    a("# Referência\n")
    a("KOENECKE, A. et al. Racial disparities in automated speech recognition. **Proceedings of the National Academy of "
      "Sciences**, v. 117, n. 14, p. 7684-7689, 2020.\n")
    SAIDA.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(SAIDA)


if __name__ == "__main__":
    main()
