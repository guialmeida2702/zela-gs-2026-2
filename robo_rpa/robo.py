"""Robô Zela — automação diária do gestor (RPA + IA). Ponto de entrada único.

    python robo.py                 # execução real (usa a API do Zela e envia/salva o boletim)
    python robo.py --simular       # dry-run: não altera o Zela e salva o e-mail como .eml

Etapas (cada uma falha de forma isolada, com log e caminho seguro, sem parar o robô):
  A. Web scraping de notícias oficiais (Prefeitura de SP e Defesa Civil municipal)
  B. API Open-Meteo: chuva prevista para 72 h
  C. API do Zela: login de gestor e leitura da fila
  D. Pandas: planilhas de ordens de serviço -> atualizações no Zela; inválidas -> revisão humana
  E. Regra inteligente: com alerta de chuva, eleva a prioridade de casos de drenagem em aberto
  F. IA (Visão Computacional): triagem das fotos de vistoria com o modelo de fissuras
  G. Banco SQL (auditoria) + relatório da execução + e-mail aos gestores
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
from etapas.coleta_web import FONTES, alerta_recente, coletar
from etapas.infra import RAIZ, BancoRobo, Config, com_repeticao, configurar_log
from etapas.integracoes import ApiZela, ClassificadorFissuras, previsao_chuva_sp
from etapas.planilhas import hash_arquivo, ler_planilha, validar
from etapas.relatorio import enviar_ou_salvar, montar_email


class _PrevisaoDeTeste(Exception):
    """Sinaliza que a previsão foi informada manualmente para testar a regra de priorização."""


PASTA_MODELO = RAIZ.parent / "visao_computacional" / "modelos"
ABERTOS = {"recebida", "em_analise", "encaminhada"}


def executar(cfg: Config) -> dict:
    cfg.saida.mkdir(parents=True, exist_ok=True)
    log = configurar_log(cfg.saida)
    banco = BancoRobo(cfg.banco)
    exec_id = banco.iniciar(cfg.dry_run)
    r: dict = {"execucao": exec_id, "inicio": datetime.now().isoformat(timespec="seconds"), "dry_run": cfg.dry_run,
               "falhas": [], "os_aplicadas": 0, "os_rejeitadas": 0, "priorizados": 0, "fotos_com_fissura": 0,
               "arquivos_ignorados_por_idempotencia": 0}

    def falha(etapa: str, msg: str) -> None:
        r["falhas"].append(f"[{etapa}] {msg}")
        banco.evento(etapa, "ERRO", msg)
        log.error(msg, extra={"etapa": etapa})

    def info(etapa: str, msg: str) -> None:
        banco.evento(etapa, "INFO", msg)
        log.info(msg, extra={"etapa": etapa})

    gabarito = {}
    if (cfg.entrada / "gabarito.json").exists():
        gabarito = json.loads((cfg.entrada / "gabarito.json").read_text(encoding="utf-8"))

    cabecalho = {"User-Agent": "zela-robo/1.0 (projeto academico FIAP)"}
    with httpx.Client(timeout=cfg.timeout_s, headers=cabecalho, follow_redirects=True) as http:
        # ---------------- A. web scraping
        noticias: list[dict] = []
        for fonte, url in FONTES.items():
            try:
                itens = com_repeticao(lambda u=url, f=fonte: coletar(http, u, f), log=log, etapa="A-scraping", descricao=fonte)
                noticias += itens
                for n in itens:
                    banco.conn.execute("INSERT OR REPLACE INTO noticias VALUES (?,?,?,?,?,?)",
                                       (n["url"], n["titulo"], n["data"], n["fonte"], int(n["relevante"]),
                                        datetime.now().isoformat(timespec="seconds")))
                banco.conn.commit()
                info("A-scraping", f"{fonte}: {len(itens)} notícias, {sum(n['relevante'] for n in itens)} relevantes")
            except Exception as exc:
                falha("A-scraping", f"{fonte} indisponível ({type(exc).__name__}); boletim segue sem essa fonte")
        relevantes = [n for n in noticias if n["relevante"]]
        alertas = alerta_recente(noticias)
        r.update(noticias_coletadas=len(noticias), noticias_relevantes=len(relevantes), noticias_lista=relevantes[:10],
                 alertas_oficiais_recentes=[a["titulo"] for a in alertas])

        # ---------------- B. API de clima
        try:
            if cfg.chuva_teste_mm is not None:
                raise _PrevisaoDeTeste()
            r["chuva_mm"] = com_repeticao(lambda: previsao_chuva_sp(http), log=log, etapa="B-clima", descricao="Open-Meteo")
            info("B-clima", f"chuva prevista 72h: {r['chuva_mm']} mm")
        except _PrevisaoDeTeste:
            r["chuva_mm"] = cfg.chuva_teste_mm
            info("B-clima", f"previsão de TESTE informada pelo operador: {r['chuva_mm']} mm (Open-Meteo não consultado)")
        except Exception as exc:
            r["chuva_mm"] = None
            falha("B-clima", f"previsão indisponível ({type(exc).__name__}); priorização usa só as notícias oficiais")
        gatilho = (r["chuva_mm"] is not None and r["chuva_mm"] >= cfg.limiar_chuva_mm) or bool(alertas)
        r["gatilho_alerta"] = gatilho

        # ---------------- C. API do Zela
        api: ApiZela | None = ApiZela(http, cfg.api_url)
        fila: list[dict] = []
        try:
            if not cfg.gestor_senha:
                raise RuntimeError("ZELA_GESTOR_SENHA não configurada")
            com_repeticao(lambda: api.login(cfg.gestor_usuario, cfg.gestor_senha), log=log, etapa="C-api", descricao="login")
            fila = com_repeticao(api.fila, log=log, etapa="C-api", descricao="fila")
            info("C-api", f"fila lida: {len(fila)} solicitações")
        except Exception as exc:
            falha("C-api", f"API do Zela indisponível ({type(exc).__name__}: {str(exc)[:80]}); atualizações ficam pendentes")
            api = None
        protocolos = {s["protocolo"] for s in fila}

        # ---------------- D. planilhas (Pandas)
        rejeitadas_todas, decisoes = [], {}
        pasta_os = cfg.entrada / "ordens_servico"
        arquivos = sorted([*pasta_os.glob("*.csv"), *pasta_os.glob("*.xlsx")]) if pasta_os.exists() else []
        if not arquivos:
            falha("D-planilhas", f"nenhuma planilha em {pasta_os} (arquivo ausente); etapa ignorada")
        for arquivo in arquivos:
            h = hash_arquivo(arquivo)
            if banco.arquivo_ja_processado(h):
                r["arquivos_ignorados_por_idempotencia"] += 1
                info("D-planilhas", f"{arquivo.name} já processado antes; ignorado (idempotência)")
                continue
            try:
                df = ler_planilha(arquivo)
            except Exception as exc:
                falha("D-planilhas", f"{arquivo.name} ilegível: {exc}; movido para revisão humana")
                continue
            df["linha"] = range(2, len(df) + 2)
            if api is None:
                df["motivo_rejeicao"] = "API indisponível: reprocessar na próxima execução"
                rejeitadas_todas.append(df.assign(arquivo=arquivo.name))
                continue
            validas, rejeitadas = validar(df, protocolos)
            for _, linha in validas.iterrows():
                decisoes[f"{arquivo.name}:{linha['linha']}"] = "aceita"
                if cfg.dry_run:
                    r["os_aplicadas"] += 1
                    continue
                try:
                    nota = (f"[robô] OS '{linha['status_os']}' em {linha['data_execucao']:%d/%m/%Y} pela equipe "
                            f"{str(linha['equipe'])[:40]}")
                    com_repeticao(lambda p=linha["protocolo"], s=linha["status_zela"], n=nota: api.atualizar(p, {"status": s, "nota": n}),
                                  log=log, etapa="D-planilhas", descricao=f"atualizar {linha['protocolo']}")
                    r["os_aplicadas"] += 1
                except Exception as exc:
                    falha("D-planilhas", f"{linha['protocolo']}: atualização recusada ({type(exc).__name__})")
                    rejeitadas = pd.concat([rejeitadas, validas.loc[[_]].assign(motivo_rejeicao="erro ao atualizar na API")])
            for _, linha in rejeitadas.iterrows():
                decisoes[f"{arquivo.name}:{linha['linha']}"] = "rejeitada"
            rejeitadas_todas.append(rejeitadas.assign(arquivo=arquivo.name))
            if not cfg.dry_run:
                banco.marcar_arquivo(h, arquivo.name, len(validas), len(rejeitadas))
            info("D-planilhas", f"{arquivo.name}: {len(validas)} válidas, {len(rejeitadas)} para revisão humana")
        caminho_rejeitados = cfg.saida / f"revisao_humana_{exec_id}.csv"
        if rejeitadas_todas:
            todas = pd.concat(rejeitadas_todas, ignore_index=True)
            r["os_rejeitadas"] = len(todas)
            colunas = [c for c in ("arquivo", "linha", "protocolo", "status_os", "data_execucao", "equipe", "motivo_rejeicao")
                       if c in todas.columns]
            todas[colunas].to_csv(caminho_rejeitados, index=False, encoding="utf-8-sig")
        # observações nunca são enviadas ao Zela: podem conter dados pessoais digitados pela equipe

        # ---------------- E. regra inteligente: priorização por alerta
        if gatilho and api is not None:
            motivo = (f"chuva prevista de {r['chuva_mm']} mm em 72h" if r["chuva_mm"] and r["chuva_mm"] >= cfg.limiar_chuva_mm
                      else "alerta em notícia oficial recente")
            for s in fila:
                if s["categoria"] == "alagamento_drenagem" and s["status"] in ABERTOS and s["urgencia"] in ("baixa", "media"):
                    if not cfg.dry_run:
                        try:
                            api.atualizar(s["protocolo"], {"urgencia_final": "alta",
                                                           "nota": f"[robô] prioridade elevada: {motivo}. Revisar."})
                        except Exception as exc:
                            falha("E-priorizacao", f"{s['protocolo']}: {type(exc).__name__}")
                            continue
                    r["priorizados"] += 1
                    r.setdefault("priorizados_protocolos", []).append(s["protocolo"])
            info("E-priorizacao", f"alerta ativo ({motivo}); {r['priorizados']} casos de drenagem priorizados")
        else:
            info("E-priorizacao", "sem alerta ativo; nenhuma prioridade alterada")

        # ---------------- F. IA: fotos de vistoria
        fotos = sorted((cfg.entrada / "fotos_vistoria").glob("*")) if (cfg.entrada / "fotos_vistoria").exists() else []
        r["fotos"] = []
        try:
            clf = ClassificadorFissuras(PASTA_MODELO)
            for foto in fotos:
                try:
                    p = clf.probabilidade(foto)
                except Exception as exc:
                    falha("F-visao", f"{foto.name}: imagem inválida ({type(exc).__name__}); enviada para revisão humana")
                    continue
                classe = "com_fissura" if p >= clf.limiar else "sem_fissura"
                esperado = gabarito.get("fotos", {}).get(foto.name)
                banco.conn.execute("INSERT INTO vistorias_foto VALUES (?,?,?,?,?,?)",
                                   (foto.name, exec_id, classe, p, esperado, datetime.now().isoformat(timespec="seconds")))
                r["fotos"].append({"arquivo": foto.name, "classe": classe, "probabilidade": round(p, 3), "esperado": esperado})
                r["fotos_com_fissura"] += classe == "com_fissura"
            banco.conn.commit()
            info("F-visao", f"{len(r['fotos'])} fotos analisadas, {r['fotos_com_fissura']} com possível fissura")
        except Exception as exc:
            falha("F-visao", f"modelo de visão indisponível ({type(exc).__name__}); fotos ficam para triagem manual")

        # ---------------- métricas com dados de teste rotulados
        r["validacao"] = _metricas(gabarito, decisoes, r["fotos"], r.get("priorizados_protocolos", []),
                                   bool(r.get("gatilho_alerta")))

        # ---------------- G. relatório + e-mail
        r["fim"] = datetime.now().isoformat(timespec="seconds")
        _salvar_relatorio(cfg.saida, r)
        try:
            msg = montar_email(r, cfg.smtp_usuario, cfg.email_destino, caminho_rejeitados)
            r["email"] = com_repeticao(lambda: enviar_ou_salvar(msg, cfg, cfg.saida), tentativas=2, log=log,
                                       etapa="G-email", descricao="envio do boletim")
            info("G-email", r["email"])
        except Exception as exc:
            falha("G-email", f"envio falhou ({type(exc).__name__}); boletim salvo em arquivo")
            cfg.dry_run = True
            r["email"] = enviar_ou_salvar(montar_email(r, "", "", caminho_rejeitados), cfg, cfg.saida)
    banco.finalizar({k: v for k, v in r.items() if k not in ("noticias_lista", "fotos")})
    _salvar_relatorio(cfg.saida, r)
    return r


def _metricas(gabarito: dict, decisoes: dict, fotos: list[dict], priorizados: list[str] | None = None,
              alerta: bool = False) -> dict:
    saida: dict = {}
    casos = gabarito.get("priorizacao", {})
    if casos and alerta:  # só faz sentido medir a regra E quando o alerta está ativo
        feitos = set(priorizados or [])
        acertos = sum((p in feitos) == (esperado == "elevar") for p, esperado in casos.items())
        saida["priorizacao"] = {"casos_avaliados": len(casos), "acertos": acertos,
                                "erros": [p for p, e in casos.items() if (p in feitos) != (e == "elevar")]}
    esperadas = gabarito.get("linhas", {})
    comuns = [k for k in esperadas if k in decisoes]
    if comuns:
        acertos = sum(esperadas[k] == decisoes[k] for k in comuns)
        saida["planilhas"] = {"linhas_avaliadas": len(comuns), "acertos": acertos, "acuracia": round(acertos / len(comuns), 3),
                              "erros": [k for k in comuns if esperadas[k] != decisoes[k]]}
    rotuladas = [f for f in fotos if f["esperado"]]
    if rotuladas:
        acertos = sum(f["classe"] == f["esperado"] for f in rotuladas)
        vp = sum(f["classe"] == f["esperado"] == "com_fissura" for f in rotuladas)
        fn = sum(f["esperado"] == "com_fissura" and f["classe"] != "com_fissura" for f in rotuladas)
        fp = sum(f["esperado"] == "sem_fissura" and f["classe"] == "com_fissura" for f in rotuladas)
        saida["fotos"] = {"avaliadas": len(rotuladas), "acertos": acertos, "acuracia": round(acertos / len(rotuladas), 3),
                          "falsos_negativos": fn, "falsos_positivos": fp, "verdadeiros_positivos": vp}
    return saida


def _salvar_relatorio(pasta: Path, r: dict) -> None:
    (pasta / f"execucao_{r['execucao']}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    linhas = [f"# Relatório da execução {r['execucao']}", "", f"- Início: {r['inicio']} · Fim: {r.get('fim', '-')} · "
              f"Simulação: {'sim' if r['dry_run'] else 'não'}",
              f"- Notícias coletadas: {r.get('noticias_coletadas', 0)} (relevantes: {r.get('noticias_relevantes', 0)})",
              f"- Chuva prevista 72h: {r.get('chuva_mm')} mm · Alerta ativo: {'sim' if r.get('gatilho_alerta') else 'não'}",
              f"- OS aplicadas: {r['os_aplicadas']} · Linhas para revisão humana: {r['os_rejeitadas']} · "
              f"Arquivos ignorados (já processados): {r['arquivos_ignorados_por_idempotencia']}",
              f"- Casos de drenagem priorizados: {r['priorizados']}",
              f"- Fotos com possível fissura: {r['fotos_com_fissura']} de {len(r.get('fotos', []))}",
              f"- E-mail: {r.get('email', '-')}", "", "## Validação com dados de teste rotulados", "",
              "```json", json.dumps(r.get("validacao", {}), indent=2, ensure_ascii=False), "```", "", "## Falhas tratadas", ""]
    linhas += [f"- {f}" for f in r["falhas"]] or ["- nenhuma"]
    (pasta / f"execucao_{r['execucao']}.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--simular", action="store_true", help="dry-run: não altera o Zela e não envia e-mail")
    parser.add_argument("--api", help="URL da API do Zela (padrão: ZELA_API_URL ou http://localhost:8000)")
    parser.add_argument("--chuva-teste-mm", type=float, help="só para teste: usa esta previsão de chuva em vez do Open-Meteo")
    args = parser.parse_args()
    cfg = Config()
    cfg.dry_run = args.simular
    if args.api:
        cfg.api_url = args.api
    cfg.chuva_teste_mm = args.chuva_teste_mm
    r = executar(cfg)
    print(json.dumps({k: r[k] for k in ("execucao", "os_aplicadas", "os_rejeitadas", "priorizados", "fotos_com_fissura",
                                         "validacao", "falhas")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
