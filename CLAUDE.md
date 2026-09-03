# api-simulator

Discrete-event simulation of an image-processing API, built with [SimPy](https://simpy.readthedocs.io/) for a systems modeling class. Code, comments, and output are in pt-BR.

## Model

Single-server FIFO queue with an infinite buffer and a finite user pool:

- **Arrivals**: `N_USUARIOS` users, each sending exactly one request. Interarrival times are exponential (`TAXA_CHEGADA`, rate λ) — a Poisson arrival process.
- **Service**: one server, no parallelism (`simpy.Resource(capacity=1)`). Each request has an image size drawn `Uniform(TAMANHO_MIN, TAMANHO_MAX)` MB; processing time is linear in size: `TEMPO_BASE + tamanho_imagem * TEMPO_POR_UNIDADE`.
- **Queue discipline**: FIFO, unbounded.
- **Stop condition**: simulation ends naturally once all `N_USUARIOS` requests have arrived and finished (no explicit `until=`).

All tunable parameters live as named constants at the top of `api_simulator.py` (`N_USUARIOS`, `TAXA_CHEGADA`, `TAMANHO_MIN`/`TAMANHO_MAX`, `TEMPO_BASE`, `TEMPO_POR_UNIDADE`, `SEMENTE_ALEATORIA`).

## Files

- `api_simulator.py` — the simulation: config, `Estatisticas` collector, `processar_requisicao` / `gerador_usuarios` processes, `imprimir_relatorio` (summary stats incl. utilization, throughput, and a Little's Law check), `imprimir_tabela_amostra` (per-request table: arrival time, wait time, image size, processing time).
- `plot_distributions.py` — samples the same two distributions the simulation uses (interarrival time, processing time) and plots empirical histograms against their theoretical PDFs, saved to `distributions.png`. Imports its constants directly from `api_simulator.py` so it stays in sync with config changes.
- `requirements.txt` — `simpy` (plus `matplotlib`/`numpy` needed only for `plot_distributions.py`).

## Running

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install matplotlib numpy  # only needed for plot_distributions.py
.venv/bin/python api_simulator.py
.venv/bin/python plot_distributions.py
```

## Conventions

- Identifiers, comments, and all printed output are in pt-BR — keep new code consistent with this.
- No CLI args/argparse: parameters are edited directly as constants in `api_simulator.py` for quick tuning between simulation runs.
- Simulation results are deterministic (fixed `SEMENTE_ALEATORIA`), so reruns without config changes should reproduce identical output — useful for verifying edits didn't change behavior.
