# Etapa 2 — Decisões técnicas, dificuldades e divisão de tarefas

> **Para a equipe:** os trechos marcados com **[CONFIRMAR]** descrevem fatos sobre o
> trabalho de vocês e precisam ser revistos antes da entrega. O restante descreve
> decisões que estão no código e podem ser conferidas linha a linha.

## 1. Decisões técnicas

### 1.1 Câmera look-at ancorada, interpolada no referencial da âncora

A câmera mantém olho e alvo e reconstrói a base ortonormal `(right, up, forward)` a cada
quadro, tratando o caso degenerado de olhar reto para cima ou para baixo.

O que ela guarda, porém, não é a posição absoluta: é o **deslocamento em relação à
âncora, no referencial da âncora**. A estação viaja a 7,7 km/s em torno da Terra, que
viaja a 30 km/s em torno do Sol; interpolar em coordenadas de mundo deixava a câmera
para trás, e interpolar fora do referencial LVLH fazia o horizonte oscilar. Guardando o
deslocamento local, a transição continua suave e a pose fica estável.

Entre a doca (40 m) e o Cinturão de Kuiper (190 UA) há treze ordens de grandeza. Uma
interpolação linear percorreria quase tudo no primeiro quadro e rastejaria no resto, por
isso o comprimento do deslocamento é interpolado **em escala logarítmica**: cada quadro
percorre a mesma fração de ordens de grandeza, e a viagem de zoom fica visível.

### 1.2 Profundidade medida no espaço de câmera

O algoritmo do pintor ordenava as faces pelo **Z de mundo**, o que só equivale à
profundidade real quando a câmera olha na direção do eixo Z. Hoje a ordenação usa a
profundidade em espaço de câmera, calculada durante a própria transformação.

### 1.3 Recorte no plano próximo

As faces são recortadas contra o plano `z = NEAR` com Sutherland-Hodgman de um plano só.
Para não pagar o teste em toda face, o recorte é verificado por malha (se o vértice mais
próximo já está à frente do plano, nenhuma face precisa ser testada) e, dentro da malha,
as faces inteiramente atrás do olho são descartadas antes de qualquer conta de normal.

O `NEAR` é ajustável: 8 unidades (1,6 m) fora e 2 unidades (40 cm) dentro da cabine,
senão o rack ao lado da câmera desaparece.

### 1.4 Sombreamento, luz de bordo e lado noturno

Sombreamento Lambertiano plano com quatro contribuições: ambiente, difusa do Sol, uma
luz de preenchimento vinda da Terra e um realce especular Blinn-Phong. O brilho é
propriedade de cada malha, então rocha e painel ficam foscos e o casco metálico brilha.

Duas exceções foram necessárias:

- **Dentro da cabine**, a luz não vem do Sol. A malha do interior tem `luz_local` (a
  direção das luminárias, presa ao referencial da estação) e ambiente próprio, alto.
- **No lado escuro da Terra**, cada face tem uma **segunda cor**, amostrada do mapa
  noturno. A face escolhe entre dia e noite pelo cosseno da incidência, com mistura
  contínua na faixa do terminador para a linha não serrilhar.

> **Sobre o §9 do enunciado.** O texto exclui "iluminação realista, texturas complexas e
> shaders". O realce especular aqui é Blinn-Phong clássico, calculado em Python por face,
> sem GPU, sem textura e sem shader. As cores vindas dos mapas também não são textura: é
> **uma cor por face**, amostrada uma única vez na construção da malha — o mesmo
> sombreamento plano de sempre, com a cor escolhida pela direção.

### 1.5 Visibilidade por traçado de raio, em três lugares

O requisito 9 é atendido por interseção raio-esfera de verdade (`ray_sphere`):

1. **Sensor da antena** (`Scene.line_of_sight`): dispara um raio até cada alvo e testa
   contra as esferas envolventes dos detritos e do núcleo. Linha verde quando livre,
   vermelha com marcador no ponto de impacto quando bloqueada, e o HUD nomeia o obstáculo.
