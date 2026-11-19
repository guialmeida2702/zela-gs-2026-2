# OuviAí · IoT (Edge Impulse no celular)

**Autor:** Guilherme Almeida (RM 563972) · turma 2TIAPY · trabalho individual

Classificador de sons domésticos para pessoas surdas ou com deficiência auditiva: o celular escuta e mostra na tela se tocou a **campainha**, se alguém **bateu na porta** ou se é só **ambiente**. Tudo roda no próprio celular, sem enviar áudio para a internet.

**Ligação com o Zela.** O Zela trata acessibilidade como requisito (alto contraste, leitura em voz alta, assistente por voz). O OuviAí leva a mesma ideia para dentro de casa e abre uma evolução direta para a zeladoria: uma classe de **sirene de alerta da Defesa Civil**, para que quem não ouve a sirene de alagamento receba o aviso por vibração e luz.

> **Situação (17/11/2026):** gravações, treino e teste com arquivos feitos no Edge Impulse (projeto privado "almeidareff / OuviAí"). Validação 90,1%; Classify all nos 15 arquivos de Test: 76,1% por janela e 12 de 15 arquivos. Teste ao vivo em 18/11: 10 de 15 acertos (campainha e batida 5 de 5, ambiente 0 de 5) e 5 falsos positivos em ambiente, com obra no vizinho durante o teste. Vídeo do teste ao vivo: https://youtube.com/shorts/BKm9vIrK8n4. Na conferência auditiva, ambiente_06 tem uma batida (rótulo errado, documentado no relatório) e ambiente_11 tem ruído de avião.
>
> Resultados guardados em `resultados/` (gravações, parâmetros e Classify all); capturas em `capturas/`; `python gerar_planilha.py` refaz a planilha a partir deles.

| Arquivo | Para que serve |
|---|---|
| `README.md` | Roteiro passo a passo e checklist de entrega |
| `planilha_ouviai.xlsx` | Registro das 60 gravações, dos 15 áudios de Test (Classify all) e das 15 tentativas ao vivo, com acertos e falsos positivos calculados (gerada por `gerar_planilha.py`) |
| `verificar_audios.py` | Confere se os WAV estão em 16 kHz, mono, 16 bits e cerca de 5 s; converte gravações do celular com ffmpeg |
| `relatorio_ouviai.md` | Relatório na ordem do enunciado, com capa, pronto para preencher |
| `arquitetura.png` | Diagrama microfone → MFE → CNN → tela (fonte em `arquitetura.dot`) |

## Roteiro

### 1. Gravação (cerca de 40 min)

- Classes: `campainha`, `batida_porta`, `ambiente` (sons da casa sem campainha nem batida: TV baixa, ventilador, passos, louça).
- **20 gravações de 5 s por classe**: 15 para Training e 5 para Test. Os 5 de Test não podem ser reutilizados no Training. Varie distância (perto e do outro cômodo), volume e o tipo de batida (nós dos dedos, mão aberta).
- Formato: 16 kHz, mono. O mais simples é gravar direto no Edge Impulse pelo celular (Devices > Connect a new device > Use your mobile phone, frequência 16000 Hz). Se gravar com outro aplicativo, rode `python verificar_audios.py pasta/ --converter` para chegar em WAV PCM 16 bits.
- Ouça cada gravação e confirme que ela contém o evento do rótulo. **Não grave conversas** que identifiquem pessoas; se alguém falar, descarte o arquivo.
- Anote cada arquivo na aba `Gravacoes` da planilha.

### 2. Edge Impulse (cerca de 30 min)

Faça uma captura de tela em cada etapa. São as cinco capturas pedidas no enunciado.

1. **Data acquisition:** confira os rótulos e a divisão 15/5 por classe.
2. **Impulse design (Create impulse):** janela de 1.000 ms com passo de 500 ms; bloco de processamento **Audio (MFE)**; bloco de aprendizado **Classification**.
3. **Generate features:** na tela do MFE, gere as features e capture o Feature explorer. Anote os parâmetros do MFE.
4. **Classifier:** treine a CNN; anote ciclos, taxa de aprendizado, acurácia de validação e a matriz de confusão.
5. **Model testing:** rode **Classify all** nos 15 arquivos de Test; anote o resultado de cada arquivo na aba `Teste_arquivos` e a matriz de confusão.

### 3. Teste ao vivo no celular (obrigatório)

**Deployment > Run this model**: leia o QR Code com o celular, abra no navegador e autorize o microfone. Faça 5 tentativas por classe (15 ao todo), com o celular no lugar onde ficaria de verdade. Para cada tentativa, anote na aba `Teste_ao_vivo` o som produzido, a classe prevista e se acertou. A planilha calcula o percentual de acertos e os **falsos positivos em ambiente**. Grave um vídeo curto ou faça capturas mostrando o QR Code aberto, o microfone autorizado e as classes mudando.

Lembrete do enunciado: a probabilidade que aparece na tela não é a acurácia. A acurácia ao vivo é o número de acertos dividido por 15.

### 4. Relatório

1. Coloque as capturas em `iot_ouviai/capturas/` e troque cada `[CAPTURA n: ...]` do `relatorio_ouviai.md` por `![legenda](capturas/arquivo.png){width=90%}`.
2. Preencha os campos entre colchetes com os números da planilha.
3. Gere o PDF: `bash docs/relatorios/gerar_pdfs.sh iot_ouviai/relatorio_ouviai.md` (sai em `docs/relatorios/pdf/relatorio_ouviai.pdf`). Se preferir, abra o `.docx` gerado na mesma pasta e edite no Word.

## Checklist de entrega (itens do enunciado)

- [x] Capa com título do projeto, nome e RM
- [x] Descrição do problema, público beneficiado e ODS (texto pronto, seção 1)
- [x] Arquitetura microfone → MFE → CNN → classificação visual (seção 2)
- [x] Origem dos áudios e distribuição Training/Test preenchidas (seções 2 e 3)
- [x] Capturas de Data acquisition, Impulse design, Generate features, Classifier e Model testing
- [x] Parâmetros do MFE e da CNN, resultado de validação e matriz de confusão (seção 4)
- [x] Tabela com os 15 áudios de Test, matriz de confusão e discussão dos erros (seção 5)
- [x] Vídeo curto do modelo rodando no celular (https://youtube.com/shorts/BKm9vIrK8n4); registro das 15 tentativas, percentual de acertos e falsos positivos em ambiente (seção 6)
- [x] Comparação das três avaliações e limitações (seção 7)
- [x] Evolução para notificações e vibração (seção 8)
- [ ] Nenhuma gravação com conversa identificável
