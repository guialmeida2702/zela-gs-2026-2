"""Relógio do serviço.

Os horários gravados e exibidos seguem o fuso configurado (padrão: Brasília), e não o do
servidor. Em contêiner ou nuvem o relógio costuma estar em UTC, o que mostraria ao cidadão
um horário três horas adiantado.
"""

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings


def _fuso() -> tzinfo:
    try:
        return ZoneInfo(get_settings().fuso_horario)
    except (ZoneInfoNotFoundError, ValueError):
        # Sem base de fusos no sistema: Brasília é UTC-3 o ano todo (sem horário de verão desde 2019).
        return timezone(timedelta(hours=-3))


def agora() -> datetime:
    """Data e hora locais do serviço, sem informação de fuso (formato usado no banco)."""
    return datetime.now(UTC).astimezone(_fuso()).replace(tzinfo=None, microsecond=0)
