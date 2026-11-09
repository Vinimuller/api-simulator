"""
Simulação de fila de API (SimPy).

Modela uma API de processamento de imagens com dois processos em sequência —
Validador e Processador, cada um com fila própria FIFO e fila infinita — e
uma decisão de rota condicional: imagens pequenas (já otimizadas) saem direto
após a validação, sem passar pelo processamento pesado. Um grupo finito de
usuários envia exatamente uma requisição cada; as requisições chegam como um
processo de Poisson e levam mais tempo para processar quanto maior a imagem
(tamanho uniforme).
"""

import random
from dataclasses import dataclass, field

import simpy

# ---------------------------------------------------------------------------
# Configuração — ajuste estes valores entre execuções
# ---------------------------------------------------------------------------

N_USUARIOS = 1000            # tamanho do grupo finito de usuários (cada um envia 1 requisição)
TAXA_CHEGADA = 0.8           # requisições/seg, chegada exponencial (lambda)

TAMANHO_MIN = 1.0            # limite inferior do tamanho da imagem (MB)
TAMANHO_MAX = 10.0           # limite superior do tamanho da imagem (MB)
TEMPO_BASE = 0.1             # overhead fixo por requisição (seg)
TEMPO_POR_UNIDADE = 0.15     # segundos de processamento por MB de imagem

TEMPO_VALIDACAO_MIN = 0.02   # limite inferior do tempo de validação (seg)
TEMPO_VALIDACAO_MAX = 0.05   # limite superior do tempo de validação (seg)

LIMIAR_ROTA_MB = 3.0         # decisão de rota: abaixo disso, imagem já é
                              # considerada otimizada e sai direto após a
                              # validação, sem passar pelo Processador

SEMENTE_ALEATORIA = 42


@dataclass
class Estatisticas:
    tempos_espera_validacao: list = field(default_factory=list)
    tempos_validacao: list = field(default_factory=list)
    tempos_espera_processamento: list = field(default_factory=list)
    tempos_processamento: list = field(default_factory=list)
    tempos_resposta: list = field(default_factory=list)
    contagem_rota_rapida: int = 0
    contagem_rota_completa: int = 0
    historico_tamanho_fila_validacao: list = field(default_factory=list)  # (tempo, tamanho)
    historico_tamanho_fila_processamento: list = field(default_factory=list)  # (tempo, tamanho)
    registros: list = field(default_factory=list)  # detalhe por requisição, um dict cada


def registrar_tamanho_fila(ambiente, recurso, historico):
    tamanho = len(recurso.queue) + recurso.count
    historico.append((ambiente.now, tamanho))


def processar_requisicao(ambiente, validador, processador, estatisticas, id_usuario):
    tempo_chegada = ambiente.now
    tamanho_imagem = random.uniform(TAMANHO_MIN, TAMANHO_MAX)

    with validador.request() as requisicao_validacao:
        yield requisicao_validacao
        registrar_tamanho_fila(ambiente, validador, estatisticas.historico_tamanho_fila_validacao)

        tempo_espera_validacao = ambiente.now - tempo_chegada
        estatisticas.tempos_espera_validacao.append(tempo_espera_validacao)

        tempo_validacao = random.uniform(TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX)
        estatisticas.tempos_validacao.append(tempo_validacao)

        yield ambiente.timeout(tempo_validacao)

    registrar_tamanho_fila(ambiente, validador, estatisticas.historico_tamanho_fila_validacao)

    # Decisão de rota condicional: imagens já pequenas/otimizadas (abaixo do
    # limiar) saem direto, sem passar pelo processamento pesado.
    tempo_espera_processamento = None
    tempo_processamento = None

    if tamanho_imagem >= LIMIAR_ROTA_MB:
        rota = "completa"
        estatisticas.contagem_rota_completa += 1

        with processador.request() as requisicao_processamento:
            yield requisicao_processamento
            registrar_tamanho_fila(ambiente, processador, estatisticas.historico_tamanho_fila_processamento)

            tempo_espera_processamento = ambiente.now - tempo_chegada - tempo_espera_validacao - tempo_validacao
            estatisticas.tempos_espera_processamento.append(tempo_espera_processamento)

            tempo_processamento = TEMPO_BASE + tamanho_imagem * TEMPO_POR_UNIDADE
            estatisticas.tempos_processamento.append(tempo_processamento)

            yield ambiente.timeout(tempo_processamento)

        registrar_tamanho_fila(ambiente, processador, estatisticas.historico_tamanho_fila_processamento)
    else:
        rota = "rapida"
        estatisticas.contagem_rota_rapida += 1

    tempo_resposta = ambiente.now - tempo_chegada
    estatisticas.tempos_resposta.append(tempo_resposta)

    estatisticas.registros.append({
        "id_usuario": id_usuario,
        "tempo_chegada": tempo_chegada,
        "tamanho_imagem": tamanho_imagem,
        "rota": rota,
        "tempo_espera_validacao": tempo_espera_validacao,
        "tempo_validacao": tempo_validacao,
        "tempo_espera_processamento": tempo_espera_processamento,
        "tempo_processamento": tempo_processamento,
        "tempo_resposta": tempo_resposta,
    })


