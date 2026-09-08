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
