# Visão Computacional · fissuras em estruturas urbanas

Classificador de fissuras em concreto (MobileNetV3-Small, transferência de aprendizado, exportado para ONNX) integrado ao Zela: foto no relato do cidadão, evidência para a triagem, monitoramento em lote para o gestor e triagem das fotos de vistoria no robô RPA.

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

- Relatório: [`docs/relatorios/visao_computacional.md`](../docs/relatorios/visao_computacional.md) (PDF em `docs/relatorios/pdf/`)
- Código completo do treino à exportação: [`pipeline.py`](pipeline.py)
- Modelo e pré-processamento: `modelos/` (cópia usada pela API em `backend/app/modelos/`)
- Resultados: `resultados/` (métricas, matrizes de confusão, análise de erros, robustez, vídeo de monitoramento simulado)
- Inferência na API: `backend/app/providers/visao.py` · testes: `backend/tests/test_inteligencia.py`

```bash
pip install -r requirements.txt
# base: https://data.mendeley.com/datasets/5y9wdsg2zt/2 (CC BY 4.0), pastas Positive/ e Negative/
python pipeline.py --dados /caminho/ConcreteCrack --threads 2
```

Lembrete do enunciado que guia a interface: **a presença de fissura não determina a gravidade.** O modelo prioriza vistorias; quem avalia o risco é o técnico.
