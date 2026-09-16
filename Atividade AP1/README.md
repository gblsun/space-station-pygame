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
5. Câmera com pelo menos dois modos de apresentação, alternados por tecla.
6. Pelo menos 3 animações distintas: uma transformação espacial, uma animação composta por estados e uma sequência com dois ou mais objetos.
7. Comandos de teclado documentados para iniciar, pausar, retomar, reiniciar e alternar animações (ações discretas).
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
python "Atividade AP1/ap1.py"                 # janela 1080x720
python "Atividade AP1/ap1.py" --tela-cheia    # abre direto em tela cheia
python "Atividade AP1/ap1.py" --offline       # não toca na rede
```

No Python 3.14 o `pygame` clássico não tem wheel e falha ao compilar; use
`pip install pygame-ce`, que é compatível e também se importa como `pygame`.

A cena funciona sem internet: os dados reais estão versionados em `dados/`. Com rede,
uma thread atualiza em segundo plano os elementos dos satélites, os vetores do James
Webb, a agenda do telescópio e as imagens de fundo.

## Comandos de teclado

A tecla `F1` mostra esta mesma tabela dentro da aplicação.

| Tecla | Ação |
|---|---|
| `ESPAÇO` | Iniciar · pausar · retomar · reiniciar quando concluída |
| `R` | Reiniciar a cena no estado inicial |
| `1` `2` `3` `4` | Saltar direto para o início de cada fase |
| `C` `W` `S` `A` `D` | Câmeras: plano geral, superior, inferior, flanco esquerdo e direito. Dentro da cabine viram corredor, cúpula, bancada, escotilha do laboratório e visor da doca |
| `F` | Foco animado, acompanha o cargueiro |
| `T` | Tour de câmera: um enquadramento por fase |
| `Z` / `X` | Enquadramento: cabine, doca, estação, vizinhança, órbita baixa, Terra e satélites, Terra-Lua-L2, sistema interno, Sistema Solar e Kuiper |
| `P` / `Shift+P` | Foco em corpo celeste ou nave, do Sol para fora |
| `,` / `.` | Relógio orbital: tempo real, 1 min/s, 1 h/s, 1 dia/s, 1 semana/s, 1 mês/s, 1 ano/s |
| `+` / `-` | Velocidade da sequência, de 0,25x a 3x |
| `L` | Repetir a sequência sem parar |
| `O` | Órbita de inspeção estendida, com cerca de três voltas dos robôs |
| `B` | Mostrar / ocultar o traçado das órbitas |
| `N` | Rótulos dos objetos, com o papel de cada um no requisito 3 |
| `V` | Fundo: estrelas reais, imagem do James Webb ou do Hubble |
| `K` | Olho do telescópio: vê pelo James Webb (apontado para o alvo real da agenda) e pelo Hubble |
| `H` | Painel de dados: FPS, custo do quadro, faces, marcadores e dados orbitais |
| `F1` | Ajuda com todos os comandos |
| `F2` | Modo avaliação: onde cada requisito obrigatório aparece |
| `F9` | Modo apresentação automático, com legendas |
| `F11` | Tela cheia na resolução nativa do monitor |
| `F12` | Captura de tela, salva em `docs/img` |
| `TAB` | Tela de créditos |
| `ESC` | Encerrar |

## A sequência (4 fases, 14 s)

| Fase | Intervalo | O que acontece |
|---|---|---|
| 1 — Aproximação | 0 s – 4 s | O cargueiro Vega-7 se aproxima corrigindo a atitude; balizas em alerta âmbar sequencial; comporta `FECHADA`. |
| 2 — Abertura da doca | 4 s – 7 s | Comporta `ABRINDO → ABERTA`; o cargueiro desacelera com pulsação de escala e emite partículas de retrofoguete. |
| 3 — Acoplamento | 7 s – 10 s | O cargueiro encaixa no anel; comporta `FECHANDO → FECHADA`; balizas passam de âmbar a verde. Da cabine, o visor da escotilha mostra a manobra por dentro. |
| 4 — Órbita de inspeção | 10 s – 14 s | Os quatro robôs saem em órbita helicoidal, desviando do mastro da antena, com os braços em operação; o sensor testa a linha de visão até cada um. |

Em paralelo, e independente da sequência, corre o **relógio orbital**: a estação dá uma
volta na Terra a cada 92 minutos, entra e sai da sombra, os planetas seguem as órbitas
reais e os painéis solares acompanham o Sol.

## Onde cada requisito obrigatório está implementado

Mapa direto do §3 do enunciado para o código, para consulta durante a apresentação.
A tecla `F2` mostra este mapa dentro da aplicação, com etiquetas nos próprios objetos.

| # | Requisito | Implementação |
|---|---|---|
| 1 | Janela, laço, FPS, Δt, encerramento | `App.run()` — `clock.tick(FPS)`, `dt` limitado a 50 ms, `configurar_viewport` refazendo a projeção quando a janela muda de tamanho, tela cheia por `F11`, saída por `ESC` e `pygame.quit()` |
| 2 | ≥3 tipos de primitivas | Polígonos (faces das malhas), círculos (partículas, balizas e marcadores), linhas (raios do sensor e traçados de órbita), pontos (estrelas reais e ~5.900 asteroides e satélites), retângulos e texto (HUD) e sprites (halos pré-renderizados e a imagem de fundo dos telescópios) — 6 tipos |
| 3 | ≥5 objetos, com 3 instâncias, 1 sem partes e 1 composto | 62 corpos celestes, 40 naves e a estação. **Instâncias:** robôs MR-1 a MR-4 (cor, escala, raio orbital, velocidade e fase diferentes), a constelação GPS (mesmo modelo, 31 órbitas reais) e 9 detritos. **Sem partes:** Terra e Lua, cada uma uma esfera. **Compostos:** o núcleo Órbita-2 (casco, colares, anel de doca, mastros, treliça, radiadores, escotilhas, propulsores, antena, painéis articulados e a cabine interna), a ISS e o James Webb. A tecla `N` rotula cada papel |
| 4 | Translação, rotação e escala, com duas variando | **Translação:** todas as órbitas reais, o cargueiro e os robôs. **Rotação:** planetas pela orientação IAU, juntas solares seguindo o Sol, braços dos robôs e atitude LVLH da estação. **Escala:** pulsação do cargueiro na fase 2 e escalas distintas por robô |
| 5 | Câmera com ≥2 modos alternados por tecla | Cinco presets em três referenciais — estação, órbita e cabine —, foco animado `F`, tour `T`, dez níveis de zoom `Z/X` e foco em qualquer corpo `P`. Toda troca é interpolada no referencial da âncora |
| 6 | ≥3 animações | **Espacial:** aproximação e acoplamento do cargueiro. **Por estados:** `DoorFSM` (`FECHADA → ABRINDO → ABERTA → FECHANDO`), aninhada na FSM principal. **Sequência com 2+ objetos:** o acoplamento coordena cargueiro, comporta e balizas; a fase 4 coordena os quatro robôs com o sensor |
| 7 | Comandos discretos documentados | `App.handle_event` só trata `KEYDOWN`; tabela acima, rodapé do HUD e tela `F1` |
| 8 | Interface com estado, etapa e progresso | Painel principal (título, estado, fase, comporta, balizas, câmera, sensor, enquadramento e relógio UTC), ficha do corpo em foco, painel dos telescópios, painel de dados `[H]` e barra de progresso com as marcas das fases |
| 9 | Visibilidade por traçado de raio | `ray_sphere()` em três lugares: o sensor da antena até cada alvo (linha verde ou vermelha, com o obstáculo nomeado), o Sol ocultado pela Terra (o brilho some quando a estação entra na sombra) e o eclipse cilíndrico que apaga painéis e naves. O terminador dia/noite completa a iluminação binária, e o painel `[H]` anuncia o próximo eclipse |
| 10 | Créditos | `TAB`: os quatro integrantes com RA e contribuição, referências dos materiais, fontes dos dados reais com licença e o crédito da imagem de fundo em uso |

## Testes

Suíte automatizada, roda sem abrir janela e sem rede:

```bash
python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v
```

São **228 testes**. `test_ap1.py` cobre a matemática vetorial e as matrizes, o winding
das malhas, a câmera em todos os referenciais, o recorte, o frustum culling, os níveis
de detalhe e marcadores, a máquina de estados, as fases, a comporta, as balizas, a
evitação de colisão, a cabine, o lado noturno, a ficha do corpo em foco, o modo
apresentação, a ajuda e o modo avaliação. `test_sistema_solar.py` compara as efemérides
com valores do JPL Horizons e exercita o catálogo, os leitores das fontes online e o
cálculo topocêntrico da passagem da ISS. Os **quadros-ouro** comparam a assinatura visual
de cada enquadramento com `dados/assinaturas.json` (regravável por `--assinaturas`).

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
2. **Pausar** — `ESPAÇO`. O estado vira `PAUSADO`, o tempo para e a barra de progresso congela.
3. **Retomar** — `ESPAÇO`. Volta a `EXECUTANDO` do ponto exato em que parou.
4. **Alternar câmera** — `W`, `S`, `A`, `D`, `C` e `F`. Em todos os modos a estação continua enquadrada; a transição é suave.
5. **Alternar animações** — `1` a `4`. Cada tecla salta para o início da fase; confira o estado da comporta no HUD.
6. **Entrar na nave** — `Z` até o enquadramento `Cabine`. Use `W` para a cúpula (a Terra passa embaixo) e `D` para o visor da doca.
7. **Explorar o Sistema Solar** — `X` até `Sistema Solar`, `P` para percorrer os corpos e `.` para acelerar o relógio orbital. `K` senta a câmera atrás do espelho do James Webb.
8. **Concluir a sequência** — deixe chegar aos 14 s. O estado vira `CONCLUIDO` e o progresso marca 100%.
9. **Reiniciar** — `R` a qualquer momento, ou `ESPAÇO` depois de concluída.
10. **Apresentação e ajuda** — `F9` roda o roteiro sozinho; `F1` lista os comandos; `F2` mostra onde está cada requisito.
11. **Créditos** — `TAB` abre e fecha.
12. **Encerrar** — `ESC` fecha a janela.

Durante a fase 4, observe o sensor no HUD: quando um robô passa atrás do núcleo ou de um
detrito, a linha fica vermelha e o HUD nomeia o obstáculo.
