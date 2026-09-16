# Etapa 2 — Roteiro das animações

A cena tem **dois relógios independentes**:

| Relógio | O que move | Controles |
|---|---|---|
| Sequência de acoplamento | As quatro fases, 14 segundos ao todo | `ESPAÇO`, `R`, `1`–`4`, `+`/`-`, `L`, `O` |
| Relógio orbital | O Sistema Solar inteiro, a partir do UTC real | `,` e `.`, de tempo real a 1 ano por segundo |

Pausar a sequência não congela o Sistema Solar, e acelerar o Sistema Solar não adianta a
sequência. A pose de todo objeto é **função pura do tempo**: pausar, reiniciar ou saltar
de fase reconstrói exatamente o mesmo estado, sem acúmulo de erro.

Estados da máquina principal: `PARADO`, `EXECUTANDO`, `PAUSADO`, `CONCLUIDO`.

## Fase 1 — Aproximação do cargueiro · 0 s a 4 s

| Objeto | O que acontece |
|---|---|
| Cargueiro Vega-7 | Translada de `x = 470` para `x = 300` no referencial da estação, suavizado por `smoothstep`. O desalinhamento residual em posição e atitude diminui conforme se aproxima |
| Balizas | Seis luzes no anel de doca acendem em rodízio, em âmbar, a quatro trocas por segundo |
| Comporta | `FECHADA` |
| Robôs MR-1 a MR-4 | Ancorados em pontos distintos do casco, com os braços em operação |
| Sensor | Linha de visão apontada para o cargueiro |

## Fase 2 — Abertura da comporta de doca · 4 s a 7 s

| Objeto | O que acontece |
|---|---|
| Comporta | `ABRINDO` de 4 s a 6 s, depois `ABERTA`. As duas folhas deslizam em sentidos opostos até 36 unidades, com curva suavizada |
| Cargueiro | Desacelera de `x = 300` para `x = 222`, com pulsação de escala de ±3,5% |
| Retrofoguetes | Emissão contínua de partículas, no referencial da estação, com rastros estirados e halo quente nas mais recentes |
| Balizas | Seguem em âmbar |

## Fase 3 — Acoplamento do módulo · 7 s a 10 s

| Objeto | O que acontece |
|---|---|
| Cargueiro | Percurso final até `x = 178`; o nariz encaixa dentro do anel de doca |
| Comporta | `ABERTA` até 8,5 s, depois `FECHANDO` até 10 s, quando volta a `FECHADA` |
| Balizas | Mudam de âmbar para **verde** a partir de 7 s, sinalizando travamento |
| Trava | Aos 10 s, faíscas radiais, clarão no anel e um tremor curto de câmera |
| Cabine | Pelo visor da escotilha de doca (`Z` até `Cabine`, depois `D`), a mesma manobra vista de dentro |

## Fase 4 — Órbita de inspeção dos robôs · 10 s a 14 s

| Objeto | O que acontece |
|---|---|
| Robôs MR-1 a MR-4 | Deixam a ancoragem numa transição suavizada de 1,2 s e entram em trajetória helicoidal. Cada um tem raio, velocidade, fase e inclinação de plano próprios |
| Evitação de colisão | A trajetória é testada contra o cilindro de segurança do mastro da antena; se entrar nele, o ponto é empurrado radialmente para fora |
| Braços | Ombro e cotovelo oscilam fora de fase, em cadeia hierárquica de dois segmentos |
| Sensor | Passa a traçar uma linha para **cada** robô. Quando um deles passa atrás do núcleo ou de um detrito, a linha fica vermelha e o HUD nomeia o obstáculo |

Ao fim dos 14 s o estado passa a `CONCLUIDO` e a barra de progresso marca 100%. Um novo
`ESPAÇO` reinicia a sequência; `L` a repete sem parar.

## Animações permanentes

Rodam em qualquer fase, inclusive com a sequência parada, porque pertencem ao relógio
orbital:

- **A estação orbita a Terra de verdade**: 420 km, 92,9 minutos, atitude LVLH. A cada
  volta ela entra e sai da sombra — cerca de 36% do tempo em eclipse.
- **Os painéis solares seguem o Sol.** A Órbita-2 e os satélites reais têm juntas de um
  ou dois eixos: a ISS combina a junta da treliça com a de cada asa, o GPS gira o corpo
  (*yaw steering*) e depois a asa, o Hubble mantém o eixo das asas perpendicular ao Sol e
  o James Webb mantém o escudo de frente para ele. Na sombra as juntas voltam a zero.
- **O dia e a noite passam embaixo.** O lado escuro da Terra acende com as luzes das
  cidades, e o terminador atravessa o planeta enquanto a estação avança.
- **Os planetas percorrem as órbitas reais**, cada um no lugar onde está agora, com a
  rotação própria pela orientação IAU. As luas giram em torno dos planetas, em travamento
  de maré.
- **Os satélites artificiais orbitam**: estações, GNSS, geoestacionários e Starlink, com
  os elementos do CelesTrak.
- **Milhares de asteroides e cometas** percorrem o cinturão principal, os troianos de
  Júpiter e o Cinturão de Kuiper.
- **Detritos** derivam em órbita relativa lenta em torno da estação, cada um em ritmo próprio.
- **Os cometas ganham cauda** quando entram em 4 UA, sempre apontada para longe do Sol.
- **O rastro da órbita e o terminador** aparecem desenhados sobre o globo quando a Terra
  está grande na tela.
- **As estrelas cintilam**, nas posições e cores reais.
- **A câmera interpola** a cada troca de modo, enquadramento ou foco.

## Mapa das três animações exigidas no requisito 6

| Tipo exigido | Onde está |
|---|---|
| Transformação espacial | Aproximação e acoplamento do cargueiro: translação, rotação de atitude e escala pulsante |
| Animação composta por estados | `DoorFSM`, com `FECHADA → ABRINDO → ABERTA → FECHANDO`, aninhada na máquina de estados principal |
| Sequência com dois ou mais objetos | O acoplamento coordena cargueiro, comporta e balizas; a fase 4 coordena os quatro robôs com o sensor |

## Modo apresentação (`F9`)

Doze passos encadeados, com legenda em tela, que percorrem a cabine, o acoplamento visto
de fora e de dentro, a fase 4, os painéis seguindo o Sol, uma volta orbital acelerada,
os satélites reais, a Lua e o James Webb, e o Sistema Solar até o Cinturão de Kuiper.
Qualquer tecla encerra e devolve o controle.
