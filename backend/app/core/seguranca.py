"""Autenticação do perfil gestor (RBAC simples: cidadão é anônimo, gestor usa token JWT)."""

import hmac
from datetime import UTC, datetime, timedelta

import jwt

from app.config import Settings
from app.core.erros import NaoAutorizado

_ALGORITMO = "HS256"


def verificar_credenciais(settings: Settings, usuario: str, senha: str) -> bool:
    if not settings.gestor_senha:  # sem senha configurada, o login de gestor fica desabilitado
        return False
    usuario_ok = hmac.compare_digest(usuario.encode(), settings.gestor_usuario.encode())
    senha_ok = hmac.compare_digest(senha.encode(), settings.gestor_senha.encode())
    return usuario_ok and senha_ok


def emitir_token(settings: Settings, usuario: str) -> tuple[str, datetime]:
    expira = datetime.now(UTC) + timedelta(minutes=settings.token_ttl_min)
    token = jwt.encode({"sub": usuario, "perfil": "gestor", "exp": expira}, settings.jwt_secret, algorithm=_ALGORITMO)
    return token, expira


def validar_token(settings: Settings, token: str) -> dict:
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITMO])
    except jwt.PyJWTError as exc:
        raise NaoAutorizado(detalhe_tecnico=type(exc).__name__) from exc
    if dados.get("perfil") != "gestor":
        raise NaoAutorizado(detalhe_tecnico="perfil sem permissão")
    return dados