def gerador_usuarios(ambiente, validador, processador, estatisticas):
    for id_usuario in range(N_USUARIOS):
        yield ambiente.timeout(random.expovariate(TAXA_CHEGADA))
        ambiente.process(processar_requisicao(ambiente, validador, processador, estatisticas, id_usuario))
        registrar_tamanho_fila(ambiente, validador, estatisticas.historico_tamanho_fila_validacao)


def media(valores):
    return sum(valores) / len(valores) if valores else 0.0


def calcular_metricas(ambiente, estatisticas):
    tempo_total = ambiente.now
    n_completadas = len(estatisticas.tempos_resposta)

    utilizacao_validador = sum(estatisticas.tempos_validacao) / tempo_total if tempo_total else 0.0
    utilizacao_processador = sum(estatisticas.tempos_processamento) / tempo_total if tempo_total else 0.0
    vazao = n_completadas / tempo_total if tempo_total else 0.0

    espera_validacao_media = media(estatisticas.tempos_espera_validacao)
    espera_processamento_media = media(estatisticas.tempos_espera_processamento)
    resposta_media = media(estatisticas.tempos_resposta)
    tamanho_medio_fila_validacao = media([t for _, t in estatisticas.historico_tamanho_fila_validacao])
    tamanho_medio_fila_processamento = media([t for _, t in estatisticas.historico_tamanho_fila_processamento])

    percentual_rota_rapida = estatisticas.contagem_rota_rapida / n_completadas if n_completadas else 0.0
    percentual_rota_completa = estatisticas.contagem_rota_completa / n_completadas if n_completadas else 0.0

    return {
        "n_completadas": n_completadas,
        "tempo_total": tempo_total,
        "vazao": vazao,
        "contagem_rota_rapida": estatisticas.contagem_rota_rapida,
        "contagem_rota_completa": estatisticas.contagem_rota_completa,
        "percentual_rota_rapida": percentual_rota_rapida,
        "percentual_rota_completa": percentual_rota_completa,
        "utilizacao_validador": utilizacao_validador,
        "espera_validacao_media": espera_validacao_media,
        "tamanho_medio_fila_validacao": tamanho_medio_fila_validacao,
        "utilizacao_processador": utilizacao_processador,
        "espera_processamento_media": espera_processamento_media,
        "tamanho_medio_fila_processamento": tamanho_medio_fila_processamento,
        "resposta_media": resposta_media,
        "resposta_maxima": max(estatisticas.tempos_resposta, default=0.0),
    }


def imprimir_relatorio(ambiente, estatisticas):
    m = calcular_metricas(ambiente, estatisticas)

    print("=" * 50)
    print("RESUMO DA SIMULAÇÃO DE FILA DA API")
    print("=" * 50)
    print(f"Requisições concluídas:  {m['n_completadas']} / {N_USUARIOS}")
    print(f"Tempo total simulado:    {m['tempo_total']:.2f} s")
    print(f"Vazão:                   {m['vazao']:.4f} req/s")
    print("-" * 50)
    print(f"Rota rápida (sem Processador):   {m['contagem_rota_rapida']} "
          f"({m['percentual_rota_rapida']:.2%})")
    print(f"Rota completa (com Processador): {m['contagem_rota_completa']} "
          f"({m['percentual_rota_completa']:.2%})")
    print("-" * 50)
    print(f"Utilização do Validador:    {m['utilizacao_validador']:.2%}")
    print(f"Tempo médio de espera:      {m['espera_validacao_media']:.4f} s")
    print(f"Tamanho médio da fila:      {m['tamanho_medio_fila_validacao']:.4f}")
    print("-" * 50)
    print(f"Utilização do Processador:  {m['utilizacao_processador']:.2%}")
    print(f"Tempo médio de espera:      {m['espera_processamento_media']:.4f} s")
    print(f"Tamanho médio da fila:      {m['tamanho_medio_fila_processamento']:.4f}")
    print("-" * 50)
    print(f"Tempo médio de resposta:    {m['resposta_media']:.4f} s")
    print(f"Tempo máximo de resposta:   {m['resposta_maxima']:.4f} s")
    print("-" * 50)


def executar_simulacao(semente):
    random.seed(semente)

    ambiente = simpy.Environment()
    validador = simpy.Resource(ambiente, capacity=1)
    processador = simpy.Resource(ambiente, capacity=1)
    estatisticas = Estatisticas()

    ambiente.process(gerador_usuarios(ambiente, validador, processador, estatisticas))
    ambiente.run()

    return ambiente, estatisticas


def principal():
    ambiente, estatisticas = executar_simulacao(SEMENTE_ALEATORIA)

    imprimir_relatorio(ambiente, estatisticas)
    print()


if __name__ == "__main__":
    principal()
