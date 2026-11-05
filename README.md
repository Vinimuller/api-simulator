# Simulação e Modelagem de Sistemas

Trabalhos da disciplina Simulação e Modelagem de Sistemas (Ciência da Computação, Unisinos). O trabalho em andamento é o do Grau B; o repositório também guarda o do Grau A.

## Trabalho do Grau B: Processamento de Imagens de Drones

Estudo de simulação de uma plataforma que recebe imagens de drones e gera mapas topográficos de alta resolução. A pergunta central é se a capacidade atual de GPUs cumpre a meta de 5 minutos no pico do fim do dia ou se vale a pena acrescentar uma GPU.

**Situação:** o modelo conceitual está definido, e a implementação ainda não começou. Os valores das distribuições são iniciais e ainda serão verificados.

### Por onde começar

1. Leia o [modelo conceitual](grau-b/docs/modelo_conceitual.md): sistema, fluxo, indicadores, cenários e o motivo de cada decisão.
2. Consulte o [enunciado](<grau-b/docs/Trabalho do Grau B - Enunciado.pdf>), que prevalece sobre os demais documentos.
3. Veja o [resumo do trabalho e as convenções](grau-b/CLAUDE.md).

O modelo conceitual também está em [HTML](grau-b/docs/modelo_conceitual.html). O GitHub mostra esse arquivo como código, então, para ver a página formatada, baixe o repositório e abra o arquivo no navegador.

### Modelo em resumo

| Item | Definição |
|---|---|
| Ferramenta | Python + SimPy |
| Entidade | Mapa, que representa o processamento de um voo |
| Fluxo | Validação em CPU, rota por número de imagens, alinhamento em GPU, ortomosaico e modelo de elevação em paralelo, notificação |
| Indicador principal | P90 do lead time, com meta de até 5 min |
| Contagem | Mapas fora do prazo por noite |
| Cenários | Atual (2 GPUs comuns + 2 de alta capacidade) contra uma GPU de alta capacidade a mais, ambos no pico |

### Próximos passos

Os itens abertos estão em [Pontos a verificar](grau-b/docs/modelo_conceitual.md#pontos-a-verificar) e [Próximos passos](grau-b/docs/modelo_conceitual.md#próximos-passos). No Moodle, ainda falta obter o template do relatório e confirmar a data de entrega.
