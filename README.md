# Simulação e Modelagem de Sistemas

Trabalhos da disciplina Simulação e Modelagem de Sistemas (Ciência da Computação, Unisinos). O trabalho em andamento é o do Grau B; o repositório também guarda o do Grau A.

## Trabalho do Grau B: Processamento de Imagens de Drones

Estudo de simulação de uma plataforma que recebe as imagens de voos de drone e gera mapas topográficos (ortomosaico e modelo de elevação). A pergunta central é se a capacidade atual de servidores cumpre a meta de 10 minutos no pico do fim do dia ou se vale a pena colocar mais um servidor em paralelo.

**Situação:** todos os entregáveis estão prontos — modelo em Python e SimPy (scripts modulares e caderno Jupyter autocontido `simulacao_drones_tgb.ipynb`), simulação dos dois cenários com 30 replicações cada, animação em vídeo MP4 (`animacao_modelo.mp4`), relatório final (`Trabalho do Grau B - Relatorio Final.docx`) e slides da apresentação (`Apresentacao_Grau_B_Drones.pptx`).

### Por onde começar

1. Leia o [modelo conceitual](grau-b/docs/modelo_conceitual.md): contexto, plataforma, modelo, experimento, resultados e o motivo de cada decisão.
2. Consulte o [enunciado](<grau-b/docs/Trabalho do Grau B - Enunciado.pdf>), que prevalece sobre os demais documentos.
3. Veja o [resumo do trabalho e as convenções](grau-b/CLAUDE.md).

O modelo conceitual também está em [HTML](grau-b/docs/modelo_conceitual.html). O GitHub mostra esse arquivo como código, então, para ver a página formatada, baixe o repositório e abra o arquivo no navegador.

### Como rodar

O código fica em [`grau-b/simulacao/`](grau-b/simulacao/). O ambiente virtual fica na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/pip install -r grau-b/simulacao/requirements.txt

cd grau-b/simulacao
../../.venv/bin/python modelo.py              # uma noite de cada cenário, com os indicadores
../../.venv/bin/python executar_cenarios.py   # 30 replicações por cenário e IC de 95%
../../.venv/bin/python graficos.py            # gráficos em resultados/graficos/
../../.venv/bin/python animacao.py            # vídeo MP4 em resultados/animacao_modelo.mp4
```

Os resultados (CSV e PNG) ficam em `grau-b/simulacao/resultados/`. As sementes são fixas, então os números se repetem a cada execução.

### Modelo em resumo

| Item | Definição |
|---|---|
| Ferramenta | Python + SimPy, em scripts locais |
| Entidade | Mapa, que representa o processamento de um voo |
| Fluxo | Validação em CPU (com reenvio dos arquivos faltantes), rota por número de imagens, alinhamento, ortomosaico e modelo de elevação em paralelo, notificação |
| Tempos de processamento | Por imagem, do benchmark da Puget Systems com PIX4Dmatic |
| Indicador principal | P90 do lead time, com meta de até 10 min |
| Contagem | Mapas fora do prazo por noite |
| Cenários | Atual (2 servidores de voos pequenos + 3 de voos grandes) contra um servidor de voos grandes a mais, ambos no pico, com 100 mapas por noite |

### Resultados

| Indicador | Atual | Servidor extra |
|---|---|---|
| P90 do lead time | 9,47 min, IC [8,74; 10,20] | 7,10 min, IC [6,89; 7,32] |
| Mapas fora do prazo | 8,3 mapas/noite | 0,7 mapas/noite |

O cenário atual opera no limite da meta. O servidor extra reduz o P90 em 2,37 min, com IC sem sobreposição. A análise completa está na [seção 5 do modelo conceitual](grau-b/docs/modelo_conceitual.md#5-resultados-da-simulação).

### Próximos passos

Os itens abertos estão em [Pontos a verificar](grau-b/docs/modelo_conceitual.md#pontos-a-verificar) e [Próximos passos](grau-b/docs/modelo_conceitual.md#próximos-passos). No Moodle, ainda falta obter o template do relatório e confirmar a data de entrega.
