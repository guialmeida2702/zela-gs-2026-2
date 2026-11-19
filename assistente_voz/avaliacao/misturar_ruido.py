"""Teste de estresse: mistura o mesmo ruído de rua dos áudios sintéticos (10 dB de SNR) nas 20 gravações reais.

Por que existe: nas gravações reais feitas com a TV ou o ventilador ligados, o piso de ruído medido ficou igual ao das
gravações silenciosas (o gravador do celular reduz ruído). Misturar um ruído controlado mede o STT com vozes reais em
condição ruim, com o mesmo método da linha de base sintética.

Os áudios gerados ficam fora do repositório (.gitignore), porque são derivados das vozes reais; o script os recria.
Uso (na pasta assistente_voz):
  python avaliacao/misturar_ruido.py
  python avaliacao/avaliar_stt.py --pasta avaliacao/audios_reais_ruido10db --opcoes small,small+vocab
"""

import csv
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from avaliacao.gerar_audios_sinteticos import SNR_DB, _ruido_rua  # noqa: E402
from voz.stt import TAXA, carregar_audio  # noqa: E402

ORIGEM = AQUI / "audios_reais"
SAIDA = AQUI / "audios_reais_ruido10db"


def main() -> None:
    SAIDA.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    with open(ORIGEM / "manifesto.csv", encoding="utf-8") as f:
        itens = [r for r in csv.DictReader(f, delimiter=";") if r.get("arquivo")]
    linhas = []
    for r in itens:
        sinal = carregar_audio(ORIGEM / r["arquivo"]).astype(np.float64)
        ruido = _ruido_rua(len(sinal), rng, TAXA)
        ruido *= np.sqrt(np.mean(sinal ** 2) / (10 ** (SNR_DB / 10)))  # mesmo cálculo da linha de base sintética
        misturado = sinal + ruido
        misturado = 0.9 * misturado / max(1e-6, np.max(np.abs(misturado)))
        nome = Path(r["arquivo"]).stem + ".wav"
        sf.write(SAIDA / nome, misturado.astype(np.float32), TAXA, subtype="PCM_16")
        linhas.append({**r, "arquivo": nome, "condicao": "ruido_10db"})
    with open(SAIDA / "manifesto.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} áudios em {SAIDA}")


if __name__ == "__main__":
    main()
