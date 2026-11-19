#!/bin/bash
# Converte os relatórios em Markdown para DOCX e PDF (pandoc + LibreOffice). Uso: bash docs/relatorios/gerar_pdfs.sh [arquivo.md ...]
set -e
# Caminhos passados como argumento valem a partir da pasta de onde o comando foi chamado
ARQS=(); for md in "$@"; do ARQS+=("$(realpath -m "$md")"); done
cd "$(dirname "$0")"
mkdir -p pdf
[ ${#ARQS[@]} -eq 0 ] && ARQS=(visao_computacional.md cluster.md quantica.md genai_avaliacao.md pln_assistente_voz.md ../../iot_ouviai/relatorio_ouviai.md)
for md in "${ARQS[@]}"; do
  [ -f "$md" ] || { echo "pulando $md (não existe)"; continue; }
  nome=$(basename "$md" .md)
  pandoc "$md" -o "pdf/$nome.docx" --reference-doc=referencia_estilo.docx --resource-path=".:../..:$(dirname "$md")"
  soffice --headless --convert-to pdf --outdir pdf "pdf/$nome.docx" >/dev/null 2>&1
  echo "pdf/$nome.pdf ($(pdfinfo "pdf/$nome.pdf" | awk '/Pages/{print $2}') páginas)"
done
