"""Documento integrador (Governança em IA & Business Analysis) no padrão ABNT/FIAP.

Uso:  python docs/governanca/gerar_documento.py
Saídas: docs/governanca/Zela_documentacao_integrada.docx e .pdf

Os resultados numéricos são lidos dos arquivos de avaliação de cada módulo (metricas.py).
A CONCLUSÃO foi escrita pelo autor, sem IA na redação (regra do enunciado); a IA só revisou fatos e gramática.
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
from abnt import Trabalho, gerar  # noqa: E402
from metricas import cluster, genai, m, pln  # noqa: E402

RAIZ = AQUI.parents[1]
G, P = genai(), pln()
C = {c["cenario"]: c for c in cluster()}
CP = C.get("principal", {})


def br(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",") if isinstance(x, (int, float)) else str(x)


AUTORES = ["Guilherme Almeida", "RM 563972"]
FONTE_AUTORES = "elaborado pelo autor (2026)."

blocos = [
    ("h1", "1 INTRODUÇÃO"),
    ("p", "Os canais SP156 da Prefeitura de São Paulo recebem, em média, 157.120 solicitações por mês, segundo dados de "
          "2022 da Secretaria Municipal de Inovação e Tecnologia (SÃO PAULO, [20--]). Boa parte dessas solicitações trata de "
          "zeladoria urbana: buracos, iluminação, árvores, calçadas, bueiros e descarte irregular de lixo. A execução desses "
          "serviços é distribuída entre 32 subprefeituras, concessionárias e órgãos como a CET e a Defesa Civil."),
    ("p", "Dois problemas aparecem dos dois lados do atendimento. O cidadão nem sempre sabe a qual órgão recorrer, descreve "
          "o problema sem as informações de que a equipe precisa e não sabe dizer se há risco. A prefeitura, por sua vez, "
          "gasta tempo classificando relatos, conferindo planilhas das equipes de campo e decidindo prioridades, trabalho "
          "que pesa mais justamente nos dias de chuva forte."),
    ("p", "O **Zela** é uma prova de conceito (POC) de CitizenTech para esse cenário. O cidadão relata o problema com suas "
          "palavras e, se quiser, uma foto; a inteligência artificial sugere o tipo, a urgência e o órgão responsável; o "
          "cidadão confere e confirma; a equipe gestora trata a solicitação com o histórico completo. Ao redor desse núcleo, "
          "cada disciplina do semestre acrescentou uma parte: análise de fotos, assistente que responde com base em páginas "
          "oficiais, assistente por voz, robô de automação, estudo de capacidade em cluster, roteiro de computação quântica e "
          "um classificador de sons para acessibilidade."),
    ("figura", "Arquitetura integrada do Zela", RAIZ / "docs/img/arquitetura_integrada.png", FONTE_AUTORES, 15),
    ("p", "A seção 2 descreve a contribuição de cada disciplina e termina com a governança: inventário dos componentes de "
          "IA, riscos, LGPD, indicadores e o que foi ou não foi integrado. A seção 3 traz a conclusão do autor e a seção 4, "
          "os links do vídeo e do repositório."),
    ("p", "O Zela é um protótipo acadêmico e não é canal oficial da Prefeitura. Os testes usam dados sintéticos ou públicos, e "
          "as avaliações de IA foram executadas com um modelo de linguagem pequeno rodando localmente, sem custo de API. Os "
          "números apresentados valem para essas condições."),

    ("h1", "2 DESENVOLVIMENTO", False),
    ("p", "Cada subseção a seguir corresponde a uma disciplina e informa o problema tratado, as decisões técnicas, os "
          "resultados medidos e as limitações. Todo o código e os arquivos de avaliação estão no repositório (seção 4)."),

    ("h2", "2.1 Front End & Mobile"),
    ("p", "O front-end foi feito em Streamlit e conversa com uma API em FastAPI. O cidadão passa por três etapas "
          "visíveis: relatar, conferir o que a IA entendeu e receber o protocolo. A análise só vira solicitação depois da "
          "confirmação do cidadão, que pode trocar o tipo e a urgência sugeridos. Essa revisão humana é a primeira camada de "
          "controle da IA e também gera dado de qualidade: cada correção fica registrada e aparece no painel do gestor como "
          "taxa de correção."),
    ("p", "Enquanto o modelo trabalha, o cidadão vê as etapas reais; se a API cair ou demorar, o texto digitado não se "
          "perde. Há alto contraste, ajuste do tamanho do texto, leitura em voz alta e aviso fixo de emergência. A área do "
          "gestor exige login e mostra a fila priorizada, indicadores de qualidade da IA e o monitoramento de fotos."),
    ("p", "A triagem usa saída estruturada validada com Pydantic, regras determinísticas que só podem elevar a urgência e "
          "encaminhamento por tabela, e não pelo modelo. A avaliação com 10 casos de teste mostrou o valor de medir antes de "
          "confiar: o modelo local marcou risco imediato em quase todos os relatos e acertou 3 de 10 casos. Depois de dois "
          "ajustes (regra de risco reescrita no prompt e remoção de frases com ordens ao sistema antes do envio ao modelo), "
          "acertou 8 de 10. As duas falhas restantes estão documentadas em docs/avaliacao_ia.md."),
    ("p", "Limitação: o teste de usabilidade com três pessoas e o vídeo de demonstração ainda precisam ser feitos; o roteiro e a "
          "planilha estão em docs/validacao_usuarios.md."),

    ("h2", "2.2 Visão Computacional"),
    ("p", "O tema escolhido foi a classificação de fissuras em concreto, ligada aos relatos sobre muros, viadutos e calçadas. "
          "Usei a base de Özgenel (2019), com 40 mil recortes de 227 por 227 pixels, e uma amostra de 5.800 imagens. "
          "Como os recortes vêm de poucas fotos grandes, a divisão entre treino, validação e teste foi feita por blocos de 50 "
          "arquivos consecutivos, para reduzir o risco de recortes da mesma foto caírem em conjuntos diferentes."),
    ("p", "A arquitetura é a MobileNetV3-Small pré-treinada no ImageNet (HOWARD et al., 2019), com entrada de 160 pixels, "
          "treinada em CPU em 7,3 minutos e exportada para ONNX (6,1 MB). A escolha privilegiou rodar sem GPU no servidor "
          "gratuito do Zela. O limiar de decisão de 0,15 foi escolhido na validação priorizando o recall, porque deixar de "
          "sinalizar uma fissura custa mais do que pedir uma vistoria a mais."),
    ("tabela", "Resultados da visão computacional no conjunto de teste (2.000 imagens)",
     ["Medida", "Resultado"],
     [["Precisão / recall / F1 (limiar 0,15)", "0,990 / 0,999 / 0,9945"],
      ["Falsos positivos / falsos negativos", "10 / 1"],
      ["Inferência por recorte (CPU 2 threads, ONNX Runtime)", "1,34 ms (p95 1,85 ms)"],
      ["Pior condição no teste de robustez (compressão JPEG forte)", "F1 0,985"]],
     FONTE_AUTORES, [10, 6]),
    ("p", "A análise de erros mostrou falsos positivos em bordas de sombra, juntas e riscos, e alguns casos que parecem "
          "erro de rótulo da própria base. A métrica alta vale para fotos parecidas com as da base; em fotos de rua, com "
          "obstáculos e outros materiais, são esperados mais falsos positivos. No Zela, a foto do relato é dividida em áreas, as "
          "áreas suspeitas aparecem marcadas para o cidadão e o resumo entra no prompt da triagem. O texto da interface "
          "deixa claro que a presença de fissura não indica gravidade, e a imagem não é armazenada."),

    ("h2", "2.3 Generative AI & Advanced Nets"),
    ("p", "O Assistente Zela responde dúvidas sobre zeladoria com base em seis páginas oficiais da Prefeitura de São Paulo "
          "(poda de árvores, calçadas, chuvas e perguntas frequentes das subprefeituras) e em um guia do próprio serviço, "
          "todos com endereço e data de consulta registrados. A técnica é a geração aumentada por recuperação, ou RAG "
          "(LEWIS et al., 2020): o sistema busca os trechos mais próximos da pergunta e só então pede a resposta ao modelo, "
          "que é obrigado a citar as fontes."),
    ("p", "Comparei duas formas de dividir os textos: blocos fixos de 400 caracteres e blocos de até 700 caracteres que "
          "respeitam seções, frases e itens de perguntas frequentes, com sobreposição de 120 caracteres. Também comparei "
          "três buscadores: lexical (BM25), denso (embeddings multilíngues) e híbrido, que combina os dois por fusão de "
          "rankings (CORMACK; CLARKE; BUETTCHER, 2009). Com blocos fixos, a fonte certa ficou em primeiro lugar em "
          f"{m(G, 'hit1_fixo_bm25')} das perguntas no BM25 e em {m(G, 'hit1_fixo_denso')} no denso; com a divisão por "
          f"estrutura e busca híbrida, em {m(G, 'hit1_estrutura_hibrido')}. Mantive a divisão por estrutura e a busca "
          "híbrida, com 4 trechos por resposta."),
    ("p", "O modelo pequeno, sozinho, não se protege. Com o contexto errado de propósito, ele se absteve em apenas "
          f"{m(G, 'gerador_irrelevante_absteve')} casos e inventou respostas nos demais. Por isso o assistente tem camadas "
          "fora do modelo: abstenção quando a busca não encontra evidência suficiente, citações obrigatórias, conferência de "
          "cada frase e de seus números numa mesma fonte, remoção de dados pessoais da pergunta, bloqueio de pedidos para "
          "mudar as regras e recusa fixa de pedidos de orientação médica, "
          "jurídica ou financeira. Esta última foi incluída depois que o teste por voz mostrou o modelo dando orientação "
          "médica a partir de uma página sobre chuvas. Também testei e descartei uma verificação de pertinência que "
          "bloqueava respostas certas; o relatório de avaliação mostra os números."),
    ("tabela", "Avaliação ponta a ponta do Assistente Zela",
     ["Tipo de pergunta", "Resultado adequado"],
     [["Respondíveis pelas fontes (resposta correta e citada)", m(G, "respondiveis")],
      ["Sem resposta nas fontes (abstenção)", m(G, "sem_resposta")],
      ["Ambíguas", m(G, "ambiguas")], ["Fora do escopo (recusa)", m(G, "fora_escopo")],
      ["Conversa com continuação (3 turnos)", m(G, "conversa")],
      ["Testes adversariais (injeção direta e indireta, prompt, dados pessoais)", m(G, "seguranca")]],
     f"elaborado pelo autor (2026), modelo {m(G, 'modelo')}.", [11, 5]),
    ("p", "Sem as camadas de mitigação, o modelo respondeu sem fonte a "
          f"{m(G, 'sem_mitigacao_respondeu')} perguntas que não tinham resposta nas fontes. O relatório completo, com cada "
          "pergunta, resposta e julgamento, está em docs/relatorios/genai_avaliacao.md."),

    ("h2", "2.4 NLP, Chatbots & Virtual Agents"),
    ("p", "O assistente de voz permite tirar as mesmas dúvidas falando. Cada etapa é um módulo separado: transcrição com "
          "faster-whisper (RADFORD et al., 2022), resposta pelo Assistente Zela da seção 2.3 com memória da conversa, "
          "adaptação do texto para a fala e síntese com uma voz sintética pronta do Piper. A adaptação para fala retira "
          "citações, listas e emojis, quebra frases longas e escreve números, valores, datas, siglas e telefones do jeito "
          "que são falados."),
    ("p", "Antes do primeiro uso, a interface pede consentimento e explica que o áudio é apagado logo depois da "
          "transcrição, que a voz que responde é sintética e que o assistente não substitui os serviços de emergência. Nenhuma "
          "voz de pessoa real foi clonada. Tudo roda localmente, então a voz do cidadão não sai da máquina."),
    ("tabela", "Resultados do assistente de voz",
     ["Teste", "Resultado"],
     [["STT: WER do whisper tiny, small e small com vocabulário do tema (20 frases, 3 vozes, 5 com ruído)",
       (f"{m(P, 'wer_reais_tiny')}%, {m(P, 'wer_reais_small')}% e {m(P, 'wer_reais')}% nas gravações reais (sintéticos: "
        f"{m(P, 'wer_tiny')}%, {m(P, 'wer_small')}% e {m(P, 'wer_small_vocab')}%)" if "wer_reais_small" in P else
        f"{m(P, 'wer_tiny')}%, {m(P, 'wer_small')}% e {m(P, 'wer_small_vocab')}% (áudios sintéticos; gravações reais: "
        f"{m(P, 'wer_reais')}{'%' if 'wer_reais' in P else ''})")],
      ["LLM: 30 perguntas (20 diretas, 5 continuações, 5 fora do escopo)",
       f"{m(P, 'llm_corretas')}% corretas; {m(P, 'llm_recusas')}% recusas adequadas"],
      ["TTS: notas de 3 pessoas para 10 respostas (1 a 5)", f"naturalidade {m(P, 'tts_nat')}; clareza {m(P, 'tts_cla')}"],
      ["Ponta a ponta: 10 conversas de 3 turnos", f"{m(P, 'e2e_adequados')}% dos turnos adequados; mediana de "
                                                  f"{m(P, 'e2e_total_mediana')} s até começar a falar"]],
     "elaborado pelo autor (2026).", [9, 7]),
    ("p", "O gargalo é o modelo de linguagem em CPU; transcrição e síntese levam cerca de 1,5 segundo cada. Os testes com "
          "voz sintética subestimam o uso real e devem ser refeitos com gravações de vozes reais."),
    ("p", "A disciplina exige também a ferramenta de corpus do enunciado geral (corpus_pln/): ela limpa PDF, DOCX, HTML, "
          "texto e CSV e monta corpora de texto puro, perguntas e respostas e conversa para o ajuste fino de um modelo pequeno."),

    ("h2", "2.5 AI for RPA"),
    ("p", "O Robô Zela automatiza a rotina diária do gestor em uma execução: coleta notícias oficiais da Prefeitura e da "
          "Defesa Civil (web scraping), consulta a previsão de chuva (API Open-Meteo), lê e valida as planilhas de ordens de "
          "serviço das subprefeituras com Pandas, atualiza as solicitações pela API do Zela, eleva a prioridade de casos de "
          "drenagem quando há alerta de chuva, classifica as fotos de vistoria com o modelo da seção 2.2, registra tudo num "
          "banco SQLite de auditoria e envia um boletim por e-mail."),
    ("p", "Com dados de teste rotulados, o robô acertou 17 de 17 decisões sobre linhas de planilha, 16 de 16 fotos e 3 de 3 "
          "decisões de priorização, e não reaplicou arquivos já processados. Falhas previsíveis (API fora do ar, planilha "
          "corrompida, foto inválida, ausência de SMTP) foram provocadas e tratadas sem interromper a execução. O caso de falha "
          "real foi o filtro de notícias: a primeira versão teve precisão de 0,62 numa amostra de 35 notícias rotuladas à mão; "
          "depois do ajuste das palavras-chave, 0,93, com o mesmo recall de 0,87."),

    ("h2", "2.6 Physical Computing, Robotics & Cognitive IoT"),
    ("p", "O OuviAí é um classificador de sons para pessoas surdas ou com deficiência auditiva, feito no Edge Impulse e "
          "executado no próprio celular: distingue campainha, batida na porta e som ambiente, com processamento MFE e rede "
          "convolucional. Foram 20 gravações de 5 segundos por classe feitas com o celular (15 para treino e 5 para "
          "teste), teste com o conjunto separado e 15 tentativas ao vivo, com contagem de falsos positivos no som ambiente."),
    ("p", "Resultados: 90,1% na validação do treino e 76,1% no teste por janela (12 de 15 arquivos); o erro principal é "
          "som ambiente confundido com campainha. Ao vivo, com o celular a 50 cm da porta, foram 10 de 15 acertos "
          "e 5 falsos positivos nas 5 tentativas de ambiente. O projeto não troca dados com o Zela; a ligação é de "
          "propósito (acessibilidade) e a evolução proposta é uma classe de sirene de alerta da Defesa Civil, que avisaria "
          "por vibração quem não ouve a sirene de alagamento."),

    ("h2", "2.7 Cluster Computing"),
    ("p", "Simulei no iSPD (MANACERO et al., 2012) a fila de processamento dos relatos num pico após um temporal: 240 "
          "tarefas de 300.000 MFlop cada (30 segundos numa máquina de 10 GFlop/s, a média medida na triagem), com escalonador "
          "Workqueue, enlaces de 1 Gbit/s e a mesma carga nos dois cenários. Só o número de workers mudou."),
    ("tabela", "Tempo total simulado no iSPD: 2 x 4 workers",
     ["Cenário", "T2 (s)", "T4 (s)", "Redução", "T2/T4"],
     [[nome.replace("_", " "), br(c["T2_s"]), br(c["T4_s"]), br(c["reducao_pct"]) + "%", br(c["speedup_T2_T4"], 3)]
      for nome, c in C.items()] or [["[a medir]", "", "", "", ""]],
     "elaborado pelo autor (2026) com o iSPD.", [5.5, 2.5, 2.5, 2.5, 2.5]),
    ("p", "No cenário principal o ganho foi o máximo possível (redução de 50% e T2/T4 igual a 2), porque os relatos são "
          "independentes e a rede ficou ociosa. Os cenários de sensibilidade mostram quando isso deixa de valer: com poucas "
          "tarefas o ganho cai para cerca de 1,5, e com vídeos passando por um switch de 10 Mbit/s a rede satura: 8 workers "
          "levaram o mesmo tempo que 4. Como o processamento total é o mesmo, ligar workers extras só nos picos reduz a "
          "espera sem aumentar o gasto de processamento."),

    ("h2", "2.8 Computação Quântica & IA"),
    ("p", "Analisando cada etapa do Zela, o gargalo que não escala com computação clássica não é entender o relato, que é "
          "paralelo, mas despachar as equipes: decidir quais equipes atendem quais ocorrências, em que ordem, respeitando "
          "urgência e prazos. É um problema de roteamento de veículos com janelas de tempo, de natureza combinatória. A "
          "capacidade quântica escolhida foi a otimização (recozimento quântico e QAOA sobre uma formulação QUBO), com a "
          "criptografia pós-quântica como frente paralela para proteger dados de cidadãos no longo prazo (NIST, 2024)."),
    ("p", "O roteiro é conservador porque a pesquisa atual só resolve instâncias pequenas: hoje, solvers clássicos; depois, "
          "testes com solvers híbridos, que só entram em uso se vencerem o clássico nas métricas medidas. A função de custo "
          "precisa incluir equidade entre bairros, e só dados agregados podem ir para provedores quânticos em nuvem."),

    ("h2", "2.9 Governança em IA & Business Analysis"),
    ("p", "Esta subseção junta os módulos sob uma mesma visão de governança: o que cada IA faz, quem decide, quais riscos "
          "existem, como os dados pessoais são tratados, como medir valor e o que, de fato, ficou integrado."),
    ("h3", "2.9.1 Inventário dos componentes de IA"),
    ("quadro", "Inventário dos componentes de IA do Zela",
     ["Componente", "Modelo e licença", "O que decide ou sugere", "Supervisão humana"],
     [["Triagem de relatos", "Qwen2.5-1.5B-Instruct local (Apache-2.0) ou modelo via Groq/Gemini", "Sugere tipo, urgência, "
       "risco e orientações", "Cidadão confirma ou corrige; gestor revisa"],
      ["Regras de segurança", "Código determinístico", "Só eleva urgência (risco à vida, vulneráveis, chuva)", "Regras "
       "versionadas e testadas"],
      ["Visão computacional", "MobileNetV3-Small (pesos BSD-3, base CC BY 4.0), ONNX", "Sinaliza áreas com possível fissura",
       "Técnico decide vistoria e gravidade"],
      ["Assistente (RAG)", "BM25 + MiniLM multilíngue (Apache-2.0) + LLM", "Responde com fontes ou se abstém", "Fontes "
       "públicas datadas; cidadão pode seguir o link"],
      ["Assistente de voz", "faster-whisper (MIT) e Piper (GPL-3.0; voz faber, base CC0)", "Transcreve e fala a resposta",
       "Texto exibido junto do áudio"],
      ["Robô RPA", "Regras + modelo de visão", "Aplica OS válidas e prioriza drenagem", "Linhas inválidas vão para revisão; "
       "notas \"[robô]\" auditáveis"],
      ["OuviAí", "CNN do Edge Impulse no celular", "Indica o som detectado", "Usuário vê o resultado; nada é enviado"]],
     FONTE_AUTORES, [3, 4.3, 4.3, 4.4]),
    ("h3", "2.9.2 Riscos e mitigações"),
    ("quadro", "Matriz de riscos da solução",
     ["Risco", "Prob.", "Impacto", "Mitigação implementada", "Evidência"],
     [["Subestimar urgência de caso com risco à vida", "Média", "Alto", "Regras que só elevam; aviso de emergência fixo",
       "Caso 3 da avaliação da triagem"],
      ["Instrução embutida no relato, na pergunta ou numa fonte adulterada", "Média", "Alto", "Remoção de frases de "
       "comando; texto tratado como dado; trechos de fonte com ordens descartados antes do LLM", "Caso 7 da triagem; "
       "teste S3 do RAG (falhou, foi corrigido e passou)"],
      ["Resposta inventada pelo assistente", "Alta sem mitigação", "Alto", "Abstenção, citação obrigatória, conferência "
       "de cada frase e de seus números numa mesma fonte", "Comparação com e sem mitigação"],
      ["Orientação médica, jurídica ou financeira", "Média", "Alto", "Recusa fixa antes da busca, com indicação de "
       "profissional", "Teste por voz (seção 2.4)"],
      ["Exposição de dados pessoais", "Média", "Alto", "Anonimização antes do LLM e do banco; painel público agregado",
       "Testes automatizados de anonimização"],
      ["Viés territorial na priorização", "Média", "Alto", "Prioridade por risco, não por volume; equidade exigida no "
       "roteiro quântico", "Seções 2.7 e 2.8"],
      ["Falso positivo de fissura alarmar o cidadão", "Média", "Baixo", "Texto sem diagnóstico; decisão do técnico",
       "Tela de revisão da foto"],
      ["Indisponibilidade do LLM", "Alta (plano gratuito)", "Médio", "Mensagens claras, texto preservado, abstenção segura",
       "Testes de erro da API"]],
     FONTE_AUTORES, [3.6, 1.6, 1.4, 5, 4.4]),
    ("h3", "2.9.3 Privacidade e LGPD"),
    ("p", "O tratamento segue o princípio da necessidade da LGPD (BRASIL, 2018): o relato não exige identificação; CPF, "
          "telefone, e-mail, placas e nomes declarados são removidos antes do envio ao modelo e antes do armazenamento; o "
          "contato para retorno é opcional, só a equipe gestora o vê e o cidadão consente na tela de confirmação. Fotos e "
          "áudios são processados em memória e descartados. O painel público mostra apenas tipo, urgência, situação, bairro e "
          "localização aproximada. Quando o modelo é hospedado fora do Brasil, ocorre transferência internacional do texto "
          "anonimizado, o que precisa constar no aviso de privacidade de uma versão em produção, com relatório de impacto."),
    ("h3", "2.9.4 Indicadores e valor para o negócio"),
    ("quadro", "Indicadores propostos para acompanhar o Zela",
     ["Indicador", "Para quem", "Como é medido hoje"],
     [["Tempo até a triagem do relato", "Cidadão e gestão", "Latência registrada por análise (24 a 33 s com modelo local)"],
      ["Taxa de correção da IA pelo cidadão", "Equipe de IA", "Campo de correção na confirmação; painel do gestor"],
      ["Avaliação de utilidade", "Gestão", "Botão útil/não útil por solicitação"],
      ["Respostas com fonte x abstenções", "Equipe de IA", "Campos do Assistente; relatório de avaliação"],
      ["OS aplicadas pelo robô x enviadas à revisão", "Subprefeitura", "Relatório de cada execução do robô"],
      ["Tempo para esvaziar a fila no pico", "Infraestrutura", "Estudo no iSPD (seção 2.7)"]],
     FONTE_AUTORES, [5.5, 3.2, 7.3]),
    ("p", "O modelo de negócio pensado é a contratação por prefeituras (B2G), por meio do Contrato Público para Solução "
          "Inovadora previsto no Marco Legal das Startups (BRASIL, 2021), que permite testar a solução por tempo limitado antes "
          "de uma contratação maior. O custo variável principal é o processamento do modelo de linguagem: com o modelo local, "
          "cerca de 30 segundos de CPU por relato; com provedores em nuvem, o custo passa a ser por token e deve ser comparado "
          "com o tempo de atendimento humano que a triagem economiza."),
    ("h3", "2.9.5 O que foi e o que não foi integrado"),
    ("quadro", "Situação de integração de cada disciplina",
     ["Disciplina", "Módulo", "Integração com o Zela", "Evidência"],
     [["Front End & Mobile", "Interface e API", "Integrado (núcleo)", "frontend/, backend/"],
      ["Visão Computacional", "Fissuras", "Integrado: relato com foto, triagem, gestor e robô", "backend/tests/test_inteligencia.py"],
      ["Generative AI", "Assistente RAG", "Integrado: aba \"Tire dúvidas\" e uso do protocolo", "avaliacao/genai/"],
      ["NLP", "Assistente de voz", "Integrado pela API do assistente; aplicativo separado", "assistente_voz/"],
      ["NLP", "Ferramenta de corpus", "Separada; usa as fontes do assistente como exemplo", "corpus_pln/"],
      ["AI for RPA", "Robô Zela", "Integrado pela API do gestor", "robo_rpa/evidencias/"],
      ["Cluster Computing", "Estudo no iSPD", "Não roda no Zela; usa medições do Zela", "cluster/"],
      ["Computação Quântica", "Roteiro", "Não integrado em código; proposta de evolução", "docs/relatorios/quantica.md"],
      ["Cognitive IoT", "OuviAí", "Não integrado; evolução proposta (sirene)", "iot_ouviai/"]],
     FONTE_AUTORES, [3.4, 3, 5.6, 4]),
    ("p", "Três partes ficaram fora do código do Zela por decisão consciente: o estudo de cluster é uma análise de capacidade, "
          "não um componente em execução; o roteiro quântico depende de hardware que ainda não resolve instâncias reais; e o "
          "OuviAí roda isolado no celular para que nenhum áudio da casa do usuário saia do aparelho."),

    ("h1", "3 CONCLUSÃO"),
    ("p", 'O Zela partiu de uma dificuldade comum na zeladoria urbana. O morador sabe dizer que um bueiro transbordou ou que há uma fissura em um muro, mas nem sempre sabe a quem recorrer ou como descrever o risco. A equipe gestora, por sua vez, precisa decidir quais ocorrências atender primeiro. O protótipo reuniu essas duas perspectivas em um fluxo no qual o cidadão relata o problema com suas palavras, confere a classificação sugerida pela IA e recebe um protocolo que permite acompanhar a solicitação.'),
    ("p", 'Nos testes, a revisão das instruções e o tratamento do texto de entrada elevaram os acertos da triagem de 3 para 8 nos mesmos 10 casos. O assistente respondeu corretamente e citou a fonte em 10 das 11 perguntas que podiam ser respondidas com a documentação. A análise de fotos, o assistente por texto e voz e o robô que atualiza as ordens de serviço foram integrados ao atendimento. O cluster serviu para simular filas após temporais, a otimização quântica ficou como proposta para o despacho de equipes e o OuviAí permaneceu no celular para preservar a privacidade do áudio.'),
    ("p", 'Ao integrar as disciplinas, aprendi que governar a IA exige definir quando ela pode responder, quem pode corrigir sua decisão e como reconstruir o que aconteceu. Em um teste por voz, o assistente deu orientação médica com base em uma página sobre chuvas. Essa falha levou à criação de uma regra de recusa antes da busca. No Zela, o assistente deve se abster quando falta evidência, as regras de segurança só podem elevar a urgência e o histórico preserva tanto a sugestão original quanto a classificação confirmada pelo cidadão.'),
    ("p", 'O próximo passo é testar o fluxo com moradores e equipes de campo. Comparar o tempo de triagem e examinar os casos que exigem correção permitirá avaliar se o Zela reduz o retrabalho e ajuda as ocorrências urgentes a chegar mais cedo à equipe responsável.'),

    ("h1", "4 LINKS", False),
    ("itens", ["Vídeo integrador (YouTube, não listado): https://youtu.be/WPcYaI7U0ww",
               "Repositório no GitHub: https://github.com/guialmeida2702/zela-gs-2026-2",
               "Vídeos de cada disciplina: tabela no início do README do repositório"]),
]

referencias = [
    "BRASIL. **Lei nº 13.709, de 14 de agosto de 2018**. Lei Geral de Proteção de Dados Pessoais (LGPD). Brasília, DF: "
    "Presidência da República, 2018. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm. "
    "Acesso em: 12 nov. 2026.",
    "BRASIL. **Lei Complementar nº 182, de 1º de junho de 2021**. Institui o marco legal das startups e do "
    "empreendedorismo inovador. Brasília, DF: Presidência da República, 2021. Disponível em: "
    "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp182.htm. Acesso em: 12 nov. 2026.",
    "CORMACK, G. V.; CLARKE, C. L. A.; BUETTCHER, S. Reciprocal rank fusion outperforms Condorcet and individual rank "
    "learning methods. *In*: SIGIR, 32., 2009, Boston. **Proceedings** [...]. New York: ACM, 2009. p. 758-759.",
    "HOWARD, A. *et al*. Searching for MobileNetV3. *In*: IEEE/CVF INTERNATIONAL CONFERENCE ON COMPUTER VISION, 2019, Seul. "
    "**Proceedings** [...]. Piscataway: IEEE, 2019. p. 1314-1324.",
    "LEWIS, P. *et al*. Retrieval-augmented generation for knowledge-intensive NLP tasks. *In*: ADVANCES IN NEURAL "
    "INFORMATION PROCESSING SYSTEMS, 33., 2020. **Proceedings** [...]. 2020. p. 9459-9474.",
    "MANACERO, A. *et al*. iSPD: an iconic-based modeling simulator for distributed grids. *In*: ANNUAL SIMULATION "
    "SYMPOSIUM, 45., 2012. **Proceedings** [...]. San Diego: SCS, 2012. p. 40-47.",
    "NATIONAL INSTITUTE OF STANDARDS AND TECHNOLOGY (NIST). **FIPS 203**: Module-Lattice-Based Key-Encapsulation Mechanism "
    "Standard. Gaithersburg: NIST, 2024. Disponível em: https://csrc.nist.gov/pubs/fips/203/final. Acesso em: 12 nov. 2026.",
    "ÖZGENEL, Ç. F. **Concrete Crack Images for Classification**. Mendeley Data, v. 2, 2019. Disponível em: "
    "https://data.mendeley.com/datasets/5y9wdsg2zt/2. Acesso em: 12 nov. 2026.",
    "RADFORD, A. *et al*. **Robust speech recognition via large-scale weak supervision**. arXiv:2212.04356, 2022.",
    "SÃO PAULO (Município). Secretaria Municipal de Inovação e Tecnologia. **Perguntas frequentes sobre os canais SP156**. "
    "São Paulo, [20--]. Disponível em: https://prefeitura.sp.gov.br/web/inovacao/w/acesso_a_informacao/350229. Acesso em: "
    "12 nov. 2026.",
]

TRABALHO = Trabalho(
    instituicao="FIAP – Faculdade de Informática e Administração Paulista",
    curso="Curso Superior de Tecnologia em Inteligência Artificial",
    autores=AUTORES,
    titulo="Zela: zeladoria urbana com inteligência artificial",
    subtitulo="Documentação integrada da Global Solution 2026.2",
    natureza=("Documentação apresentada à disciplina de Governança em IA & Business Analysis da FIAP, como parte da "
              "Global Solution 2026.2 da turma 2TIAPY, integrando as entregas das disciplinas do semestre."),
    local="São Paulo",
    ano="2026",
    blocos=blocos,
    referencias=referencias,
)

if __name__ == "__main__":
    docx = AQUI / "Zela_documentacao_integrada.docx"
    pdf = gerar(TRABALHO, docx, AQUI)
    print(docx, pdf)
