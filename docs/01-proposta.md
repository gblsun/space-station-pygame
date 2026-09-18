# Etapa 1 — Proposta da equipe

**Disciplina:** Computação Gráfica e RA/RV · **Projeto:** AP1 — Mundo Virtual Animado
**Equipe 2 · Variação temática:** Estação Espacial
**Integrantes:** Fellipe Augusto (2401525), Gabriel Muchon (2401895),
Paloma Eduarda (2401660), Victor Wenzel (2401698)

## Cenário

Uma estação orbital, a **Órbita-2**, recebe a visita programada do cargueiro de
suprimentos **Vega-7**. A cena mostra a manobra completa: aproximação, abertura da
comporta de doca, acoplamento e, depois de tudo travado, a saída de quatro robôs de
manutenção para uma volta de inspeção ao redor da estrutura.

A escolha atende diretamente às quatro animações sugeridas no enunciado para a
Equipe 2 — acoplamento de módulos, trajetória orbital de robôs, portas com estados e
alerta sequencial — e dá a cada uma delas um papel na narrativa, em vez de deixá-las
soltas na cena.

A estação é fictícia, mas **o resto não é**: ela voa numa órbita baixa física de 420 km
e 92 minutos, e tudo ao redor — Terra, Lua, planetas, satélites artificiais, asteroides e
estrelas — está na posição real do instante em que o programa roda. O usuário pode
afastar a câmera da doca até o Cinturão de Kuiper, ou aproximá-la até **entrar dentro do
módulo**.

## O que a cena contém

| Elemento | Papel |
|---|---|
| Núcleo Órbita-2 | Objeto composto: casco, colares, anel de doca, mastros, treliça de antena, radiadores, escotilhas, propulsores de atitude e dois painéis articulados |
| Cabine do núcleo | Interior habitável: casca com janelas, piso em grade, racks, corrimãos e luminárias |
| Módulo Laboratório | Segundo módulo acoplado por túnel, com cúpula de observação |
| Cargueiro Vega-7 | Objeto composto: nariz, casco, cintas, bocal, aletas e luzes de navegação |
| 4 robôs de manutenção | Quatro instâncias do mesmo tipo, com cor, escala, raio orbital, velocidade e fase diferentes; cada um tem braço de dois segmentos |
| Campo de detritos | Nove rochas geradas por ruído, em órbita relativa à estação, que bloqueiam o sensor |
| Terra e Lua | Objetos sem partes, em escala e posição reais, com dia, noite e eclipses |
| Oito planetas e cinco anões | Posições pelos elementos do JPL, com anéis em Saturno e Urano |
| 25 luas | Elementos do JPL Horizons, em travamento de maré |
| ~4.100 asteroides e cometas | Cinturão principal, troianos, Kuiper e cometas, como pontos |
| Satélites artificiais reais | ISS, Hubble, Tiangong, GOES, GPS e mais ~1.800 objetos do CelesTrak |
| James Webb | No ponto L2, a 1,5 milhão de km, pelos vetores do JPL Horizons |
| Céu estrelado | Estrelas reais do Yale Bright Star Catalogue, nas cores verdadeiras |

## Sequência

Quatro fases, catorze segundos ao todo, controladas por uma máquina de estados
(`PARADO`, `EXECUTANDO`, `PAUSADO`, `CONCLUIDO`) e disparadas apenas por teclado:

1. **Aproximação** — o cargueiro corrige a atitude enquanto se aproxima; balizas em
   alerta âmbar sequencial.
2. **Abertura da doca** — a comporta percorre a própria máquina de estados
   (`FECHADA → ABRINDO → ABERTA`) e o cargueiro freia com os retrofoguetes.
3. **Acoplamento** — o nariz encaixa no anel, a comporta fecha e as balizas passam a
   verde. De dentro da cabine, a manobra pode ser vista pelo visor da escotilha.
4. **Órbita de inspeção** — os robôs deixam os pontos de ancoragem, percorrem
   trajetórias helicoidais e desviam do mastro da antena, enquanto o sensor da estação
   testa a linha de visão até cada um.

Em paralelo corre o relógio orbital, que pode ser acelerado de tempo real até um ano por
segundo sem afetar a sequência.

## Como o projeto exercita o conteúdo da disciplina

Todo o pipeline gráfico é calculado no próprio programa, com matemática vetorial e
matrizes 3×3 escritas à mão: câmera *look-at* com base ortonormal, projeção em
perspectiva, recorte no plano próximo, *back-face culling*, *frustum culling*, ordenação
por profundidade (algoritmo do pintor), sombreamento Lambertiano com realce especular e
níveis de detalhe pelo tamanho projetado.

O teste de visibilidade exigido no requisito 9 aparece em três formas, todas com
interseção raio-esfera: o sensor da antena até cada alvo, o Sol desaparecendo atrás da
Terra e o eclipse que apaga os painéis solares.

Não são usados OpenGL, motores 3D, `numpy` nem bibliotecas de modelagem — apenas Python,
Pygame e a biblioteca padrão, como determina a restrição didática do enunciado.
