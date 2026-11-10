"""
Gera a animação em vídeo MP4 da execução do modelo (requisito 3f e seção 4 do enunciado).

Apresenta o Cenário Atual (2 servidores de voos pequenos + 3 de voos grandes) ao longo
da noite de pico na semente de referência, exibindo:
- Título do cenário e relógio da simulação (17h00 até o último mapa pronto);
- Quatro indicadores vivos em texto, cada um com sua unidade;
- Esquema visual do fluxo completo (Chegadas -> Validação CPU com laço de reenvio ->
  Decisão condicional por num_imagens -> Filas e Servidores de voos pequenos e grandes ->
  Alinhamento + Ortomosaico // Elevação em paralelo -> Saída);
- Gráfico dinâmico em degraus da fila dos servidores de voos grandes com eixos rotulados.

Saída: `resultados/animacao_modelo.mp4`
"""

import os
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.patches import Circle, FancyBboxPatch, Polygon
import numpy as np

from executar_cenarios import PASTA_RESULTADOS
from modelo import (
    CENARIOS,
    HORA_INICIO,
    LIMITE_ROTA,
    META_LEAD_TIME,
    SEMENTE_REFERENCIA,
    executar_simulacao,
    formatar_hora,
)

# Paleta alinhada ao restante do projeto (graficos.py)
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE = "#1baf7a"
ROXO = "#6250d6"
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
GRADE = "#e4e3df"
NEUTRO = "#8a8984"
FUNDO_CAIXA = "#f3f2ee"
FUNDO_FILA_PEQ = "#eef8f4"
FUNDO_FILA_GRD = "#eef4fc"

ARQUIVO_PADRAO = os.path.join(PASTA_RESULTADOS, "animacao_modelo.mp4")


def _buscar_ffmpeg():
    """Localiza o executável do ffmpeg no PATH ou em pacotes Python (imageio_ffmpeg)."""
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def preparar_quadros(cenario="Atual", semente=SEMENTE_REFERENCIA, passo=1):
    """Executa a simulação e enriquece as amostras do monitor para cada quadro da animação."""
    ambiente, estatisticas, capacidades = executar_simulacao(cenario, semente)
    amostras = estatisticas.amostras
    mapas = estatisticas.mapas

    # Garante uma amostra final exatamente no término do último mapa
    if not amostras or amostras[-1]["tempo"] < ambiente.now:
        amostras.append(
            {
                "tempo": ambiente.now,
                "fila_cpu": 0,
                "fila_pequenos": 0,
                "fila_grandes": 0,
                "ocupados_pequenos": 0,
                "ocupados_grandes": 0,
                "concluidos": len(mapas),
            }
        )

    quadros = []
    for idx in range(0, len(amostras), passo):
        a = dict(amostras[idx])
        t = a["tempo"]
        enviados = sum(1 for m in mapas if m.instante_entrada <= t)
        concluidos_ate_t = [m for m in mapas if m.instante_saida is not None and m.instante_saida <= t]
        fora_prazo_ate_t = sum(1 for m in concluidos_ate_t if m.lead_time > META_LEAD_TIME)
        reenvios_ate_t = sum(1 for m in mapas if m.instante_entrada <= t and m.tentativas > 1)
        em_cpu = 1 if any(
            m.instante_entrada <= t and (m.instante_saida is None or m.instante_saida > t)
            and abs(t - m.instante_entrada) < 0.35
            for m in mapas
        ) else 0

        a["indice_amostra"] = idx
        a["enviados"] = enviados
        a["fora_prazo"] = fora_prazo_ate_t
        a["reenvios"] = reenvios_ate_t
        a["ocupado_cpu"] = max(em_cpu, 1 if a["fila_cpu"] > 0 else 0)
        a["pct_ocup_grandes"] = 100.0 * a["ocupados_grandes"] / capacidades["servidores_grandes"]
        a["pct_ocup_pequenos"] = 100.0 * a["ocupados_pequenos"] / capacidades["servidores_pequenos"]
        quadros.append(a)

    return ambiente, estatisticas, capacidades, amostras, quadros


