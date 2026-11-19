"""Explica, em linguagem simples, como o Zela funciona, o que a IA faz e o que ela NÃO faz."""

import streamlit as st


def tela() -> None:
    st.subheader("Como o Zela funciona", anchor=False)
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("### 1. Você conta\nEscreva com suas palavras o problema da rua e informe o CEP. Se quiser, "
                    "mande uma foto. Telefones, CPF e e-mails são apagados do texto antes de qualquer análise.")
    with c2.container(border=True):
        st.markdown("### 2. A IA organiza\nUma inteligência artificial sugere o tipo de problema, a urgência e o que "
                    "você pode fazer agora. Na foto, outra IA procura sinais de fissura. Regras de segurança revisam "
                    "casos de risco e cruzamos o local com a previsão de chuva.")
    with c3.container(border=True):
        st.markdown("### 3. Você confirma\nVocê confere, corrige se precisar e só então o relato é registrado, com "
                    "protocolo e o órgão responsável. A equipe da prefeitura também revisa.")

    st.markdown("#### O que a IA **não** faz")
    st.markdown(
        "- Não substitui os serviços de emergência: em perigo, ligue **193** (Bombeiros), **199** (Defesa Civil) ou **192** (SAMU).\n"
        "- Não decide sozinha: nada é enviado sem a sua confirmação, e a equipe da prefeitura revisa cada caso.\n"
        "- Não inventa telefones, órgãos ou prazos: o encaminhamento vem de uma tabela oficial mantida pela equipe.\n"
        "- Não promete prazo de solução: o prazo exibido é apenas uma referência.\n"
        "- Não mede a gravidade de uma rachadura pela foto: ela só indica que vale uma vistoria técnica.\n"
        "- Na aba **Tire dúvidas**, responde só com base em páginas oficiais da Prefeitura e mostra a fonte. Se a resposta "
        "não estiver nas fontes, diz que não encontrou e indica o 156.\n"
        "- Pode errar. Por isso mostramos o quanto ela tem certeza e pedimos que você confira."
    )

    st.markdown("#### Seus dados")
    st.markdown(
        "- Você não precisa se identificar. Contato é opcional e só a equipe responsável vê.\n"
        "- O painel público mostra apenas tipo, urgência, situação e bairro, com a localização aproximada (cerca de 100 m).\n"
        "- O texto do relato é guardado já sem dados pessoais. A foto é analisada e descartada: só o resultado da análise fica no relato."
    )

    st.markdown("#### Acessibilidade")
    st.markdown(
        "- **Alto contraste** e **tamanho do texto** no menu lateral.\n"
        "- **Ouvir em voz alta**: o resultado da análise pode ser lido pelo navegador.\n"
        "- Urgência sempre mostrada com **cor + ícone + texto**; gráficos com texturas, texto alternativo e versão em tabela.\n"
        "- Todos os campos têm rótulo e dica; dá para usar tudo pelo teclado (Tab, Enter, Espaço)."
    )
    st.caption("Fontes de dados abertos: BrasilAPI e ViaCEP (endereço), OpenStreetMap/Nominatim (localização), "
               "Open-Meteo (previsão de chuva).")
