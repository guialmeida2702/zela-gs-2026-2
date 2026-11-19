from datetime import datetime

from pydantic import BaseModel, Field


class LoginEntrada(BaseModel):
    usuario: str = Field(min_length=3, max_length=50)
    senha: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    perfil: str = "gestor"
    expira_em: datetime
