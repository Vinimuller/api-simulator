"""
Executa N_REPLICACOES noites independentes em cada cenário e calcula o IC de
95% dos indicadores.

A replicação i usa a mesma semente em todos os cenários (números aleatórios
comuns): os mapas, as quantidades de imagens e os tempos sorteados são os
mesmos, e a diferença entre os cenários vem só do número de servidores.

Saídas, na pasta `resultados/`:
- `replicacoes.csv`: uma linha por cenário e replicação, padrão pt-BR
  (`;` como separador de campo e `,` como separador decimal).
- `resumo_cenarios.csv`: média, desvio-padrão e IC de 95% por cenário e indicador.
"""

import csv
import os

import numpy as np

from modelo import CENARIOS, META_LEAD_TIME, calcular_metricas, executar_simulacao

N_REPLICACOES = 30
SEMENTE_BASE = 1000
SEMENTES = [SEMENTE_BASE + i for i in range(N_REPLICACOES)]

PASTA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")

# Valor crítico t de Student bicaudal para 95%, por graus de liberdade (n - 1).
# Tabelado para não depender do scipy.
T_CRITICO_95 = {9: 2.262, 19: 2.093, 29: 2.045, 39: 2.023, 49: 2.010, 59: 2.001, 99: 1.984}

INDICADORES_RESUMO = [
    ("p90_lead_time_min", "P90 do lead time", "min"),
    ("mapas_fora_prazo", "Mapas fora do prazo", "mapas/noite"),
    ("percentual_fora_prazo", "Mapas fora do prazo", "%"),
    ("lead_time_medio_min", "Lead time médio", "min"),
    ("vazao_mapas_h", "Vazão", "mapas/h"),
    ("utilizacao_pequenos", "Utilização voos pequenos", "%"),
    ("utilizacao_grandes", "Utilização voos grandes", "%"),
]


def intervalo_confianca(valores):
    """Média, desvio-padrão amostral e meia-largura do IC de 95% (t de Student)."""
    valores = np.asarray(valores, dtype=float)
    n = len(valores)
    media = valores.mean()
    desvio = valores.std(ddof=1)
    t = T_CRITICO_95.get(n - 1, 1.96)
    return media, desvio, t * desvio / np.sqrt(n)


def rodar_cenarios():
    """Devolve {cenario: [metricas da replicação 1, ..., N]}."""
    resultados = {}
    for cenario in CENARIOS:
        resultados[cenario] = []
        for semente in SEMENTES:
            ambiente, estatisticas, capacidades = executar_simulacao(cenario, semente)
            resultados[cenario].append(calcular_metricas(ambiente, estatisticas, capacidades))
    return resultados


def resumir(resultados):
    """Devolve {cenario: {indicador: (media, desvio, meia_largura)}}."""
    return {
        cenario: {chave: intervalo_confianca([m[chave] for m in metricas]) for chave, _, _ in INDICADORES_RESUMO}
        for cenario, metricas in resultados.items()
    }


def formatar(valor):
    if isinstance(valor, (float, np.floating)):
        return f"{valor:.6f}".replace(".", ",")
    return valor


def gravar_csv(resultados, resumo):
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)

    caminho = os.path.join(PASTA_RESULTADOS, "replicacoes.csv")
    linhas = []
    for cenario, metricas in resultados.items():
        for replicacao, (semente, m) in enumerate(zip(SEMENTES, metricas), start=1):
            linha = {"cenario": cenario, "replicacao": replicacao, "semente": semente, **m}
            linhas.append({k: formatar(v) for k, v in linha.items()})
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0].keys()), delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)

    caminho_resumo = os.path.join(PASTA_RESULTADOS, "resumo_cenarios.csv")
    with open(caminho_resumo, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["cenario", "indicador", "unidade", "media", "desvio_padrao",
                           "ic95_inferior", "ic95_superior"])
        for cenario, indicadores in resumo.items():
            for chave, nome, unidade in INDICADORES_RESUMO:
                media, desvio, meia = indicadores[chave]
                escritor.writerow([cenario, nome, unidade, formatar(media), formatar(desvio),
                                   formatar(media - meia), formatar(media + meia)])

    return caminho, caminho_resumo


def imprimir_resumo(resumo):
    print(f"{N_REPLICACOES} replicações por cenário, IC de 95% (t de Student)")
    print()
    for chave, nome, unidade in INDICADORES_RESUMO:
        print(f"{nome} ({unidade})")
        for cenario, indicadores in resumo.items():
            media, _, meia = indicadores[chave]
            escala = 100 if unidade == "%" else 1
            print(f"  {cenario:<16} {media * escala:8.2f}  IC [{(media - meia) * escala:.2f}; "
                  f"{(media + meia) * escala:.2f}]")
        print()

    # Comparação no indicador principal
    (c1, i1), (c2, i2) = list(resumo.items())[:2]
    m1, _, h1 = i1["p90_lead_time_min"]
    m2, _, h2 = i2["p90_lead_time_min"]
    sobrepoe = (m1 - h1) <= (m2 + h2) and (m2 - h2) <= (m1 + h1)
    print("Indicador principal: P90 do lead time")
    print(f"  Diferença entre as médias: {m1 - m2:.2f} min ({c1} − {c2})")
    if sobrepoe:
        print("  Os intervalos se sobrepõem: não é possível concluir pela diferença.")
    else:
        print("  Os intervalos não se sobrepõem: a diferença é conclusiva.")
    for cenario, indicadores in resumo.items():
        media, _, meia = indicadores["p90_lead_time_min"]
        if media + meia <= META_LEAD_TIME:
            situacao = "atende à meta (IC inteiro abaixo)"
        elif media - meia > META_LEAD_TIME:
            situacao = "não atende à meta (IC inteiro acima)"
        else:
            situacao = "inconclusivo (o IC contém a meta)"
        print(f"  {cenario}: {situacao} de {META_LEAD_TIME:.0f} min")


def principal():
    resultados = rodar_cenarios()
    resumo = resumir(resultados)
    imprimir_resumo(resumo)
    caminhos = gravar_csv(resultados, resumo)
    print()
    for caminho in caminhos:
        print(f"Gravado: {os.path.relpath(caminho)}")


if __name__ == "__main__":
    principal()
