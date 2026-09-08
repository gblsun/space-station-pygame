# Exercício 3 — Criação e instanciação de uma cena

**Complexidade:** intermediária

## Objetivo

Construir uma cena composta por várias instâncias de um mesmo modelo, aplicando transformações diferentes a cada objeto.

## Enunciado

Use o arquivo `modelo_torre.obj` como referência para criar uma praça virtual com, no mínimo, cinco torres. As torres devem compartilhar a mesma geometria, mas possuir transformações e cores de representação diferentes.

## Tarefas

1. Carregue ou replique a geometria do modelo de torre.
2. Crie uma estrutura de dados para representar cada instância com posição, escala, rotação e cor.
3. Organize as torres em uma cena com pelo menos dois planos de profundidade.
4. Desenhe um piso e um eixo de referência para indicar a orientação da cena.
5. Permita selecionar uma instância pelo teclado e alterar sua posição ou escala.
6. Apresente na interface o índice da instância selecionada e seus parâmetros.
7. Diferencie visualmente objetos mais próximos e mais distantes usando uma regra simples definida pelo estudante.

## Critérios

- Geometria compartilhada entre as instâncias.
- Transformações independentes por objeto.
- Organização legível da cena.
- Interação coerente com os eventos do Pygame.
- Ausência de dependências 3D externas.

## Observação

Não é necessário implementar colisão, iluminação, textura ou animação. O foco está em modelos, transformações, instanciação, cena e interface básica.
