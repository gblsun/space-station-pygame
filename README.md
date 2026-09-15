# Projeto AP1 — Computação Gráfica e RA/RV
## Mundo Virtual Animado: Estação Orbital Órbita-2

---

### Integrantes da Equipe

| Integrante | RA | Contribuição |
|---|---|---|
| Fellipe Augusto | 2401525 | Coordenação e integração |
| Gabriel Muchon | 2401895 | Modelagem e composição da cena |
| Paloma Eduarda | 2401660 | Animação e máquinas de estado |
| Victor Wenzel | 2401698 | Câmera, interface e testes |

**Variação temática:** Equipe 2 — Estação Espacial (acoplamento de módulos,
trajetória orbital de robôs, portas com estados e alerta sequencial).

---

### 1. Visão geral

Ambiente virtual tridimensional animado e interativo, escrito inteiramente em
**Python** com **Pygame**, sem OpenGL, sem motores 3D, sem `numpy` e sem
bibliotecas externas de modelagem — atendendo à restrição didática do enunciado.

A cena mostra a estação orbital **Órbita-2** recebendo o cargueiro **Vega-7**:
o núcleo com painéis solares em grade, radiadores, treliça de antena e propulsores
de atitude; um módulo-laboratório acoplado por túnel; uma comporta de doca com
máquina de estados própria; seis balizas de alerta em rodízio; quatro robôs de
manutenção com braço articulado de dois segmentos; um cinturão de nove detritos e
três satélites em órbita da Terra; e a própria Terra, a Lua e o Sol — 32 malhas ao todo.

Todo o pipeline gráfico é calculado analiticamente com matemática vetorial pura:
transformações de modelo, câmera look-at, recorte no plano próximo, projeção em
perspectiva, back-face culling, frustum culling, ordenação por profundidade e
sombreamento Lambertiano com luz de preenchimento e realce especular.

---

### 2. Como executar

**Pré-requisitos:** Python 3.10 ou superior e o Pygame.

```bash
pip install -r "Atividade AP1/requirements.txt"
python "Atividade AP1/ap1.py"
```

No **Python 3.14** o `pygame` clássico ainda não publica wheel e falha ao
compilar; instale `pygame-ce`, que é compatível e também se importa como
`pygame`. Em Python 3.13 ou anterior, `pip install pygame` basta.

A janela abre em `1080x720` a 60 FPS, com a simulação parada até o primeiro
`ESPAÇO`.

---

### 3. Controles

| Tecla | Ação |
|---|---|
| `ESPAÇO` | Iniciar · pausar · retomar · reiniciar quando concluída |
| `R` | Reiniciar a cena no estado inicial |
| `1` `2` `3` `4` | Saltar para o início de cada fase |
| `C` | Câmera — plano geral |
| `W` / `S` | Câmera — visão superior / inferior |
| `A` / `D` | Câmera — flanco esquerdo / direito |
| `F` | Câmera — foco animado, acompanha o cargueiro |
| `T` | Tour de câmera: um enquadramento por fase (qualquer tecla de câmera desliga) |
| `Z` / `X` | Enquadramento — aproximar / afastar (doca, estação, órbita baixa, Terra e Lua, sistema) |
| `+` / `-` | Velocidade da simulação, de 0,25x a 3x |
| `L` | Repetir a sequência sem parar |
| `O` | Órbita de inspeção estendida, com cerca de três voltas dos robôs |
| `B` | Mostrar / ocultar o traçado das órbitas |
| `N` | Rótulos dos objetos, com o papel de cada um no requisito 3 |
| `H` | Painel de dados: FPS medido, custo do quadro e pipeline |
| `F12` | Captura de tela, salva em `docs/img` |
| `TAB` | Tela de créditos |
| `ESC` | Encerrar |

São todas ações discretas: não há navegação livre, mouse nem controle contínuo
da cena. A troca de câmera é interpolada por `lerp`, não é corte seco.

---

### 4. Sequência de animação

A simulação percorre quatro estados (`PARADO`, `EXECUTANDO`, `PAUSADO`,
`CONCLUIDO`) e, dentro de `EXECUTANDO`, quatro fases somando 14 segundos:

1. **Aproximação (0 s – 4 s)** — o cargueiro Vega-7 se desloca em direção à
   doca corrigindo a atitude: o desalinhamento residual em posição e rotação
   diminui conforme ele se aproxima. As balizas piscam em alerta âmbar
   sequencial. Comporta `FECHADA`.
2. **Abertura da doca (4 s – 7 s)** — a comporta percorre `ABRINDO → ABERTA`,
   com as duas folhas deslizando em sentidos opostos. O cargueiro desacelera
   com pulsação de escala e emite partículas de retrofoguete.
3. **Acoplamento (7 s – 10 s)** — o nariz do cargueiro encaixa no anel, a
   comporta faz `FECHANDO → FECHADA` e as balizas passam de âmbar para verde.
4. **Órbita de inspeção (10 s – 14 s)** — os quatro robôs deixam seus pontos de
   ancoragem e entram em trajetória helicoidal ao redor da estação, desviando
   do cilindro de segurança do mastro da antena, com os braços em operação. O
   sensor traça a linha de visão até cada robô: quando um passa atrás do núcleo
   ou de um detrito, a linha fica vermelha e o HUD nomeia o obstáculo.

Ao final o estado vira `CONCLUIDO`; um novo `ESPAÇO` reinicia a sequência.

