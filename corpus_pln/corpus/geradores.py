"""Montagem dos três corpora a partir dos documentos limpos.

- texto puro: trechos de texto corrido, para adaptar o modelo ao vocabulário do domínio;
- perguntas e respostas: pares (pergunta, resposta), para ajuste por instrução;
- conversacional: diálogos com papéis (system, user, assistant), para ajuste de modelos de chat.

Cada exemplo guarda de onde veio (arquivo, seção e origem), para a rastreabilidade do corpus.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .leitura import Documento
from .limpeza import Bloco, OpcoesLimpeza, mascarar_dados_pessoais, normalizar_unicode

_INTERROGATIVOS = ("como", "o que", "quando", "onde", "quem", "qual", "quais", "por que", "quanto", "quantos", "posso",
                   "preciso", "devo", "pode", "existe", "há")
_FRASE = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\[\"'-])")
# Início de um item de perguntas frequentes escrito em texto corrido: "3 - Posso pedir...?" ou "3) ..."
_INICIO_ITEM_FAQ = re.compile(r"(?:(?<=\s)|^)\d{1,2}\s*[-.)]\s*(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])")
_SINAL_DE_PERGUNTA = re.compile(r"\b(como|quem|qual|quais|quando|onde|o que|que|quanto|quantos|por que|posso|pode|podem|devo|"
                                r"deve|preciso|precisa|existe|tem)\b", re.I)
_PREFIXO_RESPOSTA = re.compile(r"^(?:R|Resposta)\s*[:.-]\s*", re.I)
_PREFIXO_PERGUNTA = re.compile(r"^(?:\d{1,2}\s*[-.)]\s*)?(?:(?:P|Pergunta)\s*[:.-]\s*)?", re.I)

RECUSAS_PADRAO = (
    "Me indica um restaurante bom aqui perto?",
    "Qual remédio eu tomo para dor de cabeça?",
    "Quem vai ganhar o jogo de domingo?",
    "Você pode fazer a minha declaração de imposto de renda?",
    "Conta uma piada?",
)
SISTEMA_PADRAO = ("Você é um assistente que orienta cidadãos com base em documentos oficiais. Responda de forma curta e "
                  "clara, em português. Se a informação não estiver na sua base, diga que não sabe e indique o canal "
                  "oficial.")


@dataclass
class Secao:
    fonte: str
    titulo_doc: str
    caminho: str
    blocos: list[Bloco] = field(default_factory=list)

    @property
    def titulo(self) -> str:
        return self.caminho.split(" > ")[-1] if self.caminho else ""

    @property
    def texto(self) -> str:
        return "\n".join(("- " + b.texto) if b.tipo == "item" else b.texto for b in self.blocos)


def secoes(doc: Documento, blocos: list[Bloco]) -> list[Secao]:
    """Agrupa os blocos sob o título mais recente e guarda o caminho ("Título > Subtítulo")."""
    resultado: list[Secao] = []
    pilha: list[tuple[int, str]] = []
    atual = Secao(doc.nome, doc.titulo, "")
    for bloco in blocos:
        if bloco.tipo == "titulo":
            if atual.blocos:
                resultado.append(atual)
            while pilha and pilha[-1][0] >= bloco.nivel:
                pilha.pop()
            pilha.append((bloco.nivel, bloco.texto))
            atual = Secao(doc.nome, doc.titulo, " > ".join(t for _, t in pilha))
        else:
            atual.blocos.append(bloco)
    if atual.blocos:
        resultado.append(atual)
    return resultado


# ---------------------------------------------------------------- texto puro
def _partir(texto: str, limite: int) -> list[str]:
    """Divide um texto longo em partes de até `limite` caracteres, sempre em fim de frase."""
    if len(texto) <= limite:
        return [texto]
    partes, atual = [], ""
    for frase in _FRASE.split(texto):
        if atual and len(atual) + 1 + len(frase) > limite:
            partes.append(atual)
            atual = frase
        else:
            atual = f"{atual} {frase}".strip()
    if atual:
        partes.append(atual)
    return partes


def corpus_texto_puro(secoes_por_doc: dict[str, list[Secao]], tamanho: int = 1200) -> list[dict]:
    """Trechos de até `tamanho` caracteres, fechados em fim de seção, bloco ou frase."""
    exemplos = []
    for fonte, lista in secoes_por_doc.items():
        for secao in lista:
            cabecalho = f"{secao.titulo}\n" if secao.titulo else ""
            atual = cabecalho
            for bloco in secao.blocos:
                linha = ("- " + bloco.texto) if bloco.tipo == "item" else bloco.texto
                for parte in _partir(linha, tamanho - len(cabecalho)):
                    if len(atual) > len(cabecalho) and len(atual) + 1 + len(parte) > tamanho:
                        exemplos.append({"text": atual.strip(), "fonte": fonte, "secao": secao.caminho, "origem": "texto_limpo"})
                        atual = cabecalho
                    atual += parte + "\n"
            if atual.strip() and atual.strip() != cabecalho.strip():
                exemplos.append({"text": atual.strip(), "fonte": fonte, "secao": secao.caminho, "origem": "texto_limpo"})
    return exemplos


# ---------------------------------------------------------------- perguntas e respostas
def _limpar_curto(texto: str, opcoes: OpcoesLimpeza) -> str:
    if opcoes.normalizar_unicode:
        texto = normalizar_unicode(texto)
    if opcoes.mascarar_dados_pessoais:
        texto, _ = mascarar_dados_pessoais(texto, opcoes.preservar)
    return re.sub(r"\s+", " ", texto).strip()


def _itens_faq(texto: str) -> list[str]:
    """Separa um parágrafo com vários itens numerados de perguntas frequentes ("1 - ...? R: ... 2 - ...? R: ...")."""
    inicios = [m.start() for m in _INICIO_ITEM_FAQ.finditer(texto)]
    if len(inicios) < 2:
        return [texto]
    if inicios[0] != 0:
        inicios = [0, *inicios]
    return [texto[a:b].strip() for a, b in zip(inicios, [*inicios[1:], len(texto)], strict=True) if texto[a:b].strip()]


def pares_no_texto(texto: str) -> list[tuple[str, str]]:
    """Perguntas escritas no meio do texto corrido: a frase que termina em "?" é a pergunta, e as frases seguintes,
    até a próxima pergunta, são a resposta. Perguntas retóricas sem palavra interrogativa ficam de fora."""
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if f.strip()]
    pares, i = [], 0
    while i < len(frases):
        pergunta = _PREFIXO_PERGUNTA.sub("", frases[i])
        if pergunta.endswith("?") and 8 <= len(pergunta) <= 220 and _SINAL_DE_PERGUNTA.search(pergunta):
            resposta = []
            j = i + 1
            while j < len(frases) and not frases[j].endswith("?"):
                resposta.append(frases[j])
                j += 1
            texto_resposta = _PREFIXO_RESPOSTA.sub("", " ".join(resposta)).strip()
            if len(texto_resposta) >= 15:
                pares.append((pergunta, texto_resposta))
            i = j
        else:
            i += 1
    return pares


def _resposta_ate(blocos: list[Bloco], limite: int) -> str:
    partes, total = [], 0
    for bloco in blocos:
        linha = ("- " + bloco.texto) if bloco.tipo == "item" else bloco.texto
        if partes and total + len(linha) > limite:
            break
        partes.append(linha)
        total += len(linha) + 1
    return "\n".join(partes)[: limite * 2].strip()


def corpus_perguntas_respostas(docs: list[Documento], secoes_por_doc: dict[str, list[Secao]], opcoes: OpcoesLimpeza | None = None,
                               derivar: bool = True, limite_resposta: int = 900) -> list[dict]:
    """Pares vindos de quatro origens, registradas em cada exemplo:

    - `estruturada`: colunas ou campos de pergunta e resposta em CSV, JSON ou JSONL;
    - `extraida`: perguntas frequentes encontradas no texto ("Pergunta? R: resposta" ou título em forma de pergunta);
    - `titulo_interrogativo`: título de seção que já é uma pergunta sem o ponto de interrogação ("Como solicitar");
    - `derivada_do_titulo`: pergunta montada por modelo fixo a partir do título da seção (opcional).
    """
    op = opcoes or OpcoesLimpeza()
    pares: list[dict] = []

    def incluir(pergunta: str, resposta: str, fonte: str, secao: str, origem: str) -> None:
        pergunta, resposta = re.sub(r"\s+", " ", pergunta).strip(), resposta.strip()
        pergunta = re.sub(r"^\d{1,2}\s*[-.)]\s*", "", pergunta)
        if len(pergunta) >= 8 and len(resposta) >= 15:
            pares.append({"pergunta": pergunta, "resposta": resposta, "fonte": fonte, "secao": secao, "origem": origem})

    for doc in docs:
        for pergunta, resposta in doc.pares:
            incluir(_limpar_curto(pergunta, op), _limpar_curto(resposta, op), doc.nome, "", "estruturada")
        for secao in secoes_por_doc.get(doc.nome, []):
            usados: set[int] = set()
            if secao.titulo.endswith("?"):
                incluir(secao.titulo, _resposta_ate(secao.blocos, limite_resposta), doc.nome, secao.caminho, "extraida")
                continue
            for i, bloco in enumerate(secao.blocos):
                for item in _itens_faq(bloco.texto):
                    for pergunta, resposta in pares_no_texto(item):
                        incluir(pergunta, resposta[: 2 * limite_resposta], doc.nome, secao.caminho, "extraida")
                        usados.add(i)
                if i not in usados and bloco.tipo == "paragrafo" and bloco.texto.endswith("?") and len(bloco.texto) <= 220:
                    seguintes = []
                    for j in range(i + 1, len(secao.blocos)):
                        if secao.blocos[j].tipo == "paragrafo" and secao.blocos[j].texto.endswith("?"):
                            break
                        seguintes.append(secao.blocos[j])
                        usados.add(j)
                    if seguintes:
                        incluir(bloco.texto, _resposta_ate(seguintes, limite_resposta), doc.nome, secao.caminho, "extraida")
                        usados.add(i)
            if usados or not secao.titulo or len(secao.texto) < 80:
                continue
            if secao.titulo.lower().startswith(_INTERROGATIVOS):
                incluir(secao.titulo.rstrip(".:") + "?", _resposta_ate(secao.blocos, limite_resposta), doc.nome, secao.caminho,
                        "titulo_interrogativo")
            elif derivar:
                incluir(f'O que o documento "{secao.titulo_doc}" informa sobre "{secao.titulo}"?',
                        _resposta_ate(secao.blocos, limite_resposta), doc.nome, secao.caminho, "derivada_do_titulo")

    unicos, vistos = [], set()
    for par in pares:
        chave = re.sub(r"\W+", " ", par["pergunta"].lower()).strip()
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(par)
    return unicos


# ---------------------------------------------------------------- conversacional
def corpus_conversacional(pares: list[dict], sistema: str = SISTEMA_PADRAO, turnos: int = 3, recusas: tuple[str, ...] = RECUSAS_PADRAO,
                          escopo: str = "") -> list[dict]:
    """Diálogos no formato de mensagens com papéis. Perguntas vizinhas da mesma fonte viram turnos de uma mesma
    conversa (até `turnos` por conversa). As recusas ensinam o limite do assistente; `recusas=()` desliga."""
    conversas = []
    por_fonte: dict[str, list[dict]] = {}
    for par in pares:
        por_fonte.setdefault(par["fonte"], []).append(par)
    turnos = max(1, turnos)
    for fonte, lista in por_fonte.items():
        for inicio in range(0, len(lista), turnos):
            grupo = lista[inicio:inicio + turnos]
            mensagens = [{"role": "system", "content": sistema}] if sistema else []
            for par in grupo:
                mensagens += [{"role": "user", "content": par["pergunta"]}, {"role": "assistant", "content": par["resposta"]}]
            conversas.append({"messages": mensagens, "fonte": fonte, "secao": grupo[0]["secao"], "origem": "pares_da_fonte",
                              "turnos": len(grupo)})
    if recusas:
        ajuda = f"Posso ajudar com {escopo}." if escopo else "Posso ajudar com os assuntos tratados nos documentos desta base."
        for pergunta in recusas:
            mensagens = [{"role": "system", "content": sistema}] if sistema else []
            mensagens += [{"role": "user", "content": pergunta},
                          {"role": "assistant", "content": f"Esse assunto está fora do que eu consigo orientar. {ajuda}"}]
            conversas.append({"messages": mensagens, "fonte": "(modelo de recusa)", "secao": "", "origem": "recusa_modelo", "turnos": 1})
    return conversas


# ---------------------------------------------------------------- pares gerados por LLM (opcional)
_PROMPT_LLM = (
    "Leia o TEXTO e escreva {n} perguntas que um cidadão faria e que o TEXTO responde. "
    "A resposta deve usar apenas informações do TEXTO, em uma ou duas frases. "
    'Responda somente com JSON neste formato: [{{"pergunta": "...", "resposta": "..."}}]\n\nTEXTO:\n{texto}'
)


def _apoio(resposta: str, texto: str) -> float:
    """Fração das palavras de conteúdo da resposta que aparecem no texto de origem."""
    palavras = [p for p in re.findall(r"\w{4,}", resposta.lower())]
    if not palavras:
        return 0.0
    base = set(re.findall(r"\w{4,}", texto.lower()))
    return sum(p in base for p in palavras) / len(palavras)


def gerar_pares_com_llm(trechos: list[dict], base_url: str, modelo: str, chave: str = "local", por_trecho: int = 2,
                        timeout: float = 180.0, apoio_minimo: float = 0.6, cliente=None) -> tuple[list[dict], dict]:
    """Pede a um LLM (API compatível com a da OpenAI: llama.cpp, Ollama, Groq) perguntas e respostas sobre cada trecho.

    A saída do modelo é conferida antes de entrar no corpus: precisa ser JSON válido, a pergunta precisa terminar
    em "?" e pelo menos 60% das palavras de conteúdo da resposta precisam estar no trecho. O que não passa é
    contado e descartado. Falha de rede ou resposta inválida não interrompe a geração.
    """
    import httpx

    http = cliente or httpx.Client(timeout=timeout)
    pares: list[dict] = []
    resumo = {"trechos": len(trechos), "pares_aceitos": 0, "pares_rejeitados": 0, "chamadas_com_falha": 0}
    for trecho in trechos:
        try:
            r = http.post(f"{base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {chave}"}, json={
                "model": modelo, "temperature": 0.2, "max_tokens": 500,
                "messages": [{"role": "user", "content": _PROMPT_LLM.format(n=por_trecho, texto=trecho["text"])}]})
            r.raise_for_status()
            conteudo = r.json()["choices"][0]["message"]["content"]
            lista = json.loads(conteudo[conteudo.index("["): conteudo.rindex("]") + 1])
        except Exception:  # rede, tempo esgotado, JSON inválido: segue para o próximo trecho
            resumo["chamadas_com_falha"] += 1
            continue
        for item in lista if isinstance(lista, list) else []:
            pergunta = str(item.get("pergunta", "")).strip() if isinstance(item, dict) else ""
            resposta = str(item.get("resposta", "")).strip() if isinstance(item, dict) else ""
            if pergunta.endswith("?") and 8 <= len(pergunta) <= 220 and len(resposta) >= 15 and _apoio(resposta, trecho["text"]) >= apoio_minimo:
                pares.append({"pergunta": pergunta, "resposta": resposta, "fonte": trecho["fonte"], "secao": trecho["secao"], "origem": "llm"})
                resumo["pares_aceitos"] += 1
            else:
                resumo["pares_rejeitados"] += 1
    return pares, resumo
