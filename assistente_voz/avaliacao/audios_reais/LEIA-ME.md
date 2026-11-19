# Gravações reais para o teste de STT

O enunciado pede 20 áudios gravados por pessoas, com pelo menos 3 vozes diferentes e 5 com ruído de fundo.

1. Peça a pelo menos mais duas pessoas (além de você) para participar. Explique para que serve a gravação e peça o consentimento de cada uma; as vozes ficam só neste repositório de teste.
2. Cada pessoa lê frases de `../frases_stt.csv` (são 20; divida entre as vozes, por exemplo 7, 7 e 6). As frases S16 a S20 devem ser gravadas com ruído de fundo (TV, rua, ventilador).
3. Salve cada gravação nesta pasta, em WAV, MP3 ou M4A, com um nome como `S01_guilherme.wav`.
4. Preencha o `manifesto.csv`, uma linha por áudio:

| Coluna | Como preencher |
|---|---|
| `arquivo` | nome do arquivo nesta pasta |
| `id` | código da frase lida (S01 a S20) |
| `locutor` | um apelido por pessoa (voz1, voz2, voz3) |
| `condicao` | `silencioso` ou `ruido` |
| `genero`, `faixa_etaria`, `sotaque` | opcionais, usados na análise de viés (ex.: `feminino`, `60+`, `paulistano`). Deixe em branco se a pessoa preferir não informar |

Exemplo de linha: `S01_voz1.wav;S01;voz1;silencioso;masculino;18-29;paulistano`

5. Rode `python avaliacao/avaliar_stt.py --pasta avaliacao/audios_reais` e depois `python avaliacao/gerar_relatorio.py`.
