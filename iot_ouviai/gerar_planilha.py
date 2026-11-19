"""Gera a planilha do OuviAí (planilha_ouviai.xlsx) com os resultados reais do Edge Impulse e fórmulas de acerto.

Abas: Gravacoes (60 gravações), Teste_arquivos (Classify all nos 15 áudios de Test), Teste_ao_vivo (15 tentativas no
celular, preenchidas pelo autor), Modelo (parâmetros e validação) e Resumo.
Lê: resultados/gravacoes_edge_impulse.csv, resultados/model_testing_int8.csv e resultados/modelo.json.
Uso: python gerar_planilha.py
"""

import contextlib
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path(__file__).parent
RES = AQUI / "resultados"
CLASSES = ["campainha", "batida_porta", "ambiente"]
CAB, FUNDO = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0F5C63")
ALTURA_QUASE_SILENCIO_DB = -45  # RMS abaixo disto: gravação quase silenciosa


def cabecalho(ws, colunas, larguras):
    ws.append(colunas)
    for i, c in enumerate(ws[1]):
        c.font, c.fill = CAB, FUNDO
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[c.column_letter].width = larguras[i]
    ws.freeze_panes = "A2"


def lista_de_classes(ws, intervalo, extra=""):
    dv = DataValidation(type="list", formula1=f'"{",".join(CLASSES)}{extra}"')
    ws.add_data_validation(dv)
    dv.add(intervalo)


def hora_brasilia(hora_utc: str) -> str:
    h, m, s = (int(x) for x in hora_utc.split(":"))
    return f"{(h - 3) % 24:02d}:{m:02d}:{s:02d}"


def conferencia(classe: str, pico: float, rms: int) -> str:
    """Leitura da forma de onda feita na conferência (não substitui ouvir a gravação)."""
    if classe != "ambiente":
        return "evento visível na forma de onda"
    if rms < ALTURA_QUASE_SILENCIO_DB:
        return "quase silêncio"
    if pico >= 0.9:
        return "som de fundo com pico alto: confirmar ouvindo"
    return "som de fundo"


def previsao_por_arquivo(linha: dict) -> tuple[str, str]:
    """Resposta mais frequente entre as janelas; 'incerto' conta como resposta; empate vira incerto."""
    contagem = {c: int(linha[f"janelas_{c}"]) for c in CLASSES}
    contagem["incerto"] = int(linha["janelas_incerto"])
    ordem = sorted(contagem.items(), key=lambda kv: -kv[1])
    if ordem[0][1] == ordem[1][1]:
        return "incerto", f"empate: {ordem[0][1]} {ordem[0][0]} e {ordem[1][1]} {ordem[1][0]}"
    return ordem[0][0], ""


