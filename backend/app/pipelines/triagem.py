"""Pipeline de triagem: relato do cidadão -> análise estruturada pronta para revisão humana.

Etapas:
  1. Anonimização (remove CPF, telefone, e-mail... antes de qualquer envio externo) e remoção de frases
     com ordens ao sistema (prompt injection)
  2. Enriquecimento com dados abertos (endereço pelo CEP, coordenadas, previsão de chuva)
  3. Chamada ao LLM com saída estruturada (Pydantic) — com cache por conteúdo
  4. Regras de segurança determinísticas (só elevam a urgência)
  5. Encaminhamento determinístico (órgão/canal/prazo pela tabela, não pelo LLM)
  6. Registro da análise como rascunho, aguardando a confirmação do cidadão
"""

import hashlib
import logging
import time
import uuid

from cachetools import TTLCache

from app.pipelines.anonimizacao import anonimizar
from app.pipelines.prompts import PROMPT_VERSAO, SYSTEM_PROMPT, montar_prompt_usuario
from app.pipelines.protecao import remover_instrucoes
from app.pipelines.regras import aplicar_regras
from app.pipelines.roteamento import rotear
from app.providers.clima import ProvedorClima
from app.providers.database import Repositorio
from app.providers.geo import ProvedorGeo
from app.providers.llm.base import ProvedorLLM
from app.schemas.analise import AnaliseIA, AnaliseResposta, ContextoExterno
from app.schemas.relato import RelatoEntrada

log = logging.getLogger("zela.triagem")


class PipelineTriagem:
    def __init__(self, llm: ProvedorLLM, geo: ProvedorGeo, clima: ProvedorClima, repo: Repositorio):
        self.llm = llm
        self.geo = geo
        self.clima = clima
        self.repo = repo
        # Cache da saída do LLM por conteúdo: reenvios idênticos não geram nova chamada (custo e latência)
        self._cache_llm: TTLCache[str, AnaliseIA] = TTLCache(maxsize=512, ttl=3600)

    async def _contexto(self, entrada: RelatoEntrada) -> ContextoExterno:
        ctx = ContextoExterno()
        endereco = await self.geo.buscar_cep(entrada.cep)
        if endereco is None:
            ctx.avisos.append("Não conseguimos confirmar o endereço pelo CEP agora. A análise seguiu sem ele.")
            return ctx
        ctx.fontes_consultadas.append(endereco.fonte)
        if endereco.latitude is None or (entrada.numero and endereco.logradouro):
            coords = await self.geo.geocodificar(endereco, entrada.numero)
            if coords:
                endereco.latitude, endereco.longitude = coords
                ctx.fontes_consultadas.append("OpenStreetMap/Nominatim")
        ctx.endereco = endereco
        if endereco.latitude is not None and endereco.longitude is not None:
            clima = await self.clima.previsao_chuva(endereco.latitude, endereco.longitude)
            if clima:
                ctx.clima = clima
                ctx.fontes_consultadas.append("Open-Meteo")
            else:
                ctx.avisos.append("A previsão do tempo não pôde ser consultada agora.")
        return ctx

    async def analisar(self, entrada: RelatoEntrada) -> AnaliseResposta:
        inicio = time.perf_counter()
        anon = anonimizar(entrada.descricao)
        if entrada.ponto_referencia:
            ref = anonimizar(entrada.ponto_referencia)
            ponto_ref = ref.texto
            anon.removidos.extend(r for r in ref.removidos if r not in anon.removidos)
        else:
            ponto_ref = None
        ctx = await self._contexto(entrada)

        # Frases com ordens ao sistema ("ignore as instruções...") não chegam ao LLM
        texto_llm, instrucoes_removidas = remover_instrucoes(anon.texto)
        prompt_usuario = montar_prompt_usuario(texto_llm, ctx.endereco, ctx.clima, entrada.categoria_sugerida, ponto_ref,
                                               entrada.evidencia_visual)
        chave = hashlib.sha256(f"{PROMPT_VERSAO}|{self.llm.modelo}|{prompt_usuario}".encode()).hexdigest()
        em_cache = chave in self._cache_llm
        if em_cache:
            analise_ia = self._cache_llm[chave]
        else:
            analise_ia = await self.llm.gerar_estruturado(SYSTEM_PROMPT, prompt_usuario, AnaliseIA)
            self._cache_llm[chave] = analise_ia

        analise_final, ajustes = aplicar_regras(analise_ia, anon.texto, ctx.clima)
        if instrucoes_removidas:
            ajustes.insert(0, "Um trecho do relato tentava dar ordens ao sistema e foi ignorado na análise.")
        encaminhamento = rotear(analise_final.categoria, ctx.endereco, analise_final.risco_imediato)
        latencia_ms = int((time.perf_counter() - inicio) * 1000)

        resposta = AnaliseResposta(
            analise_id=uuid.uuid4().hex[:16],
            analise=analise_final,
            urgencia_sugerida_pela_ia=analise_ia.urgencia,
            ajustes_de_seguranca=ajustes,
            encaminhamento=encaminhamento,
            contexto=ctx,
            dados_pessoais_removidos=anon.removidos,
            provedor_ia=self.llm.nome,
            modelo_ia=self.llm.modelo,
            latencia_ms=latencia_ms,
            em_cache=em_cache,
        )
        entrada_salva = entrada.model_dump(mode="json") | {"descricao": anon.texto, "ponto_referencia": ponto_ref}
        self.repo.salvar_analise(
            id=resposta.analise_id,
            entrada=entrada_salva,
            resposta=resposta.model_dump(mode="json"),
            provedor=self.llm.nome,
            modelo=self.llm.modelo,
            prompt_versao=PROMPT_VERSAO,
            latencia_ms=latencia_ms,
        )
        # Log sem o texto do relato (privacidade): apenas metadados
        log.info(
            "analise=%s categoria=%s urgencia=%s ajustes=%d cache=%s latencia_ms=%d",
            resposta.analise_id, analise_final.categoria.value, analise_final.urgencia.value,
            len(ajustes), em_cache, latencia_ms,
        )
        return resposta
