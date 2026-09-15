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

## O que a cena contém

| Elemento | Papel |
|---|---|
| Núcleo Órbita-2 | Objeto composto: casco, colares, anel de doca, dois painéis solares em grade, radiadores, treliça de antena, escotilhas e propulsores de atitude |
| Módulo Laboratório | Segundo módulo acoplado por túnel, com cúpula de observação |
| Cargueiro Vega-7 | Objeto composto: nariz, casco, cinta, bocal, aletas e luzes de navegação |
| 4 robôs de manutenção | Quatro instâncias do mesmo tipo, com cor, escala, raio orbital, velocidade e fase diferentes; cada um tem braço de dois segmentos |
| Planeta Kaltus | Objeto sem partes: uma única esfera |
| Cinturão de detritos | Nove rochas geradas por ruído, cada uma com semente própria |
| Satélite Farol-3 | Objeto de fundo em órbita alta |

## Sequência

Quatro fases, catorze segundos ao todo, controladas por uma máquina de estados
(`PARADO`, `EXECUTANDO`, `PAUSADO`, `CONCLUIDO`) e disparadas apenas por teclado:

1. **Aproximação** — o cargueiro corrige a atitude enquanto se aproxima; balizas em
   alerta âmbar sequencial.
2. **Abertura da doca** — a comporta percorre a própria máquina de estados
   (`FECHADA → ABRINDO → ABERTA`) e o cargueiro freia com os retrofoguetes.
3. **Acoplamento** — o nariz encaixa no anel, a comporta fecha e as balizas passam a
   verde.
4. **Órbita de inspeção** — os robôs deixam os pontos de ancoragem, percorrem
   trajetórias helicoidais e desviam do mastro da antena, enquanto o sensor da estação
   testa a linha de visão até cada um.

## Como o projeto exercita o conteúdo da disciplina

Todo o pipeline gráfico é calculado no próprio programa, com matemática vetorial pura:
câmera *look-at* com base ortonormal, projeção em perspectiva, recorte no plano
próximo, *back-face culling*, ordenação por profundidade (algoritmo do pintor) e
sombreamento Lambertiano com luz de preenchimento e realce especular. O teste de
visibilidade exigido no requisito 9 é uma interseção raio-esfera de verdade, disparada
do sensor da antena até cada alvo.

Não são usados OpenGL, motores 3D, `numpy` nem bibliotecas de modelagem — apenas
Python e Pygame, como determina a restrição didática do enunciado.
