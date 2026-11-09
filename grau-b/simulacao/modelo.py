"""
Modelo de simulação da plataforma de processamento de imagens de drone (SimPy).

Cada entidade é um mapa, gerado pelo envio dos arquivos de um voo. O mapa passa
pela validação em CPU (com reenvio dos arquivos faltantes, decisão por
probabilidade), segue a rota definida por `num_imagens` (decisão por condição)
para o grupo de servidores de voos pequenos ou de voos grandes, é alinhado e
se duplica em ortomosaico e modelo de elevação, que rodam em paralelo até a
junção. O lead time vai do fim do primeiro upload até a notificação.

O modelo conceitual completo, com a fonte de cada parâmetro, está em
`../docs/modelo_conceitual.md`.

Unidade de tempo da simulação: minutos. O instante 0 corresponde às 17h.
"""

from dataclasses import dataclass, field

import numpy as np
import simpy

# ---------------------------------------------------------------------------
# Parâmetros (seção 4.2 do modelo conceitual)
# ---------------------------------------------------------------------------

HORA_INICIO = 17                  # hora do relógio que corresponde ao instante 0

MAPAS_POR_NOITE_MEDIA = 100       # Poisson, mapas/noite (sem fonte)

ENVIO_MIN = 0.0                   # Triangular do horário de envio, em minutos após as 17h
ENVIO_MODA = 90.0                 # 18h30
ENVIO_MAX = 240.0                 # 21h

IMAGENS_MIN = 20                  # Triangular de num_imagens
IMAGENS_MODA = 80
IMAGENS_MAX = 200
LIMITE_ROTA = 80                  # acima disso, o mapa vai para os servidores de voos grandes

VALIDACAO_MIN_S = 5.0             # Uniform, segundos
VALIDACAO_MAX_S = 15.0
PROB_FALTA_ARQUIVOS = 0.05        # Bernoulli por tentativa de validação
CORRECAO_MIN = 1.0                # Uniform, minutos
CORRECAO_MAX = 3.0

# Tempos por imagem (s/imagem), benchmark Puget Systems / PIX4Dmatic, ±20%
ALINHAMENTO_S_IMG = (0.69, 1.03)
ELEVACAO_S_IMG = (1.22, 1.84)
ORTOMOSAICO_S_IMG = (0.15, 0.23)

CAPACIDADE_CPU = 1

META_LEAD_TIME = 10.0             # minutos

INTERVALO_MONITOR = 0.5           # minutos entre amostras do monitor

SEMENTE_REFERENCIA = 2026

# Cenários: número de servidores em cada grupo (seção 4.3)
CENARIOS = {
    "Atual": {"servidores_pequenos": 2, "servidores_grandes": 3},
    "Servidor extra": {"servidores_pequenos": 2, "servidores_grandes": 4},
}


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Mapa:
    id: int
    num_imagens: int
    rota: str
    instante_entrada: float
    rng: np.random.Generator
    tentativas: int = 0
    instante_saida: float = None

    @property
    def lead_time(self):
        return self.instante_saida - self.instante_entrada


@dataclass
class Estatisticas:
    mapas: list = field(default_factory=list)
    tempo_ocupado: dict = field(default_factory=lambda: {"pequenos": 0.0, "grandes": 0.0, "cpu": 0.0})
    concluidos: int = 0
    amostras: list = field(default_factory=list)  # uma por INTERVALO_MONITOR, ver `monitor`


# ---------------------------------------------------------------------------
# Processos
# ---------------------------------------------------------------------------

def tempo_etapa(mapa, faixa_s_img):
    """Tempo de uma etapa de processamento, em minutos."""
    return mapa.num_imagens * mapa.rng.uniform(*faixa_s_img) / 60.0


def tarefa_servidor(ambiente, servidores, mapa, faixa_s_img, estatisticas):
    """Ocupa um servidor do grupo do mapa pela duração de uma etapa."""
    grupo = servidores[mapa.rota]
    duracao = tempo_etapa(mapa, faixa_s_img)
    with grupo.request() as pedido:
        yield pedido
        yield ambiente.timeout(duracao)
    estatisticas.tempo_ocupado[mapa.rota] += duracao


