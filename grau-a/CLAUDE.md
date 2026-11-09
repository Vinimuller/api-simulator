# api-simulator

Discrete-event simulation of an image-processing API, built with [SimPy](https://simpy.readthedocs.io/) for a systems modeling class. Code, comments, and output are in pt-BR.

## Model

Two servers in sequence, each with its own FIFO infinite-buffer queue, plus a conditional routing decision, and a finite user pool:

- **Arrivals**: `N_USUARIOS` users, each sending exactly one request. Interarrival times are exponential (`TAXA_CHEGADA`, rate λ) — a Poisson arrival process. Each request's image size is drawn once at arrival, `Uniform(TAMANHO_MIN, TAMANHO_MAX)` MB.
- **Stage 1 — `Validador`**: one server, no parallelism (`simpy.Resource(capacity=1)`), queue `FilaValidacao`. Validation time is `Uniform(TEMPO_VALIDACAO_MIN, TEMPO_VALIDACAO_MAX)`.
- **Routing decision (conditional)**: after validation, requests with `tamanho_imagem < LIMIAR_ROTA_MB` skip straight to exit ("rota rápida" — already small enough); the rest proceed to stage 2 ("rota completa").
- **Stage 2 — `Processador`**: one server, no parallelism, queue `FilaProcessamento`, only for "rota completa" requests. Processing time is linear in size: `TEMPO_BASE + tamanho_imagem * TEMPO_POR_UNIDADE`.
- **Queue discipline**: FIFO, unbounded, for both queues.
- **Stop condition**: simulation ends naturally once all `N_USUARIOS` requests have arrived and finished (no explicit `until=`).

All tunable parameters live as named constants at the top of `api_simulator.py` (`N_USUARIOS`, `TAXA_CHEGADA`, `TAMANHO_MIN`/`TAMANHO_MAX`, `TEMPO_BASE`, `TEMPO_POR_UNIDADE`, `TEMPO_VALIDACAO_MIN`/`TEMPO_VALIDACAO_MAX`, `LIMIAR_ROTA_MB`, `SEMENTE_ALEATORIA`).

## Files

- `api_simulator.py` — the simulation: config, `Estatisticas` collector, `processar_requisicao` / `gerador_usuarios` processes (two sequential stages — `Validador` then, conditionally, `Processador` — with a routing decision in between), `executar_simulacao(semente)` (runs one simulation for a given seed, returns `(ambiente, estatisticas)`), `calcular_metricas(ambiente, estatisticas)` (returns the summary metrics as a dict), `imprimir_relatorio` (prints `calcular_metricas`'s output), `imprimir_tabela_amostra` (per-request table: image size, route taken, wait/service time at each stage).
- `plot_distributions.py` — samples the same three distributions the simulation uses (interarrival time, validation time, processing time) and plots empirical histograms against their theoretical PDFs, saved to `distributions.png`. Imports its constants directly from `api_simulator.py` so it stays in sync with config changes.
- `executar_replicacoes.py` — runs `N_REPLICACOES` (10) independent replications, each with its own seed (`SEMENTE_ALEATORIA + 1 + i`, deliberately distinct from the single-run reference seed), reusing `executar_simulacao`/`calcular_metricas` from `api_simulator.py`; writes one row per replication to `replicacoes.csv`, one column per metric.
- `requirements.txt` — `simpy` (plus `matplotlib`/`numpy` needed only for `plot_distributions.py`).

## Running

Run from inside `grau-a/`; the `.venv` lives at the repository root.

```bash
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/pip install matplotlib numpy  # only needed for plot_distributions.py
../.venv/bin/python api_simulator.py
../.venv/bin/python plot_distributions.py
../.venv/bin/python executar_replicacoes.py
```

## Conventions

- Identifiers, comments, and all printed output are in pt-BR — keep new code consistent with this.
- No CLI args/argparse: parameters are edited directly as constants in `api_simulator.py` for quick tuning between simulation runs.
- Simulation results are deterministic (fixed `SEMENTE_ALEATORIA`), so reruns without config changes should reproduce identical output — useful for verifying edits didn't change behavior.
