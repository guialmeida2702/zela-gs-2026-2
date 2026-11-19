"""Cliente HTTP da API Zela. Única porta de saída do front-end.

Não depende do Streamlit (pode ser testado isoladamente). Toda falha vira um
ErroApi com mensagem pronta para o cidadão; o detalhe técnico fica só em
`erro.tecnico`, nunca exibido na interface.
"""

from typing import Any

import httpx

MENSAGENS = {
    "API_FORA_DO_AR": (
        "Não conseguimos falar com o serviço agora. Verifique sua internet ou tente de novo em alguns minutos. "
        "Se for urgente, ligue 156."
    ),
    "TEMPO_ESGOTADO": "O serviço demorou demais para responder. Seu texto continua aqui: tente enviar de novo.",
    "RESPOSTA_INVALIDA": "Recebemos uma resposta inesperada do serviço. Tente novamente em instantes.",
    "ERRO_DESCONHECIDO": "Algo deu errado. Tente novamente em alguns minutos.",
}


class ErroApi(Exception):
    def __init__(self, codigo: str, mensagem: str | None = None, *, status: int | None = None,
                 campos: dict[str, str] | None = None, tecnico: str | None = None):
        self.codigo = codigo
        self.mensagem = mensagem or MENSAGENS.get(codigo, MENSAGENS["ERRO_DESCONHECIDO"])
        self.status = status
        self.campos = campos or {}
        self.tecnico = tecnico
        super().__init__(f"{codigo}: {tecnico or self.mensagem}")

    @property
    def fora_do_ar(self) -> bool:
        return self.codigo in {"API_FORA_DO_AR", "TEMPO_ESGOTADO"}


class ClienteZela:
    def __init__(self, base_url: str, timeout_s: float = 40.0, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s, connect=5.0),
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "zela-frontend/1.0"},
        )

    def _req(self, metodo: str, caminho: str, *, token: str | None = None,
             exigir: tuple[str, ...] = (), lista: bool = False, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = self._http.request(metodo, caminho, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:  # (subclasse de TransportError: tratar antes)
            raise ErroApi("TEMPO_ESGOTADO", tecnico=repr(exc)) from exc
        except httpx.TransportError as exc:  # conexão recusada, DNS, rede
            raise ErroApi("API_FORA_DO_AR", tecnico=repr(exc)) from exc

        try:
            corpo = resp.json()
        except ValueError as exc:
            # Proxies/plataformas costumam devolver HTML em 502/503 quando a API está fora
            codigo = "API_FORA_DO_AR" if resp.status_code >= 500 else "RESPOSTA_INVALIDA"
            raise ErroApi(codigo, status=resp.status_code, tecnico=f"corpo não-JSON (HTTP {resp.status_code})") from exc

        if resp.status_code >= 400:
            erro = corpo.get("erro") if isinstance(corpo, dict) else None
            if isinstance(erro, dict) and erro.get("mensagem"):
                raise ErroApi(erro.get("codigo", "ERRO"), erro["mensagem"], status=resp.status_code,
                              campos=erro.get("campos"))
            raise ErroApi("ERRO_DESCONHECIDO", status=resp.status_code, tecnico=str(corpo)[:300])

        # Validação mínima do contrato: protege a interface de respostas fora do formato
        if lista and not isinstance(corpo, list):
            raise ErroApi("RESPOSTA_INVALIDA", tecnico="esperava lista")
        if exigir and (not isinstance(corpo, dict) or any(c not in corpo for c in exigir)):
            raise ErroApi("RESPOSTA_INVALIDA", tecnico=f"campos ausentes: {exigir}")
        return corpo

    # ---------------- público / cidadão ----------------
    def saude(self) -> dict:
        return self._req("GET", "/health", exigir=("status", "ia"))

    def categorias(self) -> list[dict]:
        return self._req("GET", "/categorias", lista=True)

    def buscar_cep(self, cep: str) -> dict:
        return self._req("GET", f"/enderecos/{cep}", exigir=("cidade", "uf"))

    def analisar(self, relato: dict) -> dict:
        return self._req("POST", "/relatos/analisar", json=relato,
                         exigir=("analise_id", "analise", "encaminhamento", "contexto"))

    def registrar(self, confirmacao: dict) -> dict:
        return self._req("POST", "/solicitacoes", json=confirmacao, exigir=("protocolo", "status"))

    def consultar(self, protocolo: str) -> dict:
        return self._req("GET", f"/solicitacoes/{protocolo.strip()}", exigir=("protocolo", "status"))

    def avaliar(self, protocolo: str, util: bool, comentario: str | None = None) -> dict:
        return self._req("POST", f"/solicitacoes/{protocolo}/feedback",
                         json={"util": util, "comentario": comentario}, exigir=("protocolo",))

    def publicas(self, dias: int = 90) -> list[dict]:
        return self._req("GET", "/solicitacoes/publicas", params={"dias": dias}, lista=True)

    # ---------------- módulos de IA ----------------
    def analisar_imagem(self, nome: str, conteudo: bytes, tipo: str) -> dict:
        return self._req("POST", "/visao/analisar", files={"arquivo": (nome, conteudo, tipo)},
                         exigir=("classe", "probabilidade_max", "blocos", "largura", "altura"))

    def analisar_lote(self, arquivos: list[tuple[str, bytes, str]]) -> dict:
        return self._req("POST", "/visao/lote", files=[("arquivos", a) for a in arquivos],
                         exigir=("resultados", "imagens"), timeout=httpx.Timeout(120.0, connect=5.0))

    def perguntar(self, pergunta: str, historico: list[dict], protocolo: str | None = None,
                  timeout_s: float = 120.0) -> dict:
        corpo = {"pergunta": pergunta, "historico": historico[-12:], "protocolo": protocolo or None}
        return self._req("POST", "/assistente/perguntar", json=corpo, exigir=("resposta", "citacoes", "sem_evidencia"),
                         timeout=httpx.Timeout(timeout_s, connect=5.0))

    # ---------------- gestor ----------------
    def login(self, usuario: str, senha: str) -> dict:
        return self._req("POST", "/auth/login", json={"usuario": usuario, "senha": senha},
                         exigir=("access_token", "expira_em"))

    def gestor_listar(self, token: str) -> list[dict]:
        return self._req("GET", "/gestor/solicitacoes", token=token, lista=True)

    def gestor_atualizar(self, token: str, protocolo: str, mudancas: dict) -> dict:
        return self._req("PATCH", f"/gestor/solicitacoes/{protocolo}", token=token, json=mudancas,
                         exigir=("protocolo", "status"))

    def gestor_indicadores(self, token: str) -> dict:
        return self._req("GET", "/gestor/indicadores", token=token, exigir=("total",))
