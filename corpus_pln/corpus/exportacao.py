"""Exportação dos corpora: divisão em treino e validação, arquivos JSONL, rastreabilidade, estatísticas e ficha.

Os arquivos de treino têm só os campos que as ferramentas de fine-tuning esperam:
- texto puro:            {"text": ...}
- perguntas e respostas: {"instruction": pergunta, "input": "", "output": resposta}
- conversacional:        {"messages": [{"role": "system" | "user" | "assistant", "content": ...}]}
A origem de cada linha (arquivo, seção, forma de obtenção) fica em rastreabilidade.csv.
"""

from __future__ import annotations

import csv
import io
import json
import random
import zipfile
from datetime import datetime
from pathlib import Path

from .limpeza import _DADOS_PESSOAIS, _EMAIL_INSTITUCIONAL

CORPORA = ("texto_puro", "perguntas_respostas", "conversacional")
NOMES = {"texto_puro": "Texto puro", "perguntas_respostas": "Perguntas e respostas", "conversacional": "Conversacional"}


def linha_de_treino(corpus: str, exemplo: dict) -> dict:
    if corpus == "texto_puro":
        return {"text": exemplo["text"]}
    if corpus == "perguntas_respostas":
        return {"instruction": exemplo["pergunta"], "input": "", "output": exemplo["resposta"]}
    return {"messages": exemplo["messages"]}


def _texto_do_exemplo(corpus: str, exemplo: dict) -> str:
    if corpus == "texto_puro":
        return exemplo["text"]
    if corpus == "perguntas_respostas":
        return exemplo["pergunta"] + " " + exemplo["resposta"]
    return " ".join(m["content"] for m in exemplo["messages"] if m["role"] != "system")


def dividir(exemplos: list[dict], fracao_validacao: float = 0.1, semente: int = 42) -> tuple[list[dict], list[dict]]:
    """Separa treino e validação. Com 5 fontes ou mais, a divisão é por fonte (um documento inteiro fica de um lado
    só, para a validação não repetir texto visto no treino). Com menos fontes, a divisão é por exemplo."""
    if len(exemplos) < 10 or fracao_validacao <= 0:
        return list(exemplos), []
    sorteio = random.Random(semente)
    alvo = max(1, round(len(exemplos) * fracao_validacao))
    fontes = sorted({e["fonte"] for e in exemplos})
    if len(fontes) >= 5:
        sorteio.shuffle(fontes)
        escolhidas: set[str] = set()
        total = 0
        for fonte in fontes:
            tamanho = sum(e["fonte"] == fonte for e in exemplos)
            if total and total + tamanho > 2 * alvo:
                continue
            escolhidas.add(fonte)
            total += tamanho
            if total >= alvo:
                break
        if 0 < total < len(exemplos):
            return [e for e in exemplos if e["fonte"] not in escolhidas], [e for e in exemplos if e["fonte"] in escolhidas]
    indices = list(range(len(exemplos)))
    sorteio.shuffle(indices)
    validacao = set(indices[:alvo])
    return [e for i, e in enumerate(exemplos) if i not in validacao], [e for i, e in enumerate(exemplos) if i in validacao]


def estatisticas(corpora: dict[str, list[dict]], divisoes: dict[str, tuple[list[dict], list[dict]]]) -> dict:
    resumo = {}
    for corpus in CORPORA:
        exemplos = corpora.get(corpus, [])
        textos = [_texto_do_exemplo(corpus, e) for e in exemplos]
        caracteres = sum(len(t) for t in textos)
        por_origem: dict[str, int] = {}
        por_fonte: dict[str, int] = {}
        for e in exemplos:
            por_origem[e["origem"]] = por_origem.get(e["origem"], 0) + 1
            por_fonte[e["fonte"]] = por_fonte.get(e["fonte"], 0) + 1
        treino, validacao = divisoes.get(corpus, (exemplos, []))
        resumo[corpus] = {
            "exemplos": len(exemplos), "treino": len(treino), "validacao": len(validacao), "caracteres": caracteres,
            "media_de_caracteres": round(caracteres / len(exemplos)) if exemplos else 0,
            # estimativa grosseira (4 caracteres por token); o número real depende do tokenizador do modelo
            "tokens_estimados": round(caracteres / 4),
            "por_origem": dict(sorted(por_origem.items())), "por_fonte": dict(sorted(por_fonte.items())),
        }
        if corpus == "conversacional" and exemplos:
            resumo[corpus]["media_de_turnos"] = round(sum(e.get("turnos", 1) for e in exemplos) / len(exemplos), 2)
    return resumo


