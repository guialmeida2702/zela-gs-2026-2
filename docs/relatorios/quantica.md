---
title: "Zela · Programação Quântica: onde a computação quântica pode ajudar a zeladoria"
subtitle: "Global Solution 2026.2 · Análise de gargalo e roteiro"
author: "Guilherme Almeida (RM 563972)"
date: "Novembro de 2026"
lang: pt-BR
---

# 1. O gargalo real quando o número de cidadãos cresce

Os canais SP156 da Prefeitura de São Paulo recebem em média 157.120 solicitações por mês (média de 2022, segundo a Secretaria Municipal de Inovação e Tecnologia), e a execução da zeladoria é distribuída por 32 subprefeituras. A demanda também se concentra: num levantamento do portal Metrópoles com dados de transparência do 156, problemas com árvores foram cerca de 6 em cada 10 chamados à Defesa Civil municipal nos nove primeiros meses do ano, e temporais derrubam centenas de árvores de uma vez.

Para cada etapa do Zela, a pergunta foi o que quebra primeiro quando o volume multiplica:

| Etapa | Escala bem com computação clássica? | Evidência |
|---|---|---|
| Receber e registrar relatos | Sim | API sem estado, banco simples |
| Triagem por IA e análise de fotos | Sim, com mais máquinas | No estudo de cluster, dobrar os workers reduziu o tempo da fila em 50%, porque cada relato é independente (`docs/relatorios/cluster.md`) |
| **Decidir quais equipes atendem quais ocorrências, em que ordem** | **Não** | É um problema combinatório: o número de planos possíveis cresce de forma explosiva com o número de ocorrências e equipes |
| Proteger por décadas os dados dos cidadãos | Hoje sim, no futuro não | A criptografia de chave pública atual pode ser quebrada por computadores quânticos grandes; dados capturados hoje podem ser abertos depois |

O gargalo principal, então, não está em entender o relato, e sim em **despachar as equipes de campo**. Cada subprefeitura tem poucas equipes (poda, tapa-buraco, limpeza de bueiros) para centenas de ocorrências com urgências, prazos, locais e tipos de equipe diferentes. Escolher a melhor combinação é uma variação do problema de roteamento de veículos com janelas de tempo, que é NP-difícil: para 30 ocorrências e 3 equipes já existem mais combinações de ordem do que é possível testar uma a uma. Hoje esse planejamento costuma ser feito por regras simples (atender por ordem de chegada ou por região), o que deixa ocorrências urgentes esperando e faz caminhões cruzarem a cidade sem necessidade.

# 2. Capacidade quântica escolhida: otimização

A capacidade principal escolhida é a **otimização combinatória**, com a **criptografia pós-quântica (PQC)** como frente complementar obrigatória.

**Por que otimização.** O despacho das equipes pode ser escrito como um problema de otimização binária: variáveis do tipo "a equipe *e* atende a ocorrência *o* na posição *k* da rota", com custo que soma tempo de deslocamento e penalidades por atraso ponderadas pela urgência que o Zela já calcula (baixa, média, alta, crítica). Esse formato (QUBO) é o que algoritmos quânticos de otimização recebem:

- **Recozimento quântico** (*quantum annealing*), em que o hardware busca configurações de baixa energia do problema;
- **QAOA** (*Quantum Approximate Optimization Algorithm*), algoritmo híbrido para computadores quânticos de portas, em que um otimizador clássico ajusta os parâmetros de um circuito quântico.

**O que a pesquisa mostra hoje, sem exagero.** Os resultados ainda são de pequena escala. Um estudo de 2025 que executou QAOA em hardware real resolveu um roteamento de 3 locais e 2 veículos, mas uma instância de 4 locais gerou circuito de 14 qubits com milhares de portas, levou mais de 2 horas e não encontrou solução viável. Abordagens híbridas com recozimento quântico e reparo clássico chegaram a uma diferença média de 3,86% em relação ao ótimo em instâncias de teste, mas a viabilidade das soluções cai conforme o problema cresce. Outra linha decompõe o problema grande em subproblemas pequenos que cabem no hardware atual. Ou seja: a vantagem quântica para roteamento ainda não foi demonstrada em escala real, e o Zela não deve depender dela hoje.

**Por que PQC também.** Relatos têm localização, fotos e, às vezes, contato do cidadão. Um atacante pode copiar dados criptografados agora e decifrá-los quando houver computador quântico grande o bastante ("colher agora, decifrar depois"). Os algoritmos pós-quânticos padronizados pelo NIST em 2024 (ML-KEM para troca de chaves, FIPS 203; ML-DSA para assinatura, FIPS 204) rodam em computadores comuns e podem ser adotados já.

