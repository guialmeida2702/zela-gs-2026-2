"""Exceções de domínio. Cada uma carrega uma mensagem pensada para o CIDADÃO.

Detalhes técnicos vão só para o log do servidor, nunca para a resposta HTTP.
"""


class ErroZela(Exception):
    status_code = 500
    codigo = "ERRO_INTERNO"
    mensagem = "Algo deu errado do nosso lado. Tente novamente em alguns minutos."

    def __init__(self, mensagem: str | None = None, *, detalhe_tecnico: str | None = None):
        self.mensagem_usuario = mensagem or self.mensagem
        self.detalhe_tecnico = detalhe_tecnico
        super().__init__(detalhe_tecnico or self.mensagem_usuario)


class LLMIndisponivel(ErroZela):
    status_code = 503
    codigo = "IA_INDISPONIVEL"
    mensagem = "Nosso assistente de análise está fora do ar no momento. Seu relato não foi perdido: tente novamente em instantes."


class LLMTempoEsgotado(ErroZela):
    status_code = 504
    codigo = "IA_TEMPO_ESGOTADO"
    mensagem = "A análise demorou mais do que o esperado. Tente novamente; se continuar, registre direto pelo telefone 156."


class LLMRespostaInvalida(ErroZela):
    status_code = 502
    codigo = "IA_RESPOSTA_INVALIDA"
    mensagem = "Não conseguimos entender a análise automática desta vez. Tente reformular o relato ou envie novamente."


class LLMSobrecarregado(ErroZela):
    status_code = 503
    codigo = "IA_SOBRECARREGADA"
    mensagem = "Muitas pessoas estão usando o serviço agora. Aguarde um minuto e tente de novo."


class LLMConfiguracao(ErroZela):
    status_code = 503
    codigo = "IA_NAO_CONFIGURADA"
    mensagem = "O assistente de análise está em manutenção. Tente mais tarde ou ligue 156."


class NaoEncontrado(ErroZela):
    status_code = 404
    codigo = "NAO_ENCONTRADO"
    mensagem = "Não encontramos o que você procurou."


class NaoAutorizado(ErroZela):
    status_code = 401
    codigo = "NAO_AUTORIZADO"
    mensagem = "Sua sessão expirou ou as credenciais estão incorretas. Entre novamente."


class LimiteExcedido(ErroZela):
    status_code = 429
    codigo = "LIMITE_DE_ENVIOS"
    mensagem = "Você enviou muitos relatos em pouco tempo. Aguarde um minuto e tente novamente."
