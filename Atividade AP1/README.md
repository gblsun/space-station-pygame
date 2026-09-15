# Atividade AP1 — Mundo Virtual Animado

Resumo do enunciado em [Atividade-AP_1.pdf](Atividade-AP_1.pdf), para consulta rápida sem precisar reabrir o PDF. Em caso de dúvida, o PDF é a fonte oficial.

## Visão geral

- **Modalidade:** equipe de 4 alunos.
- **Duração:** 3 aulas, uma entrega por aula.
- **Produto final:** aplicação 2D/3D com animações, em Python + Pygame (sem OpenGL, motores 3D ou bibliotecas externas de modelagem).
- **Interação:** apenas comandos discretos de teclado (iniciar, pausar, reiniciar, alternar animações/câmera). Não há navegação livre, mouse, física ou tempo real.
- **Variação deste repositório:** tema **Estação Espacial** (Equipe 2) — acoplamento de módulos, trajetória orbital de robôs, portas com estados e alerta sequencial.

## Requisitos mínimos obrigatórios

1. Janela configurável, laço principal, controle de FPS, atualização por Δt e encerramento adequado.
2. Pelo menos 3 tipos de primitivas/elementos visuais (pontos/linhas, polígonos, círculos, sprites ou superfícies rasterizadas).
3. Pelo menos 5 objetos na cena: ≥3 instâncias de um mesmo tipo com parâmetros diferentes, ≥1 objeto sem partes e ≥1 objeto composto por diferentes estruturas.
4. Translação, rotação e escala aplicadas a objetos; pelo menos duas transformações devem variar durante as animações.
5. Câmera com pelo menos dois modos de apresentação, alternados por tecla (ex.: plano geral e foco animado em um objeto).
6. Pelo menos 3 animações distintas: uma transformação espacial, uma animação composta por estados e uma sequência com dois ou mais objetos.
7. Comandos de teclado documentados para iniciar, pausar, retomar, reiniciar e alternar animações (ações discretas, não navegação contínua).
8. Interface sobreposta com título do cenário, comandos disponíveis, estado da animação, tempo/etapa atual e indicador de progresso.
9. Um recurso de visibilidade inspirado em traçado de raio simplificado (teste de interseção, linha de visão ou iluminação binária).
10. Tela de créditos com os quatro integrantes, referências dos materiais utilizados e a variação escolhida.

## Etapas e entregas

| Etapa | Objetivo | Peso |
|---|---|---|
| 1 — Projeto visual e protótipo animável | Cena mínima executável: objetos, transformações e primeira animação por teclado | 30% |
| 2 — Sequências, estados e câmera | Múltiplas animações, estados, modos de câmera, instâncias e teste de visibilidade | 30% |
| 3 — Interface, acabamento e apresentação | Interface completa, revisão geral, README, testes e apresentação final (5–8 min) | 40% |

Uso de ferramentas avançadas (OpenGL, engines 3D etc.) não é permitido. Entregas incompletas são penalizadas.

## Checklist antes da entrega

- Programa executa seguindo as instruções do README do projeto.
- Os quatro integrantes identificados e capazes de explicar sua contribuição.
- Cena com objetos instanciados, transformações, câmera, estados e animações.
- Animações controladas só por comandos discretos de teclado.
- Interface informando comandos, animação atual, estado e progresso.
- Testado: iniciar, pausar, retomar, reiniciar, alternar câmera, concluir sequências, encerrar.
- Apresentação relaciona as escolhas do projeto aos conteúdos estudados.

---

## Como executar

```bash
pip install -r "Atividade AP1/requirements.txt"
python "Atividade AP1/ap1.py"
```

No Python 3.14 o `pygame` clássico não tem wheel e falha ao compilar; use
`pip install pygame-ce`, que é compatível e também se importa como `pygame`.

## Comandos de teclado

