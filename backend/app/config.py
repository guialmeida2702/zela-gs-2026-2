"""Configuração do back-end, lida de variáveis de ambiente / arquivo .env.

Nenhum segredo fica no código: a chave do LLM, o segredo do JWT e a senha do
gestor vêm sempre do ambiente. Em produção, configurações inseguras (CORS com
"*", segredo padrão) fazem a API recusar a inicialização.
"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SEGREDO_PADRAO = "troque-este-segredo-em-producao"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", description="development | production")
    app_versao: str = "1.0.0"

    # --- LLM (qualquer API compatível com OpenAI: Groq, Gemini, OpenAI, Ollama) ---
    llm_provider: str = Field(default="openai_compat", description="openai_compat | mock")
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_s: float = 25.0
    llm_temperature: float = 0.1
    llm_json_mode: str = Field(default="json_object", description="json_object | json_schema | none")
    llm_reasoning_effort: str = Field(default="", description="low | medium | high (vazio = não enviar)")
    llm_max_tentativas: int = 2
    llm_max_tokens: int = Field(default=0, description="limite de tokens gerados (0 = não enviar)")

    # --- Segurança ---
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    jwt_secret: str = SEGREDO_PADRAO
    gestor_usuario: str = "gestor"
    gestor_senha: str = ""
    token_ttl_min: int = 120
    fuso_horario: str = Field(default="America/Sao_Paulo", description="Fuso dos horários gravados e exibidos")
    rate_limit_por_min: int = 12

    # --- Dados ---
    database_path: str = "data/zela.db"
    seed_demo_data: bool = True

    # --- Assistente (RAG) ---
    busca_modo: str = Field(default="hibrido", description="hibrido | bm25 | denso")
    modelos_cache_dir: str | None = None
    assistente_k: int = 4

    # --- Fontes externas (dados abertos) ---
    usar_dados_externos: bool = True
    timeout_externo_s: float = 6.0
    nominatim_user_agent: str = "zela-citizentech-poc/1.0 (projeto academico FIAP)"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def em_producao(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def _validar_producao(self) -> "Settings":
        if self.em_producao:
            if "*" in self.cors_origin_list:
                raise ValueError("CORS com '*' não é permitido em produção. Defina CORS_ORIGINS.")
            if self.jwt_secret.startswith("troque") or len(self.jwt_secret) < 32:  # recusa os valores de exemplo
                raise ValueError("Defina JWT_SECRET aleatório com pelo menos 32 caracteres em produção.")
            if not self.gestor_senha:
                raise ValueError("Defina GESTOR_SENHA em produção.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