A pose de cada objeto é **função pura do tempo de simulação**, então pausar,
reiniciar e saltar de fase sempre reconstroem exatamente o mesmo estado.

---

### 5. Arquitetura do código (`Atividade AP1/ap1.py`)

Arquivo único, dividido em onze seções numeradas:

1. **Configurações** — resolução, FPS, distância focal, plano próximo, luz
   ambiente e a linha do tempo das fases.
2. **Matemática vetorial** — soma, subtração, escala, produto escalar e
   vetorial, norma, normalização, `lerp`, `smoothstep`, rotação nos três eixos,
   normal de face (que devolve `None` em face degenerada) e interseção
   raio-esfera. Sem `numpy`.
3. **`Camera`** — câmera *look-at* de verdade: mantém olho e alvo, ambos
   interpolados, e reconstrói a base ortonormal `(right, up, forward)` a cada
   quadro, com tratamento do caso degenerado de olhar reto para cima ou para
   baixo. O modo `F` faz o alvo acompanhar um objeto móvel.
4. **Projeção e recorte** — projeção em perspectiva a partir do espaço de
   câmera e recorte de polígonos contra o plano `z = NEAR`
   (Sutherland-Hodgman de um plano).
5. **`PolyMesh`** — malha com escala, rotação nos três eixos, translação, uma
   cor por face e um grau de brilho. Descarta a malha inteira quando ela está
   fora do tronco de visão, transforma os vértices uma única vez por quadro
   (com cache enquanto a pose não muda) e devolve as faces já projetadas, com a
   profundidade medida **em espaço de câmera**.
6. **Modelagem geométrica** — `MeshBuilder` com `add_box`, `add_prism`
   (cilindro ou cone, em qualquer eixo), `add_bar` (barra entre dois pontos
   quaisquer), `add_truss` (treliça), `add_solar_panel` (grade de células) e
   `add_dish` (antena parabólica); `build_sphere` com polos únicos; e os
   construtores do núcleo, do laboratório, do satélite, da comporta, do
   cargueiro, dos robôs e dos detritos. Cada detrito usa um `random.Random`
   próprio, nunca a semente global. A constante `DETAIL` calibra a resolução
   de todas as malhas de uma vez.
7. **Sistemas de apoio** — partículas de exaustão, campo estelar, a máquina de
   estados da comporta e as balizas de alerta sequencial.
8. **`Scene`** — todo o estado da simulação, sem nenhuma dependência de Pygame.
   É a classe que a suíte de testes exercita.
9. **`Renderer`** — desenha numa `Surface` qualquer. Faces, partículas, rastros
   e halos entram num único buffer ordenado por profundidade: o algoritmo do
   pintor aplicado a todos os elementos, não só às faces. `GlowSprites`
   pré-renderiza os halos, e a projeção do campo estelar fica em cache enquanto
   a câmera não se move.
10. **`Hud`** — interface sobreposta, painel de dados do pipeline e créditos.
11. **`App`** — janela, laço principal, controle de FPS e eventos de teclado.

Importar o módulo **não** abre janela nem inicializa o Pygame: a inicialização
acontece apenas dentro de `main()`, o que permite testar tudo sem tela.

---

### 6. Testes

```bash
# suíte automatizada, sem abrir janela
python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v

# roteiro do checklist de ponta a ponta, com relatório
python "Atividade AP1/test_ap1.py" --smoke
```

São 89 testes. A suíte cobre a matemática vetorial, o winding das malhas, a base
ortonormal da câmera em todos os presets, o recorte no plano próximo, a interseção
raio-esfera, as transições da máquina de estados, as fases, a comporta, as balizas,
a evitação de colisão, o cache de vértices, o frustum culling, os níveis de
detalhe, os halos e a renderização em todas as câmeras.

O desempenho é medido pelo modo `--bench`, que reporta o custo de cada etapa do quadro:

```bash
python "Atividade AP1/test_ap1.py" --bench
```

O orçamento a 60 FPS é de 16,7 ms por quadro; a cena atual fica em torno de 11,5 ms.

O roteiro de teste manual está em
[Atividade AP1/README.md](Atividade%20AP1/README.md).

---

### 7. Estrutura do repositório

```
space-station-pygame/
├── Atividade AP1/           # Entrega avaliativa
│   ├── ap1.py               # aplicação (arquivo único)
│   ├── test_ap1.py          # suíte de testes + modos --smoke e --bench
│   ├── requirements.txt
│   ├── Atividade-AP_1.pdf   # enunciado oficial
│   └── README.md            # resumo do enunciado, conformidade e roteiro de testes
├── docs/                    # Entregas documentais das etapas 1 a 3
│   ├── 01-proposta.md
│   ├── 02-esboco-da-cena.md
│   ├── 03-decisoes-tecnicas.md
│   ├── 04-roteiro-animacoes.md
│   ├── 05-roteiro-apresentacao.md
│   ├── gerar_figuras.py     # gera o esboço a partir do próprio motor
│   └── img/
└── Materiais de aula/       # Material de apoio da disciplina
    ├── Aulas/
    └── Exercicios/
```

Veja [Atividade AP1/README.md](Atividade%20AP1/README.md) para o enunciado
resumido, a tabela de conformidade com os dez requisitos obrigatórios e o roteiro
de testes; [docs/](docs/) para as entregas documentais das três etapas, incluindo o
roteiro da apresentação; e
[Materiais de aula/README.md](Materiais%20de%20aula/README.md) para o material de
apoio da disciplina.
