"""Tema 3 — Integração com APIs: API do Zela (login de gestor, fila, atualização) e Open-Meteo (previsão de chuva).
Tema 5 (IA de outra disciplina) — modelo ONNX de visão computacional aplicado às fotos de vistoria.
"""

import json
from pathlib import Path

import httpx
import numpy as np
from PIL import Image


class ApiZela:
    def __init__(self, cliente: httpx.Client, base: str):
        self.c = cliente
        self.base = base.rstrip("/")
        self.token: str | None = None

    def login(self, usuario: str, senha: str) -> None:
        r = self.c.post(f"{self.base}/auth/login", json={"usuario": usuario, "senha": senha})
        r.raise_for_status()
        self.token = r.json()["access_token"]

    def _cab(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def fila(self) -> list[dict]:
        r = self.c.get(f"{self.base}/gestor/solicitacoes", headers=self._cab(), params={"limite": 2000})
        r.raise_for_status()
        return r.json()

    def atualizar(self, protocolo: str, mudancas: dict) -> dict:
        r = self.c.patch(f"{self.base}/gestor/solicitacoes/{protocolo}", headers=self._cab(), json=mudancas)
        r.raise_for_status()
        return r.json()

    def indicadores(self) -> dict:
        r = self.c.get(f"{self.base}/gestor/indicadores", headers=self._cab())
        r.raise_for_status()
        return r.json()


def previsao_chuva_sp(cliente: httpx.Client, lat: float = -23.55, lon: float = -46.63) -> float:
    r = cliente.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "daily": "precipitation_sum", "forecast_days": 3, "timezone": "America/Sao_Paulo"})
    r.raise_for_status()
    return round(sum(v or 0 for v in r.json()["daily"]["precipitation_sum"]), 1)


class ClassificadorFissuras:
    """Usa o modelo treinado na disciplina de Visão Computacional (visao_computacional/modelos)."""

    def __init__(self, pasta_modelo: Path):
        import onnxruntime as ort

        self.cfg = json.loads((pasta_modelo / "preprocessamento.json").read_text(encoding="utf-8"))
        self.sessao = ort.InferenceSession(str(pasta_modelo / self.cfg["modelo"]), providers=["CPUExecutionProvider"])
        self.media = np.array(self.cfg["media"], dtype=np.float32)
        self.desvio = np.array(self.cfg["desvio"], dtype=np.float32)

    def probabilidade(self, caminho: Path) -> float:
        tam = self.cfg["tamanho"]
        im = Image.open(caminho).convert("RGB").resize((tam, tam), Image.BILINEAR)
        x = ((np.asarray(im, dtype=np.float32) / 255.0 - self.media) / self.desvio).transpose(2, 0, 1)[None]
        return float(self.sessao.run(None, {self.sessao.get_inputs()[0].name: x})[0][0, 1])

    @property
    def limiar(self) -> float:
        return float(self.cfg["limiar"])
