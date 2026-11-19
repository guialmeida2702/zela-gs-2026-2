"""Tema 4 — E-mail automatizado: boletim diário para os gestores (HTML + anexo CSV).

Sem credenciais SMTP (ou em modo de simulação), o e-mail é gravado como arquivo .eml em saida/,
que abre em qualquer cliente de e-mail: o robô nunca para por causa do envio.
"""

import html
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


def montar_email(resumo: dict, remetente: str, destino: str, anexo: Path | None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"[Zela] Boletim do robô — {datetime.now():%d/%m/%Y %H:%M}"
    msg["From"] = remetente or "robo@zela.local"
    msg["To"] = destino or "gestores@zela.local"
    linhas = [
        ("Ordens de serviço aplicadas", resumo.get("os_aplicadas", 0)),
        ("Linhas rejeitadas (revisão humana)", resumo.get("os_rejeitadas", 0)),
        ("Casos de drenagem priorizados por alerta", resumo.get("priorizados", 0)),
        ("Fotos de vistoria com possível fissura", resumo.get("fotos_com_fissura", 0)),
        ("Notícias oficiais relevantes", resumo.get("noticias_relevantes", 0)),
        ("Falhas tratadas nesta execução", len(resumo.get("falhas", []))),
    ]
    texto = "\n".join(f"- {k}: {v}" for k, v in linhas)
    msg.set_content(f"Boletim automático do Zela\n\n{texto}\n\nChuva prevista (72h): {resumo.get('chuva_mm')} mm\n"
                    "Linhas rejeitadas estão no anexo para revisão humana.")
    tabela = "".join(f"<tr><td>{html.escape(k)}</td><td style='text-align:right'><b>{v}</b></td></tr>" for k, v in linhas)
    noticias = "".join(f"<li><a href='{html.escape(n['url'])}'>{html.escape(n['titulo'])}</a> ({n['data'] or 's/d'})</li>"
                       for n in resumo.get("noticias_lista", [])[:8])
    falhas = "".join(f"<li>{html.escape(f)}</li>" for f in resumo.get("falhas", []))
    msg.add_alternative(f"""<html><body style="font-family:Arial,sans-serif">
<h2>Boletim do robô Zela</h2><p>Execução de {datetime.now():%d/%m/%Y %H:%M}. Chuva prevista para 72 h:
<b>{resumo.get('chuva_mm', 'indisponível')} mm</b>.</p>
<table border="1" cellpadding="6" style="border-collapse:collapse">{tabela}</table>
<h3>Notícias oficiais relevantes</h3><ul>{noticias or '<li>nenhuma</li>'}</ul>
<h3>Falhas tratadas</h3><ul>{falhas or '<li>nenhuma</li>'}</ul>
<p style="color:#555">Mensagem automática. Linhas rejeitadas seguem em anexo para revisão humana.</p></body></html>""",
                      subtype="html")
    if anexo and anexo.exists():
        msg.add_attachment(anexo.read_bytes(), maintype="text", subtype="csv", filename=anexo.name)
    return msg


def enviar_ou_salvar(msg: EmailMessage, cfg, pasta: Path) -> str:
    if cfg.dry_run or not (cfg.smtp_host and cfg.smtp_usuario and cfg.smtp_senha and cfg.email_destino):
        destino = pasta / f"boletim_{datetime.now():%Y%m%d_%H%M%S}.eml"
        destino.write_bytes(bytes(msg))
        return f"salvo em {destino.name} (sem credenciais SMTP ou modo simulação)"
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_porta, timeout=cfg.timeout_s) as s:
        s.starttls()
        s.login(cfg.smtp_usuario, cfg.smtp_senha)
        s.send_message(msg)
    return f"enviado para {cfg.email_destino}"
