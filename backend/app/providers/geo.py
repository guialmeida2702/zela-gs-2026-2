"""Dados abertos de endereço: BrasilAPI (CEP v2, com coordenadas), ViaCEP e Nominatim/OpenStreetMap.

Todas as consultas têm timeout curto e falham de forma silenciosa: o endereço
enriquece a análise, mas a falta dele não pode impedir o cidadão de relatar.
"""

import asyncio
import logging
import time

import httpx
from cachetools import TTLCache

from app.schemas.analise import Endereco

log = logging.getLogger("zela.geo")


class ProvedorGeo:
    def __init__(self, http: httpx.AsyncClient, *, timeout_s: float, user_agent: str, habilitado: bool = True):
        self.http = http
        self.timeout_s = timeout_s
        self.user_agent = user_agent
        self.habilitado = habilitado
        self._cache_cep: TTLCache[str, Endereco | None] = TTLCache(maxsize=2048, ttl=24 * 3600)
        self._cache_geo: TTLCache[str, tuple[float, float] | None] = TTLCache(maxsize=2048, ttl=24 * 3600)
        self._lock_nominatim = asyncio.Lock()  # política do Nominatim: no máximo 1 requisição por segundo
        self._ultima_chamada_nominatim = 0.0

    async def _get_json(self, url: str, **kwargs) -> dict | list | None:
        try:
            resp = await self.http.get(url, timeout=self.timeout_s, **kwargs)
            if resp.status_code != 200:
                return None
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.info("Fonte externa indisponível (%s): %s", url.split("?")[0], type(exc).__name__)
            return None

    async def buscar_cep(self, cep: str) -> Endereco | None:
        if not self.habilitado:
            return None
        if cep in self._cache_cep:
            return self._cache_cep[cep]

        endereco: Endereco | None = None
        dados = await self._get_json(f"https://brasilapi.com.br/api/cep/v2/{cep}")
        if isinstance(dados, dict) and dados.get("city"):
            coords = (dados.get("location") or {}).get("coordinates") or {}
            lat, lon = coords.get("latitude"), coords.get("longitude")
            endereco = Endereco(
                cep=cep,
                logradouro=dados.get("street") or None,
                bairro=dados.get("neighborhood") or None,
                cidade=dados["city"],
                uf=dados.get("state", ""),
                latitude=float(lat) if lat else None,
                longitude=float(lon) if lon else None,
                fonte="BrasilAPI",
            )
        else:
            dados = await self._get_json(f"https://viacep.com.br/ws/{cep}/json/")
            if isinstance(dados, dict) and not dados.get("erro") and dados.get("localidade"):
                endereco = Endereco(
                    cep=cep,
                    logradouro=dados.get("logradouro") or None,
                    bairro=dados.get("bairro") or None,
                    cidade=dados["localidade"],
                    uf=dados.get("uf", ""),
                    fonte="ViaCEP",
                )
        if endereco:  # falhas de rede não ficam em cache
            self._cache_cep[cep] = endereco
        return endereco

    async def geocodificar(self, endereco: Endereco, numero: str | None = None) -> tuple[float, float] | None:
        """Coordenadas via Nominatim (OpenStreetMap) quando o CEP não trouxe lat/lon."""
        if not self.habilitado:
            return None
        rua = " ".join(p for p in (numero, endereco.logradouro) if p)
        chave = f"{rua}|{endereco.cidade}|{endereco.uf}"
        if chave in self._cache_geo:
            return self._cache_geo[chave]
        params = {"city": endereco.cidade, "state": endereco.uf, "country": "Brasil", "format": "json", "limit": 1}
        if rua:
            params["street"] = rua
        async with self._lock_nominatim:
            espera = 1.0 - (time.monotonic() - self._ultima_chamada_nominatim)
            if espera > 0:
                await asyncio.sleep(espera)
            dados = await self._get_json(
                "https://nominatim.openstreetmap.org/search", params=params, headers={"User-Agent": self.user_agent}
            )
            self._ultima_chamada_nominatim = time.monotonic()
        coords = None
        if isinstance(dados, list) and dados:
            try:
                coords = (float(dados[0]["lat"]), float(dados[0]["lon"]))
            except (KeyError, ValueError, TypeError):
                coords = None
        if coords:
            self._cache_geo[chave] = coords
        return coords
