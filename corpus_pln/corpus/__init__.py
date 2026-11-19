"""Ferramenta de construção de corpus do Zela (PLN): leitura, limpeza e três corpora para fine-tuning."""

from .exportacao import arquivos, exportar, pacote_zip, validar_pasta
from .geradores import RECUSAS_PADRAO, SISTEMA_PADRAO, gerar_pares_com_llm
from .leitura import FORMATOS, Documento, ErroLeitura, ler_arquivo, ler_bytes, ler_texto_colado
from .limpeza import OpcoesLimpeza, RelatorioLimpeza, limpar, texto_limpo
from .pipeline import Configuracao, Resultado, construir

__all__ = [
    "FORMATOS", "RECUSAS_PADRAO", "SISTEMA_PADRAO", "Configuracao", "Documento", "ErroLeitura", "OpcoesLimpeza",
    "RelatorioLimpeza", "Resultado", "arquivos", "construir", "exportar", "gerar_pares_com_llm", "ler_arquivo",
    "ler_bytes", "ler_texto_colado", "limpar", "pacote_zip", "texto_limpo", "validar_pasta",
]