2. **Sol atrás da Terra** (`Renderer.sun_visible`): o brilho do Sol só é desenhado se a
   linha de visão do olho até ele não atravessar o planeta.
3. **Eclipse** (`efemerides.na_sombra_da_terra`): sombra cilíndrica com penumbra na
   borda, limitada a 1,4 milhão de km — o comprimento real da umbra. É ela que apaga os
   painéis e as naves quando entram na sombra da Terra.

### 1.6 Hierarquia por matrizes

A cena tem cadeias de até quatro níveis: estação → robô → braço → antebraço, e
estação → mastro → junta → painel. A versão anterior evitava multiplicar matrizes
escolhendo os canais de Euler com cuidado; com juntas em eixos arbitrários isso deixou
de funcionar.

Hoje `PolyMesh` aceita uma **base ortonormal** no lugar dos ângulos, e a composição
pai → filho é `mat_mul(base_pai, rotação_da_junta)`. A rotação de junta usa a fórmula de
Rodrigues, e há teste garantindo que ela dá exatamente o mesmo sentido de `rotate_xyz`
nos eixos coordenados.

### 1.7 Escala real, marcadores e níveis de detalhe

A cena é heliocêntrica e **em escala real**: 1 unidade = 0,2 m, a estação tem ~100 m, a
Terra 6.371 km e Netuno fica a 30 UA. Em ponto flutuante duplo isso sobra: a 50 UA, um
passo de arredondamento ainda é menor que um milímetro, e toda projeção trabalha com
diferenças até a câmera.

O preço é que quase tudo fica menor que um pixel. Três mecanismos resolvem:

| Mecanismo | O que faz |
|---|---|
| **Marcadores** | Malha com raio projetado menor que 1,5 px vira um ponto colorido com nome, em vez de geometria |
| **Níveis de detalhe** | Cada corpo tem malhas de 6×10 a 36×68, escolhidas pelo tamanho na tela e construídas só quando usadas |
| **Calota do horizonte** | Perto de um planeta, a esfera é trocada por uma calota que cobre só o que a câmera enxerga |

A calota merece detalhe: da órbita baixa apenas 3% da Terra aparece. Uma esfera inteira
gastaria o orçamento transformando o lado oculto, e metade das faces cairia atrás da
câmera. A calota é construída em torno do ponto sob a câmera, até o ângulo do horizonte,
com os anéis se apertando perto do limbo, e **limitada à janela que a câmera enxerga**:
o setor de azimute do olhar e o trecho a partir do raio mais baixo do quadro. Ela é
refeita só quando o ponto sob a câmera anda uma fração de célula ou o olhar gira.

### 1.8 Efemérides: onde cada corpo está

| Corpo | Modelo |
|---|---|
| Planetas | Elementos keplerianos médios do JPL (*Approximate Positions of the Planets*), com taxas seculares |
| Lua | Fórmula de baixa precisão do *Astronomical Almanac* (série de senos), com a precessão desfeita para J2000 |
| Luas, anões, asteroides e cometas | Elementos osculadores do JPL Horizons, propagados como problema de dois corpos |
| Satélites artificiais | Elementos médios do CelesTrak (formato OMM) com as derivas seculares do J2 no nó, no perigeu e na anomalia média |
| James Webb | Vetores diários do JPL Horizons, interpolados; sem tabela, cai numa aproximação do ponto L2 |

Precisão medida contra o próprio Horizons, em 2026-09-15:

| Corpo | Erro angular | Erro de distância |
|---|---|---|
| Terra | 0,003° | 0,002% |
| Marte | 0,008° | 0,007% |
| Netuno | 0,009° | 0,003% |
| Júpiter | 0,02° | 0,04% |
| Lua | 0,07° | 630 km |
| ISS (na época dos elementos) | — | ~10 km |