def ler_csv(nome: str) -> list[dict]:
    with open(RES / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    gravacoes = {r["arquivo"]: r for r in ler_csv("gravacoes_edge_impulse.csv")}
    testes = {r["arquivo"]: r for r in ler_csv("model_testing_int8.csv")}
    modelo = json.loads((RES / "modelo.json").read_text(encoding="utf-8"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Gravacoes"
    cabecalho(ws, ["arquivo (Edge Impulse)", "classe", "conjunto", "duracao_s", "hora (Brasília, 17/11/2026)",
                   "pico (0 a 1)", "rms_dbfs", "amostras_zeradas_%", "conferencia da forma de onda",
                   "ouvida pelo autor (sim/nao)", "observacao"],
              [22, 14, 11, 10, 14, 10, 10, 12, 30, 14, 40])
    ouvidas = {r["arquivo"]: r for r in ler_csv("conferencia_auditiva.csv")} if (RES / "conferencia_auditiva.csv").exists() else {}
    for classe in CLASSES:
        for i in range(1, 21):
            nome = f"{classe}_{i:02d}"
            g = gravacoes[nome]
            o = ouvidas.get(nome)
            obs = ""
            if o:
                obs = f'ouvida: {o["o_que_tem"]}' + (" (rótulo errado: ficou no treino deste modelo)" if o["rotulo_correto"] == "nao" else "")
            ws.append([nome, classe, g["conjunto"], float(g["duracao_s"]), hora_brasilia(g["hora_utc"]),
                       float(g["pico"]), int(g["rms_dbfs"]), int(g["amostras_zeradas_pct"]),
                       conferencia(classe, float(g["pico"]), int(g["rms_dbfs"])), o["ouvida_pelo_autor"] if o else "", obs])
    lista_de_classes(ws, "B2:B61")

    ws = wb.create_sheet("Teste_arquivos")
    cabecalho(ws, ["arquivo (conjunto Test)", "classe_real", "classe_prevista (mais janelas)", "janelas",
                   "janelas na classe real", "acerto por janela", "prob. media da classe prevista", "acerto",
                   "sequencia das janelas", "observacao"],
              [22, 14, 18, 9, 12, 12, 14, 9, 16, 40])
    linha = 2
    for classe in CLASSES:
        for i in range(16, 21):
            nome = f"{classe}_{i:02d}"
            t = testes[nome]
            prevista, obs = previsao_por_arquivo(t)
            media = float(t[f"media_{prevista}"]) if prevista in CLASSES else ""
            ws.append([nome, classe, prevista, int(t["janelas"]), int(t[f"janelas_{classe}"]), f"=E{linha}/D{linha}",
                       media, f'=IF(C{linha}="","",IF(C{linha}=B{linha},1,0))', t["sequencia_janelas"], obs])
            ws[f"F{linha}"].number_format = "0%"
            linha += 1
    lista_de_classes(ws, "C2:C16", ",incerto")
    ws.append([])
    ws.append(["Sequência: a = ambiente, b = batida_porta, c = campainha, i = incerto (nenhuma classe com 60% ou mais). "
               "Modelo quantizado (int8)."])

    ws = wb.create_sheet("Teste_ao_vivo")
    cabecalho(ws, ["tentativa", "som_produzido", "classe_real", "classe_prevista", "confianca_na_tela", "acerto",
                   "falso_positivo_em_ambiente", "observacao"], [10, 30, 14, 16, 12, 9, 24, 40])
    ao_vivo = {int(r["tentativa"]): r for r in ler_csv("teste_ao_vivo.csv")} if (RES / "teste_ao_vivo.csv").exists() else {}
    for i in range(1, 16):
        real = CLASSES[(i - 1) // 5]
        r = i + 1
        v = ao_vivo.get(i, {})
        confianca = v.get("confianca_na_tela", "")
        with contextlib.suppress(ValueError):  # texto livre, como "ambiente < 0.10", fica como está
            confianca = float(confianca)
        ws.append([i, v.get("som_produzido", ""), real, v.get("classe_prevista", ""), confianca,
                   f'=IF(D{r}="","",IF(D{r}=C{r},1,0))',
                   f'=IF(OR(D{r}="",C{r}<>"ambiente"),"",IF(D{r}<>"ambiente",1,0))', v.get("observacao", "")])
    lista_de_classes(ws, "D2:D16", ",incerto,oscilou")
    ws.append([])
    ws.append(["Celular em cima da mesa, a 50 cm da porta (18/11/2026). \"oscilou\": a tela alternou entre as três classes "
               "durante a tentativa; conta como erro e, em ambiente, como falso positivo."])

    ws = wb.create_sheet("Modelo")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 40, 70
    ws.append(["Item", "Valor"])
    for c in ws[1]:
        c.font, c.fill = CAB, FUNDO
    imp, mfe, cl, val = modelo["impulse"], modelo["mfe"], modelo["classificador"], modelo["validacao"]["int8"]
    for item in [
        ("Projeto no Edge Impulse", modelo["projeto_edge_impulse"]),
        ("Janela / passo", f'{imp["janela_ms"]} ms / {imp["passo_ms"]} ms, {imp["frequencia_hz"]} Hz, zero-pad'),
        ("Janelas de Training (ambiente / batida / campainha)",
         f'{imp["janelas_training"]} ({imp["janelas_por_classe_training"]["ambiente"]} / '
         f'{imp["janelas_por_classe_training"]["batida_porta"]} / {imp["janelas_por_classe_training"]["campainha"]})'),
        ("MFE: frame length / stride / filtros / FFT",
         f'{mfe["frame_length_s"]} s / {mfe["frame_stride_s"]} s / {mfe["filtros"]} / {mfe["fft"]}'),
        ("MFE: noise floor", f'{mfe["noise_floor_db"]} dB'),
        ("CNN", cl["arquitetura"]),
        ("Ciclos / taxa de aprendizado / batch", f'{cl["ciclos"]} / {cl["taxa_aprendizado"]} / {cl["batch"]}'),
        ("Validação separada pelo Edge Impulse", f'{cl["validacao_pct"]}% das janelas de Training'),
        ("Data augmentation", "não"),
        ("Acurácia de validação (int8)", val["acuracia_pct"] / 100),
        ("Loss de validação (int8)", val["loss"]),
        ("Matriz de validação: campainha prevista como ambiente", val["matriz_pct"]["campainha"]["ambiente"] / 100),
        ("Desempenho estimado em Cortex-M4F 80 MHz (int8)",
         f'MFE {mfe["tempo_processamento_ms"]} ms; rede {val["desempenho_cortex_m4f_80mhz"]["inferencia_ms"]} ms, '
         f'{val["desempenho_cortex_m4f_80mhz"]["ram_kb"]} KB de RAM, {val["desempenho_cortex_m4f_80mhz"]["flash_kb"]} KB de flash'),
        ("Model testing: acurácia por janela (int8)", modelo["model_testing"]["int8"]["acuracia_janelas_pct"] / 100),
    ]:
        ws.append(list(item))
    for celula in ("B11", "B13", "B15"):
        ws[celula].number_format = "0.0%"

    ws = wb.create_sheet("Resumo")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 56, 16
    ws.append(["Indicador", "Valor"])
    for c in ws[1]:
        c.font, c.fill = CAB, FUNDO
    for rotulo, formula in [
        ("Acertos no Classify all por arquivo (de 15 áudios Test)", "=SUM(Teste_arquivos!H2:H16)"),
        ("Taxa de acerto no Classify all por arquivo", '=IFERROR(B2/COUNT(Teste_arquivos!H2:H16),"")'),
        ("Acertos no teste ao vivo (de 15 tentativas)", "=SUM(Teste_ao_vivo!F2:F16)"),
        ("Taxa de acerto ao vivo", '=IFERROR(B4/COUNT(Teste_ao_vivo!F2:F16),"")'),
        ("Ao vivo: acertos em campainha (de 5)", "=SUM(Teste_ao_vivo!F2:F6)"),
        ("Ao vivo: acertos em batida na porta (de 5)", "=SUM(Teste_ao_vivo!F7:F11)"),
        ("Ao vivo: acertos em ambiente (de 5)", "=SUM(Teste_ao_vivo!F12:F16)"),
        ("Ao vivo: falsos positivos em ambiente (de 5)", "=SUM(Teste_ao_vivo!G12:G16)"),
        ("Acurácia de validação informada pelo Edge Impulse (int8)", "=Modelo!B11"),
        ("Acurácia do Classify all por janela (int8, Edge Impulse)", "=Modelo!B15"),
        ("Gravações por classe (campainha / batida / ambiente)",
         '=COUNTIF(Gravacoes!B2:B61,"campainha")&" / "&COUNTIF(Gravacoes!B2:B61,"batida_porta")&" / "&COUNTIF(Gravacoes!B2:B61,"ambiente")'),
        ("Training / Test", '=COUNTIF(Gravacoes!C2:C61,"Training")&" / "&COUNTIF(Gravacoes!C2:C61,"Test")'),
    ]:
        ws.append([rotulo, formula])
    for celula in ("B3", "B5", "B10", "B11"):
        ws[celula].number_format = "0.0%"
    destino = AQUI / "planilha_ouviai.xlsx"
    wb.save(destino)
    print(destino)


if __name__ == "__main__":
    main()
