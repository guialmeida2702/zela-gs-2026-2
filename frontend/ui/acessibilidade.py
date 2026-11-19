"""Recursos de acessibilidade: leitura em voz alta e idioma da página.

A leitura usa a Web Speech API do próprio navegador (pt-BR): nenhum áudio ou
texto é enviado a serviços externos.
"""

import html
import json
import uuid

import streamlit.components.v1 as components


def definir_idioma_pagina() -> None:
    """Ajusta <html lang="pt-BR"> para leitores de tela pronunciarem corretamente."""
    components.html(
        "<script>try{window.parent.document.documentElement.lang='pt-BR';}catch(e){}</script>", height=0
    )


def botao_ouvir(texto: str, rotulo: str = "🔊 Ouvir em voz alta") -> None:
    """Botão nativo (<button>), acessível por teclado, que lê o texto em português."""
    id_ = f"ouvir-{uuid.uuid4().hex[:8]}"
    texto_js = json.dumps(texto[:3000])
    rotulo_html = html.escape(rotulo)
    components.html(
        f"""
        <button id="{id_}" type="button" aria-label="Ouvir o resultado em voz alta"
          style="font: 600 15px 'Source Sans Pro', sans-serif; padding: 8px 14px; border-radius: 8px;
                 border: 2px solid #0F5C63; background: #fff; color: #0F5C63; cursor: pointer;">
          {rotulo_html}
        </button>
        <span id="{id_}-st" role="status" style="font: 13px sans-serif; color:#4A5654; margin-left:8px"></span>
        <script>
          const b = document.getElementById("{id_}");
          const st = document.getElementById("{id_}-st");
          b.addEventListener("click", () => {{
            if (!("speechSynthesis" in window)) {{ st.textContent = "Seu navegador não tem leitura em voz alta."; return; }}
            if (speechSynthesis.speaking) {{ speechSynthesis.cancel(); st.textContent = "Leitura interrompida."; return; }}
            const u = new SpeechSynthesisUtterance({texto_js});
            u.lang = "pt-BR"; u.rate = 0.95;
            u.onend = () => st.textContent = "";
            speechSynthesis.speak(u); st.textContent = "Lendo… (clique de novo para parar)";
          }});
        </script>
        """,
        height=48,
    )


def texto_para_leitura(resposta: dict) -> str:
    an = resposta["analise"]
    enc = resposta["encaminhamento"]
    partes = [
        f"Resultado da análise. {an['titulo']}.",
        f"Urgência {an['urgencia'].replace('critica', 'crítica').replace('media', 'média')}.",
    ]
    if an.get("risco_imediato"):
        partes.append("Atenção: há risco imediato. Afaste-se do local e ligue para os serviços de emergência.")
    partes.append("O que você pode fazer agora: " + " ".join(f"{i}. {p}" for i, p in enumerate(an["orientacoes"], 1)))
    partes.append(f"Seu relato será encaminhado para {enc['orgao']}. Canal: {enc['canal']}.")
    partes.append("Confira a classificação e confirme o envio para receber o protocolo.")
    return " ".join(partes)
