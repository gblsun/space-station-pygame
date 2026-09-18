# Etapa 3 — Roteiro da apresentação

**Duração:** 5 a 8 minutos, com participação dos quatro integrantes.
**Formato:** aplicação em tela cheia (`F11` ou `--tela-cheia`), com um integrante no
teclado e os outros narrando.

> **Para a equipe:** os tempos são uma sugestão de ritmo. Ensaiem uma vez com cronômetro;
> o bloco 4 costuma ser o primeiro a estourar.

## Antes de começar

- Abrir com internet pelo menos uma vez antes da apresentação: as imagens do Webb e do
  Hubble, a agenda do telescópio e os elementos dos satélites ficam em cache e continuam
  disponíveis mesmo se a rede da sala falhar.
- Rodar `python "Atividade AP1/ap1.py" --tela-cheia` e deixar no estado `PARADO`.
- Ter um terminal à parte com a suíte já executada, para mostrar o resultado.
- Combinar quem opera o teclado, para não haver duas pessoas disputando.

## Opção A — modo apresentação (`F9`)

A tecla `F9` roda um roteiro de doze passos com legendas, que passa por tudo o que
interessa sem ninguém no teclado. É a opção segura: a equipe narra por cima, e qualquer
tecla devolve o controle na hora. Use os blocos abaixo como guia da narração.

## Opção B — condução manual

### Bloco 1 · Abertura e cenário — 1 min — *Fellipe (coordenação)*

- Apresentar a equipe e a variação: Equipe 2, Estação Espacial.
- Explicar o cenário em uma frase: a estação Órbita-2 recebe o cargueiro Vega-7 e,
  depois do acoplamento, os robôs saem para inspecionar.
- Dizer o que está na tela: a estação, a Terra passando embaixo, o cargueiro à direita.
- Fechar com: "tudo isso é Python e Pygame puros, sem OpenGL nem motor 3D — e o que está
  ao redor da estação é o Sistema Solar real, na posição de agora".

### Bloco 2 · Modelagem e composição — 1 min 30 — *Gabriel (modelagem)*

- `H` abre o painel de dados: contagem de faces, marcadores, pontos e FPS medido.
- `N` liga os rótulos: percorrer o requisito 3 apontando na tela — os **quatro robôs**
  como instâncias do mesmo tipo com parâmetros diferentes, a **Terra** e a **Lua** como
  objetos sem partes, e o **núcleo** como objeto composto.
- `Z` até `Cabine`: **entrar dentro da nave**. `W` mostra a cúpula com a Terra passando
  embaixo; `C` mostra o corredor com racks e corrimãos. Explicar o truque: as janelas são
  ausência de face, e o casco visto de dentro cai no back-face culling.
- Explicar que a geometria é procedural: caixas, prismas, treliças, painéis em grade e
  antenas, montados por código.

### Bloco 3 · Animação e estados — 1 min 30 — *Paloma (animação)*

- `Z`/`X` de volta para `Doca` e `ESPAÇO` para iniciar. Narrar as fases.
- Na fase 2, a comporta: ela tem **máquina de estados própria**, aninhada na principal.
  É a "animação composta por estados" do requisito 6.
- Pausar com `ESPAÇO` no meio da fase 3, mostrar que o HUD congela junto, e retomar —
  mas notar que **o Sistema Solar continua correndo**: são dois relógios.
- `1` a `4` para saltar entre fases e mostrar que o estado é reconstruído em qualquer ponto.
- Mencionar a hierarquia por matrizes: estação → robô → braço → antebraço.

### Bloco 4 · Câmera, escala real e visibilidade — 1 min 30 — *Victor (câmera e interface)*

- `C`, `W`, `S`, `A`, `D` e `F` — o foco animado que acompanha o cargueiro.
- `X` subindo a escala: órbita baixa (o terminador e as luzes das cidades), Terra e
  satélites (ISS, GNSS, geoestacionários e Starlink reais), Terra-Lua-L2, Sistema Solar.
- `P` para focar um corpo: a ficha mostra raio, massa, gravidade, rotação, distância e
  velocidade **calculadas no instante**.
- `.` acelera o relógio orbital e mostra os planetas andando.
- Voltar à fase 4 e esperar uma linha do sensor ficar **vermelha**: interseção
  raio-esfera de verdade, com o obstáculo nomeado no HUD.
- `V` mostra o fundo com a imagem mais recente do James Webb, e o painel diz o que ele
  está observando agora, pela agenda oficial do STScI.
- `K` senta a câmera atrás do espelho do Webb, apontada para esse mesmo alvo.
- `H` mostra, junto dos dados de pipeline, o próximo eclipse e a próxima passagem da ISS
  sobre a cidade configurada.

### Bloco 5 · Conteúdos da disciplina aplicados — 1 min — *rodízio entre os quatro*

Cada integrante assume um item e fala em uma ou duas frases:

| Conteúdo | Onde aparece |
|---|---|
| Câmera look-at e transformação de visualização | Base ortonormal reconstruída a cada quadro, interpolada no referencial da âncora |
| Projeção em perspectiva e recorte | Distância focal, plano próximo ajustável e recorte 2D na borda |
| Oclusão e visibilidade | Back-face culling, frustum culling e algoritmo do pintor |
| Iluminação e sombreamento | Lambert, preenchimento, Blinn-Phong, luz de bordo e lado noturno |
| Traçado de raio | Sensor da antena, Sol oculto pela Terra e eclipse |
| Instanciação e hierarquia | Robôs, constelação GPS e juntas solares compostas por matrizes |
| Níveis de detalhe | Marcadores, LOD por tamanho projetado e calota do horizonte |

### Bloco 6 · Testes e encerramento — 30 s — *Fellipe*

- `F2` mostra onde está cada requisito obrigatório, com etiquetas na própria cena.
- No terminal, os **228 testes** passando e a saída do `--bench`.
- Dizer o número: em 1080x720 o quadro fica entre 8 e 17 ms, dentro dos 16,7 ms de 60 FPS.
- `ESC` encerra.

## Perguntas prováveis e respostas curtas

**"Por que o algoritmo do pintor e não z-buffer?"**
Um z-buffer por pixel em Python puro não fecharia o orçamento de 60 FPS. O pintor,
combinado com back-face culling e profundidade medida em espaço de câmera, resolve a
cena corretamente salvo em interpenetrações, que a composição evita.

**"As cores dos planetas não são textura?"**
Não. É **uma cor por face**, amostrada de um mapa uma única vez na construção da malha.
O sombreamento continua plano, calculado por face em Python.

**"Usar dados da internet não é biblioteca externa?"**
O download usa `urllib`, da biblioteca padrão, em thread. E a aplicação não depende
dele: os dados reais estão versionados em `dados/`, e há o modo `--offline`.

**"Como vocês sabem que as posições estão certas?"**
Comparando com o JPL Horizons. Os testes automatizados verificam Terra, Marte, Júpiter,
Netuno e Lua contra valores de referência, com tolerância de centésimos de grau.

**"Dá para navegar pela cena?"**
Não, e é proposital: o enunciado pede comandos discretos de teclado. Todos os
enquadramentos — inclusive entrar na nave — são teclas, não movimento livre.