def gerar_animacao(
    cenario="Atual",
    semente=SEMENTE_REFERENCIA,
    passo=1,
    fps=15,
    caminho_saida=ARQUIVO_PADRAO,
):
    """Constrói a animação FuncAnimation e grava em MP4."""
    ffmpeg_bin = _buscar_ffmpeg()
    if ffmpeg_bin:
        matplotlib.rcParams["animation.ffmpeg_path"] = ffmpeg_bin

    ambiente, estatisticas, capacidades, amostras, quadros = preparar_quadros(
        cenario=cenario, semente=semente, passo=passo
    )
    cap_peq = capacidades["servidores_pequenos"]
    cap_grd = capacidades["servidores_grandes"]
    total_mapas = len(estatisticas.mapas)

    figura = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=SUPERFICIE)

    # 1. Cabeçalho: título do cenário e relógio da simulação
    figura.text(
        0.035,
        0.955,
        f"Cenário {cenario} · {cap_peq} servidores de voos pequenos + {cap_grd} de voos grandes",
        fontsize=13.5,
        fontweight="bold",
        color=TEXTO,
        va="center",
    )
    figura.text(
        0.035,
        0.922,
        f"Plataforma de Processamento de Imagens de Drones · Noite de pico (meta de SLA: até {META_LEAD_TIME:.0f} min)",
        fontsize=10.0,
        color=TEXTO_SECUNDARIO,
        va="center",
    )
    txt_relogio = figura.text(
        0.965,
        0.942,
        "",
        fontsize=13.0,
        fontweight="bold",
        family="monospace",
        color=TEXTO,
        ha="right",
        va="center",
        bbox=dict(boxstyle="round,pad=0.32,rounding_size=0.15", fc="#efeee9", ec=GRADE, lw=1.2),
    )

    # 2. Faixa com 4 indicadores em texto (todos com unidade explícita)
    cartoes_ind = [
        (0.035, 0.825, 0.22, 0.068, "Fila (voos grandes)", AZUL),
        (0.273, 0.825, 0.22, 0.068, "Ocupação (voos grandes)", ROXO),
        (0.511, 0.825, 0.22, 0.068, "Mapas concluídos", VERDE),
        (0.749, 0.825, 0.216, 0.068, f"Fora do prazo (> {META_LEAD_TIME:.0f} min)", LARANJA),
    ]
    textos_indicadores = []
    for x, y, w, h, rotulo, cor in cartoes_ind:
        ax_card = figura.add_axes([x, y, w, h])
        ax_card.set_xlim(0, 1)
        ax_card.set_ylim(0, 1)
        ax_card.axis("off")
        ax_card.add_patch(
            FancyBboxPatch(
                (0.01, 0.04),
                0.98,
                0.92,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                fc="white",
                ec=GRADE,
                lw=1.3,
            )
        )
        ax_card.plot([0.01, 0.01], [0.12, 0.88], color=cor, lw=4, solid_capstyle="round")
        ax_card.text(0.06, 0.72, rotulo, fontsize=9.5, color=TEXTO_SECUNDARIO, va="center")
        t_val = ax_card.text(0.06, 0.28, "", fontsize=13.5, fontweight="bold", color= cor, va="center")
        textos_indicadores.append(t_val)

    txt_fila_grd, txt_ocup_grd, txt_concluidos, txt_fora_prazo = textos_indicadores

    # 3. Cena esquemática do modelo (meio da figura)
    cena = figura.add_axes([0.035, 0.39, 0.93, 0.415])
    cena.set_xlim(0, 18.0)
    cena.set_ylim(0, 6.4)
    cena.axis("off")

    def desenhar_caixa(x, y, w, h, titulo, subtitulo="", cor_borda=GRADE, cor_fundo="white", tamanho=10):
        patch = cena.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.04,rounding_size=0.14",
                fc=cor_fundo,
                ec=cor_borda,
                lw=1.6,
            )
        )
        if subtitulo:
            cena.text(x + w / 2, y + h * 0.64, titulo, ha="center", va="center", fontsize=tamanho, fontweight="bold", color=TEXTO)
            cena.text(x + w / 2, y + h * 0.30, subtitulo, ha="center", va="center", fontsize=8.5, color=TEXTO_SECUNDARIO)
        else:
            cena.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=tamanho, fontweight="bold", color=TEXTO)
        return patch

    def seta(x1, y1, x2, y2, cor=NEUTRO, estilo="->", tracejado=False):
        cena.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle=estilo,
                lw=1.6,
                color=cor,
                 linestyle="--" if tracejado else "-",
                shrinkA=0,
                shrinkB=0,
            ),
        )

    # Bloco Chegadas
    desenhar_caixa(0.1, 2.35, 1.9, 1.5, "Fim do Upload", "Entra o mapa", cor_borda=TEXTO_SECUNDARIO, cor_fundo=FUNDO_CAIXA)
    txt_enviados = cena.text(1.05, 2.0, "Enviados: 0 mapas", ha="center", va="top", fontsize=8.8, color=TEXTO_SECUNDARIO, fontweight="bold")
    seta(2.05, 3.1, 2.45, 3.1)

    # Bloco Validação CPU + Reenvio
    box_cpu = desenhar_caixa(2.5, 2.35, 2.1, 1.5, "Validação · CPU (1)", "5 a 15 s | 5% falha", cor_borda=TEXTO_SECUNDARIO, cor_fundo="white")
    txt_reenvios = cena.text(3.55, 2.0, "Com reenvio: 0 mapas", ha="center", va="top", fontsize=8.6, color=TEXTO_SECUNDARIO)

    # Laço de correção pelo prestador (decisão por probabilidade)
    desenhar_caixa(2.45, 4.55, 2.2, 0.95, "Correção (Prestador)", "Faltou arquivo (1 a 3 min)", cor_borda=LARANJA, cor_fundo="#fdf3ee", tamanho=8.6)
    seta(4.0, 3.9, 4.0, 4.5, cor=LARANJA, tracejado=True)
    seta(3.1, 4.5, 3.1, 3.9, cor=LARANJA, tracejado=True)

    # Losango de decisão condicional (num_imagens > 80)
    seta(4.65, 3.1, 5.05, 3.1)
    losango_x, losango_y = 5.85, 3.1
    losango = Polygon(
        [[losango_x - 0.78, losango_y], [losango_x, losango_y + 0.78], [losango_x + 0.78, losango_y], [losango_x, losango_y - 0.78]],
        closed=True,
        fc="#fff9eb",
        ec="#d99b26",
        lw=1.6,
    )
    cena.add_patch(losango)
    cena.text(losango_x, losango_y + 0.14, "num_imagens", ha="center", va="center", fontsize=8.0, fontweight="bold", color=TEXTO)
    cena.text(losango_x, losango_y - 0.16, f"> {LIMITE_ROTA}?", ha="center", va="center", fontsize=8.3, fontweight="bold", color=TEXTO)

    # Setas da decisão condicional para os dois grupos
    cena.plot([losango_x, losango_x], [losango_y + 0.78, 4.85], color=VERDE, lw=1.6)
    seta(losango_x, 4.85, 7.55, 4.85, cor=VERDE)
    cena.text((losango_x + 7.55) / 2, 5.02, "não (≤ 80 img)", ha="center", fontsize=8.2, color=VERDE, fontweight="bold")

    cena.plot([losango_x, losango_x], [losango_y - 0.78, 1.55], color=AZUL, lw=1.6)
    seta(losango_x, 1.55, 7.55, 1.55, cor=AZUL)
    cena.text((losango_x + 7.55) / 2, 1.72, "sim (> 80 img)", ha="center", fontsize=8.2, color=AZUL, fontweight="bold")

    # --- Ramo Superior: Servidores de Voos Pequenos (2) ---
    cena.add_patch(
        FancyBboxPatch(
            (7.6, 3.75),
            7.55,
            2.35,
            boxstyle="round,pad=0.04,rounding_size=0.16",
            fc=FUNDO_FILA_PEQ,
            ec=VERDE,
            lw=1.4,
            ls="--",
        )
    )
    cena.text(11.375, 5.86, f"Voos Pequenos ({cap_peq} serv.) · Alinhamento → Ortomosaico // Elevação → Junção",
              ha="center", va="center", fontsize=8.3, fontweight="bold", color=VERDE)

    # Fila voos pequenos
    cena.add_patch(FancyBboxPatch((7.85, 4.2), 3.3, 1.15, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=VERDE, lw=1.2))
    cena.text(9.5, 4.02, "Fila única FIFO (pequenos)", ha="center", va="top", fontsize=8.3, color=TEXTO_SECUNDARIO)
    max_bolas_peq = 6
    bolas_peq = [
        cena.add_patch(Circle((10.85 - i * 0.46, 4.78), 0.17, fc=VERDE, ec="white", lw=1.0, visible=False))
        for i in range(max_bolas_peq)
    ]
    txt_excesso_peq = cena.text(8.0, 4.78, "", ha="left", va="center", fontsize=8.5, fontweight="bold", color=VERDE)
    seta(11.2, 4.78, 11.75, 4.78, cor=VERDE)

    # Caixas dos 2 servidores pequenos
    caixas_serv_peq = []
    textos_serv_peq = []
    for k in range(cap_peq):
        y_s = 4.95 - k * 0.82
        p = FancyBboxPatch((11.8, y_s), 3.05, 0.66, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=VERDE, lw=1.4)
        cena.add_patch(p)
        t_s = cena.text(13.325, y_s + 0.33, f"Servidor P{k + 1}: livre", ha="center", va="center", fontsize=8.8, fontweight="bold", color=TEXTO_SECUNDARIO)
        caixas_serv_peq.append(p)
        textos_serv_peq.append(t_s)

    # --- Ramo Inferior: Servidores de Voos Grandes (3) ---
    cena.add_patch(
        FancyBboxPatch(
            (7.6, 0.25),
            7.55,
            2.95,
            boxstyle="round,pad=0.04,rounding_size=0.16",
            fc=FUNDO_FILA_GRD,
            ec=AZUL,
            lw=1.6,
            ls="--",
        )
    )
    cena.text(11.375, 2.96, f"Voos Grandes ({cap_grd} serv. · Gargalo) · Alinhamento → Ortomosaico // Elevação → Junção",
              ha="center", va="center", fontsize=8.3, fontweight="bold", color=AZUL)

    # Fila voos grandes
    cena.add_patch(FancyBboxPatch((7.85, 0.95), 3.3, 1.35, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=AZUL, lw=1.3))
    cena.text(9.5, 0.76, "Fila única FIFO (grandes)", ha="center", va="top", fontsize=8.3, color=TEXTO_SECUNDARIO)
    max_bolas_grd = 8
    pos_bolas_grd = [
        (10.85 - (i % 4) * 0.58, 1.88 if i < 4 else 1.35)
        for i in range(max_bolas_grd)
    ]
    bolas_grd = [
        cena.add_patch(Circle(pos, 0.18, fc=AZUL, ec="white", lw=1.0, visible=False))
        for pos in pos_bolas_grd
    ]
    txt_excesso_grd = cena.text(8.0, 1.62, "", ha="left", va="center", fontsize=9, fontweight="bold", color=LARANJA)
    seta(11.2, 1.62, 11.75, 1.62, cor=AZUL)

    # Caixas dos servidores grandes (3 no cenário Atual, 4 no Servidor extra)
    caixas_serv_grd = []
    textos_serv_grd = []
    altura_disp = 2.25
    passo_y = altura_disp / cap_grd
    altura_caixa = min(0.58, passo_y - 0.12)
    y_topo_grd = 2.15
    for k in range(cap_grd):
        y_s = y_topo_grd - k * passo_y
        p = FancyBboxPatch((11.8, y_s), 3.05, altura_caixa, boxstyle="round,pad=0.02,rounding_size=0.1", fc="white", ec=AZUL, lw=1.4)
        cena.add_patch(p)
        t_s = cena.text(
            13.325,
            y_s + altura_caixa / 2,
            f"Servidor G{k + 1}: livre",
            ha="center",
            va="center",
            fontsize=8.6,
            fontweight="bold",
            color=TEXTO_SECUNDARIO,
        )
        caixas_serv_grd.append(p)
        textos_serv_grd.append(t_s)

    # Bloco Saída (Notificação de Mapa Pronto)
    cena.plot([15.15, 15.65], [4.85, 3.45], color=VERDE, lw=1.6)
    cena.plot([15.15, 15.65], [1.55, 2.75], color=AZUL, lw=1.6)
    seta(15.65, 3.1, 15.95, 3.1, cor=TEXTO_SECUNDARIO)
    desenhar_caixa(16.0, 2.25, 1.8, 1.7, "Mapa Pronto", "Notificação", cor_borda=VERDE, cor_fundo="#eef8f4")

    # 4. Gráfico inferior: evolução temporal da fila de voos grandes em degraus
    graf = figura.add_axes([0.075, 0.085, 0.89, 0.255])
    graf.set_facecolor("white")
    tempos_todos = [a["tempo"] for a in amostras]
    filas_todas = [a["fila_grandes"] for a in amostras]
    fim_min = max(245.0, max(tempos_todos))
    fila_max = max(8, max(filas_todas))

    graf.set_xlim(0, fim_min)
    graf.set_ylim(0, fila_max + 2)
    marcas_x = np.arange(0, fim_min + 1, 30)
    graf.set_xticks(marcas_x)
    graf.set_xticklabels([formatar_hora(m) for m in marcas_x], fontsize=9.5, color=TEXTO_SECUNDARIO)
    graf.set_yticks(np.arange(0, fila_max + 3, 2))
    graf.tick_params(axis="y", labelsize=9.5, colors=TEXTO_SECUNDARIO)
    graf.spines["top"].set_visible(False)
    graf.spines["right"].set_visible(False)
    graf.spines["left"].set_color(GRADE)
    graf.spines["bottom"].set_color(GRADE)
    graf.grid(True, color=GRADE, lw=0.8)

    graf.set_title(
        "Evolução temporal da fila dos servidores de voos grandes (em degraus)",
        loc="left",
        fontsize=11.5,
        fontweight="bold",
        color=TEXTO,
        pad=6,
    )
    graf.set_xlabel("Horário da noite (tempo simulado, em horas)", fontsize=10, color=TEXTO_SECUNDARIO)
    graf.set_ylabel("Tarefas na fila (tarefas)", fontsize=10, color=TEXTO_SECUNDARIO)

    (linha_step,) = graf.step([], [], where="post", color=AZUL, lw=2.0)
    (ponto_atual,) = graf.plot([], [], "o", color=LARANJA, markersize=6.5, zorder=5)

    def atualizar_quadro(i):
        q = quadros[i]
        t = q["tempo"]
        n_amostra = q["indice_amostra"] + 1

        # Atualiza relógio
        txt_relogio.set_text(f"Horário: {formatar_hora(t)}  (t = {t:5.1f} min)".replace(".", ","))

        # Atualiza os 4 indicadores em texto (todos com unidade)
        txt_fila_grd.set_text(f"{q['fila_grandes']} tarefas")
        txt_ocup_grd.set_text(f"{q['pct_ocup_grandes']:.0f}% ({q['ocupados_grandes']}/{cap_grd} serv.)")
        txt_concluidos.set_text(f"{q['concluidos']} / {total_mapas} mapas")
        txt_fora_prazo.set_text(f"{q['fora_prazo']} mapas")

        # Atualiza contadores de entrada e validação
        txt_enviados.set_text(f"Enviados: {q['enviados']} mapas")
        txt_reenvios.set_text(f"Com reenvio: {q['reenvios']} mapas")
        box_cpu.set_facecolor("#fff3e6" if q["ocupado_cpu"] else "white")

        # Atualiza fila e servidores de voos pequenos
        for j, bola in enumerate(bolas_peq):
            bola.set_visible(j < q["fila_pequenos"])
        txt_excesso_peq.set_text(
            f"+{q['fila_pequenos'] - max_bolas_peq}" if q["fila_pequenos"] > max_bolas_peq else ""
        )
        for k, (caixa_s, txt_s) in enumerate(zip(caixas_serv_peq, textos_serv_peq)):
            ocupado = k < q["ocupados_pequenos"]
            caixa_s.set_facecolor(VERDE if ocupado else "white")
            txt_s.set_text(f"Servidor P{k + 1}: ocupado" if ocupado else f"Servidor P{k + 1}: livre")
            txt_s.set_color("white" if ocupado else TEXTO_SECUNDARIO)

        # Atualiza fila e servidores de voos grandes
        lotado = q["ocupados_grandes"] == cap_grd and q["fila_grandes"] > 0
        cor_serv_grd = LARANJA if lotado else AZUL
        for j, bola in enumerate(bolas_grd):
            bola.set_visible(j < q["fila_grandes"])
            bola.set_facecolor(LARANJA if q["fila_grandes"] >= 4 else AZUL)
        txt_excesso_grd.set_text(
            f"+{q['fila_grandes'] - max_bolas_grd}" if q["fila_grandes"] > max_bolas_grd else ""
        )
        for k, (caixa_s, txt_s) in enumerate(zip(caixas_serv_grd, textos_serv_grd)):
            ocupado = k < q["ocupados_grandes"]
            caixa_s.set_facecolor(cor_serv_grd if ocupado else "white")
            caixa_s.set_edgecolor(cor_serv_grd if ocupado else AZUL)
            txt_s.set_text(f"Servidor G{k + 1}: ocupado" if ocupado else f"Servidor G{k + 1}: livre")
            txt_s.set_color("white" if ocupado else TEXTO_SECUNDARIO)

        # Atualiza gráfico dinâmico em degraus
        ts = tempos_todos[:n_amostra]
        fs = filas_todas[:n_amostra]
        linha_step.set_data(ts, fs)
        ponto_atual.set_data([t], [q["fila_grandes"]])
        return []

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    anim = animation.FuncAnimation(figura, atualizar_quadro, frames=len(quadros), interval=1000 / fps)

    if animation.writers.is_available("ffmpeg"):
        caminho_tmp = caminho_saida + ".raw.mp4"
        escritor = animation.FFMpegWriter(
            fps=fps,
            codec="libx264",
            bitrate=2000,
            extra_args=["-pix_fmt", "yuv420p"],
        )
        anim.save(caminho_tmp, writer=escritor)
        plt.close(figura)

        # Converte para perfil H.264 universal com trilha de áudio silenciosa (compatibilidade total com Windows Media Player e PowerPoint)
        import base64
        import subprocess

        subprocess.run(
            [
                ffmpeg_bin or "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-i",
                caminho_tmp,
                "-c:v",
                "libx264",
                "-profile:v",
                "main",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                "-shortest",
                "-movflags",
                "+faststart",
                caminho_saida,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if os.path.exists(caminho_tmp):
            os.remove(caminho_tmp)

        # Gera também um visualizador HTML autocontido para abrir em qualquer navegador
        caminho_html = os.path.splitext(caminho_saida)[0] + ".html"
        video_b64 = base64.b64encode(open(caminho_saida, "rb").read()).decode()
        with open(caminho_html, "w", encoding="utf-8") as arq_html:
            arq_html.write(
                '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
                "<title>Animação do Modelo — TGB</title></head>"
                '<body style="background:#fcfcfb;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;padding:24px;">'
                '<h2 style="margin:0 0 12px 0;color:#0b0b0b;">Demonstração Visual — Processamento de Imagens de Drones</h2>'
                '<video width="1152" controls autoplay loop muted style="border:1px solid #e4e3df;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.08);">'
                f'<source src="data:video/mp4;base64,{video_b64}" type="video/mp4">'
                "</video></body></html>"
            )

        duracao_s = len(quadros) / fps
        print(f"Gravado: {os.path.relpath(caminho_saida)} ({len(quadros)} quadros, {duracao_s:.1f} s a {fps} fps)")
        print(f"Gravado: {os.path.relpath(caminho_html)} (visualizador para navegador)")
    else:
        plt.close(figura)
        raise RuntimeError(
            "O utilitário 'ffmpeg' não foi encontrado. Instale 'imageio-ffmpeg' (pip install imageio-ffmpeg) "
            "ou execute no Google Colab para gravar o arquivo MP4."
        )

    return caminho_saida


def principal():
    gerar_animacao()


if __name__ == "__main__":
    principal()