O CelesTrak publica os elementos no equador verdadeiro da data (TEME). Ignorar a
precessão desde J2000 custava de 36 a 49 km na posição da ISS; desfazê-la com uma
rotação em longitude eclíptica derruba o erro para ~10 km. O que sobra é a diferença
entre a nossa propagação e o SGP4 completo, e cresce com a idade dos elementos.

### 1.9 A Órbita-2 é fictícia, mas a órbita dela não é

A estação voa a 420 km, com 51,6° de inclinação e período de 92,9 minutos, em atitude
**LVLH**: X ao longo da velocidade, Y para o zênite, mais uma arfagem fixa de 32°. É essa
arfagem que põe a Terra atrás e abaixo da estação no plano geral — sem ela, o horizonte
cairia atrás do rodapé do HUD, porque a 420 km o disco da Terra tem 70° de raio angular.

Como a estação não existe, a fase e o nó da órbita são **escolhidos** na criação da cena:
entre algumas dezenas de combinações, a que começa à luz do Sol, continua iluminada por
25 minutos e deixa o Sol do lado da câmera. É determinístico para o mesmo instante, e
evita abrir o programa dentro de um eclipse.

### 1.10 O interior: o zoom entra na nave

O enquadramento mais interno põe a câmera dentro do módulo. A casca interna é construída
com as normais para dentro, e as **janelas são a ausência de face**: onde não há face na
casca, o casco externo — que está de costas para a câmera e cai no back-face culling —
deixa o espaço aparecer. Não há geometria de vidro, nem custo, nem transparência.

Duas consequências resolvidas: o casco externo é escondido enquanto a câmera está
dentro (todas as faces dele seriam descartadas de qualquer jeito, e são mil por quadro),
e o piso para antes da cúpula, senão o deck taparia justamente a janela do nadir.

### 1.10b Efeitos que saem de graça das efemérides

Com as posições reais já calculadas, alguns efeitos custam quase nada e explicam muito:

- **Rastro no solo e terminador**: a órbita projetada na superfície, no referencial do
  planeta, e o grande círculo perpendicular à direção do Sol. O rastro fica em cache e é
  refeito a cada meio minuto de tempo simulado — recalculá-lo por quadro custava 6 ms.
- **Caudas de cometa**: direção anti-solar e comprimento proporcional a 1/r², o que faz a
  cauda crescer quando o cometa se aproxima.
- **Troianos em L4 e L5**: os dois pontos a 60° de Júpiter, que explicam por que há duas
  nuvens paradas ao lado do planeta no cinturão do SBDB.
- **Próximo eclipse**: busca em dois estágios — uma varredura de seis em seis horas acha
  as luas novas e cheias, e cada candidata é refinada de dez em dez minutos. Um estágio só
  não serve: a janela do eclipse dura poucas horas e o passo grosso passa por cima. A
  busca acerta o eclipse anular de 6 de fevereiro de 2027 às 15:59 UTC e o total de
  2 de agosto de 2027 às 10:19 UTC.
- **Passagem da ISS**: elevação topocêntrica sobre uma cidade configurável
  (`LOCAL_OBSERVADOR`), varrendo 48 horas em passos de 30 segundos.

### 1.10c O olho do telescópio

A tecla `K` põe a câmera atrás do espelho do James Webb ou do Hubble, olhando para onde a
nave realmente aponta. No caso do Webb, o nome do alvo vem da agenda do STScI e é
resolvido em coordenadas pelo Sesame do CDS; a atitude mantém o escudo solar de frente
para o Sol — a restrição real da nave — e usa o grau de liberdade que sobra para chegar o
mais perto possível do alvo.

### 1.11 Rede em thread, cache e snapshots

Dados que envelhecem — elementos dos satélites, vetores do James Webb, agenda do James
Webb e as imagens mais recentes do Webb e do Hubble — são buscados em **thread**, nunca
no laço principal. A aplicação consulta o resultado uma vez por quadro; uma falha vira
estado, não exceção.

