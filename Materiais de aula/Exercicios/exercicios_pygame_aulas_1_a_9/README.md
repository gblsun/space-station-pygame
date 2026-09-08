# Exercícios práticos — Modelos, transformações, cenas e câmera

Material complementar limitado aos conteúdos trabalhados até a Aula 9.

## Escopo didático

Os exercícios usam apenas conceitos de aplicações 2D/3D, representação de objetos, modelos poliédricos simples, transformações geométricas, criação e instanciação de objetos, interação por teclado/mouse e interface visual. A câmera é tratada de forma introdutória, como uma posição/orientação de observação e uma projeção perspectiva simplificada para exibição em uma janela 2D.

Não são usados OpenGL, PyOpenGL, motores 3D, iluminação avançada, texturas, animação, física, shaders ou bibliotecas externas de carregamento de modelos.

## Arquivos

- `exercicio_01_pontos_e_eixos.md` — modelo elementar e sistema de coordenadas.
- `exercicio_02_transformacoes_3d.md` — translação, escala e rotação.
- `exercicio_03_cena_instanciada.md` — composição de uma cena com instâncias.
- `exercicio_04_camera_orbitante.md` — manipulação de câmera por teclado.
- `exercicio_05_cena_interativa_obj.md` — cena integrada com carregamento de OBJ e painel de controle.
- `modelo_torre.obj` — modelo poliédrico simples para os exercícios 3 e 5.
- `modelo_robo.obj` — modelo poliédrico simples para os exercícios 4 e 5.
- `carregar_torre_pygame.py` — exemplo de leitura e projeção de OBJ com Python + Pygame.
- `carregar_robo_pygame.py` — exemplo de leitura e projeção de OBJ com Python + Pygame.

## Execução dos exemplos

Instale o Pygame no ambiente da disciplina e execute, na mesma pasta:

```bash
python carregar_torre_pygame.py
python carregar_robo_pygame.py
```

Os exemplos são referências de infraestrutura para leitura do formato OBJ e visualização em estrutura de arame. Eles não implementam os exercícios nem fornecem respostas para as tarefas propostas.

## Formato OBJ utilizado

Os modelos contêm apenas vértices (`v`) e faces poligonais (`f`). Não dependem de materiais, texturas, normais ou arquivos auxiliares. O carregador considera os índices de vértices das faces e triangula faces com mais de três vértices por um leque simples.

## Observação sobre o limite da Aula 9

Os exercícios não exigem animação, que aparece posteriormente no planejamento. A interação solicitada restringe-se a eventos, estados, transformações, câmera, objetos e elementos básicos de interface.
