"""O cliente HTTP transforma qualquer falha em mensagem amigável (sem detalhes técnicos)."""

import httpx
import pytest

from providers.api_client import ClienteZela, ErroApi


def _cliente(handler) -> ClienteZela:
    return ClienteZela("http://api.teste", transport=httpx.MockTransport(handler))


def test_api_fora_do_ar():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).saude()
    assert exc.value.codigo == "API_FORA_DO_AR" and exc.value.fora_do_ar
    assert "Connection refused" not in exc.value.mensagem


def test_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).analisar({"descricao": "x" * 30, "cep": "01001000"})
    assert exc.value.codigo == "TEMPO_ESGOTADO"
    assert "tente enviar de novo" in exc.value.mensagem


def test_html_de_proxy_em_502_vira_fora_do_ar():
    def handler(request):
        return httpx.Response(502, text="<html>Bad Gateway</html>")

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).saude()
    assert exc.value.codigo == "API_FORA_DO_AR"


def test_resposta_invalida_quando_contrato_quebra():
    def handler(request):
        return httpx.Response(200, json={"inesperado": True})

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).analisar({"descricao": "x" * 30, "cep": "01001000"})
    assert exc.value.codigo == "RESPOSTA_INVALIDA"


def test_json_malformado():
    def handler(request):
        return httpx.Response(200, text="{quebrado", headers={"Content-Type": "application/json"})

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).categorias()
    assert exc.value.codigo == "RESPOSTA_INVALIDA"


def test_erro_de_negocio_repassa_mensagem_e_campos_da_api():
    corpo = {"erro": {"codigo": "ENTRADA_INVALIDA", "mensagem": "Alguns dados precisam de ajuste.",
                      "campos": {"cep": "Informe um CEP válido, com 8 dígitos."}}}

    def handler(request):
        return httpx.Response(422, json=corpo)

    with pytest.raises(ErroApi) as exc:
        _cliente(handler).analisar({"descricao": "x" * 30, "cep": "1"})
    assert exc.value.mensagem == "Alguns dados precisam de ajuste."
    assert exc.value.campos["cep"].startswith("Informe")


def test_token_vai_no_cabecalho():
    vistos = {}

    def handler(request):
        vistos["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=[])

    assert _cliente(handler).gestor_listar("abc") == []
    assert vistos["auth"] == "Bearer abc"
