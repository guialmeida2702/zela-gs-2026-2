from pydantic import BaseModel


class CategoriaInfo(BaseModel):
    codigo: str
    nome: str
    icone: str
    descricao: str
    orgao_padrao: str


class UrgenciaInfo(BaseModel):
    codigo: str
    nome: str
    descricao: str
