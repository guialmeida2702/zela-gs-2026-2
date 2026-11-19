"""Visão computacional: identificação de possíveis fissuras em fotos (modelo ONNX treinado em visao_computacional/).

A foto é processada em memória e descartada; só o resultado numérico é devolvido.
Fotos grandes são reduzidas e divididas em blocos de 227 px (a mesma escala dos recortes de
treino), o que também localiza as áreas suspeitas. A saída sinaliza NECESSIDADE DE INSPEÇÃO:
a presença de fissura na imagem não indica gravidade nem segurança estrutural.
"""

import io
import json
import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger("zela.visao")

PASTA_MODELOS = Path(__file__).resolve().parent.parent / "modelos"
LADO_MAXIMO = 1135  # 5 blocos de 227 px no lado maior: equilíbrio entre detalhe e tempo de resposta


class ImagemInvalida(ValueError):
    pass


class ProvedorVisao:
    def __init__(self, pasta: Path = PASTA_MODELOS, threads: int = 2):
        self.disponivel = False
        self.config: dict = {}
        try:
            import onnxruntime as ort

            self.config = json.loads((pasta / "preprocessamento.json").read_text(encoding="utf-8"))
            opcoes = ort.SessionOptions()
            opcoes.intra_op_num_threads = threads
            self.sessao = ort.InferenceSession(str(pasta / self.config["modelo"]), opcoes, providers=["CPUExecutionProvider"])
            self.entrada = self.sessao.get_inputs()[0].name
            self.media = np.array(self.config["media"], dtype=np.float32)
            self.desvio = np.array(self.config["desvio"], dtype=np.float32)
            self.disponivel = True
        except Exception as exc:  # a API sobe mesmo sem o modelo; a rota responde 503 amigável
            log.warning("Modelo de visão indisponível: %s", exc)

    @property
    def limiar(self) -> float:
        return float(self.config.get("limiar", 0.5))

    def _tensor(self, im: Image.Image) -> np.ndarray:
        tam = self.config["tamanho"]
        arr = np.asarray(im.resize((tam, tam), Image.BILINEAR), dtype=np.float32) / 255.0
        return ((arr - self.media) / self.desvio).transpose(2, 0, 1)

    @staticmethod
    def abrir(conteudo: bytes) -> Image.Image:
        try:
            im = Image.open(io.BytesIO(conteudo))
            im.verify()
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(conteudo))).convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImagemInvalida("Não conseguimos abrir a imagem. Envie uma foto JPG ou PNG.") from exc
        if min(im.size) < 64:
            raise ImagemInvalida("A imagem é pequena demais para análise (mínimo de 64 pixels).")
        return im

    def analisar(self, im: Image.Image) -> dict:
        inicio = time.perf_counter()
        escala = min(1.0, LADO_MAXIMO / max(im.size))
        if escala < 1.0:
            im = im.resize((max(1, round(im.width * escala)), max(1, round(im.height * escala))), Image.BILINEAR)
        lado = self.config.get("bloco_px", 227)
        colunas, linhas = max(1, im.width // lado), max(1, im.height // lado)
        if colunas == 1 and linhas == 1:
            caixas = [(0, 0, im.width, im.height)]
        else:
            bw, bh = im.width / colunas, im.height / linhas
            caixas = [(round(c * bw), round(r * bh), round((c + 1) * bw), round((r + 1) * bh))
                      for r in range(linhas) for c in range(colunas)]
        lote = np.stack([self._tensor(im.crop(c)) for c in caixas])
        probs = self.sessao.run(None, {self.entrada: lote})[0][:, 1]
        sinalizados = [i for i, p in enumerate(probs) if p >= self.limiar]
        p_max = float(probs.max())
        return {
            "classe": "com_fissura" if sinalizados else "sem_fissura",
            "probabilidade_max": round(p_max, 4),
            "blocos_com_fissura": len(sinalizados),
            "total_blocos": len(caixas),
            "limiar": self.limiar,
            "largura": im.width,
            "altura": im.height,
            "blocos": [{"x": c[0], "y": c[1], "w": c[2] - c[0], "h": c[3] - c[1], "p": round(float(p), 4)}
                       for c, p in zip(caixas, probs, strict=True)],
            "latencia_ms": round((time.perf_counter() - inicio) * 1000, 1),
            "modelo": self.config.get("modelo", ""),
            "interpretacao": ("Sinais de fissura encontrados: recomenda-se inspeção técnica. A imagem não indica gravidade."
                              if sinalizados else "Nenhum sinal de fissura acima do limiar nesta imagem."),
        }
