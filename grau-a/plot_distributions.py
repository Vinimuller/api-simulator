"""
Visualiza as três distribuições de probabilidade que orientam a simulação:
1) Intervalo entre chegadas de requisições -> Exponencial(taxa=TAXA_CHEGADA)
2) Tempo de validação por requisição -> Uniforme(TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX)
3) Tamanho da imagem por requisição -> Uniforme(TAMANHO_MIN, TAMANHO_MAX)

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
    TEMPO_VALIDACAO_MAX,
    TEMPO_VALIDACAO_MIN,
)

random.seed(SEMENTE_ALEATORIA)

# ---------------------------------------------------------------------------
# Amostra da mesma forma que a simulação
# ---------------------------------------------------------------------------

amostras_intervalo_chegada = [random.expovariate(TAXA_CHEGADA) for _ in range(N_USUARIOS)]

amostras_tempo_validacao = [random.uniform(TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX) for _ in range(N_USUARIOS)]

tamanhos_imagem = [random.uniform(TAMANHO_MIN, TAMANHO_MAX) for _ in range(N_USUARIOS)]

fig, eixos = plt.subplots(1, 3, figsize=(17, 5))

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

# --- Tempo de validação: Uniforme(TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX) ---
eixo = eixos[1]
eixo.hist(amostras_tempo_validacao, bins=40, density=True, alpha=0.6,
          color="mediumpurple", edgecolor="white", label="Tempos de validação amostrados")
altura_validacao = 1.0 / (TEMPO_VALIDACAO_MAX - TEMPO_VALIDACAO_MIN)
eixo.plot([TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX, TEMPO_VALIDACAO_MAX],
          [0, altura_validacao, altura_validacao, 0],
          color="darkred", linewidth=2,
          label=f"FDP Uniforme [{TEMPO_VALIDACAO_MIN:.2f}, {TEMPO_VALIDACAO_MAX:.2f}] s")
eixo.set_title("Validação de requisições\ntempo de validação ~ Uniforme")
eixo.set_xlabel("Tempo de validação (s)")
eixo.set_ylabel("Densidade")
eixo.legend()

# --- Tamanho da imagem: Uniforme(TAMANHO_MIN, TAMANHO_MAX) ---
eixo = eixos[2]
eixo.hist(tamanhos_imagem, bins=40, density=True, alpha=0.6,
          color="orange", edgecolor="white", label="Tamanhos de imagem amostrados")
altura_tamanho = 1.0 / (TAMANHO_MAX - TAMANHO_MIN)
eixo.plot([TAMANHO_MIN, TAMANHO_MIN, TAMANHO_MAX, TAMANHO_MAX],
          [0, altura_tamanho, altura_tamanho, 0],
          color="darkred", linewidth=2,
          label=f"FDP Uniforme [{TAMANHO_MIN:.1f}, {TAMANHO_MAX:.1f}] MB")
eixo.set_title("Tamanho da imagem\ntamanho ~ Uniforme(TAMANHO_MIN, TAMANHO_MAX)")
eixo.set_xlabel("Tamanho da imagem (MB)")
eixo.set_ylabel("Densidade")
eixo.legend()

fig.suptitle("Distribuições usadas na simulação de fila da API", fontsize=13)
fig.tight_layout()
fig.savefig("distributions.png", dpi=150)
print("distributions.png salvo")
