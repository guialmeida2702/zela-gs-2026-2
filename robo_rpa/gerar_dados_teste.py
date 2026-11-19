"""Gera dados de TESTE sintéticos e rotulados para o robô (nenhum dado pessoal real).

- Duas planilhas de ordens de serviço (CSV e Excel) com linhas válidas e inválidas conhecidas;
- uma planilha corrompida (sem colunas obrigatórias) para demonstrar o tratamento de falha;
- o gabarito com a decisão esperada de cada linha e o rótulo de cada foto de vistoria.

As planilhas usam protocolos que existem na API do Zela em execução (por isso a API precisa estar no ar).
    python gerar_dados_teste.py --api http://localhost:8000
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
from etapas.infra import carregar_env

RAIZ = Path(__file__).parent
ENTRADA = RAIZ / "dados" / "entrada"


def main() -> None:
    carregar_env()
    p = argparse.ArgumentParser()
    p.add_argument("--api", default=os.getenv("ZELA_API_URL", "http://localhost:8000"))
    p.add_argument("--usuario", default=os.getenv("ZELA_GESTOR_USUARIO", "gestor"))
    p.add_argument("--senha", default=os.getenv("ZELA_GESTOR_SENHA", ""))
    a = p.parse_args()
    with httpx.Client(timeout=60) as c:
        try:
            login = c.post(f"{a.api}/auth/login", json={"usuario": a.usuario, "senha": a.senha})
        except httpx.HTTPError:
            raise SystemExit(f"A API do Zela não respondeu em {a.api}. Suba a API (veja o README) ou informe --api.") from None
        if login.status_code != 200:
            raise SystemExit("Login de gestor recusado: defina ZELA_GESTOR_SENHA com a mesma senha de GESTOR_SENHA da API "
                             "(ou use --senha).")
        tok = login.json()["access_token"]
        fila = c.get(f"{a.api}/gestor/solicitacoes", headers={"Authorization": f"Bearer {tok}"}).json()
        # Casos de drenagem para testar a regra E (priorização com alerta de chuva): 2 devem subir, 1 já está alta
        priorizacao = {}
        for texto, urgencia, esperado in (
            ("Bueiro entupido de folhas na esquina da rua de teste do robô, a água empoça quando chove.", "media", "elevar"),
            ("Boca de lobo com lixo acumulado na rua de teste do robô, escoamento lento.", "baixa", "elevar"),
            ("Bueiro sem tampa na rua de teste do robô, já está como prioridade alta.", "alta", "manter"),
        ):
            an = c.post(f"{a.api}/relatos/analisar", json={"descricao": texto, "cep": "01001000"}).json()
            sol = c.post(f"{a.api}/solicitacoes", json={"analise_id": an["analise_id"], "categoria_final": "alagamento_drenagem",
                                                         "urgencia_final": urgencia, "consentimento_lgpd": True}).json()
            priorizacao[sol["protocolo"]] = esperado
    abertos = [s["protocolo"] for s in fila if s["status"] in ("recebida", "em_analise", "encaminhada")]
    assert len(abertos) >= 12, "a API precisa ter ao menos 12 solicitações abertas (use SEED_DEMO_DATA=true)"
    hoje = datetime.now()
    d = lambda dias: (hoje - timedelta(days=dias)).strftime("%d/%m/%Y")  # noqa: E731
    pasta = ENTRADA / "ordens_servico"
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*"):
        antigo.unlink()

    # (linha, esperado) — a linha 1 do arquivo é o cabeçalho, então os dados começam na linha 2
    linhas_se = [
        (abertos[0], "executada", d(1), "Equipe Tapa-Buraco 3", "Reparo concluído", "aceita"),
        (abertos[1], "programada", d(0), "Equipe Poda 1", "Agendada vistoria do agrônomo", "aceita"),
        (abertos[2], "Concluída", d(2), "Equipe Drenagem 2", "Limpeza de bueiro feita", "aceita"),
        (abertos[3], "em vistoria", d(1), "Equipe Calçadas", "Técnico no local", "aceita"),
        (abertos[4], "cancelada", d(3), "Equipe Iluminação", "Lâmpada já trocada pela concessionária", "aceita"),
        (abertos[5], "executada", d(0), "Equipe Tapa-Buraco 1", "Ok", "aceita"),
        ("ZL-123", "executada", d(1), "Equipe 9", "Protocolo digitado errado", "rejeitada"),
        ("ZL-991231-ABCDEF", "executada", d(1), "Equipe 9", "Protocolo inexistente", "rejeitada"),
        (abertos[6], "terminada?", d(1), "Equipe 4", "Status fora do padrão", "rejeitada"),
        (abertos[7], "executada", "", "Equipe 4", "Sem data", "rejeitada"),
        (abertos[8], "executada", (hoje + timedelta(days=5)).strftime("%d/%m/%Y"), "Equipe 4", "Data no futuro", "rejeitada"),
        (abertos[0], "executada", d(1), "Equipe Tapa-Buraco 3", "Linha repetida", "rejeitada"),
        (abertos[9], "executada", d(1), "Equipe 5", "Morador pediu retorno no (11) 98888-7777", "rejeitada"),
    ]
    linhas_lapa = [
        (abertos[10], "executada", d(2), "Equipe Lapa 1", "Concluído", "aceita"),
        (abertos[11], "agendada", d(0), "Equipe Lapa 2", "Programado", "aceita"),
        ("", "executada", d(1), "Equipe Lapa 2", "Sem protocolo", "rejeitada"),
        (abertos[10].lower(), "executada", d(1), "Equipe Lapa 1", "Duplicada em minúsculas", "rejeitada"),
    ]
    colunas = ["protocolo", "status_os", "data_execucao", "equipe", "observacao"]
    gabarito: dict = {"linhas": {}, "fotos": {}, "priorizacao": priorizacao}
    pd.DataFrame([x[:5] for x in linhas_se], columns=colunas).to_csv(pasta / "os_subprefeitura_se.csv", index=False, sep=";")
    pd.DataFrame([x[:5] for x in linhas_lapa], columns=colunas).to_excel(pasta / "os_subprefeitura_lapa.xlsx", index=False)
    (pasta / "os_planilha_corrompida.csv").write_text("coluna_a;coluna_b\n1;2\n", encoding="utf-8")
    for nome, linhas in (("os_subprefeitura_se.csv", linhas_se), ("os_subprefeitura_lapa.xlsx", linhas_lapa)):
        for i, x in enumerate(linhas, start=2):
            gabarito["linhas"][f"{nome}:{i}"] = x[5]

    fotos = ENTRADA / "fotos_vistoria"
    if fotos.exists():
        for f in fotos.iterdir():
            if f.name.startswith(("fissura_", "sem_fissura_")):
                gabarito["fotos"][f.name] = "com_fissura" if f.name.startswith("fissura_") else "sem_fissura"
    (ENTRADA / "gabarito.json").write_text(json.dumps(gabarito, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(gabarito['linhas'])} linhas rotuladas, {len(gabarito['fotos'])} fotos rotuladas em {ENTRADA}")


if __name__ == "__main__":
    main()
