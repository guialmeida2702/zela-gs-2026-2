"""Captura telas dos novos módulos do front (foto no relato, assistente e monitoramento por imagens) com Playwright.

Pré-requisitos: API e front rodando (front em http://localhost:8501), Playwright com Chromium.
Uso: python docs/capturar_telas.py
"""

import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
IMG = RAIZ / "docs" / "img"
FOTOS = RAIZ / "robo_rpa" / "dados" / "entrada" / "fotos_vistoria"
URL = "http://localhost:8501"


def foto_muro() -> Path:
    """Mosaico 4 x 3 de recortes (alguns com fissura) para simular uma foto de muro."""
    nomes = ["sem_fissura_00176", "fissura_01135", "sem_fissura_00806", "sem_fissura_08803",
             "sem_fissura_08833", "fissura_02617", "fissura_11792_1", "sem_fissura_08841",
             "sem_fissura_15063", "sem_fissura_16351", "fissura_17861_1", "sem_fissura_16610"]
    im = Image.new("RGB", (227 * 4, 227 * 3))
    for k, n in enumerate(nomes):
        im.paste(Image.open(FOTOS / f"{n}.jpg").convert("RGB"), ((k % 4) * 227, (k // 4) * 227))
    destino = Path("/tmp/foto_muro.jpg")
    im.save(destino, quality=90)
    return destino


def esperar_texto(page, texto: str, timeout_s: int = 240) -> None:
    page.get_by_text(texto, exact=False).first.wait_for(timeout=timeout_s * 1000)


def main() -> None:
    import sys
    pular_relato = "--sem-relato" in sys.argv
    muro = foto_muro()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1366, "height": 1000}, device_scale_factor=1)
        try:
            _capturar(page, muro, pular_relato)
        except Exception:
            page.screenshot(path="/tmp/erro_captura.png")
            raise
        finally:
            nav.close()
    for nome in ("relato_foto_revisao", "assistente_chat", "gestor_monitoramento"):
        if (IMG / f"{nome}.png").exists():
            print(nome, Image.open(IMG / f"{nome}.png").size)


def _capturar(page, muro: Path, pular_relato: bool) -> None:
        page.goto(URL)
        esperar_texto(page, "Conte o que está acontecendo", 90)
        if pular_relato:
            _assistente_e_gestor(page)
            return
        # ---- relato com foto
        page.get_by_role("textbox", name="Descreva o problema (obrigatório)").fill(
            "Apareceu uma rachadura grande no muro da escola, perto do portão de entrada. Ela aumentou depois da chuva.")
        page.get_by_role("textbox", name="CEP do local (obrigatório)").fill("01001-000")
        page.locator("input[type=file]").first.set_input_files(str(muro))
        time.sleep(2)
        page.get_by_role("button", name="Analisar meu relato").click()
        esperar_texto(page, "O que a IA viu na sua foto", 300)
        time.sleep(3)
        alvo = page.get_by_text("O que a IA viu na sua foto").first
        alvo.scroll_into_view_if_needed()
        page.screenshot(path=str(IMG / "relato_foto_revisao.png"), full_page=True)
        _assistente_e_gestor(page)


def _assistente_e_gestor(page) -> None:
        # ---- assistente
        page.get_by_role("tab", name="💬 Tire dúvidas").click()
        time.sleep(4)
        esperar_texto(page, "Experimente perguntar", 30)
        page.get_by_role("button", name="Como peço a poda de uma árvore na calçada?").click()
        esperar_texto(page, "Fontes consultadas", 300)
        page.get_by_text("Fontes consultadas").first.click()
        time.sleep(2)
        page.screenshot(path=str(IMG / "assistente_chat.png"), full_page=True)
        # ---- gestor: monitoramento por imagens
        page.get_by_text("Gestor público").first.click()
        esperar_texto(page, "Entrar como gestor", 30)
        page.get_by_role("textbox", name="Usuário").fill("gestor")
        page.get_by_role("textbox", name="Senha").fill("demo123")
        page.get_by_role("button", name="Entrar").click()
        esperar_texto(page, "Fila de atendimento", 60)
        page.get_by_role("tab", name="🖼️ Monitoramento por imagens").click()
        esperar_texto(page, "Monitoramento de estruturas por imagens", 30)
        fotos = sorted(str(f) for f in FOTOS.glob("*.jpg") if "corrompida" not in f.name)[:12]
        page.locator("input[type=file]").last.set_input_files(fotos)
        time.sleep(3)
        page.get_by_role("button", name="Analisar sequência").click()
        esperar_texto(page, "Fotos para vistoria prioritária", 120)
        time.sleep(3)
        page.screenshot(path=str(IMG / "gestor_monitoramento.png"), full_page=True)


if __name__ == "__main__":
    main()
