"""Reúne o material de avaliação do assistente de voz em uma planilha (planilha_avaliacao.xlsx).

Abas: Leia-me, STT (um áudio por linha), LLM (30 perguntas com a resposta esperada e a obtida),
TTS (notas de naturalidade e clareza, para preencher) e Ponta_a_ponta (latência de cada turno).
Os resumos são fórmulas, então recalculam quando as notas são preenchidas.

Uso: python avaliacao/gerar_planilha.py      (rode de novo depois de cada avaliação)
"""

import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path(__file__).parent
RES = AQUI / "resultados"
SAIDA = AQUI / "planilha_avaliacao.xlsx"

FONTE = Font(name="Arial", size=10)
NEGRITO = Font(name="Arial", size=10, bold=True)
CAB = Font(name="Arial", size=10, bold=True, color="FFFFFF")
FUNDO = PatternFill("solid", fgColor="0F5C63")
PREENCHER = PatternFill("solid", fgColor="FFF2CC")  # células que as pessoas preenchem


def ler_csv(nome: str) -> list[dict]:
    p = RES / nome
    return list(csv.DictReader(p.open(encoding="utf-8"), delimiter=";")) if p.exists() else []


def numero(valor: str):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return valor


def cabecalho(ws, colunas: list[str], larguras: list[int]) -> None:
    ws.append(colunas)
    for i, c in enumerate(ws[1]):
        c.font, c.fill = CAB, FUNDO
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i + 1)].width = larguras[i]
    ws.freeze_panes = "A2"


def formatar(ws, quebra: tuple[str, ...] = ()) -> None:
    for linha in ws.iter_rows(min_row=2):
        for c in linha:
            c.font = NEGRITO if c.font.bold else FONTE
            if c.column_letter in quebra:
                c.alignment = Alignment(wrap_text=True, vertical="top")


