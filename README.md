# Projeto AP1 — Computação Gráfica e RA/RV
## Mundo Virtual Animado: Base Espacial e Campo de Asteroides

---

### Integrantes da Equipe
* Fellipe Augusto - 2401525
* Gabriel Muchon - 2401895
* Paloma Eduarda - 2401660
* Victor Wenzel - 2401698

---

### 1. Visão Geral do Projeto
Este projeto consiste na implementação de um ambiente virtual tridimensional animado e interativo desenvolvido inteiramente em **Python** com **Pygame**, sem a utilização de OpenGL, motores 3D comerciais ou bibliotecas externas de modelagem (atendendo à restrição didática do enunciado).

A aplicação renderiza uma cena espacial composta por uma base de lançamento com torre de suporte monolítica, um foguete aeroespacial composto, um corpo celeste esférico (Lua) e um cinturão de três asteroides instanciados com variação de parâmetros, além de um campo estelar dinâmico em profundidade. Toda a projeção tridimensional, sombreamento, oclusão, descarte de superfícies e traçado de raio foram calculados analiticamente através de matemática vetorial pura.

---

### 2. Instruções de Execução

#### Pré-requisitos
* **Python 3.10** ou superior instalado.
* Biblioteca **Pygame** instalada.

#### Instalação das Dependências
No terminal ou prompt de comando, execute:
```bash
pip install pygame
```

#### Como Executar
A partir da raiz do repositório:
```bash
python "Atividade AP1/ap1.py"
```
A janela abre em `1080x720` a 60 FPS, com a simulação parada até o primeiro comando de teclado.

---

### 3. Controles

| Tecla | Ação |
|---|---|
| `ESPAÇO` | Inicia a sequência / alterna Pausar ↔ Retomar / reinicia ao final |
| `R` | Reseta a cena para o estado inicial (posições, rotações e câmera) |
| `W` | Câmera — Visão Superior |
| `S` | Câmera — Visão Inferior |
| `A` | Câmera — Flanco Esquerdo |
| `D` | Câmera — Flanco Direito |
| `C` | Câmera — Visão Frontal (padrão) |
| `TAB` | Alterna a tela de créditos |

A transição entre câmeras é suavizada por interpolação linear (`lerp`), não por corte instantâneo.

---

### 4. Sequência de Animação (Máquina de Estados)

A simulação percorre 4 estados (`PARADO`, `EXECUTANDO`, `PAUSADO`, `CONCLUIDO`) e, dentro de `EXECUTANDO`, 3 fases com duração total de 12s:

1. **Alinhamento e Desacoplamento (0s–3.5s)** — o foguete gira sobre a plataforma de lançamento.
2. **Ignição Principal e Subida (3.5s–7.5s)** — o foguete sobe, com leve pulsação de escala e emissão contínua de partículas de exaustão.
3. **Órbita com Evitação de Colisão (7.5s–12s)** — os três asteroides orbitam em trajetórias helicoidais; cada um é testado contra uma caixa/esfera de segurança ao redor da torre de lançamento e desviado vetorialmente caso a interceptem.

Ao final, o estado muda para `CONCLUIDO` e um novo `ESPAÇO` reinicia o tempo de simulação.

---

### 5. Arquitetura do Código (`Atividade AP1/ap1.py`)

* **Matemática vetorial pura** — soma, subtração, escala, produto vetorial/escalar, normalização e `lerp`, usadas em todo o pipeline (sem `numpy` ou bibliotecas de álgebra linear).
* **Projeção em perspectiva** (`project`) — projeta pontos 3D para a tela usando distância focal (`FOV`) e a posição da câmera.
* **`PolyMesh`** — classe genérica de malha poligonal (vértices + faces), com posição, rotação em Y e escala próprias; calcula normais por face para *back-face culling* e sombreamento.
* **Modelagem procedural** — `build_stable_rocket`, `build_launch_tower`, `build_asteroid` e `build_sphere` geram os vértices/faces do foguete, da torre, dos asteroides (com ruído radial) e da Lua.
* **Renderização** — as faces de todos os meshes são coletadas, ordenadas por profundidade (*Algoritmo do Pintor* / Z-sort) e desenhadas com sombreamento Lambertiano (flat shading) baseado em uma luz direcional fixa.
* **`ExhaustParticles`** — sistema simples de partículas para o rastro de exaustão do foguete, com decaimento de vida e cor dinâmica.
* **`Starfield`** — campo estelar de fundo com profundidade cíclica, dando sensação de movimento da câmera.
* **Traçado de raio simplificado** — um raio ligado da torre ao foguete testa a distância até o alvo; muda de cor (verde → vermelho) e ponto de impacto conforme o teste de interseção.
* **HUD** — título, estado da FSM, fase atual, tempo decorrido, status do raio, câmera ativa, comandos disponíveis e barra de progresso.
* **Créditos (`TAB`)** — equipe, tema escolhido e lista dos conceitos de computação gráfica aplicados.

---

### 6. Estrutura do Repositório

```
space-station-pygame/
├── Atividade AP1/          # Entrega avaliativa: código-fonte, enunciado e README do enunciado
│   ├── ap1.py
│   ├── Atividade-AP_1.pdf
│   └── README.md
└── Materiais de aula/       # Material de apoio da disciplina (slides e exercícios)
    ├── Aulas/
    └── Exercicios/
```

Veja [Atividade AP1/README.md](Atividade%20AP1/README.md) para o enunciado completo, requisitos mínimos e checklist de entrega, e [Materiais de aula/README.md](Materiais%20de%20aula/README.md) para o material de apoio da disciplina.
