"""Lê os resultados medidos de cada módulo (arquivos gerados pelos scripts de avaliação) para os documentos.

Quando um resultado ainda não existe, devolve "[a medir]" para o autor perceber e completar.
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FALTA = "[a medir]"


def _json(caminho: str):
    p = RAIZ / caminho
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _br(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def genai() -> dict:
    d = _json("avaliacao/genai/resultados.json")
    if not d or "ponta_a_ponta" not in d:
        return {}
    e2e = d["ponta_a_ponta"]

    def conta(tipo):
        sel = [x for x in e2e if x["tipo"] == tipo]
        return f"{sum(x['ok'] for x in sel)}/{len(sel)}"

    ger = d.get("gerador", [])
    correto = [g for g in ger if g["cenario"] == "contexto_correto"]
    irrelevante = [g for g in ger if g["cenario"] == "contexto_irrelevante"]
    seg = d.get("seguranca", [])
    sem = d.get("sem_mitigacao", [])
    rec = d["recuperacao"]
    lat = [x["segundos"] for x in e2e if not x["sem_evidencia"]]
    return {
        "modelo": d["modelo"], "data": d["data"],
        "respondiveis": conta("respondivel"), "sem_resposta": conta("sem_resposta"), "ambiguas": conta("ambigua"),
        "fora_escopo": conta("fora_do_escopo"), "conversa": conta("conversa"),
        "total_ok": f"{sum(x['ok'] for x in e2e)}/{len(e2e)}",
        "gerador_correto": f"{sum(g['correto'] for g in correto)}/{len(correto)}",
        "gerador_irrelevante_absteve": f"{sum(g['sem_evidencia'] for g in irrelevante)}/{len(irrelevante)}",
        "seguranca": f"{sum(x['ok'] for x in seg)}/{len(seg)}",
        "sem_mitigacao_respondeu": f"{sum(x['respondeu_sem_fonte'] for x in sem)}/{len(sem)}",
        "hit1_estrutura_hibrido": f"{round(100 * rec['estrutura_700_120|hibrido']['hit@1'])}%",
        "hit1_fixo_bm25": f"{round(100 * rec['fixo_400|bm25']['hit@1'])}%",
        "hit1_fixo_denso": f"{round(100 * rec['fixo_400|denso']['hit@1'])}%",
        "mrr_fixo_denso": _br(rec["fixo_400|denso"]["mrr"], 2),
        "latencia_media_s": _br(sum(lat) / len(lat)) if lat else FALTA,
        "erros_infra": sum(any(b.startswith("erro_") for b in x["bloqueios"]) for x in e2e),
    }


def pln() -> dict:
    out: dict = {}
    stt = _json("assistente_voz/avaliacao/resultados/stt_audios_sinteticos.json")
    if stt:
        out |= {"wer_small": _br(100 * stt["small"]["wer_geral"]), "wer_tiny": _br(100 * stt["tiny"]["wer_geral"]),
                "wer_small_vocab": _br(100 * stt["small+vocab"]["wer_geral"]) if "small+vocab" in stt else FALTA,
                "rtf_small": _br(stt["small"]["fator_tempo_real"], 2), "rtf_tiny": _br(stt["tiny"]["fator_tempo_real"], 2)}
    reais = _json("assistente_voz/avaliacao/resultados/stt_audios_reais.json")
    if reais:
        opcao = "small+vocab" if "small+vocab" in reais else "small"
        out |= {"wer_reais": _br(100 * reais[opcao]["wer_geral"])}
        if {"tiny", "small"} <= reais.keys():
            out |= {"wer_reais_tiny": _br(100 * reais["tiny"]["wer_geral"]), "wer_reais_small": _br(100 * reais["small"]["wer_geral"])}
    llm = _json("assistente_voz/avaliacao/resultados/llm_30_perguntas.json")
    if llm:
        out |= {"llm_corretas": _br(llm["pct_corretas_total"]), "llm_recusas": _br(llm["pct_recusas_adequadas"]),
                "llm_continuacao": _br(llm["pct_corretas_continuacao"]), "llm_latencia": _br(llm["latencia_media_s"])}
    e2e = _json("assistente_voz/avaliacao/resultados/e2e_10_conversas.json")
    if e2e:
        lat = e2e["latencia_s"]
        out |= {"e2e_adequados": _br(e2e["pct_turnos_adequados"]), "e2e_total_mediana": _br(lat["ate_inicio_da_fala_s"]["mediana"]),
                "e2e_stt": _br(lat["stt_s"]["mediana"]), "e2e_llm": _br(lat["llm_s"]["mediana"]), "e2e_tts": _br(lat["tts_s"]["mediana"])}
    tts = _json("assistente_voz/avaliacao/resultados/tts_latencia.json")
    if tts:
        out |= {"tts_rtf_faber": _br(tts["faber"]["fator_tempo_real_medio"], 2)}
    notas = _json("assistente_voz/avaliacao/resultados/tts_notas_resumo.json")
    if notas and "faber" in notas:
        out |= {"tts_nat": _br(notas["faber"]["naturalidade_media"], 2), "tts_cla": _br(notas["faber"]["clareza_media"], 2)}
    return out


def cluster() -> list[dict]:
    return _json("cluster/resultados/comparacao.json") or []


def m(d: dict, chave: str) -> str:
    return str(d.get(chave, FALTA))