def processar_mapa(ambiente, cpu, servidores, mapa, estatisticas):
    # Validação em CPU, repetida até não faltar arquivo (decisão por probabilidade)
    while True:
        duracao = mapa.rng.uniform(VALIDACAO_MIN_S, VALIDACAO_MAX_S) / 60.0
        with cpu.request() as pedido:
            yield pedido
            yield ambiente.timeout(duracao)
        estatisticas.tempo_ocupado["cpu"] += duracao
        mapa.tentativas += 1

        if mapa.rng.random() >= PROB_FALTA_ARQUIVOS:
            break
        # O prestador corrige e envia os faltantes: atraso sem fila
        yield ambiente.timeout(mapa.rng.uniform(CORRECAO_MIN, CORRECAO_MAX))

    # Alinhamento, no grupo de servidores definido pela rota
    yield ambiente.process(tarefa_servidor(ambiente, servidores, mapa, ALINHAMENTO_S_IMG, estatisticas))

    # Duplicação: ortomosaico e modelo de elevação em paralelo, com junção
    ortomosaico = ambiente.process(tarefa_servidor(ambiente, servidores, mapa, ORTOMOSAICO_S_IMG, estatisticas))
    elevacao = ambiente.process(tarefa_servidor(ambiente, servidores, mapa, ELEVACAO_S_IMG, estatisticas))
    yield ortomosaico & elevacao

    mapa.instante_saida = ambiente.now
    estatisticas.concluidos += 1


def gerar_mapas(semente):
    """Sorteia os mapas da noite: quantidade, horário de envio e num_imagens.

    Cada mapa recebe um gerador aleatório próprio, derivado da semente e do id.
    Assim, a mesma replicação produz os mesmos mapas e os mesmos tempos em
    todos os cenários (números aleatórios comuns), e a diferença entre os
    cenários vem só da capacidade.
    """
    rng = np.random.default_rng(semente)
    quantidade = rng.poisson(MAPAS_POR_NOITE_MEDIA)
    envios = np.sort(rng.triangular(ENVIO_MIN, ENVIO_MODA, ENVIO_MAX, size=quantidade))
    imagens = np.rint(rng.triangular(IMAGENS_MIN, IMAGENS_MODA, IMAGENS_MAX, size=quantidade)).astype(int)

    mapas = []
    for i, (envio, n) in enumerate(zip(envios, imagens)):
        rota = "grandes" if n > LIMITE_ROTA else "pequenos"
        mapas.append(Mapa(id=i, num_imagens=int(n), rota=rota, instante_entrada=float(envio),
                          rng=np.random.default_rng([semente, i])))
    return mapas


def chegadas(ambiente, cpu, servidores, mapas, estatisticas):
    for mapa in mapas:
        yield ambiente.timeout(mapa.instante_entrada - ambiente.now)
        estatisticas.mapas.append(mapa)
        ambiente.process(processar_mapa(ambiente, cpu, servidores, mapa, estatisticas))


def monitor(ambiente, cpu, servidores, total_mapas, estatisticas):
    """Amostra o estado do sistema em intervalos regulares, até o último mapa sair."""
    while estatisticas.concluidos < total_mapas:
        estatisticas.amostras.append({
            "tempo": ambiente.now,
            "fila_cpu": len(cpu.queue),
            "fila_pequenos": len(servidores["pequenos"].queue),
            "fila_grandes": len(servidores["grandes"].queue),
            "ocupados_pequenos": servidores["pequenos"].count,
            "ocupados_grandes": servidores["grandes"].count,
            "concluidos": estatisticas.concluidos,
        })
        yield ambiente.timeout(INTERVALO_MONITOR)


# ---------------------------------------------------------------------------
# Execução e métricas
# ---------------------------------------------------------------------------

