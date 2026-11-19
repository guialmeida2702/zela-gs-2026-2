"""Reaplica a conferência por frase (uma fonte por frase, palavras e números) às respostas já registradas nas
rodadas de avaliação, sem chamar o LLM. Serve para mostrar que a regra nova só retira conteúdo sem apoio.

Uso: python scripts/experimentos/reconferir_respostas.py > ../avaliacao/genai/reconferencia_rodadas.txt
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from app.pipelines.assistente import _ABSTENCAO_DO_MODELO, AVISO_EMERGENCIA, Assistente  # noqa: E402
from app.pipelines.conhecimento import construir_trechos  # noqa: E402
from app.providers.busca import normalizar  # noqa: E402

GENAI = RAIZ.parent / "avaliacao" / "genai"
# As rodadas 1 a 3 usaram outra divisão em trechos: os mesmos identificadores apontam hoje para textos diferentes,
# então só as rodadas feitas com a divisão atual podem ser reconferidas com fidelidade.
RODADAS = ("resultados_rodada4.json", "resultados_rodada5.json")


def main() -> None:
    por_id = {t.id: t for t in construir_trechos()}
    total = alteradas = 0
    print("Rodadas reconferidas (mesma divisão em trechos do código atual): " + ", ".join(RODADAS) + "\n")
    for arquivo in (GENAI / nome for nome in RODADAS):
        for x in json.loads(arquivo.read_text(encoding="utf-8")).get("ponta_a_ponta", []):
            if x["sem_evidencia"] or x["fora_do_escopo"] or not x["citacoes"]:
                continue
            fontes = [por_id[i] for i in x.get("trechos_recuperados") or [] if i in por_id]
            if not fontes:
                continue
            total += 1
            # a orientação de emergência é acrescentada pelo código depois da conferência
            resposta = x["resposta"].replace(AVISO_EMERGENCIA, "").strip()
            if _ABSTENCAO_DO_MODELO.search(normalizar(resposta)) and len(resposta) <= 220:
                alteradas += 1
                print(f"{arquivo.name} {x['q']}: abstenção escrita pelo modelo vira o texto padrão\n   R: {resposta[:140]}")
                continue
            conferencia = [c for c in Assistente.apoio_por_frase(resposta, fontes) if c["avaliada"]]
            sem_apoio = [c for c in conferencia if c["fonte"] is None]
            if not sem_apoio:
                continue
            alteradas += 1
            sustentacao = 1 - len(sem_apoio) / len(conferencia)
            acao = "vira abstenção" if sustentacao < 0.5 else f"{len(sem_apoio)} frase(s) retirada(s)"
            print(f"{arquivo.name} {x['q']} (critério automático: {'ok' if x['ok'] else 'falha'}): {acao}")
            for c in sem_apoio:
                print(f"   [{c['motivo']}] {c['frase'][:160]}")
    print(f"\n{alteradas} de {total} respostas entregues mudariam com a conferência por frase.")


if __name__ == "__main__":
    main()
