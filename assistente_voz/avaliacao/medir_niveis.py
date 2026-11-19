"""Mede o volume e o ruído de fundo de cada gravação, para interpretar o WER (volume baixo e ruído pioram a transcrição).

Para cada áudio: volume médio (RMS em dBFS), piso de ruído (RMS dos 10% de trechos de 50 ms mais silenciosos) e uma
estimativa da relação sinal-ruído (trechos 10% mais altos menos o piso). Resume por locutor e por condição.

Uso (na pasta assistente_voz):
  python avaliacao/medir_niveis.py --pasta avaliacao/audios_reais
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from voz.stt import TAXA, carregar_audio  # noqa: E402

AQUI = Path(__file__).parent
QUADRO = int(0.05 * TAXA)


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-9)))


def medir(caminho: Path) -> dict:
    sinal = carregar_audio(caminho)  # mesmo carregamento do STT (ffmpeg para m4a), 16 kHz mono
    n = len(sinal) // QUADRO
    quadros = sinal[: n * QUADRO].reshape(n, QUADRO)
    rms = np.sqrt((quadros ** 2).mean(axis=1))
    piso, alto = np.percentile(rms, 10), np.percentile(rms, 90)
    return {"duracao_s": round(len(sinal) / TAXA, 2), "volume_dbfs": round(db(float(np.sqrt((sinal ** 2).mean()))), 1),
            "piso_ruido_dbfs": round(db(float(piso)), 1), "snr_db": round(db(float(alto)) - db(float(piso)), 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default=str(AQUI / "audios_reais"))
    pasta = Path(ap.parse_args().pasta)
    with open(pasta / "manifesto.csv", encoding="utf-8") as f:
        itens = [r for r in csv.DictReader(f, delimiter=";") if r.get("arquivo")]
    por_audio = []
    for r in itens:
        m = medir(pasta / r["arquivo"])
        por_audio.append({"arquivo": r["arquivo"], "locutor": r["locutor"], "condicao": r["condicao"], **m})
        print(f'{r["arquivo"]:<16} volume {m["volume_dbfs"]:>6} dBFS  piso {m["piso_ruido_dbfs"]:>6} dBFS  SNR {m["snr_db"]:>5} dB')

    def resumo(campo: str) -> dict:
        grupos: dict[str, list[dict]] = {}
        for x in por_audio:
            grupos.setdefault(x[campo], []).append(x)
        return {g: {k: round(float(np.median([x[k] for x in xs])), 1) for k in ("volume_dbfs", "piso_ruido_dbfs", "snr_db")}
                | {"audios": len(xs)} for g, xs in sorted(grupos.items())}

    saida = AQUI / "resultados" / f"niveis_{pasta.name}.json"
    saida.write_text(json.dumps({"por_locutor": resumo("locutor"), "por_condicao": resumo("condicao"), "por_audio": por_audio},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(saida)


if __name__ == "__main__":
    main()
