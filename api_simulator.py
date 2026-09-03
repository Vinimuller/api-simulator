"""
Simulação de fila de API (SimPy).

Modela uma API de processamento de imagens com um único servidor, disciplina
FIFO e fila infinita. Um grupo finito de usuários envia exatamente uma
requisição cada; as requisições chegam como um processo de Poisson e levam
mais tempo para processar quanto maior a imagem (tamanho uniforme).
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

SEMENTE_ALEATORIA = 42


@dataclass
class Estatisticas:
    tempos_espera: list = field(default_factory=list)
    tempos_resposta: list = field(default_factory=list)
    tempos_processamento: list = field(default_factory=list)
    historico_tamanho_fila: list = field(default_factory=list)  # (tempo, tamanho)
    registros: list = field(default_factory=list)  # detalhe por requisição, um dict cada


def registrar_tamanho_fila(ambiente, servidor, estatisticas):
    tamanho = len(servidor.queue) + servidor.count
    estatisticas.historico_tamanho_fila.append((ambiente.now, tamanho))


def processar_requisicao(ambiente, servidor, estatisticas, id_usuario):
    tempo_chegada = ambiente.now

    with servidor.request() as requisicao:
        yield requisicao
        registrar_tamanho_fila(ambiente, servidor, estatisticas)

        tempo_espera = ambiente.now - tempo_chegada
        estatisticas.tempos_espera.append(tempo_espera)

        tamanho_imagem = random.uniform(TAMANHO_MIN, TAMANHO_MAX)
        tempo_processamento = TEMPO_BASE + tamanho_imagem * TEMPO_POR_UNIDADE
        estatisticas.tempos_processamento.append(tempo_processamento)

        yield ambiente.timeout(tempo_processamento)

    registrar_tamanho_fila(ambiente, servidor, estatisticas)
    tempo_resposta = ambiente.now - tempo_chegada
    estatisticas.tempos_resposta.append(tempo_resposta)

    estatisticas.registros.append({
        "id_usuario": id_usuario,
        "tempo_chegada": tempo_chegada,
        "tempo_espera": tempo_espera,
        "tamanho_imagem": tamanho_imagem,
        "tempo_processamento": tempo_processamento,
        "tempo_resposta": tempo_resposta,
    })


def gerador_usuarios(ambiente, servidor, estatisticas):
    for id_usuario in range(N_USUARIOS):
        yield ambiente.timeout(random.expovariate(TAXA_CHEGADA))
        ambiente.process(processar_requisicao(ambiente, servidor, estatisticas, id_usuario))
        registrar_tamanho_fila(ambiente, servidor, estatisticas)


def media(valores):
    return sum(valores) / len(valores) if valores else 0.0


def imprimir_relatorio(ambiente, estatisticas):
    tempo_total = ambiente.now
    utilizacao = sum(estatisticas.tempos_processamento) / tempo_total if tempo_total else 0.0
    vazao = len(estatisticas.tempos_resposta) / tempo_total if tempo_total else 0.0

    espera_media = media(estatisticas.tempos_espera)
    resposta_media = media(estatisticas.tempos_resposta)
    tamanho_medio_fila = media([tamanho for _, tamanho in estatisticas.historico_tamanho_fila])

    # Verificação da Lei de Little: L ~= lambda_efetivo * W
    lei_little_L = vazao * resposta_media

    print("=" * 50)
    print("RESUMO DA SIMULAÇÃO DE FILA DA API")
    print("=" * 50)
    print(f"Requisições concluídas:  {len(estatisticas.tempos_resposta)} / {N_USUARIOS}")
    print(f"Tempo total simulado:    {tempo_total:.2f} s")
    print(f"Vazão:                   {vazao:.4f} req/s")
    print(f"Utilização do servidor:  {utilizacao:.2%}")
    print("-" * 50)
    print(f"Tempo médio de espera:   {espera_media:.4f} s")
    print(f"Tempo máximo de espera:  {max(estatisticas.tempos_espera, default=0):.4f} s")
    print(f"Tempo médio de resposta: {resposta_media:.4f} s")
    print(f"Tempo máximo de resposta:{max(estatisticas.tempos_resposta, default=0):.4f} s")
    print(f"Tamanho médio da fila:   {tamanho_medio_fila:.4f}")
    print("-" * 50)
    print(f"Verificação Lei de Little: L ~= {lei_little_L:.4f} "
          f"(vazão x tempo médio de resposta)")
    print("=" * 50)


def imprimir_tabela_amostra(estatisticas, n=10):
    linhas = sorted(estatisticas.registros, key=lambda r: r["id_usuario"])[:n]

    print(f"Primeiras {len(linhas)} requisições")
    print("-" * 84)
    print(f"{'id_usuario':>10} | {'tempo_chegada':>13} | {'tempo_espera':>12} | "
          f"{'tamanho_imagem':>14} | {'tempo_processamento':>19}")
    print("-" * 84)
    for r in linhas:
        print(f"{r['id_usuario']:>10} | {r['tempo_chegada']:>13.4f} | "
              f"{r['tempo_espera']:>12.4f} | {r['tamanho_imagem']:>14.4f} | "
              f"{r['tempo_processamento']:>19.4f}")
    print("-" * 84)


def principal():
    random.seed(SEMENTE_ALEATORIA)

    ambiente = simpy.Environment()
    servidor = simpy.Resource(ambiente, capacity=1)
    estatisticas = Estatisticas()

    ambiente.process(gerador_usuarios(ambiente, servidor, estatisticas))
    ambiente.run()

    imprimir_relatorio(ambiente, estatisticas)
    print()
    imprimir_tabela_amostra(estatisticas)


if __name__ == "__main__":
    principal()
