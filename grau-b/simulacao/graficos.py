"""
Gera os gráficos de resultados da simulação, em PNG, na pasta `resultados/graficos/`.

1. chegadas_por_intervalo.png: mapas que chegam a cada 15 min (média das replicações).
2. fila_voos_grandes.png: tarefas na fila dos servidores de voos grandes ao longo
   da noite, em degraus, um painel por cenário (replicação de referência).
3. p90_lead_time_ic.png: P90 do lead time por cenário, com IC de 95% em barras de erro.
4. mapas_fora_prazo_ic.png: mapas fora do prazo por noite, com IC de 95%.
5. distribuicao_lead_time.png: proporção acumulada dos mapas por lead time.
6. ocupacao_servidores.png: ocupação média de cada grupo de servidores ao longo
   da noite, um painel por cenário.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

from executar_cenarios import PASTA_RESULTADOS, SEMENTES, resumir, rodar_cenarios
from modelo import (CENARIOS, ENVIO_MAX, HORA_INICIO, INTERVALO_MONITOR, META_LEAD_TIME, SEMENTE_REFERENCIA,
                    executar_simulacao, gerar_mapas)

PASTA_GRAFICOS = os.path.join(PASTA_RESULTADOS, "graficos")

# Paleta de referência (categórica, slots 1 e 2) e tons neutros
CORES = {"Atual": "#2a78d6", "Servidor extra": "#eb6834"}
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e4e3df"
NEUTRO = "#8a8984"

INTERVALO_CHEGADAS = 15  # minutos

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE,
    "axes.labelcolor": TEXTO_SECUNDARIO,
    "axes.titlecolor": TEXTO,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRADE,
    "grid.linewidth": 0.8,
    "xtick.color": TEXTO_SECUNDARIO,
    "ytick.color": TEXTO_SECUNDARIO,
    "legend.frameon": False,
    "font.size": 11,
})


def rotulos_hora(eixo, fim_min):
    """Marca o eixo x em horas do relógio (17h, 18h, ...)."""
    marcas = np.arange(0, fim_min + 1, 60)
    eixo.set_xticks(marcas)
    eixo.set_xticklabels([f"{HORA_INICIO + int(m // 60)}h" for m in marcas])


def br(texto):
    """Troca o ponto decimal pela vírgula, padrão pt-BR."""
    return texto.replace(".", ",")


def salvar(figura, nome):
    caminho = os.path.join(PASTA_GRAFICOS, nome)
    figura.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(figura)
    print(f"Gravado: {os.path.relpath(caminho)}")


def grafico_chegadas():
    bordas = np.arange(0, ENVIO_MAX + INTERVALO_CHEGADAS, INTERVALO_CHEGADAS)
    contagens = np.array([np.histogram([m.instante_entrada for m in gerar_mapas(s)], bins=bordas)[0]
                          for s in SEMENTES])
    media = contagens.mean(axis=0)

    figura, eixo = plt.subplots(figsize=(9, 4.2))
    eixo.bar(bordas[:-1], media, width=INTERVALO_CHEGADAS - 1.5, align="edge", color=NEUTRO)
    eixo.set_title("Chegada dos mapas ao longo da noite")
    eixo.set_xlabel("Horário do envio")
    eixo.set_ylabel(f"Mapas a cada {INTERVALO_CHEGADAS} min (média)")
    eixo.grid(axis="x", visible=False)
    rotulos_hora(eixo, ENVIO_MAX)
    pico = bordas[np.argmax(media)]
    eixo.annotate(br(f"pico: {media.max():.1f} mapas/{INTERVALO_CHEGADAS} min"),
                  xy=(pico + INTERVALO_CHEGADAS / 2, media.max()), xytext=(0, 6),
                  textcoords="offset points", ha="center", color=TEXTO_SECUNDARIO, fontsize=10)
    eixo.set_ylim(0, media.max() * 1.18)
    salvar(figura, "chegadas_por_intervalo.png")


def grafico_fila():
    execucoes = {c: executar_simulacao(c, SEMENTE_REFERENCIA) for c in CENARIOS}
    fim = max(amb.now for amb, _, _ in execucoes.values())
    fila_max = max(a["fila_grandes"] for _, est, _ in execucoes.values() for a in est.amostras)

    figura, eixos = plt.subplots(len(CENARIOS), 1, figsize=(9, 5.6), sharex=True, sharey=True)
    for eixo, (cenario, (ambiente, estatisticas, capacidades)) in zip(eixos, execucoes.items()):
        tempos = [a["tempo"] for a in estatisticas.amostras]
        fila = [a["fila_grandes"] for a in estatisticas.amostras]
        eixo.step(tempos, fila, where="post", color=CORES[cenario], linewidth=2)
        eixo.fill_between(tempos, fila, step="post", color=CORES[cenario], alpha=0.12, linewidth=0)
        eixo.text(0.995, 0.92,
                  f"{cenario}: {capacidades['servidores_grandes']} servidores de voos grandes · "
                  f"máximo de {max(fila)} tarefas",
                  transform=eixo.transAxes, ha="right", va="top", color=TEXTO, fontsize=10)
        eixo.set_ylabel("Tarefas na fila")
        eixo.set_ylim(0, fila_max * 1.25 + 1)
    eixos[0].set_title("Fila dos servidores de voos grandes ao longo da noite")
    eixos[-1].set_xlabel("Horário (uma noite simulada, mesma semente nos dois cenários)")
    rotulos_hora(eixos[-1], fim)
    salvar(figura, "fila_voos_grandes.png")


def grafico_ic(resumo, chave, titulo, rotulo_y, nome, meta=None, rotulo_meta=None, formato="{:.2f}"):
    cenarios = list(resumo)
    medias = [resumo[c][chave][0] for c in cenarios]
    meias = [resumo[c][chave][2] for c in cenarios]
    posicoes = np.arange(len(cenarios))

    figura, eixo = plt.subplots(figsize=(7, 4.8))
    eixo.bar(posicoes, medias, width=0.5, color=[CORES[c] for c in cenarios])
    eixo.errorbar(posicoes, medias, yerr=meias, fmt="none", ecolor=TEXTO, elinewidth=1.6, capsize=8, capthick=1.6)
    for x, m, h in zip(posicoes, medias, meias):
        eixo.annotate(br(f"{formato.format(m)}\nIC [{formato.format(m - h)}; {formato.format(m + h)}]"),
                      xy=(x, m + h), xytext=(0, 6), textcoords="offset points",
                      ha="center", va="bottom", color=TEXTO, fontsize=10)
    topo = max(m + h for m, h in zip(medias, meias))
    if meta is not None:
        eixo.axhline(meta, color=TEXTO_SECUNDARIO, linestyle="--", linewidth=1.4)
        eixo.text((posicoes[0] + posicoes[-1]) / 2, meta, rotulo_meta, ha="center", va="bottom",
                  color=TEXTO_SECUNDARIO, fontsize=10)
        topo = max(topo, meta)
    eixo.set_ylim(0, topo * 1.3)
    eixo.set_xticks(posicoes)
    eixo.set_xticklabels([f"{c}\n({CENARIOS[c]['servidores_pequenos']} + {CENARIOS[c]['servidores_grandes']} servidores)"
                          for c in cenarios])
    eixo.set_xlabel("Cenário (servidores de voos pequenos + voos grandes)")
    eixo.set_ylabel(rotulo_y)
    eixo.set_title(titulo)
    eixo.grid(axis="x", visible=False)
    salvar(figura, nome)


def grafico_distribuicao():
    figura, eixo = plt.subplots(figsize=(9, 4.8))
    resumo_meta = []
    for cenario in CENARIOS:
        leads = []
        for semente in SEMENTES:
            _, estatisticas, _ = executar_simulacao(cenario, semente)
            leads.extend(m.lead_time for m in estatisticas.mapas)
        leads = np.sort(leads)
        proporcao = np.arange(1, len(leads) + 1) / len(leads)
        eixo.step(leads, proporcao * 100, where="post", color=CORES[cenario], linewidth=2, label=cenario)
        dentro = np.mean(leads <= META_LEAD_TIME) * 100
        eixo.plot([META_LEAD_TIME], [dentro], "o", markersize=8, color=CORES[cenario],
                  markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=5)
        resumo_meta.append(br(f"{cenario}: {dentro:.1f}%"))
    eixo.axvline(META_LEAD_TIME, color=TEXTO_SECUNDARIO, linestyle="--", linewidth=1.4)
    eixo.text(META_LEAD_TIME + 0.4, 62, "Mapas dentro da meta:\n" + "\n".join(resumo_meta),
              color=TEXTO, fontsize=10, va="top")
    eixo.set_xticks(np.arange(0, 22, 2))
    eixo.axhline(90, color=GRADE, linewidth=1.2)
    eixo.text(0.3, 91, "90% dos mapas (P90)", color=TEXTO_SECUNDARIO, fontsize=10, va="bottom")
    eixo.text(META_LEAD_TIME, 2, f" meta: {META_LEAD_TIME:.0f} min", color=TEXTO_SECUNDARIO, fontsize=10)
    eixo.set_title(f"Lead time dos mapas ({len(SEMENTES)} noites por cenário)")
    eixo.set_xlabel("Lead time (min)")
    eixo.set_ylabel("Mapas prontos até esse tempo (%)")
    eixo.set_ylim(0, 101)
    eixo.set_xlim(0, None)
    eixo.legend(loc="lower right")
    salvar(figura, "distribuicao_lead_time.png")


def grafico_ocupacao():
    """Ocupação média de cada grupo de servidores ao longo da noite, um painel por cenário.

    Em cada instante amostrado pelo monitor, divide os servidores ocupados pela
    capacidade do grupo e suaviza cada noite com média móvel de 10 min. A linha
    é a média das replicações, e a faixa sombreada vai do percentil 10 ao 90
    entre as noites, ou seja, cobre 80% das noites. Depois do fim de uma noite,
    a ocupação daquela replicação conta como zero.
    """
    grupos = [("pequenos", "Voos pequenos", "#1baf7a"), ("grandes", "Voos grandes", "#6250d6")]
    janela = int(10 / INTERVALO_MONITOR)  # média móvel de 10 min

    series = {}
    for cenario, capacidades in CENARIOS.items():
        execucoes = [executar_simulacao(cenario, s)[1].amostras for s in SEMENTES]
        n = max(len(a) for a in execucoes)
        series[cenario] = {}
        for chave, _, _ in grupos:
            capacidade = capacidades[f"servidores_{chave}"]
            matriz = np.zeros((len(execucoes), n))
            for i, amostras in enumerate(execucoes):
                matriz[i, :len(amostras)] = [a[f"ocupados_{chave}"] / capacidade for a in amostras]
            suavizada = np.array([np.convolve(linha, np.ones(janela) / janela, mode="same")
                                  for linha in matriz]) * 100
            series[cenario][chave] = suavizada.mean(axis=0)
            series[cenario][f"{chave}_p10"] = np.percentile(suavizada, 10, axis=0)
            series[cenario][f"{chave}_p90"] = np.percentile(suavizada, 90, axis=0)
        series[cenario]["tempo"] = np.arange(n) * INTERVALO_MONITOR

    fim = max(s["tempo"][-1] for s in series.values())
    figura, eixos = plt.subplots(len(CENARIOS), 1, figsize=(9, 6), sharex=True, sharey=True)
    for eixo, (cenario, capacidades) in zip(eixos, CENARIOS.items()):
        dados = series[cenario]
        for chave, nome, cor in grupos:
            capacidade = capacidades[f"servidores_{chave}"]
            pico = dados[chave].max()
            eixo.fill_between(dados["tempo"], dados[f"{chave}_p10"], dados[f"{chave}_p90"],
                              color=cor, alpha=0.16, linewidth=0)
            eixo.plot(dados["tempo"], dados[chave], color=cor, linewidth=2, label=f"{nome} (média)")
            momento = dados["tempo"][np.argmax(dados[chave])]
            eixo.annotate(br(f"pico {pico:.0f}%"), xy=(momento, pico), xytext=(6, 4),
                          textcoords="offset points", color=TEXTO, fontsize=10)
        eixo.axhline(100, color=TEXTO_SECUNDARIO, linestyle="--", linewidth=1.2)
        eixo.text(fim, 101, "100%: todos os servidores ocupados", ha="right", va="bottom",
                  color=TEXTO_SECUNDARIO, fontsize=9)
        eixo.set_title(f"{cenario}: {capacidades['servidores_pequenos']} servidores de voos pequenos + "
                       f"{capacidades['servidores_grandes']} de voos grandes", fontsize=11)
        eixo.set_ylabel("Servidores ocupados (%)")
        eixo.set_ylim(0, 122)
    figura.suptitle(f"Ocupação dos servidores ao longo da noite (média de {len(SEMENTES)} noites)",
                    x=0.07, ha="left", fontsize=13, weight="bold", color=TEXTO)
    alcas, rotulos = eixos[0].get_legend_handles_labels()
    alcas.append(Patch(facecolor=NEUTRO, alpha=0.3, linewidth=0))
    rotulos.append("Faixa: 80% das noites (P10 a P90)")
    figura.legend(alcas, rotulos, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04))
    eixos[-1].set_xlabel("Horário (média móvel de 10 min)")
    rotulos_hora(eixos[-1], fim)
    salvar(figura, "ocupacao_servidores.png")


def principal():
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    resumo = resumir(rodar_cenarios())

    grafico_chegadas()
    grafico_fila()
    grafico_ic(resumo, "p90_lead_time_min", "P90 do lead time por cenário (IC de 95%)",
               "P90 do lead time (min)", "p90_lead_time_ic.png",
               meta=META_LEAD_TIME, rotulo_meta=f"meta: {META_LEAD_TIME:.0f} min")
    grafico_ic(resumo, "mapas_fora_prazo", "Mapas fora do prazo por noite (IC de 95%)",
               "Mapas com lead time acima da meta (mapas/noite)", "mapas_fora_prazo_ic.png",
               formato="{:.1f}")
    grafico_distribuicao()
    grafico_ocupacao()


if __name__ == "__main__":
    principal()