# 3. Roteiro: clássico hoje, quântico no futuro, benefício para o público

| Fase | O que o Zela faz | Tecnologia | Benefício para o cidadão |
|---|---|---|---|
| **Hoje (POC atual)** | A triagem dá a urgência e o órgão; o gestor vê a fila ordenada por prioridade | Regras e IA clássica | Casos com risco imediato aparecem primeiro |
| **Curto prazo (1 a 2 anos)** | Planejamento diário de rotas por subprefeitura, com urgência como peso e janela de tempo por categoria | Solvers clássicos de roteamento (por exemplo, OR-Tools) e heurísticas; formulação do problema já em QUBO, testada em simulador quântico | Menos tempo de espera para casos urgentes, menos quilômetros rodados |
| **Médio prazo (3 a 5 anos)** | Testes A/B em uma subprefeitura: plano clássico x plano híbrido (subproblemas pequenos resolvidos em hardware quântico via nuvem, com reparo clássico) | Recozimento quântico híbrido ou QAOA com decomposição | Só entra em produção se ganhar do clássico em custo, tempo e viabilidade, medido no mesmo conjunto de dias |
| **Longo prazo (mais de 5 anos)** | Replanejamento em tempo quase real da cidade inteira em eventos extremos (temporais, quedas de árvores em massa) | Computadores quânticos com correção de erros, se e quando estiverem disponíveis | Resposta coordenada entre subprefeituras, Defesa Civil e concessionárias |
| **Desde já, em paralelo** | Migração da criptografia para PQC (TLS híbrido e assinaturas pós-quânticas nos backups e na API) | ML-KEM e ML-DSA | Dados dos cidadãos protegidos também contra ataques futuros |

Critério para passar de uma fase a outra: a solução nova precisa ser **melhor que a clássica em métricas medidas** (tempo médio até o atendimento de casos críticos, quilômetros rodados, ocorrências fora do prazo) e não só "mais moderna".

# 4. Ética, LGPD e ODS ao longo do roteiro

- **Equidade.** Um otimizador que só minimiza quilômetros tende a favorecer regiões densas e centrais, onde as ocorrências ficam próximas. A função de custo precisa incluir equidade: limite de espera por bairro e peso maior para áreas com mais vulnerabilidade. Isso é escolha política e deve ser pública.
- **Supervisão humana.** O plano de rotas é uma sugestão. O gestor pode alterar a ordem, e a alteração fica registrada, como já acontece na revisão das solicitações no Zela.
- **LGPD (minimização e finalidade).** O roteamento precisa só de local aproximado, categoria, urgência e prazo. Nome, contato e foto do cidadão não entram no problema de otimização, e nada sai para provedores de computação quântica em nuvem além de coordenadas agregadas e pesos numéricos. Se a nuvem quântica estiver fora do Brasil, isso é transferência internacional e exige base legal.
- **Transparência.** O critério de prioridade e o peso de equidade devem ser publicados, para que o cidadão entenda por que um caso foi atendido antes de outro.
- **Segurança.** A migração para PQC protege a confidencialidade de longo prazo exigida pela LGPD (art. 46, medidas de segurança).
- **ODS.** ODS 11 (cidades sustentáveis: serviços urbanos mais rápidos e resilientes a eventos extremos), ODS 13 (menos quilômetros rodados, menos emissões), ODS 9 (infraestrutura e inovação) e ODS 16 (instituições eficazes e transparentes).

# Referências

- Prefeitura de São Paulo, SMIT. Perguntas frequentes SP156 (média de 157.120 solicitações por mês em 2022). <https://prefeitura.sp.gov.br/web/inovacao/w/acesso_a_informacao/350229>
- Metrópoles. Defesa Civil: 6 em cada 10 chamados são por causa de árvores em SP. <https://www.metropoles.com/sao-paulo/defesa-civil-chamados-arvores-sp>
- Quantum-Assisted Vehicle Routing: Realizing QAOA-based Approach on Gate-Based Quantum Computer (2025). <https://arxiv.org/abs/2505.01614>
- Advanced Quantum Annealing Approach to Vehicle Routing Problems with Time Windows (2025). <https://arxiv.org/abs/2503.24285>
- Solving Large-Scale Vehicle Routing Problems with Hybrid Quantum-Classical Decomposition (2025). <https://arxiv.org/abs/2507.05373>
- NIST. FIPS 203 (ML-KEM) e FIPS 204 (ML-DSA), 2024. <https://csrc.nist.gov/pubs/fips/203/final>