def aba_leia_me(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "Leia-me"
    ws.column_dimensions["A"].width = 118
    linhas = [
        ("Zela por voz: planilha de avaliação", True),
        ("Gerada por avaliacao/gerar_planilha.py a partir de avaliacao/resultados/. Rode o script de novo depois de cada avaliação.", False),
        ("", False),
        ("STT: um áudio por linha, nas opções comparadas (tiny, small, small+vocab). A coluna WER é o erro daquele áudio.", False),
        ("O WER geral do relatório soma os erros de todas as palavras; a média por áudio desta aba pode diferir um pouco.", False),
        ("LLM: as 30 perguntas, a resposta esperada, a resposta obtida, a conferência automática e a conferência humana.", False),
        ("TTS: aba para preencher. Cada avaliador ouve os áudios de avaliacao/amostras_tts/ e dá notas de 1 a 5 nas células amarelas.", False),
        ("     Exemplo de preenchimento: naturalidade 4 (soa quase como uma pessoa), clareza 5 (entendi tudo na primeira vez).", False),
        ("     O quadro de médias à direita recalcula sozinho. Para levar as notas ao relatório: python avaliacao/avaliar_tts.py --resumir", False),
        ("Ponta_a_ponta: latência de cada turno das 10 conversas, em segundos, com média, mediana e máximo por etapa.", False),
        ("", False),
        ("Escala das notas de TTS: 1 = muito ruim, 2 = ruim, 3 = aceitável, 4 = boa, 5 = muito boa.", False),
    ]
    for texto, titulo in linhas:
        ws.append([texto])
        ws.cell(row=ws.max_row, column=1).font = Font(name="Arial", size=12, bold=True) if titulo else FONTE


def aba_stt(wb: Workbook) -> None:
    ws = wb.create_sheet("STT")
    cabecalho(ws, ["conjunto", "opcao", "arquivo", "locutor", "condicao", "referencia", "transcricao", "wer", "segundos"],
              [12, 13, 20, 20, 12, 50, 50, 8, 10])
    for conjunto, nome in (("sintetico", "stt_audios_sinteticos.csv"), ("real", "stt_audios_reais.csv")):
        for x in ler_csv(nome):
            ws.append([conjunto, x.get("opcao") or x.get("modelo"), x["arquivo"], x["locutor"], x["condicao"], x["referencia"],
                       x["transcricao"], numero(x["wer"]), numero(x["segundos"])])
    ultimo = max(ws.max_row, 2)
    ws["K1"], ws["L1"], ws["M1"], ws["N1"] = "Resumo (conjunto · opção)", "áudios", "média do WER por áudio", "tempo médio (s)"
    for c in ("K1", "L1", "M1", "N1"):
        ws[c].font, ws[c].fill = CAB, FUNDO
        ws[c].alignment = Alignment(wrap_text=True, vertical="center")
    i = 2
    for conjunto in ("real", "sintetico"):
        for opcao in ["tiny", "small", "small+vocab"]:
            ws[f"K{i}"] = f"{conjunto} · {opcao}"
            filtro = f'$A$2:$A${ultimo},"{conjunto}",$B$2:$B${ultimo},"{opcao}"'
            ws[f"L{i}"] = f"=COUNTIFS({filtro})"
            ws[f"M{i}"] = f'=IFERROR(AVERAGEIFS($H$2:$H${ultimo},{filtro}),"")'
            ws[f"N{i}"] = f'=IFERROR(AVERAGEIFS($I$2:$I${ultimo},{filtro}),"")'
            ws[f"M{i}"].number_format = "0.0%"
            ws[f"N{i}"].number_format = "0.00"
            i += 1
    for linha in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        linha[0].number_format = "0.0%"
    for col, largura in (("K", 26), ("L", 9), ("M", 14), ("N", 12)):
        ws.column_dimensions[col].width = largura
    formatar(ws, quebra=("F", "G"))


def aba_llm(wb: Workbook) -> None:
    ws = wb.create_sheet("LLM")
    revisao = {}
    if (RES / "revisao_manual.json").exists():
        revisao = json.loads((RES / "revisao_manual.json").read_text(encoding="utf-8")).get("llm", {})
    cabecalho(ws, ["id", "tipo", "pergunta", "resposta_esperada", "resposta_obtida", "fontes", "conferencia_automatica",
                   "conferencia_humana", "observacao", "segundos"], [6, 15, 38, 48, 60, 30, 20, 18, 40, 9])
    for x in ler_csv("llm_30_perguntas.csv"):
        v = revisao.get(x["id"], {})
        ws.append([x["id"], x["tipo"], x["pergunta"], x.get("resposta_esperada", ""), x["resposta"], x["fontes"], x["julgamento"],
                   v.get("veredito", ""), v.get("obs", ""), numero(x["segundos"])])
    ultimo = max(ws.max_row, 2)
    resumo = [
        ("Resumo", "valor"),
        ("Perguntas diretas e de continuação", f'=COUNTIFS($B$2:$B${ultimo},"direta")+COUNTIFS($B$2:$B${ultimo},"continuacao")'),
        ("Corretas (automática)", f'=COUNTIFS($G$2:$G${ultimo},"correta")'),
        ("% corretas (automática)", "=IFERROR(M3/M2,\"\")"),
        ("Corretas (humana)", f'=COUNTIFS($H$2:$H${ultimo},"correta")'),
        ("% corretas (humana)", "=IFERROR(M5/M2,\"\")"),
        ("Perguntas fora do escopo", f'=COUNTIFS($B$2:$B${ultimo},"fora_do_escopo")'),
        ("Recusas adequadas (automática)", f'=COUNTIFS($G$2:$G${ultimo},"recusa adequada")'),
        ("% recusas adequadas", "=IFERROR(M8/M7,\"\")"),
        ("Latência média (s)", f"=IFERROR(AVERAGE($J$2:$J${ultimo}),\"\")"),
    ]
    for i, (rotulo, formula) in enumerate(resumo, start=1):
        ws[f"L{i}"], ws[f"M{i}"] = rotulo, formula
    for c in ("L1", "M1"):
        ws[c].font, ws[c].fill = CAB, FUNDO
    for c in ("M4", "M6", "M9"):
        ws[c].number_format = "0.0%"
    ws["M10"].number_format = "0.0"
    ws.column_dimensions["L"].width, ws.column_dimensions["M"].width = 36, 10
    formatar(ws, quebra=("C", "D", "E", "F", "I"))


def notas_ja_preenchidas() -> dict[tuple, tuple]:
    """Notas digitadas na planilha anterior: gerar de novo não pode apagar o trabalho dos avaliadores."""
    if not SAIDA.exists():
        return {}
    from openpyxl import load_workbook
    antiga = load_workbook(SAIDA, read_only=True)
    if "TTS" not in antiga.sheetnames:
        return {}
    return {(av, am, voz): (nat, cla, com or "")
            for av, am, voz, _arq, _txt, nat, cla, com in antiga["TTS"].iter_rows(min_row=2, max_col=8, values_only=True)
            if nat or cla}


def aba_tts(wb: Workbook) -> None:
    ws = wb.create_sheet("TTS")
    falas = {(x["amostra"], x["voz"]): x["texto_falado"] for x in ler_csv("tts_latencia.csv")}
    cabecalho(ws, ["avaliador", "amostra", "voz", "arquivo", "texto_falado", "naturalidade_1a5", "clareza_1a5", "comentario"],
              [16, 9, 8, 30, 70, 14, 12, 36])
    ja_preenchidas = notas_ja_preenchidas()
    for x in ler_csv("notas_tts.csv"):
        chave = (x["avaliador"], x["amostra"], x["voz"])
        nat, cla, com = ja_preenchidas.get(chave, (None, None, ""))
        ws.append([x["avaliador"], x["amostra"], x["voz"], x["arquivo"], falas.get((x["amostra"], x["voz"]), ""),
                   numero(x["naturalidade_1a5"]) if x["naturalidade_1a5"] else nat,
                   numero(x["clareza_1a5"]) if x["clareza_1a5"] else cla, x.get("comentario") or com])
    ultimo = max(ws.max_row, 2)
    notas = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True,
                           errorTitle="Nota inválida", error="Use um número inteiro de 1 a 5.")
    ws.add_data_validation(notas)
    notas.add(f"F2:G{ultimo}")
    for linha in ws.iter_rows(min_row=2, max_row=ultimo, min_col=6, max_col=8):
        for c in linha:
            c.fill = PREENCHER
    for c, texto in (("J1", "Resumo por voz"), ("K1", "notas preenchidas"), ("L1", "avaliadores com nota"),
                     ("M1", "naturalidade média"), ("N1", "clareza média")):
        ws[c] = texto
        ws[c].font, ws[c].fill = CAB, FUNDO
        ws[c].alignment = Alignment(wrap_text=True, vertical="center")
    for i, voz in enumerate(["faber", "cadu"], start=2):
        ws[f"J{i}"] = voz
        ws[f"K{i}"] = f'=COUNTIFS($C$2:$C${ultimo},J{i},$F$2:$F${ultimo},">=1")'
        # avaliadores distintos que deram pelo menos uma nota para a voz
        ws[f"L{i}"] = (f'=SUMPRODUCT((COUNTIFS($A$2:$A${ultimo},{{"Avaliador 1","Avaliador 2","Avaliador 3","Avaliador 4","Avaliador 5"}},'
                       f'$C$2:$C${ultimo},J{i},$F$2:$F${ultimo},">=1")>0)*1)')
        ws[f"M{i}"] = f'=IFERROR(AVERAGEIFS($F$2:$F${ultimo},$C$2:$C${ultimo},J{i}),"sem notas")'
        ws[f"N{i}"] = f'=IFERROR(AVERAGEIFS($G$2:$G${ultimo},$C$2:$C${ultimo},J{i}),"sem notas")'
        ws[f"M{i}"].number_format = ws[f"N{i}"].number_format = "0.00"
    ws["J5"] = "Mínimo pedido: 10 respostas avaliadas por 3 pessoas ou mais. Renomeie \"Avaliador n\" se quiser identificar quem ouviu."
    for col, largura in (("J", 18), ("K", 12), ("L", 13), ("M", 13), ("N", 10)):
        ws.column_dimensions[col].width = largura
    formatar(ws, quebra=("E", "H"))


