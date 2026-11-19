"""Experimento: uma verificação de pertinência mais branda que a testada (e descartada) na rodada 1.

Regra testada: se a pergunta tem termos específicos que existem na base (radicais presentes em até 25% dos
trechos), pelo menos UM deles precisa aparecer nos trechos citados. Senão, a resposta vira abstenção.

O teste roda sobre as respostas já registradas nas rodadas de avaliação (sem chamar o LLM) e mostra quais
respostas a regra bloquearia. Serve para decidir, com evidência, se a regra pode ser adotada.

Uso: python scripts/experimentos/pertinencia_termo_especifico.py > ../avaliacao/genai/pertinencia_termo_especifico.txt
(MODELOS_CACHE_DIR, se definido, indica onde está o modelo de embeddings.)
"""

import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from app.pipelines.conhecimento import Trecho, construir_trechos  # noqa: E402
from app.providers.busca import tokenizar  # noqa: E402

GENAI = RAIZ.parent / "avaliacao" / "genai"
VOZ = RAIZ.parent / "assistente_voz" / "avaliacao" / "perguntas_llm.json"
# Palavras que aparecem em perguntas sobre qualquer assunto: não servem para dizer do que a pergunta trata
GENERICOS = {"rua", "ruas", "casa", "casas", "bairro", "cidade", "prefeitura", "subprefeitura", "problema", "frente",
             "aqui", "ali", "agora", "hoje", "ta", "to", "tem", "minha", "meu", "quanto", "tempo", "fazer", "faco",
             "preciso", "posso", "pode", "devo", "quero", "resolve", "resolver", "ajuda", "local", "lugar", "pessoa"}


def termos_especificos_da_base(trechos: list[Trecho], fracao_maxima: float = 0.17) -> set[str]:
    """Radicais que aparecem em poucos trechos (até 17%, 8 dos 48): são os que dizem do que um trecho trata."""
    contagem: dict[str, int] = {}
    for t in trechos:
        for termo in set(tokenizar(t.texto_indexado)):
            contagem[termo] = contagem.get(termo, 0) + 1
    limite = max(1, int(len(trechos) * fracao_maxima))
    return {termo for termo, n in contagem.items() if n <= limite} - GENERICOS


def fonte_trata_da_pergunta(consulta: str, fontes_citadas: list[Trecho], especificos: set[str]) -> tuple[bool, list[str]]:
    """Pelo menos um termo específico da pergunta precisa estar nas fontes citadas."""
    termos = sorted({termo for termo in tokenizar(consulta) if termo in especificos})
    if not termos:
        return True, []
    vocab = set(tokenizar(" ".join(t.texto_indexado for t in fontes_citadas)))
    return any(termo in vocab for termo in termos), termos


def main() -> None:
    trechos = construir_trechos()
    por_id = {t.id: t for t in trechos}
    especificos = termos_especificos_da_base(trechos)
    total = bloqueadas = 0
    for arquivo in sorted(GENAI.glob("resultados*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for chave in ("ponta_a_ponta", "ponta_a_ponta_antes_das_salvaguardas"):
            for x in dados.get(chave, []):
                if x["sem_evidencia"] or x["fora_do_escopo"] or not x["citacoes"]:
                    continue
                # o registro guarda os títulos citados; os trechos citados são os recuperados com esses títulos
                citados = [por_id[i] for i in x["trechos_recuperados"] or [] if i in por_id and por_id[i].titulo in x["citacoes"]]
                if not citados:
                    continue
                total += 1
                pertinente, termos = fonte_trata_da_pergunta(x["consulta_usada"], citados, especificos)
                if not pertinente:
                    bloqueadas += 1
                    print(f"BLOQUEARIA {arquivo.name} {x['q']} (automático: {'ok' if x['ok'] else 'falha'}) termos={termos}\n"
                          f"   P: {x['pergunta']}\n   R: {x['resposta'][:140]}")
    print(f"\n{bloqueadas} de {total} respostas entregues seriam bloqueadas.")
    risco_nas_perguntas_de_voz(trechos, especificos)


def risco_nas_perguntas_de_voz(trechos: list[Trecho], especificos: set[str]) -> None:
    """Segunda parte: nas perguntas respondíveis do teste de voz, o trecho que traz a resposta passaria na regra?
    Usa só a busca (sem LLM): se o trecho certo não contém nenhum termo específico da pergunta, a regra barraria
    a resposta correta."""
    import unicodedata

    from app.pipelines.assistente import Assistente
    from app.providers.busca import IndiceBusca
    from app.schemas.assistente import PerguntaAssistente

    def norm(texto: str) -> str:
        return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()

    # mesma busca do produto (híbrida); MODELOS_CACHE_DIR aponta para o modelo de embeddings já baixado
    assistente = Assistente(None, IndiceBusca(trechos, modo="hibrido", cache_modelos=os.getenv("MODELOS_CACHE_DIR")))
    perguntas = [p for p in json.loads(VOZ.read_text(encoding="utf-8"))["perguntas"] if p["tipo"] != "fora_do_escopo"]
    avaliadas = em_risco = 0
    print("\nPerguntas respondíveis do teste de voz em que a regra barraria o trecho que traz a resposta:")
    for p in perguntas:
        entrada = PerguntaAssistente(pergunta=p["pergunta"], historico=p.get("historico", []))
        consulta = assistente.consulta_de_busca(entrada.pergunta, entrada.historico)
        certos = [r.trecho for r in assistente._buscar(entrada.pergunta, consulta)
                  if any(norm(chave) in norm(r.trecho.texto) for chave in p["esperado"])]
        if not certos:
            continue
        avaliadas += 1
        if not all(fonte_trata_da_pergunta(consulta, [t], especificos)[0] for t in certos):
            em_risco += 1
            termos = fonte_trata_da_pergunta(consulta, certos[:1], especificos)[1]
            print(f"  {p['id']}: {p['pergunta']} (termos específicos da pergunta: {termos})")
    print(f"{em_risco} de {avaliadas} perguntas com o trecho certo recuperado teriam a resposta correta barrada.")


if __name__ == "__main__":
    main()
