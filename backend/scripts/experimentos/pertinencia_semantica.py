"""Experimento descartado: o cosseno entre a pergunta e o trecho citado separa respostas certas de erradas?

Compara pares certos (pergunta x trecho que tem a resposta) com os pares errados vistos na avaliação
(resposta do poço de visita copiada para as perguntas do semáforo e do buraco). Resultado salvo em
avaliacao/genai/pertinencia_semantica.txt e discutido no relatório (seção 4.1).

Uso: python scripts/experimentos/pertinencia_semantica.py > ../avaliacao/genai/pertinencia_semantica.txt
"""

import importlib.util
import os
import sys
import unicodedata
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from app.pipelines.conhecimento import construir_trechos  # noqa: E402
from app.providers.busca import IndiceBusca  # noqa: E402

spec = importlib.util.spec_from_file_location("av", RAIZ / "scripts" / "avaliar_assistente.py")
av = importlib.util.module_from_spec(spec)
spec.loader.exec_module(av)


def norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def main() -> None:
    trechos = construir_trechos()
    indice = IndiceBusca(trechos, modo="hibrido", cache_modelos=os.getenv("MODELOS_CACHE_DIR"))
    posicao = {t.id: i for i, t in enumerate(trechos)}

    def cos(pergunta: str, ids: list[str]) -> float:
        v = indice._normalizar(np.array(list(indice.modelo.embed([pergunta]))))[0]
        return max(float(indice.matriz[posicao[i]] @ v) for i in ids)

    print("== pares certos (pergunta x trecho que contém a resposta)")
    certos = []
    for qid, pergunta, doc, chaves in av.RESPONDIVEIS:
        ouro = [t.id for t in trechos if t.doc_id == doc and any(norm(k) in norm(t.texto) for k in chaves)]
        certos.append(cos(pergunta, ouro))
        print(f"{qid} {certos[-1]:.3f}")
    print("== pares errados (trecho do poço de visita citado na avaliação)")
    for nome, pergunta in (("A6 semáforo", "O semáforo da minha rua está com defeito, quem resolve?"),
                           ("U4 buraco", "Qual o prazo para a prefeitura tapar um buraco na rua?")):
        print(f"{nome} {cos(pergunta, ['faq-subprefeitura#5']):.3f}")
    print(f"menor cosseno entre os pares certos: {min(certos):.3f}")


if __name__ == "__main__":
    main()
