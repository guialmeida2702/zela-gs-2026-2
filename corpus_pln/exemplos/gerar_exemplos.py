"""Gera os arquivos de exemplo nos formatos que não são texto simples (PDF, DOCX, HTML, CSV e JSONL).

Os cinco arquivos .md desta pasta são cópias da base de conhecimento do Zela (páginas oficiais da
Prefeitura de São Paulo, com URL e data da consulta no cabeçalho, e o guia do serviço). Os arquivos
criados aqui são SINTÉTICOS: foram escritos para o teste da ferramenta e trazem, de propósito, os
problemas que a limpeza precisa resolver (cabeçalho e rodapé repetidos, palavras hifenizadas no fim
da linha, menus de página web, parágrafos duplicados e dados pessoais fictícios).

Uso: python exemplos/gerar_exemplos.py
"""

import json
from pathlib import Path

AQUI = Path(__file__).parent

CARTILHA = [
    ("PREPARAÇÃO PARA O PERÍODO DE CHUVAS", [
        "Esta cartilha de exemplo reúne orientações gerais para moradores de áreas sujeitas a alagamento. Ela foi escrita "
        "para testar a ferramenta de construção de corpus e não substitui as orientações oficiais da Defesa Civil.",
        "Antes da temporada de chuvas, limpe calhas e ralos, guarde documentos em local alto e combine com a família um "
        "ponto de encontro. Anote os telefones de emergência: 193 para os Bombeiros e 199 para a Defesa Civil.",
        "Não jogue lixo nem entulho em córregos e bocas de lobo. O entupimento da drenagem é uma das principais causas de "
        "alagamento em vias urbanas, e a limpeza depende também da colaboração dos moradores.",
    ]),
    ("O QUE FAZER DURANTE UM ALAGAMENTO", [
        "Se a água começar a subir, desligue a energia elétrica no quadro geral e leve crianças, pessoas idosas e pessoas "
        "com deficiência para um local seguro. Não tente atravessar ruas alagadas a pé nem de carro.",
        "Evite o contato com a água da enchente, que pode estar contaminada. Se precisar sair, use calçado fechado e "
        "mantenha distância de postes, fios caídos e bueiros sem tampa.",
        "Quem está em local seguro deve permanecer nele. Acompanhe os avisos oficiais e só retorne para casa quando a "
        "Defesa Civil informar que não há mais risco.",
    ]),
    ("DEPOIS QUE A ÁGUA BAIXAR", [
        "Antes de entrar em casa, observe se há rachaduras novas, paredes inclinadas ou cheiro de gás. Na dúvida, não "
        "entre e peça uma vistoria à Defesa Civil pelo telefone 199.",
        "Lave e desinfete pisos, paredes e objetos que tiveram contato com a água. Descarte alimentos e remédios "
        "atingidos pela enchente, mesmo que pareçam em bom estado.",
        "Registre o problema no canal de atendimento da prefeitura para que a equipe de zeladoria programe a limpeza de "
        "bueiros e a retirada de entulho da via.",
        "Não jogue lixo nem entulho em córregos e bocas de lobo. O entupimento da drenagem é uma das principais causas de "
        "alagamento em vias urbanas, e a limpeza depende também da colaboração dos moradores.",
    ]),
]


def gerar_pdf() -> None:
    """PDF de três páginas com cabeçalho, rodapé, número de página e hifenização no fim das linhas."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def hifenizar(texto: str, largura: int = 62) -> list[str]:
        linhas, atual = [], ""
        for palavra in texto.split():
            if len(atual) + len(palavra) + 1 <= largura:
                atual = f"{atual} {palavra}".strip()
            elif len(palavra) > 9 and largura - len(atual) > 6:
                corte = max(4, largura - len(atual) - 2)
                linhas.append(f"{atual} {palavra[:corte]}-".strip())
                atual = palavra[corte:]
            else:
                linhas.append(atual)
                atual = palavra
        return [*linhas, atual]

    pdf = canvas.Canvas(str(AQUI / "cartilha_chuvas_sintetica.pdf"), pagesize=A4)
    largura, altura = A4
    for numero, (titulo, paragrafos) in enumerate(CARTILHA, start=1):
        pdf.setFont("Helvetica", 9)
        pdf.drawString(60, altura - 40, "Cartilha de exemplo - Zela (documento sintético)")
        pdf.drawString(60, 40, "Projeto Zela - Global Solution 2026.2")
        pdf.drawRightString(largura - 60, 40, f"Página {numero} de {len(CARTILHA)}")
        y = altura - 90
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(60, y, titulo)
        y -= 34
        pdf.setFont("Helvetica", 11)
        for paragrafo in paragrafos:
            for linha in hifenizar(paragrafo):
                pdf.drawString(60, y, linha)
                y -= 16
            y -= 14
        pdf.showPage()
    pdf.save()


def gerar_docx() -> None:
    from docx import Document

    doc = Document()
    doc.add_heading("Procedimento interno: pedido de poda de árvore (exemplo sintético)", level=1)
    doc.add_paragraph("Documento de exemplo, escrito para o teste da ferramenta. Descreve um fluxo fictício de atendimento.")
    doc.add_heading("Como registrar o pedido", level=2)
    doc.add_paragraph("O atendente confirma o endereço completo, o ponto de referência e se há galhos encostando na rede "
                      "elétrica. Pedidos com risco imediato são encaminhados na hora para a equipe de plantão.")
    for item in ("Endereço com número e CEP", "Foto da árvore, quando o cidadão tiver", "Descrição do risco observado"):
        doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Quando o pedido é urgente?", level=2)
    doc.add_paragraph("O pedido é urgente quando a árvore caiu, quando há galhos sobre fios ou quando a queda pode atingir "
                      "pessoas, casas ou veículos. Nesses casos o atendente orienta o cidadão a se afastar do local.")
    doc.add_heading("Contato para dúvidas", level=2)
    doc.add_paragraph("Dúvidas sobre este procedimento: maria.fictícia@exemplo.com.br ou (11) 98888-0000, com Maria Fictícia. "
                      "O atendimento ao público continua pelo telefone 156.")
    doc.save(str(AQUI / "procedimento_poda_sintetico.docx"))


def gerar_html() -> None:
    (AQUI / "pagina_iluminacao_sintetica.html").write_text("""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Iluminação pública: como pedir reparo (exemplo sintético)</title>