| Tecla | Ação |
|---|---|
| `ESPAÇO` | Iniciar · pausar · retomar · reiniciar quando concluída |
| `R` | Reiniciar a cena no estado inicial |
| `1` `2` `3` `4` | Saltar direto para o início de cada fase |
| `C` | Câmera — plano geral |
| `W` / `S` | Câmera — visão superior / inferior |
| `A` / `D` | Câmera — flanco esquerdo / direito |
| `F` | Câmera — foco animado, acompanha o cargueiro |
| `T` | Tour de câmera: um enquadramento por fase (qualquer tecla de câmera desliga) |
| `Z` / `X` | Enquadramento — aproximar / afastar (doca, estação, órbita baixa, Terra e Lua, sistema) |
| `+` / `-` | Velocidade da simulação, de 0,25x a 3x |
| `L` | Repetir a sequência sem parar |
| `O` | Órbita de inspeção estendida, com cerca de três voltas dos robôs |
| `B` | Mostrar / ocultar o traçado das órbitas |
| `N` | Rótulos dos objetos, com o papel de cada um no requisito 3 |
| `H` | Painel de dados: FPS medido, custo do quadro, faces, culling e câmera |
| `F12` | Captura de tela, salva em `docs/img` |
| `TAB` | Tela de créditos |
| `ESC` | Encerrar |

Todas as teclas disparam ações discretas. Não há navegação livre, mouse nem
controle contínuo da cena.

## A sequência (4 fases, 14 s)

| Fase | Intervalo | O que acontece |
|---|---|---|
| 1 — Aproximação | 0 s – 4 s | O cargueiro Vega-7 se aproxima corrigindo a atitude; balizas em alerta âmbar sequencial; comporta `FECHADA`. |
| 2 — Abertura da doca | 4 s – 7 s | Comporta `ABRINDO → ABERTA`; o cargueiro desacelera com pulsação de escala e emite partículas de retrofoguete. |
| 3 — Acoplamento | 7 s – 10 s | O cargueiro encaixa no anel; comporta `FECHANDO → FECHADA`; balizas passam de âmbar a verde. |
| 4 — Órbita de inspeção | 10 s – 14 s | Os quatro robôs saem em órbita helicoidal, desviando do mastro da antena, com os braços em operação; o sensor testa a linha de visão até cada um. |

## Onde cada requisito obrigatório está implementado

Mapa direto do §3 do enunciado para o código, para consulta durante a apresentação.

