"""Limite de requisições por IP (janela deslizante em memória).

Protege o endpoint que chama o LLM contra abuso e custo descontrolado.
Para várias instâncias, troque por Redis.
"""

import time
from collections import defaultdict, deque

from app.core.erros import LimiteExcedido


class LimitadorTaxa:
    def __init__(self, maximo: int, janela_s: float = 60.0):
        self.maximo = maximo
        self.janela_s = janela_s
        self._eventos: dict[str, deque[float]] = defaultdict(deque)

    def verificar(self, chave: str) -> None:
        if self.maximo <= 0:
            return
        agora = time.monotonic()
        fila = self._eventos[chave]
        while fila and agora - fila[0] > self.janela_s:
            fila.popleft()
        if len(fila) >= self.maximo:
            raise LimiteExcedido()
        fila.append(agora)
