"""Reproduz turnos do teste de voz que viraram abstenção e mostra a resposta crua do modelo e a conferência por frase.

Serve para separar abstenção causada pela proteção (resposta inventada barrada) de abstenção que barrou uma resposta
certa. A saída do modelo varia entre execuções, então o resultado é um exemplo, não uma medida.

Uso (com o modelo local no ar e as variáveis LLM_* definidas):
    python scripts/experimentos/reproduzir_abstencoes_voz.py > ../assistente_voz/avaliacao/resultados/reproducao_abstencoes.txt
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.config import get_settings
from app.pipelines.assistente import SYSTEM_ASSISTENTE, Assistente
from app.pipelines.conhecimento import construir_trechos
from app.providers.busca import IndiceBusca
from app.providers.llm import criar_provedor_llm
from app.schemas.assistente import PerguntaAssistente, SaidaLLMAssistente

llm = criar_provedor_llm(get_settings())
a = Assistente(llm, IndiceBusca(construir_trechos(), modo="hibrido", cache_modelos=os.getenv("MODELOS_CACHE_DIR")))
CASOS = [
  ("C8T1", [], "A tampa do boeiro fundou na minha rua."),
  ("C1T3", [("Como eu peço a poda de uma árvore na calçada?", "Pelo 156."), ("E quanto tempo demora?", "Até 120 dias.")],
   "E se não fizerem nesse prazo."),
  ("C4T2", [("Tenho um fio caído soltando faísca na calçada.", "Afaste-se e ligue 193.")], "Para qual número ligo?"),
  ("C5T2", [("Tem água limpa vazando no meio da rua.", "Evite o contato com a água.")], "Qual é o telefone deles?"),
  ("D09", [], "depois da enchente posso beber a água da torneira"),
]
async def main(sel):
    for cid, hist, q in CASOS:
        if sel and cid not in sel:
            continue
        h = []
        for u, r in hist:
            h += [{"papel": "cidadao", "texto": u}, {"papel": "assistente", "texto": r}]
        ent = PerguntaAssistente(pergunta=q, historico=h)
        consulta = a.consulta_de_busca(q, ent.historico)
        anterior = [m.texto for m in ent.historico if m.papel == "cidadao"]
        res = a._buscar(q, consulta, anterior[-1] if anterior else "")
        fontes = [r.trecho for r in res]
        usuario = (f"HISTÓRICO DA CONVERSA:\n{a._historico_texto(ent.historico)}\n\nFONTES:\n{a._bloco_fontes(fontes)}\n\n"
                   f"PERGUNTA: <pergunta>{q}</pergunta>\n\nResponda apenas com o JSON.")
        s = await llm.gerar_estruturado(SYSTEM_ASSISTENTE, usuario, SaidaLLMAssistente)
        print(f"\n== {cid} | consulta: {consulta} | trechos: {[t.id for t in fontes]}")
        print("MODELO:", s.resposta, s.citacoes, "sem_ev=", s.sem_evidencia)
        for c in a.apoio_por_frase(s.resposta, fontes, tuple(s.citacoes)):
            print(f"   fonte={c['fonte']} motivo={c['motivo']} | {c['frase'][:160]}")
asyncio.run(main(set(sys.argv[1:])))
