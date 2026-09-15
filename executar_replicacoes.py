"""
Executa N_REPLICACOES simulações independentes, cada uma com uma semente
aleatória diferente, e grava um CSV com uma linha por replicação e uma
coluna por métrica (as mesmas métricas resumidas em `imprimir_relatorio` de
`api_simulator.py`).

Reaproveita `executar_simulacao` e `calcular_metricas` de `api_simulator.py`
para não duplicar a lógica de simulação/cálculo entre os dois scripts.

Formato do CSV em padrão pt-BR: `;` como separador de campo e `,` como
separador decimal (para abrir direto no Excel/LibreOffice em pt-BR).
"""

import csv

from api_simulator import SEMENTE_ALEATORIA, calcular_metricas, executar_simulacao

N_REPLICACOES = 10
# Uma semente distinta por replicação, deliberadamente diferente de
# SEMENTE_ALEATORIA (reservada à execução de referência de api_simulator.py).
SEMENTES = [SEMENTE_ALEATORIA + 1 + i for i in range(N_REPLICACOES)]

ARQUIVO_SAIDA = "replicacoes.csv"


def formatar_valor(valor):
    if isinstance(valor, float):
        return f"{valor:.6f}".replace(".", ",")
    return valor


def principal():
    linhas = []
    for replicacao, semente in enumerate(SEMENTES, start=1):
        ambiente, estatisticas = executar_simulacao(semente)
        metricas = calcular_metricas(ambiente, estatisticas)
        linha = {"replicacao": replicacao, "semente": semente, **metricas}
        linhas.append({chave: formatar_valor(valor) for chave, valor in linha.items()})

    colunas = list(linhas[0].keys())
    with open(ARQUIVO_SAIDA, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"{len(linhas)} replicações gravadas em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    principal()