<style>body{font-family:sans-serif}</style><script>console.log("rastreamento");</script></head>
<body>
<nav><a href="/">Início</a> <a href="/servicos">Serviços</a> <a href="/contato">Contato</a></nav>
<header><p>Portal de exemplo</p></header>
<main>
<h1>Iluminação pública: como pedir reparo</h1>
<p>Compartilhe</p>
<p>Página de exemplo, escrita para o teste da ferramenta de construção de corpus.</p>
<h2>Como pedir o conserto de uma lâmpada apagada</h2>
<p>Informe o endereço do poste e, se possível, o número da plaqueta fixada nele. O pedido pode ser feito pela central
de atendimento da prefeitura.</p>
<ul><li>Lâmpada apagada à noite</li><li>Lâmpada acesa durante o dia</li><li>Poste danificado ou inclinado</li></ul>
<h2>O que não é iluminação pública?</h2>
<p>Fio partido, falta de energia em casa e transformador com defeito são atendidos pela distribuidora de energia, e
não pela prefeitura. Fio caído é emergência: afaste-se e ligue 193.</p>
<p>Imprimir</p>
<p>Voltar ao topo</p>
</main>
<footer><p>Todos os direitos reservados. Siga-nos nas redes sociais.</p></footer>
<form><input name="busca"><button>Buscar</button></form>
</body></html>
""", encoding="utf-8")


def gerar_csv() -> None:
    linhas = [
        ("pergunta", "resposta"),
        ("Como eu registro um problema no Zela?", "Na aba Relatar problema, descreva o que está acontecendo e informe o CEP. "
         "A inteligência artificial sugere o tipo e a urgência, você confere e confirma, e recebe um protocolo."),
        ("O Zela guarda o meu CPF?", "Não. CPF, telefone, e-mail e placas são removidos do texto antes da análise e antes "
         "de o relato ser guardado."),
        ("O prazo mostrado pelo Zela é garantido?", "Não. Os prazos são referências e não são prazos oficiais do órgão responsável."),
        ("O que significa a situação Encaminhada?", "Significa que o caso foi enviado ao órgão responsável pelo serviço."),
        ("O Zela substitui o telefone de emergência?", "Não. Em caso de risco à vida, ligue 193 (Bombeiros) ou 199 (Defesa Civil)."),
        ("Posso anexar uma foto ao relato?", "Sim. A foto é analisada para sinais de fissura e não fica armazenada."),
    ]
    (AQUI / "perguntas_sobre_o_zela.csv").write_text("\n".join(";".join(f'"{c}"' for c in linha) for linha in linhas) + "\n",
                                                      encoding="utf-8")


def gerar_jsonl() -> None:
    """Relatos fictícios de cidadãos, com dados pessoais inventados para testar o mascaramento."""
    relatos = [
        "Tem um buraco grande na Rua das Flores, em frente ao número 120. Meu CPF é 123.456.789-09 e meu celular é (11) 98765-4321.",
        "A lâmpada do poste da esquina está apagada há duas semanas. Podem me avisar pelo e-mail joao.ficticio@exemplo.com.",
        "O bueiro da rua de trás está entupido e alaga toda vez que chove. O carro de placa ABC1D23 ficou preso na água ontem.",
        "Tem um buraco grande na Rua das Flores, em frente ao número 120. Meu CPF é 123.456.789-09 e meu celular é (11) 98765-4321.",
    ]
    (AQUI / "relatos_sinteticos.jsonl").write_text("".join(json.dumps({"texto": r}, ensure_ascii=False) + "\n" for r in relatos),
                                                   encoding="utf-8")


if __name__ == "__main__":
    gerar_pdf()
    gerar_docx()
    gerar_html()
    gerar_csv()
    gerar_jsonl()
    print("Exemplos gerados em", AQUI)
