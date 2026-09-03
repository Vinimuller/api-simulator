"""
Visualiza as duas distribuições de probabilidade que orientam a simulação:
1) Intervalo entre chegadas de requisições -> Exponencial(taxa=TAXA_CHEGADA)
2) Tempo de processamento por requisição -> TEMPO_BASE + Uniforme(TAMANHO_MIN, TAMANHO_MAX) * TEMPO_POR_UNIDADE
   (uma transformação linear de uma variável uniforme, portanto também é uniforme)

Gera N_USUARIOS amostras de cada uma (mesmo tamanho de amostra da simulação
real) e sobrepõe a FDP teórica ao histograma empírico.
"""

import random

import matplotlib.pyplot as plt
import numpy as np

from api_simulator import (
    N_USUARIOS,
    SEMENTE_ALEATORIA,
    TAMANHO_MAX,
    TAMANHO_MIN,
    TAXA_CHEGADA,
    TEMPO_BASE,
    TEMPO_POR_UNIDADE,
)

random.seed(SEMENTE_ALEATORIA)

# ---------------------------------------------------------------------------
# Amostra da mesma forma que a simulação
# ---------------------------------------------------------------------------

amostras_intervalo_chegada = [random.expovariate(TAXA_CHEGADA) for _ in range(N_USUARIOS)]

tamanhos_imagem = [random.uniform(TAMANHO_MIN, TAMANHO_MAX) for _ in range(N_USUARIOS)]
amostras_tempo_processamento = [TEMPO_BASE + tamanho * TEMPO_POR_UNIDADE for tamanho in tamanhos_imagem]

proc_min = TEMPO_BASE + TAMANHO_MIN * TEMPO_POR_UNIDADE
proc_max = TEMPO_BASE + TAMANHO_MAX * TEMPO_POR_UNIDADE

fig, eixos = plt.subplots(1, 2, figsize=(12, 5))

# --- Intervalo entre chegadas: Exponencial(taxa=TAXA_CHEGADA) ---
eixo = eixos[0]
eixo.hist(amostras_intervalo_chegada, bins=40, density=True, alpha=0.6,
          color="steelblue", edgecolor="white", label="Intervalos entre chegadas amostrados")
x = np.linspace(0, max(amostras_intervalo_chegada), 300)
fdp = TAXA_CHEGADA * np.exp(-TAXA_CHEGADA * x)
eixo.plot(x, fdp, color="darkred", linewidth=2,
          label=f"FDP Exponencial (λ={TAXA_CHEGADA})")
eixo.set_title("Chegadas de requisições\nIntervalo entre chegadas ~ Exponencial(λ)")
eixo.set_xlabel("Intervalo entre chegadas (s)")
eixo.set_ylabel("Densidade")
eixo.legend()

# --- Tempo de processamento: TEMPO_BASE + Uniforme(TAMANHO_MIN, TAMANHO_MAX) * TEMPO_POR_UNIDADE ---
eixo = eixos[1]
eixo.hist(amostras_tempo_processamento, bins=40, density=True, alpha=0.6,
          color="seagreen", edgecolor="white", label="Tempos de processamento amostrados")
altura = 1.0 / (proc_max - proc_min)
eixo.plot([proc_min, proc_min, proc_max, proc_max],
          [0, altura, altura, 0],
          color="darkred", linewidth=2,
          label=f"FDP Uniforme [{proc_min:.2f}, {proc_max:.2f}] s")
eixo.set_title("Tempo de processamento\ntempo = TEMPO_BASE + Uniforme(tamanho) × TEMPO_POR_UNIDADE")
eixo.set_xlabel("Tempo de processamento (s)")
eixo.set_ylabel("Densidade")
eixo.legend()

fig.suptitle("Distribuições usadas na simulação de fila da API", fontsize=13)
fig.tight_layout()
fig.savefig("distributions.png", dpi=150)
print("distributions.png salvo")
