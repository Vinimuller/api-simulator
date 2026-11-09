# Trabalho do Grau B (TGB): mapas a partir de imagens de drone

Estudo de simulação da disciplina Simulação e Modelagem de Sistemas (Ciência da Computação, Unisinos). Vale 50% da nota do Grau B; os outros 50% vêm da prova. Grupo de 1 a 4 pessoas.

O enunciado completo está em `docs/Trabalho do Grau B - Enunciado.pdf` e prevalece sobre este resumo.

## Sistema proposto

**Título registrado na Wiki:** Processamento de Imagens de Drones.

Plataforma que recebe imagens de drone e as processa até gerar um mapa, similar ao DJI SmartFarm.

## Estado atual

- [x] Registrar o trabalho na Wiki da disciplina (obrigatório antes de iniciar a construção do modelo).
- [x] Modelo conceitual (`docs/modelo_conceitual.md` e `.html`).
- [x] Modelo implementado em `simulacao/`, com os dois cenários, 30 replicações cada, IC e gráficos de resultados (requisitos a–e, g, h).
- [x] Conclusões e recomendações na seção 5 do modelo conceitual (requisito i).
- [ ] Animação em MP4 (requisito f e vídeo da seção 4).
- [ ] Obter o template do relatório no Moodle.
- [ ] Confirmar a data de entrega na tarefa do Moodle (o enunciado não informa a data).

## Requisitos mínimos do modelo (seção 3)

- **a) Base do estudo:** modelo conceitual documentado, fluxo completo e distribuições de probabilidade justificadas.
- **b) Decisões:** ao menos uma por probabilidade e uma por condição. Desistência de fila conta como decisão condicional.
- **c) Indicadores:** ao menos dois, sendo uma contagem específica e o lead time (tempo total da entidade no sistema, da entrada até a saída, incluídas as esperas). Recomenda-se acrescentar uma medida de dispersão (como P90) ou de fluxo (como vazão).
- **d) Atributos e variáveis:** ao menos um atributo com significado (tipo, prioridade, tamanho), usado em rota, tempo ou indicador, ou uma variável global, no padrão de controle de estoque.
- **e) Lotes ou duplicações:** ao menos um agrupamento, montagem ou fluxo paralelo coerente com o sistema.
- **f) Demonstração visual:** animação do modelo em execução, com o estado do sistema visível ao longo da rodada. A cena deve ter título do cenário, relógio da simulação, ao menos três indicadores em texto, cada um com unidade, e um gráfico com eixos rotulados.
- **g) Gráficos de resultados:** ao menos dois, com título, eixos rotulados e unidades:
  - evolução temporal de uma variável de estado, desenhada em degraus;
  - comparação dos cenários no indicador principal, com o IC em barras de erro.
- **h) Experimentação:** ao menos 2 cenários, com no mínimo 30 replicações por cenário e IC do indicador principal. Intervalos que não se sobrepõem indicam diferença conclusiva; intervalos sobrepostos não permitem concluir pela diferença.
- **i) Análise:** conclusões e recomendações sempre com número, unidade e comparação.

O sistema também precisa ter de forma natural uma decisão condicional e um indicador de interesse para a gestão. As perguntas do estudo devem ser relevantes, e ao menos uma deve comparar cenários (por exemplo, situação atual contra um recurso adicional, ou demanda normal contra pico).

## Vídeo da demonstração (seção 4)

MP4 gravado previamente, sem áudio, com até 1 minuto. A execução é explicada pelo grupo durante a exibição.

Procedimento em Python, de preferência com matplotlib (também são aceitas Plotly, salabim e equivalentes):

1. **Registro do estado:** um processo monitor amostra o sistema em intervalos regulares e guarda o instante e as variáveis de interesse (filas, ocupação dos recursos, entidades concluídas).
2. **Desenho de um quadro:** uma função redesenha, para cada amostra, o esquema do fluxo e a série temporal até aquele instante.
3. **Montagem:** `matplotlib.animation.FuncAnimation` encadeia os quadros.
4. **Exportação:** o método `save` grava o MP4 por meio do ffmpeg.

## Entregáveis (Moodle)

1. **Modelo:** roda sem erros, com os cenários incluídos. Em Python, é um caderno que inclui o código da animação.
2. **Vídeo:** MP4 da demonstração.
3. **Relatório no template da disciplina:** sistema, modelo conceitual, hipóteses, dados de entrada, dois indicadores no molde "nome, em unidade, medido de A a B, com meta definida", tabela de cenários com IC, gráficos, conclusões e recomendações.
4. **Slides:** PPTX ou Canva com o vídeo incorporado, ou PDF com o vídeo exibido à parte. No Canva, entregar o link de visualização.

Envios após o prazo são registrados como atraso.