def aba_e2e(wb: Workbook) -> None:
    ws = wb.create_sheet("Ponta_a_ponta")
    colunas = ["conversa", "turno", "pergunta_dita", "transcricao", "resposta_texto", "adequada", "stt_s", "llm_s", "adaptacao_s",
               "tts_s", "ate_inicio_da_fala_s", "duracao_resposta_s"]
    cabecalho(ws, colunas, [9, 7, 36, 36, 60, 10, 8, 8, 12, 8, 14, 14])
    for x in ler_csv("e2e_10_conversas.csv"):
        ws.append([int(x["conversa"]), int(x["turno"]), x["pergunta_dita"], x["transcricao"], x["resposta_texto"],
                   "sim" if x["adequada"] == "True" else "não", *[numero(x[c]) for c in colunas[6:]]])
    ultimo = max(ws.max_row, 2)
    ws["N1"] = "Latência (s)"
    for j, titulo in enumerate(["média", "mediana", "máximo"]):
        ws.cell(row=1, column=15 + j, value=titulo)
    etapas = [("STT", "G"), ("Assistente (busca + LLM)", "H"), ("Adaptação para fala", "I"), ("TTS", "J"),
              ("Total até começar a falar", "K")]
    for i, (nome, col) in enumerate(etapas, start=2):
        ws[f"N{i}"] = nome
        ws[f"O{i}"] = f'=IFERROR(AVERAGE({col}$2:{col}${ultimo}),"")'
        ws[f"P{i}"] = f'=IFERROR(MEDIAN({col}$2:{col}${ultimo}),"")'
        ws[f"Q{i}"] = f'=IFERROR(MAX({col}$2:{col}${ultimo}),"")'
        for c in ("O", "P", "Q"):
            ws[f"{c}{i}"].number_format = "0.00"
    ws["N8"], ws["O8"] = "Turnos adequados (automática)", f'=IFERROR(COUNTIFS($F$2:$F${ultimo},"sim")/COUNTA($F$2:$F${ultimo}),"")'
    ws["O8"].number_format = "0.0%"
    for c in ("N1", "O1", "P1", "Q1"):
        ws[c].font, ws[c].fill = CAB, FUNDO
    ws.column_dimensions["N"].width = 30
    formatar(ws, quebra=("C", "D", "E"))


def main() -> None:
    wb = Workbook()
    aba_leia_me(wb)
    aba_stt(wb)
    aba_llm(wb)
    aba_tts(wb)
    aba_e2e(wb)
    wb.save(SAIDA)
    print(SAIDA)


if __name__ == "__main__":
    main()
