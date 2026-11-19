"""Previsão de chuva (Open-Meteo, dado aberto e sem chave) para cruzar com o relato."""

import logging

import httpx
from cachetools import TTLCache

from app.schemas.analise import Clima

log = logging.getLogger("zela.clima")


class ProvedorClima:
    URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, http: httpx.AsyncClient, *, timeout_s: float, habilitado: bool = True):
        self.http = http
        self.timeout_s = timeout_s
        self.habilitado = habilitado
        self._cache: TTLCache[str, Clima | None] = TTLCache(maxsize=512, ttl=1800)

    async def previsao_chuva(self, lat: float, lon: float) -> Clima | None:
        if not self.habilitado:
            return None
        chave = f"{lat:.2f},{lon:.2f}"  # ~1 km: reaproveita a consulta para relatos próximos
        if chave in self._cache:
            return self._cache[chave]
        params = {
            "latitude": round(lat, 3),
            "longitude": round(lon, 3),
            "daily": "precipitation_sum,precipitation_probability_max",
            "forecast_days": 3,
            "timezone": "America/Sao_Paulo",
        }
        clima: Clima | None = None
        try:
            resp = await self.http.get(self.URL, params=params, timeout=self.timeout_s)
            resp.raise_for_status()
            diario = resp.json().get("daily", {})
            chuvas = [v or 0.0 for v in diario.get("precipitation_sum", [])]
            probs = [v for v in diario.get("precipitation_probability_max", []) if v is not None]
            if chuvas:
                total = round(sum(chuvas), 1)
                prob = int(max(probs)) if probs else None
                if total >= 30:
                    resumo = f"chuva forte prevista: cerca de {total:.0f} mm nos próximos 3 dias"
                elif total >= 5:
                    resumo = f"chuva moderada prevista: cerca de {total:.0f} mm nos próximos 3 dias"
                else:
                    resumo = "pouca ou nenhuma chuva prevista para os próximos 3 dias"
                clima = Clima(chuva_prevista_mm_72h=total, prob_max_chuva_pct=prob, resumo=resumo)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            log.info("Open-Meteo indisponível: %s", type(exc).__name__)
            return None  # não guarda falha no cache
        self._cache[chave] = clima
        return clima
