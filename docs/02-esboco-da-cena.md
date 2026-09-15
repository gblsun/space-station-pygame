# Etapa 1 — Esboço da cena

As duas figuras deste documento são **geradas pelo próprio programa**
(`python docs/gerar_figuras.py`), de modo que nunca divergem do que a aplicação
desenha. Regere-as depois de qualquer mudança na cena.

## Planta do plano XZ

![Planta da cena](img/esboco-planta.png)

A planta mostra, vista de cima: a posição de cada objeto, a trajetória de aproximação
do cargueiro com as marcas de fim de fase, as órbitas dos quatro robôs, o cinturão de
detritos e a posição e a mira de cada câmera.

## Relações espaciais

A estação fica na origem da cena, em `(0, 0, 560)` no mundo. O eixo do casco é o **X**,
e todos os módulos se alinham a ele:

```
      -X                         núcleo                        +X
   [cúpula][ Laboratório ]==túnel==[ casco Órbita-2 ]==[anel]==[ Vega-7 ]-->
                                        |     |
                             painéis solares em ±Z
                                        |
                              treliça da antena em +Y
                            (sensor da linha de visão no topo)
```

| Objeto | Posição (relativa à estação) | Observação |
|---|---|---|
| Núcleo Órbita-2 | `(0, 0, 0)` | pai de toda a hierarquia |
| Módulo Laboratório | `(-184, 0, 0)` | filho do núcleo, herda a inclinação |
| Comportas | `(92, ±deslocamento, 0)` | filhas do núcleo; deslizam em Y |
| Balizas | anel de raio 38 em `x = 92` | seis, acesas em rodízio |
| Sensor da antena | `(-77, 208, 0)` | origem dos raios de visibilidade |
| Cargueiro Vega-7 | `x` de 470 a 178 | aproxima-se ao longo de X |
| Robôs MR-1 a MR-4 | ancorados no casco; órbitas de raio 150 a 272 | saem na fase 4 |
| Planeta Kaltus | `(-1180, -470, +1750)` | objeto sem partes, ao fundo |

A hierarquia de transformações tem três níveis, e é o mesmo conceito da Aula 6:

```
estação (inclinação de repouso + rotação lenta)
 ├── módulo laboratório
 ├── comporta superior / inferior
 ├── balizas de alerta
 └── robô MR-n
      └── braço (junta do ombro)
           └── antebraço com garra (junta do cotovelo)
```

## Câmeras

| Tecla | Modo | Intenção |
|---|---|---|
| `C` | Plano geral | Enquadra a estação inteira com o cargueiro |
| `W` | Visão superior | Mostra a abertura dos painéis e as órbitas |
| `S` | Visão inferior | Revela o lado oposto do casco |
| `A` / `D` | Flancos | Dão a leitura de profundidade da estrutura |
| `F` | Foco animado | Acompanha o cargueiro quadro a quadro |

Toda troca é interpolada por `lerp`, tanto na posição do olho quanto no ponto
observado: nunca há corte seco.

## Sequência visual

![As quatro fases](img/fases.png)

Cada miniatura é um quadro real da aplicação, capturado em 2,0 s, 5,5 s, 8,8 s e
12,6 s de simulação. O roteiro detalhado está em
[04-roteiro-animacoes.md](04-roteiro-animacoes.md).
