"""Testes de integração da API (FastAPI TestClient), executáveis sem subir a interface."""

import pytest
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import ORIGEM_FRONT, RELATO_OK, ClimaFalso


def _analisar(cliente, **extra):
    r = cliente.post("/relatos/analisar", json=RELATO_OK | extra)
    assert r.status_code == 200, r.text
    return r.json()


def _registrar(cliente, analise, **extra):
    corpo = {
        "analise_id": analise["analise_id"],
        "categoria_final": analise["analise"]["categoria"],
        "urgencia_final": analise["analise"]["urgencia"],
        "consentimento_lgpd": True,
    } | extra
    return cliente.post("/solicitacoes", json=corpo)


def _token(cliente) -> dict:
    r = cliente.post("/auth/login", json={"usuario": "gestor", "senha": "senha-teste"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------- fluxo do cidadão ----------------
def test_health(cliente):
    dados = cliente.get("/health").json()
    assert dados["status"] == "ok" and dados["ia"]["simulada"] is True


def test_analise_retorna_saida_estruturada_e_encaminhamento(cliente):
    dados = _analisar(cliente)
    assert dados["analise"]["categoria"] == "buraco_via"
    assert dados["encaminhamento"]["orgao"].startswith("Subprefeitura")
    assert dados["contexto"]["endereco"]["bairro"] == "Sé"
    assert dados["contexto"]["clima"]["chuva_prevista_mm_72h"] == 2.0


def test_segunda_analise_identica_usa_cache(cliente):
    assert _analisar(cliente)["em_cache"] is False
    assert _analisar(cliente)["em_cache"] is True


def test_dados_pessoais_nao_sao_armazenados(cliente):
    analise = _analisar(cliente, descricao="Buraco enorme na rua, me liga no 11 98765-4321 para mais detalhes.")
    assert analise["dados_pessoais_removidos"] == ["telefone"]
    sol = _registrar(cliente, analise).json()
    assert "98765" not in sol["descricao"] and "[TELEFONE]" in sol["descricao"]


def test_fluxo_completo_com_correcao_humana_e_feedback(cliente):
    analise = _analisar(cliente)
    r = _registrar(cliente, analise, categoria_final="calcada_acessibilidade", urgencia_final="alta",
                   comentario_cidadao="Na verdade é a calçada", contato="pessoa@email.com")
    assert r.status_code == 201
    sol = r.json()
    assert sol["protocolo"].startswith("ZL-") and sol["status"] == "recebida"
    assert sol["categoria"] == "calcada_acessibilidade"
    assert "contato" not in sol  # contato nunca volta na visão do cidadão

    consulta = cliente.get(f"/solicitacoes/{sol['protocolo'].lower()}")
    assert consulta.status_code == 200

    fb = cliente.post(f"/solicitacoes/{sol['protocolo']}/feedback", json={"util": True})
    assert fb.json()["feedback_util"] is True

    cab = _token(cliente)
    fila = cliente.get("/gestor/solicitacoes", headers=cab).json()
    registro = next(s for s in fila if s["protocolo"] == sol["protocolo"])
    assert registro["categoria_ia"] == "buraco_via"  # sugestão original preservada para auditoria
    assert registro["corrigida_pelo_cidadao"] is True
    assert registro["contato"] == "pessoa@email.com"


def test_confirmacao_e_idempotente(cliente):
    analise = _analisar(cliente)
    p1 = _registrar(cliente, analise).json()["protocolo"]
    p2 = _registrar(cliente, analise).json()["protocolo"]
    assert p1 == p2


def test_sem_consentimento_nao_registra(cliente):
    r = _registrar(cliente, _analisar(cliente), consentimento_lgpd=False)
    assert r.status_code == 422
    assert "consentimento_lgpd" in r.json()["erro"]["campos"]


def test_analise_inexistente(cliente):
    r = cliente.post("/solicitacoes", json={"analise_id": "naoexiste123", "categoria_final": "outros",
                                            "urgencia_final": "baixa", "consentimento_lgpd": True})
    assert r.status_code == 404 and r.json()["erro"]["codigo"] == "ANALISE_NAO_ENCONTRADA"


def test_protocolo_inexistente_tem_mensagem_amigavel(cliente):
    r = cliente.get("/solicitacoes/ZL-000000-XXXXXX")
    assert r.status_code == 404 and "protocolo" in r.json()["erro"]["mensagem"]


def test_painel_publico_e_anonimo(cliente):
    _registrar(cliente, _analisar(cliente), contato="pessoa@email.com")
    publicas = cliente.get("/solicitacoes/publicas").json()
    assert publicas
    item = publicas[0]
    for campo in ("contato", "descricao", "endereco_resumo"):
        assert campo not in item
    assert item["latitude"] == round(item["latitude"], 3)


# ---------------- validação ----------------
@pytest.mark.parametrize(
    "corpo, campo",
    [
        ({"descricao": "curto", "cep": "01001000"}, "descricao"),
        ({"descricao": "x" * 1001, "cep": "01001000"}, "descricao"),
        ({"descricao": "Buraco grande na rua principal do bairro", "cep": "123"}, "cep"),
        ({"descricao": "1234567890 1234567890 12345", "cep": "01001000"}, "descricao"),
        ({"cep": "01001000"}, "descricao"),
    ],
)
def test_validacao_de_entrada_com_mensagens_amigaveis(cliente, corpo, campo):
    r = cliente.post("/relatos/analisar", json=corpo)
    assert r.status_code == 422
    erro = r.json()["erro"]
    assert erro["codigo"] == "ENTRADA_INVALIDA" and campo in erro["campos"]
    assert "Traceback" not in r.text and "pydantic" not in r.text.lower()


def test_json_malformado(cliente):
    r = cliente.post("/relatos/analisar", content=b"{nao e json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# ---------------- falhas da IA ----------------
def test_timeout_da_ia_vira_504_amigavel(cliente_timeout):
    r = cliente_timeout.post("/relatos/analisar", json=RELATO_OK)
    assert r.status_code == 504
    corpo = r.json()["erro"]
    assert corpo["codigo"] == "IA_TEMPO_ESGOTADO"
    assert "25s" not in r.text  # detalhe técnico fica só no log


def test_resposta_invalida_da_ia_vira_502_amigavel(cliente_resposta_invalida):
    r = cliente_resposta_invalida.post("/relatos/analisar", json=RELATO_OK)
    assert r.status_code == 502
    assert r.json()["erro"]["codigo"] == "IA_RESPOSTA_INVALIDA"
    assert "ValidationError" not in r.text


def test_sem_chave_api_sobe_mas_responde_503(fabrica_cliente):
    from app.providers.llm import criar_provedor_llm

    llm = criar_provedor_llm(Settings(llm_provider="openai_compat", llm_api_key=""))
    with fabrica_cliente(llm=llm) as c:
        assert c.get("/health").json()["ia"]["configurada"] is False
        r = c.post("/relatos/analisar", json=RELATO_OK)
        assert r.status_code == 503 and r.json()["erro"]["codigo"] == "IA_NAO_CONFIGURADA"


def test_chuva_forte_externa_eleva_urgencia(fabrica_cliente):
    with fabrica_cliente(clima=ClimaFalso(mm=70)) as c:
        r = c.post("/relatos/analisar", json=RELATO_OK | {"descricao": "Bueiro entupido na esquina, a rua sempre enche de água."})
        dados = r.json()
        assert dados["analise"]["categoria"] == "alagamento_drenagem"
        assert dados["urgencia_sugerida_pela_ia"] == "alta"
        assert dados["analise"]["urgencia"] == "critica"


# ---------------- segurança ----------------
def test_rate_limit(fabrica_cliente):
    with fabrica_cliente(rate_limit_por_min=2) as c:
        assert c.post("/relatos/analisar", json=RELATO_OK).status_code == 200
        assert c.post("/relatos/analisar", json=RELATO_OK).status_code == 200
        r = c.post("/relatos/analisar", json=RELATO_OK)
        assert r.status_code == 429 and r.json()["erro"]["codigo"] == "LIMITE_DE_ENVIOS"


def test_area_do_gestor_exige_token(cliente):
    assert cliente.get("/gestor/solicitacoes").status_code == 401
    assert cliente.get("/gestor/solicitacoes", headers={"Authorization": "Bearer invalido"}).status_code == 401
    assert cliente.post("/auth/login", json={"usuario": "gestor", "senha": "errada"}).status_code == 401


def test_gestor_atualiza_e_indicadores(cliente):
    sol = _registrar(cliente, _analisar(cliente)).json()
    cab = _token(cliente)
    r = cliente.patch(f"/gestor/solicitacoes/{sol['protocolo']}", headers=cab,
                      json={"status": "encaminhada", "urgencia_final": "alta", "nota": "Equipe agendada"})
    assert r.status_code == 200
    atualizado = r.json()
    assert atualizado["status"] == "encaminhada" and atualizado["urgencia"] == "alta"
    assert atualizado["historico"][-1]["nota"].startswith("[gestor]")
    ind = cliente.get("/gestor/indicadores", headers=cab).json()
    assert ind["total"] == 1 and ind["abertas"] == 1
    assert ind["concordancia_categoria_pct"] == 100.0


def test_patch_vazio_e_rejeitado(cliente):
    sol = _registrar(cliente, _analisar(cliente)).json()
    r = cliente.patch(f"/gestor/solicitacoes/{sol['protocolo']}", headers=_token(cliente), json={})
    assert r.status_code == 422


def test_cors_restritivo(cliente):
    ok = cliente.options("/relatos/analisar", headers={"Origin": ORIGEM_FRONT, "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == ORIGEM_FRONT
    negado = cliente.options("/relatos/analisar", headers={"Origin": "https://site-malicioso.com",
                                                           "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in negado.headers


def test_producao_recusa_cors_aberto_e_segredo_padrao():
    with pytest.raises(ValidationError):
        Settings(app_env="production", cors_origins="*", jwt_secret="y" * 40, gestor_senha="s")
    with pytest.raises(ValidationError):
        Settings(app_env="production", cors_origins="https://zela.app", gestor_senha="s")
    with pytest.raises(ValidationError):  # o valor de exemplo do .env.example também é recusado
        Settings(app_env="production", cors_origins="https://zela.app", gestor_senha="s",
                 jwt_secret="troque-por-um-segredo-longo-e-aleatorio-com-32-ou-mais-caracteres")
    ok = Settings(app_env="production", cors_origins="https://zela.app", gestor_senha="s", jwt_secret="a" * 48)
    assert ok.em_producao


def test_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
