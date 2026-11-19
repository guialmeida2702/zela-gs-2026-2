# Validação com pessoas do público-alvo

> **Importante:** este documento é o **roteiro** e a **ficha** do teste. Os resultados precisam vir de sessões
> reais com pelo menos 3 pessoas (exigência 3.8a). Não preencha com dados inventados: a banca pede evidência real,
> e o vídeo deve mostrar esse material.

## 1. Quem convidar (mínimo 3, ideal 5)

| Perfil | Por que importa | Exemplo |
|---|---|---|
| Pessoa 60+ ou com pouca familiaridade digital | Testa linguagem simples e tamanho do texto | Avó, vizinho, porteiro |
| Pessoa com deficiência ou mobilidade reduzida (ou quem convive com uma) | Testa acessibilidade e o caso “calçada” | Usuário de cadeira de rodas, pessoa com baixa visão |
| Morador(a) de área sujeita a alagamento | Testa urgência, risco e orientação de segurança | Moradores de várzea/periferia |
| (Opcional) Servidor(a) público(a) ou síndico(a) | Testa a visão do gestor | Zelador, síndico, servidor de subprefeitura |

Peça consentimento verbal para observar e anotar (sem gravar o rosto, se a pessoa preferir). Não registre nome completo:
use P1, P2, P3…

## 2. Roteiro da sessão (≈ 15 min por pessoa)

1. **Contexto (1 min)** — “Estamos testando um site que ajuda a avisar a prefeitura sobre problemas da rua. Vamos
   avaliar o site, não você. Pense em voz alta.”
2. **Tarefa 1 — relatar (5 min)** — “Pense num problema real da sua rua ou bairro e registre pelo site.”
   Observe sem ajudar. Anote onde a pessoa hesita.
3. **Tarefa 2 — conferir (3 min)** — “A análise faz sentido? Mudaria algo antes de enviar?”
   Observe se ela entende “urgência”, “certeza da IA” e se encontra onde corrigir.
4. **Tarefa 3 — acompanhar (2 min)** — “Onde você veria se a prefeitura já resolveu?”
5. **Tarefa 4 — acessibilidade (2 min, opcional)** — ative alto contraste, aumente o texto e use “Ouvir em voz alta”.
6. **Perguntas finais (2 min)** — veja a seção 3.

## 3. Perguntas finais (escala de 1 = discordo totalmente a 5 = concordo totalmente)

| # | Afirmação |
|---|---|
| Q1 | Foi fácil descrever o problema. |
| Q2 | Entendi o que a IA respondeu. |
| Q3 | Confiei na classificação (tipo e urgência). |
| Q4 | Saberia corrigir a classificação se estivesse errada. |
| Q5 | Usaria isto em vez de ligar para o 156. |

Pergunta aberta: **“O que mais te atrapalhou?”** e **“O que você mudaria primeiro?”**

## 4. Ficha de observação (preencher uma linha por pessoa)

| Pessoa | Perfil | Concluiu a tarefa 1? | Tempo até o protocolo | Corrigiu a IA? | Dificuldades observadas | Q1 | Q2 | Q3 | Q4 | Q5 | Frase marcante |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | | | | | | | | | | | |
| P2 | | | | | | | | | | | |
| P3 | | | | | | | | | | | |
| P4 | | | | | | | | | | | |
| P5 | | | | | | | | | | | |

## 5. Síntese e ajuste realizado

- **Principais observações:** _(o que se repetiu entre as pessoas)_
- **Ajuste feito a partir do feedback:** _(o que mudou no código/tela, com o arquivo e o commit)_
- **Resultado após o ajuste:** _(se possível, teste de novo com 1 pessoa)_

### Pontos que vale observar (hipóteses de ajuste que o próprio projeto já prevê)
Use apenas se a observação **realmente** acontecer nos testes:
- Se pessoas não souberem o CEP → tornar o CEP opcional e usar só o ponto de referência (`features/relatar.py`, `validar_relato`).
- Se a palavra “urgência” confundir → trocar por “prioridade” nos selos (`ui/theme.py`, `URGENCIA[...]["nome"]`).
- Se “certeza da IA” gerar desconfiança → reescrever o texto do medidor (`ui/components.py`, `medidor_confianca`).
- Se o texto do resultado for longo → limitar orientações a 3 passos no prompt (`backend/app/pipelines/prompts.py`).
