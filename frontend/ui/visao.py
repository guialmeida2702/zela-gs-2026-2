"""Apresentação do resultado da visão computacional (fissuras): áreas sinalizadas desenhadas sobre a foto.

A foto fica só na sessão do navegador, para mostrar o resultado. A API não guarda a imagem.
"""

import io

from PIL import Image, ImageDraw, ImageOps

COR = (185, 28, 28)  # vermelho escuro: contraste alto sobre concreto e asfalto


def sobrepor_blocos(conteudo: bytes, resultado: dict) -> bytes:
    """Redimensiona a foto como o modelo viu e desenha as áreas acima do limiar, com a probabilidade."""
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(conteudo))).convert("RGB")
    im = im.resize((resultado["largura"], resultado["altura"]))
    desenho = ImageDraw.Draw(im, "RGBA")
    for b in resultado.get("blocos", []):
        if b["p"] < resultado["limiar"]:
            continue
        x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"] - 1, b["y"] + b["h"] - 1
        desenho.rectangle([x0, y0, x1, y1], outline=(*COR, 255), width=4, fill=(*COR, 35))
        rotulo = f"fissura {b['p']:.0%}"
        desenho.rectangle([x0 + 4, y0 + 4, x0 + 10 + 7 * len(rotulo), y0 + 22], fill=(0, 0, 0, 190))
        desenho.text((x0 + 8, y0 + 7), rotulo, fill=(255, 255, 255, 255))
    buffer = io.BytesIO()
    im.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def evidencia_para_relato(resultado: dict) -> dict:
    """Só o resumo da análise vai junto do relato (sem a imagem)."""
    return {k: resultado[k] for k in ("classe", "probabilidade_max", "blocos_com_fissura", "total_blocos", "modelo")}


def resumo(resultado: dict) -> str:
    if resultado["classe"] == "com_fissura":
        return (f"Sinais de fissura em **{resultado['blocos_com_fissura']} de {resultado['total_blocos']}** áreas da foto "
                f"(confiança máxima de {resultado['probabilidade_max']:.0%}). Isso indica que vale uma inspeção técnica. "
                "A foto sozinha **não mostra a gravidade** da fissura.")
    return ("Nenhum sinal de fissura acima do limiar nesta foto. Isso não garante que a estrutura esteja boa: "
            "se você vê rachaduras crescendo, conte no relato.")