def _jsonl(linhas: list[dict]) -> str:
    return "".join(json.dumps(linha, ensure_ascii=False) + "\n" for linha in linhas)


def ficha(documentos: list[dict], opcoes: dict, configuracao: dict, resumo: dict, erros: list[tuple[str, str]]) -> str:
    """Ficha do corpus (datasheet): de onde veio, o que foi removido, quanto ficou e o que conferir antes de usar."""
    a = []
    a.append("# Ficha do corpus\n")
    a.append(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} pela ferramenta de construção de corpus do Zela.\n")
    a.append("## Documentos de origem\n")
    a.append("| Arquivo | Formato | Caracteres antes | Caracteres depois | Redução | Dados pessoais mascarados |\n|---|---|---|---|---|---|")
    for d in documentos:
        r = d["relatorio"]
        pii = ", ".join(f"{k}: {v}" for k, v in r.dados_pessoais.items()) or "nenhum"
        a.append(f"| {d['nome']} | {d['formato']} | {r.caracteres_antes} | {r.caracteres_depois} | {r.reducao_pct}% | {pii} |")
    if erros:
        a.append("\nArquivos que não puderam ser lidos: " + "; ".join(f"{n} ({m})" for n, m in erros) + ".")
    a.append("\n## Limpeza aplicada\n")
    nomes = {"normalizar_unicode": "Normalização Unicode (NFC), aspas e traços simples, sem caracteres invisíveis",
             "remover_cabecalho_rodape": "Remoção de cabeçalho, rodapé e número de página repetidos (PDF)",
             "remover_ruido_web": "Remoção de linhas de menu e botões de página web",
             "juntar_linhas_quebradas": "Junção de linhas quebradas e de palavras hifenizadas no fim da linha",
             "remover_urls": "Remoção de endereços (URL)", "mascarar_dados_pessoais": "Mascaramento de CPF, e-mail pessoal, celular, RG e placa",
             "remover_duplicados": "Remoção de parágrafos duplicados entre os documentos", "minusculas": "Conversão para minúsculas"}
    for chave, nome in nomes.items():
        a.append(f"- {'[x]' if opcoes.get(chave) else '[ ]'} {nome}")
    a.append(f"- Parágrafos com menos de {opcoes.get('min_caracteres')} caracteres descartados")
    campos = ("linhas_cabecalho_rodape", "linhas_ruido", "hifens_unidos", "linhas_unidas", "urls_removidas",
              "paragrafos_duplicados", "paragrafos_curtos")
    totais = {campo: sum(getattr(d["relatorio"], campo) for d in documentos) for campo in campos}
    a.append("\nContagem do que saiu: " + ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in totais.items()) + ".\n")
    a.append("## Corpora gerados\n")
    a.append("| Corpus | Exemplos | Treino | Validação | Caracteres | Tokens (estimativa) | Origem dos exemplos |\n|---|---|---|---|---|---|---|")
    for corpus in CORPORA:
        r = resumo[corpus]
        origem = ", ".join(f"{k}: {v}" for k, v in r["por_origem"].items()) or "-"
        a.append(f"| {NOMES[corpus]} | {r['exemplos']} | {r['treino']} | {r['validacao']} | {r['caracteres']} | {r['tokens_estimados']} | {origem} |")
    a.append(f"\nConfiguração: trechos de até {configuracao.get('tamanho_trecho')} caracteres; até {configuracao.get('turnos')} "
             f"turnos por conversa; validação de {round(100 * configuracao.get('fracao_validacao', 0))}%; semente {configuracao.get('semente')}.\n")
    a.append("## Antes de usar\n")
    a.append("- Leia uma amostra de cada corpus. Perguntas de origem `derivada_do_titulo` são montadas por modelo fixo e "
             "servem de ponto de partida; as de origem `llm` foram escritas por um modelo e conferidas só por regra.")
    a.append("- O mascaramento de dados pessoais é uma heurística. Confira nomes de pessoas e outros dados que as regras não cobrem.")
    a.append("- Confira a licença e os termos de uso dos documentos de origem antes de publicar o corpus ou um modelo treinado com ele.")
    a.append("- O corpus reflete as fontes: se elas cobrem uma cidade ou um órgão, o modelo ajustado responderá com esse viés.")
    a.append("- A contagem de tokens é uma estimativa de 4 caracteres por token; meça com o tokenizador do modelo escolhido.")
    return "\n".join(a) + "\n"