Há três camadas de proteção: o **snapshot** versionado em `dados/`, com que a cena
sempre começa; o **cache em disco**, fora do repositório, que devolve conteúdo vencido
quando a rede cai; e o modo `--offline`. Os testes e o CI nunca tocam na rede.

### 1.12 Tela cheia e HUD escalável

`configurar_viewport` refaz projeção, centro óptico e planos do tronco de visão quando a
superfície muda de tamanho, e a distância focal acompanha a altura: o enquadramento
vertical é o mesmo em qualquer resolução, e uma tela mais larga ganha campo nas laterais.
A tela cheia usa a resolução nativa do monitor, e no Windows o processo se declara ciente
de DPI — sem isso, o sistema amplia a janela e tudo sai borrado.

O HUD é escrito em unidades de projeto (a janela de referência de 1080×720) e
multiplicado por uma escala na hora de desenhar, com as fontes rasterizadas no tamanho
final. Em 4K o painel cresce junto com a tela em vez de virar um selo no canto.

### 1.13 Desempenho

O orçamento a 60 FPS é 16,7 ms. Medições em 1080×720, com a sequência rodando:

| Enquadramento | Mediana em 1080×720 |
|---|---|
| Terra, Lua e L2 | 4 ms |
| Terra e satélites | 9 ms |
| Órbita baixa | 10 ms |
| Sistema interno, Sistema Solar e Kuiper | 12 a 13 ms |
| Vizinhança (3 km) | 15 ms |
| Cabine | 18 ms |
| Estação | 19 ms |
| Doca, com os retrofoguetes acesos | 22 ms |

As vistas de acoplamento são as mais densas — a estação inteira em primeiro plano e a
calota da Terra ocupando o fundo — e ficam entre 45 e 55 FPS. Em 1920×1080 o custo sobe
cerca de 20%. O `--bench` aceita `--res` e `--max-ms`, e o CI falha quando a mediana
passa do limite. As decisões que mais renderam:

| Medida | Efeito |
|---|---|
| Frustum culling por esfera envolvente | Descarta a malha antes de transformar qualquer vértice |
| Marcadores abaixo de 1,5 px | A maior parte da cena, em escala real, nunca vira polígono |
| Calota do horizonte limitada à janela da câmera | Terra de 1.512 para ~500 faces, todas visíveis |
| Casco externo escondido dentro da cabine | Mil faces por quadro que só seriam descartadas |
| Nuvens de pontos propagadas em lotes, em rodízio | 4.100 asteroides e 1.800 satélites sem estourar o quadro |
| Detalhe e atitude só perto da câmera | 31 satélites GPS invisíveis não pagam atitude nem juntas |
| Cache de vértices por comparação de pose | Evita recalcular objetos parados |
| Cache das superfícies de texto do HUD | A interface caiu de 2,4 ms para cerca de 0,3 ms |
| Lista de alvos da tecla P em cache | Era remontada 44 vezes por quadro, uma por nave |
| Halos como sprites pré-renderizados, com teto de raio | Sem o teto, uma faísca perto da câmera pedia um brilho do tamanho da tela |
| Traçados de órbita filtrados por contexto | Perto da estação, nenhuma linha heliocêntrica cruza o céu |

### 1.13b Quadros-ouro

Alguns defeitos passam por todos os testes numéricos e só aparecem na tela: uma malha que
sumiu, uma cor que virou preta, a câmera apontando para o lado. Por isso cada
enquadramento é renderizado em data fixa, sem HUD, e reduzido a uma assinatura de 96
blocos quantizados, comparada com `dados/assinaturas.json`. A tolerância é folgada de
propósito: versões diferentes do SDL rasterizam com um pixel de diferença.

Foi esse teste que revelou uma dependência de ordem antiga na suíte: um teste restaurava
`DETAIL` para 1.0 em vez do valor da cena, e todas as malhas construídas depois ficavam
mais finas. Hoje cada teste fixa e devolve o que precisa.

