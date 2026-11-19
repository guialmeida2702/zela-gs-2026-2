"""LLM + base de conhecimento + memória: delega ao Assistente Zela (API), que tem o system prompt
(papel, tom e limites), a busca nas fontes oficiais (RAG) e as proteções contra respostas sem fonte.
A memória da conversa fica aqui e é enviada a cada turno (perguntas de continuação funcionam).
"""

import time
from dataclasses import dataclass, field

import httpx


@dataclass
class Memoria:
    max_mensagens: int = 8
    mensagens: list[dict] = field(default_factory=list)

    def adicionar(self, papel: str, texto: str) -> None:
        self.mensagens.append({"papel": papel, "texto": texto[:1500]})
        self.mensagens = self.mensagens[-self.max_mensagens:]

    def limpar(self) -> None:
        self.mensagens.clear()


class Cerebro:
    INDISPONIVEL = "Desculpe, não consegui falar com o serviço agora. Tente de novo em instantes. Em emergência, ligue 193 ou 199."

    def __init__(self, api_url: str, timeout_s: float = 300):
        self.api_url = api_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout_s)

    def responder(self, pergunta: str, memoria: Memoria) -> dict:
        inicio = time.perf_counter()
        try:
            r = self.http.post(f"{self.api_url}/assistente/perguntar",
                               json={"pergunta": pergunta[:500], "historico": memoria.mensagens[-8:]})
            r.raise_for_status()
            dados = r.json()
        except (httpx.HTTPError, ValueError) as exc:  # caminho seguro: fala um aviso em vez de travar
            return {"resposta": self.INDISPONIVEL, "fontes": [], "sem_evidencia": True, "fora_do_escopo": False,
                    "erro": type(exc).__name__, "segundos": round(time.perf_counter() - inicio, 2), "modelo": "-"}
        return {"resposta": dados["resposta"], "fontes": [c["orgao"] for c in dados["citacoes"]],
                "sem_evidencia": dados["sem_evidencia"], "fora_do_escopo": dados["fora_do_escopo"],
                "bloqueios": dados.get("bloqueios", []), "segundos": round(time.perf_counter() - inicio, 2),
                "modelo": dados.get("modelo", "-")}
