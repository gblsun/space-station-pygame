# Etapa 2 — Roteiro das animações

Duração total: **14 segundos**. Estados da máquina principal: `PARADO`,
`EXECUTANDO`, `PAUSADO`, `CONCLUIDO`. Todos os tempos abaixo são de simulação, não de
relógio: pausar congela a linha do tempo, e as teclas `1` a `4` saltam para o início de
cada fase.

A pose de todo objeto é **função pura do tempo de simulação**. Pausar, reiniciar ou
saltar de fase reconstrói exatamente o mesmo estado — não há acúmulo de erro nem
dependência da ordem dos comandos.

## Fase 1 — Aproximação do cargueiro · 0 s a 4 s

| Objeto | O que acontece |
|---|---|
| Cargueiro Vega-7 | Translada de `x = 470` para `x = 300`, suavizado por `smoothstep`. O desalinhamento residual em posição e atitude diminui conforme se aproxima: a oscilação lateral e o giro de rolagem vão a zero |
| Balizas | Seis luzes no anel de doca acendem em rodízio, em âmbar, a quatro trocas por segundo |
| Comporta | `FECHADA` |
| Robôs MR-1 a MR-4 | Ancorados em pontos distintos do casco, com os braços em operação |
| Estação | Inclinação de repouso de 26°, mais rotação lenta de 2,2°/s |
| Sensor | Linha de visão apontada para o cargueiro |

## Fase 2 — Abertura da comporta de doca · 4 s a 7 s

| Objeto | O que acontece |
|---|---|
| Comporta | `ABRINDO` de 4 s a 6 s, depois `ABERTA`. As duas folhas deslizam em sentidos opostos até 36 unidades, com curva suavizada |
| Cargueiro | Desacelera de `x = 300` para `x = 222`, com pulsação de escala de ±3,5% |
| Retrofoguetes | Emissão contínua de partículas, desenhadas como rastros estirados na direção da velocidade, com halo quente nas mais recentes |
| Balizas | Seguem em âmbar |

## Fase 3 — Acoplamento do módulo · 7 s a 10 s

| Objeto | O que acontece |
|---|---|
| Cargueiro | Percurso final até `x = 178`; o nariz encaixa dentro do anel de doca |
| Comporta | `ABERTA` até 8,5 s, depois `FECHANDO` até 10 s, quando volta a `FECHADA` |
| Balizas | Mudam de âmbar para **verde** a partir de 7 s, sinalizando travamento |
| Partículas | Cessam ao fim da fase |

## Fase 4 — Órbita de inspeção dos robôs · 10 s a 14 s

| Objeto | O que acontece |
|---|---|
| Robôs MR-1 a MR-4 | Deixam a ancoragem numa transição suavizada de 1,2 s e entram em trajetória helicoidal. Cada um tem raio, velocidade, fase e inclinação de plano próprios |
| Evitação de colisão | A trajetória é testada contra o cilindro de segurança do mastro da antena; se entrar nele, o ponto é empurrado radialmente para fora |
| Braços | Ombro e cotovelo oscilam fora de fase, em cadeia hierárquica de dois segmentos |
| Sensor | Passa a traçar uma linha para **cada** robô. Quando um deles passa atrás do núcleo ou de um detrito, a linha fica vermelha e o HUD nomeia o obstáculo |

Ao fim dos 14 s o estado passa a `CONCLUIDO` e a barra de progresso marca 100%. Um novo
`ESPAÇO` reinicia a sequência.

## Animações permanentes

Rodam em qualquer fase, inclusive com a simulação parada:

- Rotação lenta da estação, arrastando módulo, comportas e balizas pela hierarquia.
- Rotação do planeta e do satélite.
- Deriva e tombamento dos nove detritos, cada um em ritmo próprio.
- Cintilação do campo estelar.
- Transição interpolada da câmera a cada troca de modo.

## Mapa das três animações exigidas no requisito 6

| Tipo exigido | Onde está |
|---|---|
| Transformação espacial | Aproximação e acoplamento do cargueiro: translação, rotação de atitude e escala pulsante |
| Animação composta por estados | `DoorFSM`, com `FECHADA → ABRINDO → ABERTA → FECHANDO`, aninhada na máquina de estados principal |
| Sequência com dois ou mais objetos | O acoplamento coordena cargueiro, comporta e balizas; a fase 4 coordena os quatro robôs com o sensor da estação |
