# Exercício 4 — Manipulação de câmera em uma cena 3D

**Complexidade:** intermediária-avançada

## Objetivo

Manipular a observação de uma cena por meio de uma câmera virtual simples e compreender a relação entre posição da câmera, orientação e projeção.

## Enunciado

Crie uma cena contendo o `modelo_robo.obj`, um piso e pelo menos três marcadores de referência. A câmera deve poder se aproximar, afastar e orbitar ao redor do centro da cena.

## Tarefas

1. Implemente uma estrutura de câmera com distância, ângulo horizontal, altura e ponto observado.
2. Transforme os pontos do mundo para o sistema de coordenadas da câmera.
3. Implemente uma projeção perspectiva simplificada, tratando pontos atrás da câmera.
4. Use as setas esquerda/direita para orbitar horizontalmente.
5. Use as setas para cima/baixo para alterar a altura ou o ângulo vertical.
6. Use `W` e `S` para aproximar e afastar a câmera.
7. Mostre na interface os parâmetros da câmera e uma indicação do centro observado.
8. Inclua uma tecla para restaurar a câmera ao estado inicial.

## Questões para reflexão

- Como a distância da câmera afeta o tamanho aparente do modelo?
- O que acontece com a projeção quando um ponto fica atrás da câmera?
- Qual é a diferença entre mover o objeto e mover a câmera?

## Restrições

A câmera deve ser implementada com cálculos próprios usando Python e a biblioteca padrão. O Pygame deve ser usado para janela, eventos, desenho e texto. Não usar OpenGL ou motores 3D.
