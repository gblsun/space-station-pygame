# Etapa 3 — Roteiro da apresentação

**Duração:** 5 a 8 minutos, com participação dos quatro integrantes.
**Formato sugerido:** aplicação aberta em tela cheia, trocando de quem fala a cada bloco.

> **Para a equipe:** os tempos são uma sugestão de ritmo. Ensaiem uma vez com
> cronômetro; o bloco 5 costuma ser o primeiro a estourar.

## Antes de começar

- Rodar `python "Atividade AP1/ap1.py"` e deixar a janela aberta no estado `PARADO`.
- Ter um terminal à parte com a suíte já executada, para mostrar o resultado.
- Combinar quem opera o teclado, para não haver duas pessoas disputando.

## Bloco 1 · Abertura e cenário — 1 min — *Fellipe (coordenação)*

- Apresentar a equipe e a variação: Equipe 2, Estação Espacial.
- Explicar o cenário em uma frase: a estação Órbita-2 recebe o cargueiro Vega-7 e,
  depois do acoplamento, os robôs saem para inspecionar.
- Dizer o que está na tela sem rodar nada ainda: núcleo, laboratório, painéis solares,
  cargueiro à direita, cinturão de detritos, planeta ao fundo.
- Fechar com: "tudo isso é Python e Pygame puros, sem OpenGL nem motor 3D".

## Bloco 2 · Modelagem e composição — 1 min 30 — *Gabriel (modelagem)*

- Apertar `H` para abrir o painel de dados e mostrar a contagem de faces.
- Percorrer o requisito 3 apontando na tela: os **quatro robôs** como instâncias do
  mesmo tipo com parâmetros diferentes, o **planeta** como objeto sem partes e o
  **núcleo** como objeto composto.
- Mostrar `A` e `D` para dar a leitura de profundidade da estrutura.
- Explicar que a geometria é procedural: o `MeshBuilder` monta caixas, prismas,
  treliças, painéis em grade e antenas, e cada detrito nasce de uma semente própria.

## Bloco 3 · Animação e estados — 1 min 30 — *Paloma (animação)*

- `ESPAÇO` para iniciar. Narrar as fases enquanto acontecem.
- Na fase 2, chamar atenção para a comporta: ela tem **máquina de estados própria**,
  aninhada na principal. É a "animação composta por estados" do requisito 6.
- Pausar com `ESPAÇO` no meio da fase 3, mostrar que o HUD congela junto, e retomar.
- Usar `1` a `4` para saltar entre fases e mostrar que o estado é reconstruído
  corretamente em qualquer ponto.
- Mencionar a hierarquia: estação → robô → braço → antebraço.

## Bloco 4 · Câmera, interface e visibilidade — 1 min 30 — *Victor (câmera e interface)*

- Passar por `C`, `W`, `S`, `A`, `D` e terminar em `F`, o **foco animado** que
  acompanha o cargueiro — exatamente o que o requisito 5 pede.
- Apontar que a troca é interpolada, não é corte seco.
- Mostrar o HUD: título, estado, fase, comporta, balizas, câmera, sensor, comandos e a
  barra de progresso com as marcas de troca de fase.
- Ir para a fase 4 e esperar uma linha do sensor ficar **vermelha**: explicar que é
  interseção raio-esfera de verdade e que o HUD nomeia o obstáculo.
- `TAB` para os créditos.

## Bloco 5 · Conteúdos da disciplina aplicados — 1 min 30 — *rodízio entre os quatro*

Cada integrante assume um item e fala em uma ou duas frases:

| Conteúdo | Onde aparece |
|---|---|
| Câmera look-at e transformação de visualização | Base ortonormal reconstruída a cada quadro |
| Projeção em perspectiva e recorte | Distância focal e plano próximo |
| Oclusão e visibilidade | Back-face culling e algoritmo do pintor |
| Iluminação e sombreamento | Lambert, luz de preenchimento e realce especular |
| Traçado de raio | Interseção raio-esfera para a linha de visão |
| Instanciação e hierarquia | Quatro robôs paramétricos, cadeia de três níveis |

## Bloco 6 · Testes e encerramento — 30 s — *Fellipe*

- Mostrar no terminal a suíte com todos os testes passando e a saída do `--bench`.
- Dizer o número: o quadro fica em torno de 11,5 ms, dentro dos 16,7 ms de 60 FPS.
- Encerrar a aplicação com `ESC`, fechando o roteiro do checklist.

## Perguntas prováveis e respostas curtas

**"Por que o algoritmo do pintor e não z-buffer?"**
Um z-buffer por pixel em Python puro não fecharia o orçamento de 60 FPS. O pintor,
combinado com back-face culling e profundidade medida em espaço de câmera, resolve a
cena corretamente salvo em interpenetrações, que a composição evita.

**"O realce especular não é iluminação realista, que o enunciado exclui?"**
É o modelo Blinn-Phong clássico, calculado por face em Python, sem GPU, textura ou
shader. É conteúdo de sombreamento da disciplina, não iluminação baseada em física.
A justificativa completa está em [03-decisoes-tecnicas.md](03-decisoes-tecnicas.md).

**"Como vocês garantem que pausar e reiniciar não quebram a cena?"**
A pose de cada objeto é função pura do tempo de simulação, e há teste automatizado
verificando que `reset()` devolve exatamente as poses iniciais.

**"Dá para navegar pela cena?"**
Não, e é proposital: o enunciado pede comandos discretos de teclado, sem navegação
livre nem controle contínuo.
