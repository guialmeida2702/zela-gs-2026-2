"""Teste de ponta a ponta no navegador (Playwright): percorre o que o cidadão e o gestor fazem.

Não entra na suíte do pytest porque precisa da API e do front no ar.

    pip install playwright && playwright install chromium
    python frontend/tests/e2e/fluxo_completo.py --url http://localhost:8501 --senha <GESTOR_SENHA>

Fluxo: relato com foto → análise da IA → revisão e confirmação → protocolo → consulta do
protocolo → pergunta ao assistente → login do gestor → tratamento na fila → monitoramento
por imagens. Sai com código 0 quando todas as etapas passam e grava uma captura por etapa.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[3]
FOTOS = RAIZ / "robo_rpa" / "dados" / "entrada" / "fotos_vistoria"


def esperar(page: Page, texto: str, timeout_s: int = 120) -> None:
    page.get_by_text(texto, exact=False).first.wait_for(timeout=timeout_s * 1000)


def foto_de_teste(destino: Path) -> Path:
    """Mosaico de recortes públicos (alguns com fissura) para simular a foto de um muro."""
    nomes = ["sem_fissura_00176", "fissura_01135", "sem_fissura_00806", "fissura_02617"]
    im = Image.new("RGB", (227 * 2, 227 * 2))
    for k, n in enumerate(nomes):
        im.paste(Image.open(FOTOS / f"{n}.jpg").convert("RGB"), ((k % 2) * 227, (k // 2) * 227))
    im.save(destino, quality=90)
    return destino


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--usuario", default="gestor")
    ap.add_argument("--senha", required=True)
    ap.add_argument("--saida", default="/tmp/zela_e2e")
    ap.add_argument("--espera-ia", type=int, default=300, help="segundos de tolerância para respostas do modelo")
    args = ap.parse_args()

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    etapas: list[tuple[str, bool, str]] = []

    def etapa(nome: str, ok: bool, detalhe: str = "") -> None:
        etapas.append((nome, ok, detalhe))
        print(f"[{'ok   ' if ok else 'FALHA'}] {nome}" + (f" · {detalhe}" if detalhe else ""), flush=True)

    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1366, "height": 1000})
        try:
            # 1. relato com foto
            page.goto(args.url)
            esperar(page, "Conte o que está acontecendo", 90)
            page.get_by_role("textbox", name="Descreva o problema (obrigatório)").fill(
                "Apareceu uma rachadura grande no muro da escola, perto do portão. Ela aumentou depois da chuva."
            )
            page.get_by_role("textbox", name="CEP do local (obrigatório)").fill("01001-000")
            page.locator("input[type=file]").first.set_input_files(str(foto_de_teste(saida / "foto_muro.jpg")))
            time.sleep(2)
            page.get_by_role("button", name="Analisar meu relato").click()
            esperar(page, "Confira o que a IA entendeu", args.espera_ia)
            etapa("IA analisa o relato e mostra a revisão", True)
            etapa("resultado da foto aparece na revisão", page.get_by_text("O que a IA viu na sua foto").count() > 0)
            page.screenshot(path=str(saida / "1_revisao.png"), full_page=True)

            # 2. confirmação humana (sem consentimento não registra)
            page.get_by_role("button", name="Confirmar e registrar").click()
            time.sleep(3)
            etapa("sem consentimento LGPD o registro não acontece", page.get_by_text("Seu protocolo").count() == 0)
            page.get_by_text("Autorizo o uso destas informações", exact=False).first.click()
            page.get_by_role("button", name="Confirmar e registrar").click()
            esperar(page, "Seu protocolo", 60)
            achado = re.search(r"ZL-\d{6}-[A-Z0-9]{6}", page.inner_text("body"))
            protocolo = achado.group(0) if achado else ""
            etapa("protocolo gerado", bool(protocolo), protocolo)
            page.screenshot(path=str(saida / "2_protocolo.png"), full_page=True)

            # 3. acompanhamento pelo protocolo
            page.get_by_role("tab", name="🗂️ Minhas solicitações").click()
            esperar(page, "Minhas solicitações", 30)
            page.get_by_role("textbox", name="Acompanhar um protocolo").fill(protocolo)
            page.get_by_role("button", name="Consultar").click()
            time.sleep(4)
            etapa("cidadão acompanha pelo protocolo", page.get_by_text(protocolo).count() > 0)
            page.screenshot(path=str(saida / "3_acompanhar.png"), full_page=True)

            # 4. assistente com fontes
            page.get_by_role("tab", name="💬 Tire dúvidas").click()
            esperar(page, "Experimente perguntar", 30)
            page.get_by_role("button", name="Como peço a poda de uma árvore na calçada?").click()
            esperar(page, "Fontes consultadas", args.espera_ia)
            etapa("assistente responde citando fontes", True)
            page.screenshot(path=str(saida / "4_assistente.png"), full_page=True)

            # 5. painel público
            page.get_by_role("tab", name="🗺️ Painel da cidade").click()
            time.sleep(5)
            etapa("painel da cidade carrega", page.get_by_text("Não foi possível", exact=False).count() == 0)
            page.screenshot(path=str(saida / "5_painel.png"), full_page=True)

            # 6. gestor: login, fila e tratamento
            page.get_by_text("Gestor público").first.click()
            esperar(page, "Entrar como gestor", 30)
            page.get_by_role("textbox", name="Usuário").fill(args.usuario)
            page.get_by_role("textbox", name="Senha").fill("senha-errada")
            page.get_by_role("button", name="Entrar").click()
            time.sleep(3)
            etapa("senha errada não abre a área do gestor", page.get_by_role("tab", name="📥 Fila de atendimento").count() == 0)
            page.get_by_role("textbox", name="Senha").fill(args.senha)
            page.get_by_role("button", name="Entrar").click()
            page.get_by_role("tab", name="📥 Fila de atendimento").wait_for(timeout=60000)
            time.sleep(3)
            etapa("gestor entra e vê a fila", True)
            page.get_by_role("textbox", name="Buscar protocolo").fill(protocolo)
            page.keyboard.press("Enter")
            time.sleep(4)
            etapa("relato recém-criado é achado pelo protocolo na fila",
                  page.get_by_text(f"Tratando {protocolo}").count() > 0, protocolo)
            page.screenshot(path=str(saida / "6_fila.png"), full_page=True)

            page.get_by_role("tab", name="📊 Indicadores e qualidade da IA").click()
            time.sleep(4)
            etapa("indicadores carregam", page.get_by_text("Não foi possível", exact=False).count() == 0)
            page.screenshot(path=str(saida / "7_indicadores.png"), full_page=True)

            # 7. monitoramento por imagens
            page.get_by_role("tab", name="🖼️ Monitoramento por imagens").click()
            esperar(page, "Monitoramento de estruturas por imagens", 30)
            fotos = [str(f) for f in sorted(FOTOS.glob("fissura_*.jpg"))[:4] + sorted(FOTOS.glob("sem_fissura_*.jpg"))[:4]]
            page.locator("input[type=file]").last.set_input_files(fotos)
            time.sleep(3)
            page.get_by_role("button", name="Analisar sequência").click()
            esperar(page, "Fotos para vistoria prioritária", 120)
            etapa("monitoramento por imagens sinaliza fotos", True)
            page.screenshot(path=str(saida / "8_monitoramento.png"), full_page=True)
        except Exception as exc:  # a captura ajuda a entender onde o fluxo parou
            page.screenshot(path=str(saida / "erro.png"), full_page=True)
            etapa("fluxo interrompido", False, f"{type(exc).__name__}: {str(exc)[:200]}")
        finally:
            nav.close()

    falhas = [n for n, ok, _ in etapas if not ok]
    print(f"\n{len(etapas) - len(falhas)}/{len(etapas)} etapas passaram. Capturas em {saida}.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