def exportar(resultado, pasta: str | Path) -> dict:
    """Grava os arquivos na pasta e devolve as estatísticas. `resultado` vem de `pipeline.construir`."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in arquivos(resultado).items():
        (pasta / nome).write_text(conteudo, encoding="utf-8")
    return resultado.estatisticas


def arquivos(resultado) -> dict[str, str]:
    """Conteúdo de cada arquivo de saída, pelo nome."""
    saida: dict[str, str] = {}
    trilha = io.StringIO()
    escritor = csv.writer(trilha, delimiter=";")
    escritor.writerow(["corpus", "divisao", "linha", "fonte", "secao", "origem"])
    for corpus in CORPORA:
        for divisao, exemplos in zip(("treino", "validacao"), resultado.divisoes[corpus], strict=True):
            saida[f"{corpus}_{divisao}.jsonl"] = _jsonl([linha_de_treino(corpus, e) for e in exemplos])
            for numero, e in enumerate(exemplos, start=1):
                escritor.writerow([corpus, divisao, numero, e["fonte"], e.get("secao", ""), e["origem"]])
    saida["texto_puro.txt"] = "\n\n".join(e["text"] for e in resultado.corpora["texto_puro"]) + "\n"
    saida["rastreabilidade.csv"] = trilha.getvalue()
    saida["estatisticas.json"] = json.dumps(resultado.estatisticas, ensure_ascii=False, indent=2) + "\n"
    saida["FICHA_DO_CORPUS.md"] = ficha(resultado.documentos, resultado.opcoes, resultado.configuracao, resultado.estatisticas, resultado.erros)
    return saida


def pacote_zip(resultado) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos(resultado).items():
            z.writestr(f"corpus/{nome}", conteudo)
    return memoria.getvalue()


def validar_pasta(pasta: str | Path) -> list[str]:
    """Confere se os arquivos exportados estão prontos para o fine-tuning. Devolve a lista de problemas (vazia = ok)."""
    pasta = Path(pasta)
    problemas: list[str] = []
    for corpus in CORPORA:
        for divisao in ("treino", "validacao"):
            arquivo = pasta / f"{corpus}_{divisao}.jsonl"
            if not arquivo.exists():
                problemas.append(f"{arquivo.name}: arquivo ausente")
                continue
            for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), start=1):
                onde = f"{arquivo.name}:{numero}"
                try:
                    registro = json.loads(linha)
                except json.JSONDecodeError:
                    problemas.append(f"{onde}: não é JSON")
                    continue
                problemas += [f"{onde}: {p}" for p in _problemas_do_registro(corpus, registro)]
    return problemas


def _problemas_do_registro(corpus: str, registro: dict) -> list[str]:
    problemas = []
    if corpus == "texto_puro":
        textos = [registro.get("text", "")]
        if not str(textos[0]).strip():
            problemas.append("campo text vazio")
    elif corpus == "perguntas_respostas":
        textos = [registro.get("instruction", ""), registro.get("output", "")]
        if not all(str(t).strip() for t in textos):
            problemas.append("instruction ou output vazio")
    else:
        mensagens = registro.get("messages") or []
        textos = [m.get("content", "") for m in mensagens]
        papeis = [m.get("role") for m in mensagens]
        if papeis and papeis[0] == "system":
            papeis = papeis[1:]
        if not papeis or len(papeis) % 2 or any(p != ("user", "assistant")[i % 2] for i, p in enumerate(papeis)):
            problemas.append("os papéis não alternam user e assistant (terminando em assistant)")
        if not all(str(t).strip() for t in textos):
            problemas.append("mensagem vazia")
    for tipo, padrao in _DADOS_PESSOAIS:
        for texto in textos:
            for achado in padrao.finditer(str(texto)):
                if tipo == "EMAIL" and _EMAIL_INSTITUCIONAL.match(achado.group(0)):
                    continue
                problemas.append(f"possível dado pessoal não mascarado ({tipo})")
    return problemas
