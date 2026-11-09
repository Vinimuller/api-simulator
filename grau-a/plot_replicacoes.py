"""
Visualiza o tempo médio de resposta das N_REPLICACOES repetições em
replicacoes.csv: uma barra por repetição, com linha tracejada marcando a
média entre as repetições e sua faixa de intervalo de confiança de 95%.

Calcula média, desvio padrão amostral e IC 95% de `resposta_media` usando o
t crítico de Student para df = N_REPLICACOES - 1 = 9 (t = 2,262), fixo porque
N_REPLICACOES é uma constante do projeto (ver executar_replicacoes.py).
"""

import csv

import matplotlib.pyplot as plt
import numpy as np

T_CRITICO_95_DF9 = 2.262  # t de Student, 95% de confiança, df = N_REPLICACOES - 1 = 9

with open("replicacoes.csv", newline="", encoding="utf-8") as arquivo:
    linhas = list(csv.DictReader(arquivo, delimiter=";"))

repeticoes = [int(linha["replicacao"]) for linha in linhas]
respostas_medias = np.array([float(linha["resposta_media"].replace(",", ".")) for linha in linhas])

media = respostas_medias.mean()
desvio_padrao = respostas_medias.std(ddof=1)
erro_padrao = desvio_padrao / np.sqrt(len(respostas_medias))
margem_ic = T_CRITICO_95_DF9 * erro_padrao
ic_inferior, ic_superior = media - margem_ic, media + margem_ic

print(f"Tempo médio de resposta (média das {len(respostas_medias)} repetições): {media:.4f} s")
print(f"Desvio padrão amostral: {desvio_padrao:.4f} s")
print(f"IC 95%: [{ic_inferior:.4f}, {ic_superior:.4f}] s (margem ±{margem_ic:.4f} s)")

fig, eixo = plt.subplots(figsize=(9, 5.5))
eixo.bar(repeticoes, respostas_medias, color="steelblue", edgecolor="white", label="Tempo médio de resposta por repetição")
eixo.axhline(media, color="darkred", linewidth=2, linestyle="--", label=f"Média das repetições ({media:.2f} s)")
eixo.set_title("Tempo médio de resposta por repetição")
eixo.set_xlabel("Repetição")
eixo.set_ylabel("Tempo médio de resposta (s)")
eixo.set_xticks(repeticoes)
eixo.legend()

fig.tight_layout()
fig.savefig("resposta_media_replicacoes.png", dpi=150)
print("resposta_media_replicacoes.png salvo")