## Avaliação e apresentação

| Critério | Peso |
|---|---|
| Modelo correto e completo (requisitos da seção 3) | 40% |
| Experimentação e análise (cenários, replicações, IC, recomendação fundamentada) | 30% |
| Relatório (clareza, organização, template, indicadores no molde) | 15% |
| Apresentação (domínio do conteúdo, três atos, tempo respeitado) | 15% |

Apresentação presencial no dia da entrega, de 8 a 12 minutos, seguida de perguntas da turma e do professor. Os três atos são:

1. o vídeo, com a visão geral do sistema;
2. o problema investigado;
3. a evidência, com a comparação de cenários por IC e a recomendação final.

## Regras

- **IA:** permitida como assistente, com declaração no relatório. Os integrantes precisam saber explicar cada decisão de modelagem, então registre o porquê das decisões e não apenas o resultado.
- **Comunicação:** poucos indicadores relevantes, com unidade em cada número. A animação ilustra o comportamento, mas as conclusões devem se apoiar na evidência estatística.

## Modelo implementado

O modelo completo, com o porquê de cada decisão e os resultados, está em `docs/modelo_conceitual.md`. Em resumo:

- **Ferramenta:** Python + SimPy, em scripts locais (sem notebook).
- **Usuário e entidade:** prestador de serviço que envia os voos no fim do dia; cada voo dá origem a um mapa, a entidade do modelo.
- **Fluxo:** validação em CPU, rota por `num_imagens` para servidores de voos pequenos ou grandes, alinhamento, ortomosaico e modelo de elevação em paralelo, notificação.
- **Decisões:** por probabilidade, a falta de arquivos na validação, com reenvio dos faltantes; por condição, a rota por número de imagens.
- **Tempos de processamento:** por imagem, do benchmark da Puget Systems com PIX4Dmatic (alinhamento 0,86 s, elevação 1,53 s, ortomosaico 0,19 s), com ±20% assumido. Todos os servidores têm a mesma velocidade, porque a GPU muda pouco o tempo total.
- **Indicadores:** P90 do lead time (principal), com meta de até 10 min, e mapas fora do prazo por noite.
- **Cenários:** no pico, com 100 mapas por noite, atual (2 servidores de voos pequenos + 3 de voos grandes) contra um servidor de voos grandes a mais.

## Programa

O código fica em `simulacao/` e roda localmente como scripts Python (sem notebook), a partir dessa pasta:

- `modelo.py`: parâmetros, modelo SimPy, `executar_simulacao(cenario, semente)` e `calcular_metricas(...)`. Rodado sozinho, imprime uma noite de cada cenário.
- `executar_cenarios.py`: 30 replicações por cenário, com números aleatórios comuns, e IC de 95%. Grava os CSV em `simulacao/resultados/`.
- `graficos.py`: gera os PNG de resultados em `simulacao/resultados/graficos/`.

Comandos, a partir de `simulacao/`: `../../.venv/bin/python executar_cenarios.py` e `../../.venv/bin/python graficos.py`. A seção 3.6 do modelo conceitual liga cada elemento do modelo ao código.

**Resultados:** P90 do lead time de 9,47 min, IC [8,74; 10,20], no cenário atual, contra 7,10 min, IC [6,89; 7,32], com o servidor extra. A diferença é conclusiva. Os números do modelo conceitual e do README estão escritos à mão: se o código mudar, atualize-os junto com os gráficos.

## Decisões em aberto

- **Parâmetros:** validação, falta de arquivos e correção ainda não têm fonte.
- **Meta de mapas fora do prazo:** o limite de 10% dos mapas da noite é uma proposta a confirmar.
- **Formato do entregável do modelo:** o enunciado pede um caderno; o projeto usa scripts. Confirmar se são aceitos ou gerar um `.ipynb` que chame os scripts.

## Reaproveitamento do Grau A

`../grau-a/` é a entrega anterior: uma simulação em SimPy de uma API de processamento de imagens. Serve como referência, e o GB não deve depender dos arquivos de lá.

- `../grau-a/api_simulator.py`: separação entre `executar_simulacao(semente)` e `calcular_metricas(ambiente, estatisticas)`.
- `../grau-a/executar_replicacoes.py`: replicações independentes com sementes distintas.
- `../grau-a/docs/modelo_conceitual.md`: exemplo de modelo conceitual.

## Convenções

- Identificadores, comentários e saídas em pt-BR.
- Parâmetros como constantes nomeadas no topo, sem CLI ou argparse.
- Sementes fixas, para que os resultados sejam reproduzíveis.
- O `.venv` fica na raiz do repositório: `../.venv/bin/python` a partir de `grau-b/` e `../../.venv/bin/python` a partir de `grau-b/simulacao/`.