### 1.14 Testabilidade

`ap1.py` não inicializa o Pygame ao ser importado: a janela só é criada dentro de
`main()`. `efemerides.py` e `catalogo.py` não importam pygame; a `Scene` só o usa para
ler os mapas de cor. `Renderer` desenha em qualquer `Surface`. Por isso os 228 testes
rodam sem abrir janela e sem rede.

## 2. Dificuldades encontradas

1. **A câmera não orientava.** Diagnosticada capturando quadros fora da tela e comparando
   os cinco modos: quatro deles não enquadravam a cena.
2. **Ordem de desenho errada nas vistas laterais**, pela profundidade medida no eixo errado.
3. **`random.seed()` global** dentro do construtor de asteroides contaminava as partículas
   e o campo estelar. Hoje cada malha usa seu próprio `random.Random`.
4. **8 GB de memória** nos halos, antes do teto de raio e do cache com orçamento.
5. **O mundo saía espelhado.** A câmera do motor tem `right × up = forward`, que é
   convenção de mão esquerda na tela: uma cena destra apareceria invertida, com as
   constelações trocadas e os planetas girando ao contrário. A ponte entre a eclíptica e
   o motor aplica uma reflexão que compensa isso, e há teste conferindo que a Terra
   percorre a órbita no sentido anti-horário vista do norte.
6. **45 km de erro na ISS**, por ignorar a precessão do referencial TEME. Só ficou claro
   ao comparar na própria época dos elementos, onde a propagação não tem erro: o
   referencial respondia por 40 km, e a propagação pelo resto.
7. **A Terra cobrindo a tela inteira.** Com a arfagem de 57° que tínhamos escolhido, o
   horizonte saía fora do quadro — a 420 km o disco da Terra tem 70° de raio angular, e
   não os 20° que a intuição sugere.
8. **Metade da calota atrás da câmera.** A primeira versão cobria 360° de azimute: 415
   faces por quadro eram recortadas contra o plano próximo para nada, e o quadro passava
   de 29 ms. Limitar a calota à janela do olhar resolveu.
9. **A escotilha tapada.** O aro da escotilha era um prisma, e a tampa do prisma fechava
   justamente o vão por onde se vê a doca. Virou um anel chapado.
10. **As luzes das cidades sumindo.** Amostrar o mapa noturno em pontos soltos quase nunca
    acerta as cidades, que ocupam 0,5% do mapa. A solução foi reduzir o mapa uma vez com
    média de blocos e amplificar o que sobra, cortando o fundo para o oceano continuar escuro.
11. **Órbitas cruzando o céu da doca.** Vista de dentro, a órbita de Vênus é um arco que
    corta a tela. Os traçados passaram a depender do enquadramento.
12. **[CONFIRMAR]** Dificuldades de organização da equipe, prazos ou ferramentas que
    valham registro.

## 3. Divisão de tarefas

Papéis conforme o §4 do enunciado. **[CONFIRMAR]** — ajustem a coluna da direita para o
que cada um realmente fez, já que na apresentação cada integrante precisa saber explicar
a própria contribuição.

| Integrante | Papel | Contribuição |
|---|---|---|
| Fellipe Augusto (2401525) | Coordenação e integração | **[CONFIRMAR]** |
| Gabriel Muchon (2401895) | Modelagem e composição da cena | **[CONFIRMAR]** |
| Paloma Eduarda (2401660) | Animação e máquinas de estado | **[CONFIRMAR]** |
| Victor Wenzel (2401698) | Câmera, interface e testes | **[CONFIRMAR]** |

> **Atenção:** o histórico do repositório registra commits de poucos autores. O checklist
> do §8 pede que os quatro integrantes estejam identificados e consigam explicar sua
> contribuição — vale distribuir commits reais antes da entrega.
