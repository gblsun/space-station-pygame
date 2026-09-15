# Etapa 2 — Decisões técnicas, dificuldades e divisão de tarefas

> **Para a equipe:** os trechos marcados com **[CONFIRMAR]** descrevem fatos sobre o
> trabalho de vocês e precisam ser revistos antes da entrega. O restante descreve
> decisões que estão no código e podem ser conferidas linha a linha.

## 1. Decisões técnicas

### 1.1 Câmera *look-at* em vez de deslocamento do olho

A primeira versão projetava os pontos apenas subtraindo a posição da câmera, sem
nenhuma orientação. O efeito era que só a vista frontal funcionava: no flanco esquerdo
a cena inteira saía de quadro. A câmera atual mantém olho e alvo, constrói a base
ortonormal `(right, up, forward)` a cada quadro e trata o caso degenerado de olhar
exatamente para cima ou para baixo, trocando o vetor de referência.

### 1.2 Profundidade medida no espaço de câmera

O algoritmo do pintor ordenava as faces pelo **Z de mundo**, o que só é equivalente à
profundidade real quando a câmera olha na direção do eixo Z. Em qualquer vista lateral
a ordem de desenho saía errada. Hoje a ordenação usa a profundidade em espaço de
câmera, calculada durante a própria transformação.

### 1.3 Recorte no plano próximo

Em vez de forçar `z` a um mínimo — o que deforma o polígono —, as faces são recortadas
contra o plano `z = NEAR` com Sutherland-Hodgman de um plano só. Para não pagar o teste
em toda face, o recorte é verificado por malha: se o vértice mais próximo da malha já
está à frente do plano, nenhuma face dela precisa ser testada.

### 1.4 Sombreamento

Lambertiano plano com quatro contribuições: ambiente, difusa do sol, uma luz de
preenchimento fria vinda do planeta e um realce especular Blinn-Phong. O brilho é
propriedade de cada malha (`gloss`), então rocha e painel solar ficam foscos e o casco
metálico brilha.

> **Sobre o §9 do enunciado.** O texto exclui "iluminação realista, texturas complexas
> e shaders". O realce especular aqui é o modelo Blinn-Phong clássico, calculado em
> Python por face, sem GPU, sem textura e sem shader — é conteúdo de sombreamento da
> disciplina, não iluminação baseada em física. Se houver questionamento, esta é a
> justificativa; remover o termo é uma linha de código em `shade()` e no laço de
> `PolyMesh.collect`.

### 1.5 Teste de visibilidade

O requisito 9 é atendido por interseção raio-esfera de verdade
(`ray_sphere` + `Scene.line_of_sight`): o sensor no topo da antena dispara um raio até
cada alvo e testa contra as esferas envolventes dos detritos e do núcleo. A linha fica
verde quando livre e vermelha com marcador no ponto de impacto quando bloqueada, e o
HUD nomeia o obstáculo. Durante a fase 4 é comum ver uma das quatro linhas bloqueada
pelo próprio núcleo.

### 1.6 Hierarquia de transformações

A cena tem três níveis de composição pai-filho: estação → robô → braço → antebraço.
Para o braço, a orientação do corpo deliberadamente não usa o canal X, o que torna a
soma do ângulo da junta nesse canal **exatamente** equivalente a girar o elo no próprio
eixo antes de aplicar a orientação do pai. Foi uma alternativa a implementar
multiplicação de matrizes só para essa cadeia.

### 1.7 Desempenho

Com a cena densificada, o custo por quadro passou a ser o fator limitante. As medições
estão em `python "Atividade AP1/test_ap1.py" --bench`. As decisões que mais renderam:

| Medida | Efeito |
|---|---|
| Transformar os vértices uma vez por malha, não uma vez por face | `to_view` caía 1.868 vezes por quadro para 912 vértices |
| Cache dos vértices de mundo, invalidado por comparação de pose | evita recalcular objetos parados |
| Matriz de rotação por malha em vez de seno/cosseno por vértice | a rotação é linear: bastam os três vetores da base |
| Sombrear no espaço de câmera, levando a luz para lá uma vez por quadro | dispensa guardar as normais em coordenadas de mundo |
| *Frustum culling* por esfera envolvente | descarta a malha inteira antes de transformar qualquer vértice |
| Cache das superfícies de texto do HUD | a interface caiu de 2,37 ms para cerca de 0,25 ms |
| Halos como sprites pré-renderizados, com a cor pré-multiplicada | a soma aditiva do Pygame ignora o alpha; sem pré-multiplicar, o halo vira um disco chapado |
| `DETAIL`, multiplicador global de resolução | calibra a cena inteira sem reescrever construtores |

Resultado: o quadro saiu de **10,25 ms** (cena antiga, 823 faces) para cerca de
**11,5 ms** com a cena atual, que tem aproximadamente o dobro de faces, 28 malhas e
efeitos adicionais. O orçamento de 60 FPS é 16,7 ms.

### 1.8 Testabilidade

`ap1.py` não inicializa o Pygame ao ser importado: a janela só é criada dentro de
`main()`. A classe `Scene` não importa nada de Pygame, e `Renderer` desenha em qualquer
`Surface`. Por isso a suíte roda inteira sem abrir janela.

## 2. Dificuldades encontradas

1. **A câmera não orientava.** Diagnosticada capturando quadros fora da tela e
   comparando os cinco modos: quatro deles não enquadravam a cena.
2. **Ordem de desenho errada nas vistas laterais**, pela profundidade medida no eixo
   errado.
3. **Faixas na esfera do planeta**, causadas por usar o valor absoluto do produto
   escalar no sombreamento: os dois lados ficavam iluminados.
4. **`random.seed()` global** dentro do construtor de asteroides contaminava as
   partículas e o campo estelar. Hoje cada malha usa seu próprio `random.Random`.
5. **Orçamento de quadro.** Ao densificar as malhas, o tempo por quadro chegou a
   17,1 ms — acima dos 16,7 ms de 60 FPS. Foi preciso perfilar e otimizar antes de
   continuar aumentando a cena.
6. **Halos chapados.** A soma aditiva do Pygame ignora o canal alpha, e o brilho do
   planeta virava um anel sólido até a cor ser pré-multiplicada.
7. **[CONFIRMAR]** Dificuldades de organização da equipe, prazos ou ferramentas que
   valham registro.

## 3. Divisão de tarefas

Papéis conforme o §4 do enunciado. **[CONFIRMAR]** — ajustem a coluna da direita para
o que cada um realmente fez, já que na apresentação cada integrante precisa saber
explicar a própria contribuição.

| Integrante | Papel | Contribuição |
|---|---|---|
| Fellipe Augusto (2401525) | Coordenação e integração | **[CONFIRMAR]** |
| Gabriel Muchon (2401895) | Modelagem e composição da cena | **[CONFIRMAR]** |
| Paloma Eduarda (2401660) | Animação e máquinas de estado | **[CONFIRMAR]** |
| Victor Wenzel (2401698) | Câmera, interface e testes | **[CONFIRMAR]** |

> **Atenção:** o histórico do repositório registra commits de apenas dois autores. O
> checklist do §8 pede que os quatro integrantes estejam identificados e consigam
> explicar sua contribuição — vale distribuir commits reais antes da entrega.
