"""Adaptação do texto para fala: o que o TTS recebe precisa soar natural e completo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from voz.fala import adaptar_para_fala  # noqa: E402


def test_citacoes_markdown_e_emojis_somem():
    fala = adaptar_para_fala("**Ligue** para o 156 [1]. ✅ O pedido é gratuito [2].")
    assert "[" not in fala and "*" not in fala and "✅" not in fala
    assert "cento e cinquenta e seis" in fala


def test_telefone_e_dito_digito_a_digito():
    fala = adaptar_para_fala("A Sabesp atende no 0800 055 0195.")
    assert "zero oito zero zero, zero cinco cinco, zero um nove cinco" in fala


def test_dinheiro_porcentagem_e_data():
    fala = adaptar_para_fala("A multa é de R$ 439,66 por metro. A faixa livre é de 50% da calçada. Vale desde 07/08/2020.")
    assert "quatrocentos e trinta e nove reais e sessenta e seis centavos" in fala
    assert "cinquenta por cento" in fala
    assert "sete de agosto de dois mil e vinte" in fala


def test_link_vira_site_oficial_sem_repetir_a_palavra_site_e_sem_engolir_o_ponto():
    fala = adaptar_para_fala(
        "Peça pelo site https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=1071. O pedido leva alguns dias."
    )
    assert "pelo site oficial." in fala
    assert "site o site" not in fala
    assert "O pedido leva alguns dias." in fala


def test_endereco_sem_http_tambem_nao_e_lido():
    fala = adaptar_para_fala("A programação está em www.locatsp.com.br e em sp156.prefeitura.sp.gov.br/portal/servicos.")
    assert "locatsp" not in fala and "prefeitura.sp" not in fala
    assert fala.endswith(".")


def test_siglas_ficam_pronunciaveis():
    fala = adaptar_para_fala("A CET cuida do semáforo e o Zela remove o CPF.")
    assert "cê é tê" in fala and "cê pê éfe" in fala


def test_frase_longa_e_dividida_em_duas_frases_completas():
    longa = ("O munícipe poderá solicitar a vistoria de um técnico da Prefeitura de São Paulo pelo telefone 156, "
             "na Praça de Atendimento da Subprefeitura mais próxima da sua casa, levando um documento com foto e o "
             "endereço completo do local onde está a árvore.")
    fala = adaptar_para_fala(longa)
    frases = [f for f in fala.split(". ") if f]
    assert len(frases) >= 2
    assert all(f[0].isupper() for f in frases)


def test_resposta_fica_curta_para_quem_ouve():
    fala = adaptar_para_fala("Um. Dois. Três. Quatro. Cinco. Seis.", max_frases=4)
    assert fala.count(".") == 4


def test_protocolo_e_soletrado():
    fala = adaptar_para_fala("Seu protocolo é ZL-261111-A1B2C3.")
    assert "dois seis um um um um" in fala and "A um B dois C três" in fala