def executar_simulacao(cenario, semente):
    """Simula uma noite de pico no cenário indicado. Devolve ambiente, estatísticas e capacidades."""
    capacidades = CENARIOS[cenario]
    ambiente = simpy.Environment()
    cpu = simpy.Resource(ambiente, capacity=CAPACIDADE_CPU)
    servidores = {
        "pequenos": simpy.Resource(ambiente, capacity=capacidades["servidores_pequenos"]),
        "grandes": simpy.Resource(ambiente, capacity=capacidades["servidores_grandes"]),
    }
    estatisticas = Estatisticas()
    mapas = gerar_mapas(semente)

    ambiente.process(chegadas(ambiente, cpu, servidores, mapas, estatisticas))
    ambiente.process(monitor(ambiente, cpu, servidores, len(mapas), estatisticas))
    ambiente.run()

    return ambiente, estatisticas, capacidades


def calcular_metricas(ambiente, estatisticas, capacidades):
    mapas = estatisticas.mapas
    lead_times = np.array([m.lead_time for m in mapas])
    fim = ambiente.now
    horizonte_h = fim / 60.0
    fora_prazo = int(np.sum(lead_times > META_LEAD_TIME))
    filas_grandes = [a["fila_grandes"] for a in estatisticas.amostras]

    return {
        "mapas": len(mapas),
        "mapas_grandes": sum(m.rota == "grandes" for m in mapas),
        "mapas_com_reenvio": sum(m.tentativas > 1 for m in mapas),
        "p90_lead_time_min": float(np.percentile(lead_times, 90)),
        "lead_time_medio_min": float(lead_times.mean()),
        "lead_time_maximo_min": float(lead_times.max()),
        "mapas_fora_prazo": fora_prazo,
        "percentual_fora_prazo": fora_prazo / len(mapas),
        "vazao_mapas_h": len(mapas) / horizonte_h,
        "utilizacao_pequenos": estatisticas.tempo_ocupado["pequenos"] / (capacidades["servidores_pequenos"] * fim),
        "utilizacao_grandes": estatisticas.tempo_ocupado["grandes"] / (capacidades["servidores_grandes"] * fim),
        "utilizacao_cpu": estatisticas.tempo_ocupado["cpu"] / (CAPACIDADE_CPU * fim),
        "fila_maxima_grandes": max(filas_grandes, default=0),
        "fim_min": fim,
    }


def formatar_hora(minutos):
    total = int(round(HORA_INICIO * 60 + minutos))
    return f"{total // 60:02d}h{total % 60:02d}"


def imprimir_relatorio(cenario, m):
    print("=" * 56)
    print(f"Cenário: {cenario}")
    print("=" * 56)
    print(f"Mapas na noite:             {m['mapas']} ({m['mapas_grandes']} grandes, "
          f"{m['mapas_com_reenvio']} com reenvio)")
    print(f"Último mapa pronto:         {formatar_hora(m['fim_min'])}")
    print(f"P90 do lead time:           {m['p90_lead_time_min']:.2f} min (meta: até {META_LEAD_TIME:.0f} min)")
    print(f"Lead time médio:            {m['lead_time_medio_min']:.2f} min")
    print(f"Lead time máximo:           {m['lead_time_maximo_min']:.2f} min")
    print(f"Mapas fora do prazo:        {m['mapas_fora_prazo']} mapas ({m['percentual_fora_prazo']:.1%})")
    print(f"Vazão:                      {m['vazao_mapas_h']:.1f} mapas/h")
    print(f"Utilização voos pequenos:   {m['utilizacao_pequenos']:.1%}")
    print(f"Utilização voos grandes:    {m['utilizacao_grandes']:.1%}")
    print(f"Utilização da CPU:          {m['utilizacao_cpu']:.1%}")
    print(f"Fila máxima voos grandes:   {m['fila_maxima_grandes']} tarefas")


def principal():
    for cenario in CENARIOS:
        ambiente, estatisticas, capacidades = executar_simulacao(cenario, SEMENTE_REFERENCIA)
        imprimir_relatorio(cenario, calcular_metricas(ambiente, estatisticas, capacidades))
        print()


if __name__ == "__main__":
    principal()
