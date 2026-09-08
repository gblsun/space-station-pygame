# Exercício 5 — Cena interativa com OBJ, transformações e câmera

**Complexidade:** avançada

## Objetivo

Integrar carregamento de modelos, composição de cena, transformações, manipulação de câmera e interface de controle em uma única aplicação.

## Enunciado

Desenvolva uma pequena galeria virtual que carregue `modelo_torre.obj` e `modelo_robo.obj`. A galeria deve permitir alternar o modelo selecionado, modificar suas transformações e observar a cena por diferentes posições de câmera.

## Tarefas

1. Implemente um carregador OBJ que leia vértices e faces.
2. Projete faces ou arestas dos modelos em uma janela Pygame.
3. Crie uma cena com piso, molduras ou pedestais e pelo menos uma instância de cada modelo.
4. Permita selecionar uma instância e alterar translação, escala e rotação.
5. Permita controlar a câmera com órbita, altura e zoom.
6. Crie um painel de controle com modelo selecionado, transformações e parâmetros da câmera.
7. Inclua uma opção de reset da instância e outra de reset da câmera.
8. Defina uma regra de ordenação das faces ou arestas para reduzir sobreposição visual e explique sua escolha.
9. Registre no código quais partes correspondem a modelo, transformação, cena, câmera, entrada e interface.

## Requisitos de entrega

- Código-fonte principal.
- Os dois arquivos OBJ utilizados.
- Uma descrição curta da arquitetura da aplicação.
- Duas capturas de tela com câmeras diferentes.
- Respostas às questões de reflexão dos exercícios anteriores, adaptadas ao projeto.

## Restrições

O projeto deve permanecer limitado ao conteúdo até a Aula 9: representação de objetos, transformações, criação e instanciação, eventos, interação e interface básica. Não incluir animação, física, iluminação avançada, texturas, shaders, OpenGL ou bibliotecas de cena 3D.