| # | Requisito | Implementação em `ap1.py` |
|---|---|---|
| 1 | Janela, laço, FPS, Δt, encerramento | `App.run()` — `WIDTH/HEIGHT/FPS`, `clock.tick(FPS)`, `dt` limitado a 50 ms contra engasgos, saída por `ESC`/fechar janela e `pygame.quit()` |
| 2 | ≥3 tipos de primitivas | Polígonos (faces das malhas), círculos (partículas e balizas), linhas (raios do sensor), pontos (campo estelar, `set_at`), retângulos e texto (HUD) — 6 tipos |
| 3 | ≥5 objetos, com 3 instâncias, 1 sem partes e 1 composto | 32 malhas. **4 instâncias:** robôs MR-1 a MR-4, com escala, cor, raio orbital, velocidade e fase diferentes. **Sem partes:** Terra e Lua, cada uma uma esfera única. **Compostos:** Núcleo Órbita-2 (casco, colares, anel de doca, 2 painéis solares em grade, radiadores, treliça de antena, escotilhas, propulsores e antena parabólica), Módulo Laboratório e Cargueiro Vega-7. A tecla `N` rotula cada objeto com o seu papel |
| 4 | Translação, rotação e escala, com duas variando na animação | **Translação:** cargueiro, robôs, detritos, satélites, Terra e Lua. **Rotação:** detritos (3 eixos), Terra, Lua, Sol, satélites, robôs e as juntas dos braços. **Escala:** pulsação do cargueiro na fase 2 e escalas distintas por robô. As três variam durante a sequência |
| 5 | Câmera com ≥2 modos alternados por tecla | `Camera` com 5 presets fixos (`C W S A D`), o **foco animado** `F`, que acompanha o cargueiro quadro a quadro, e o **tour** `T`, que troca de enquadramento a cada fase. Toda troca é interpolada sobre o deslocamento em relação à âncora, não é corte seco |
| 6 | ≥3 animações: espacial, por estados e sequência com 2+ objetos | **Espacial:** aproximação e acoplamento do cargueiro (`_animate_cargo`). **Por estados:** `DoorFSM` (`FECHADA → ABRINDO → ABERTA → FECHANDO`) aninhada na FSM geral. **Sequência com 2+ objetos:** acoplamento coordenando cargueiro, comporta e balizas, e a órbita dos 4 robôs com evitação do mastro |
| 7 | Comandos discretos documentados | `App.handle_event` — só `KEYDOWN`; tabela de teclas acima |
| 8 | Interface com título, comandos, estado, etapa e progresso | `Hud._draw_main` e `Hud._draw_footer`: título, estado da FSM, fase atual, estado da comporta, balizas, câmera, leitura do sensor, comandos e barra de progresso com marcas das trocas de fase |
| 9 | Recurso de visibilidade por traçado de raio | `ray_sphere()` + `Scene.line_of_sight()`: o sensor no topo da antena dispara um raio até cada alvo e testa interseção com as esferas envolventes dos detritos e do núcleo. Linha verde quando livre, vermelha com marcador no ponto de impacto quando bloqueada; o HUD nomeia o obstáculo |
| 10 | Créditos com integrantes, referências e variação | `Hud._draw_credits` (`TAB`): os quatro integrantes com RA e contribuição, referências dos materiais e a variação Equipe 2 — Estação Espacial |

## Testes

Suíte automatizada, roda sem abrir janela (usa o driver de vídeo `dummy`):

```bash
python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v
```

São 89 testes, cobrindo a matemática vetorial, o winding das malhas (normais
apontando para fora), a base ortonormal da câmera em todos os presets, o recorte
no plano próximo, a interseção raio-esfera, a máquina de estados, as fases, a
comporta, as balizas, a evitação de colisão, o cache de vértices, o frustum
culling, os níveis de detalhe, os halos e a renderização em todas as câmeras.

Roteiro do checklist executado de ponta a ponta, com relatório:

```bash
python "Atividade AP1/test_ap1.py" --smoke
```

Medição de desempenho, com o custo de cada etapa do quadro:

```bash
python "Atividade AP1/test_ap1.py" --bench
```

### Roteiro de teste manual (checklist do enunciado)

Com a aplicação aberta, na ordem:

1. **Iniciar** — `ESPAÇO`. O estado sai de `PARADO` para `EXECUTANDO` e o cargueiro começa a se aproximar.
2. **Pausar** — `ESPAÇO`. O estado vira `PAUSADO`, o tempo para de correr e a barra de progresso congela.
3. **Retomar** — `ESPAÇO`. Volta a `EXECUTANDO` do ponto exato em que parou.
4. **Alternar câmera** — `W`, `S`, `A`, `D`, `C` e `F`. Em todos os modos a estação deve continuar enquadrada; a transição é suave.
5. **Alternar animações** — `1` a `4`. Cada tecla salta para o início da fase correspondente; confira o estado da comporta no HUD em cada uma.
6. **Concluir a sequência** — deixe chegar aos 14 s. O estado vira `CONCLUIDO` e o progresso marca 100%.
7. **Reiniciar** — `R` a qualquer momento, ou `ESPAÇO` depois de concluída. A cena volta exatamente à pose inicial.
8. **Créditos** — `TAB` abre e fecha.
9. **Encerrar** — `ESC` fecha a janela.

Durante a fase 4, observe o sensor no HUD: quando um robô passa atrás do núcleo
ou de um detrito, a linha fica vermelha e o HUD nomeia o obstáculo.
