# Projeto AP1 — Computação Gráfica e RA/RV
## Estação Orbital Órbita-2: Mundo Virtual Animado em Pygame

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/engine-pygame--ce%202.5+-green.svg)](https://pyga.me/)
[![3D Pipeline](https://img.shields.io/badge/pipeline-anal%C3%ADtico%20puro%20(sem%20OpenGL)-orange.svg)]()
[![Zero External Math](https://img.shields.io/badge/math-vetorial%20pura%20(sem%20NumPy)-red.svg)]()
[![Test Suite](https://img.shields.io/badge/testes-228%20automatizados-brightgreen.svg)]()
[![Dados reais](https://img.shields.io/badge/efem%C3%A9rides-JPL%20Horizons%20%7C%20CelesTrak-9cf.svg)]()

Ambiente tridimensional interativo e animado, desenvolvido inteiramente em **Python** e **Pygame**, sem auxílio de OpenGL, Vulkan, motores 3D ou bibliotecas matemáticas externas como `numpy` — atendendo a todas as restrições didáticas da disciplina de **Computação Gráfica e Realidade Aumentada / Realidade Virtual**.

Todo o pipeline gráfico — desde as transformações afins, câmera *look-at*, projeção em perspectiva analítica, *back-face culling*, recorte em plano próximo (*near-plane clipping*), ordenação por profundidade (*Painter's Algorithm*) e sombreamento Lambertiano com iluminação ambiente e realce especular — foi implementado do zero com matemática vetorial pura.

A estação **Órbita-2** é fictícia, mas voa numa órbita baixa física de 420 km e 92 minutos com atitude LVLH. **Tudo ao redor dela é real e está na posição do instante em que o programa roda**: planetas, luas, asteroides, cometas, satélites artificiais e estrelas, com elementos do JPL e do CelesTrak. O zoom vai da **cabine da estação**, por dentro, até o **Cinturão de Kuiper**, a 190 UA.

---

## 👥 Integrantes da Equipe

| Integrante | RA | Contribuição Principal |
|---|---|---|
| **Fellipe Augusto** | 2401525 | Coordenação, integração e testes |
| **Gabriel Muchon** | 2401895 | Modelagem geométrica e composição da cena |
| **Paloma Eduarda** | 2401660 | Animação e máquinas de estado finitas (FSM) |
| **Victor Wenzel** | 2401698 | Câmera, interface do usuário (HUD) e testes |

**Variação Temática:** Equipe 2 — *Estação Espacial* (acoplamento de módulos orbitais, trajetória orbital de robôs de manutenção com evitação de mastro, portas com máquina de estados e alerta sequencial de balizas).

---

## 🛰️ Demonstração Geral

![Demonstração Geral da Estação Orbital Órbita-2](docs/img/visao-geral.gif)

A simulação retrata a estação orbital **Órbita-2** em órbita baixa da Terra recebendo a nave cargueira automatizada **Vega-7**. A estação conta com núcleo e treliças estruturais, painéis solares articulados com rastreamento solar, comporta deslizante de doca, quatro robôs com braços mecânicos articulados, cinturão de detritos, **interior navegável** (cúpula e corredor) e, ao redor, o Sistema Solar inteiro em **escala real**: 1 unidade de mundo = 0,2 m, a estação tem ~100 m e a Terra, 6.371 km. O que fica menor que um pixel e meio deixa de ser malha e vira marcador com nome.

---

## 🚀 Como Executar

### Pré-requisitos
- Python 3.10 ou superior.
- Pygame (ou `pygame-ce` para Python 3.14).

```bash
# 1. Clone o repositório
git clone https://github.com/gblsun/space-station-pygame.git
cd space-station-pygame

# 2. Instale as dependências
pip install -r "Atividade AP1/requirements.txt"

# 3. Execute a aplicação
python "Atividade AP1/ap1.py"                 # janela 1080x720
python "Atividade AP1/ap1.py" --tela-cheia    # abre direto em tela cheia
python "Atividade AP1/ap1.py" --offline       # não toca na rede
```

> [!NOTE]
> No **Python 3.14**, utilize `pip install pygame-ce` (já configurado no `requirements.txt`), pois o Pygame tradicional não disponibiliza rodas pré-compiladas para esta versão.

> [!TIP]
> **A aplicação funciona sem internet.** Os dados reais ficam versionados em `Atividade AP1/dados/`. Havendo rede, uma thread em segundo plano busca o que envelhece — elementos dos satélites, vetores do James Webb, agenda do telescópio e as imagens mais recentes — sem nunca bloquear a animação.

---

## 🎮 Controles de Teclado

Todas as interações são **ações discretas disparadas por teclado**, conforme estipulado no enunciado acadêmico (sem controle contínuo por mouse ou física descontrolada). A tela `F1` lista tudo dentro da própria aplicação.

| Tecla | Categoria | Ação |
|---|---|---|
| `ESPAÇO` | **Simulação** | Iniciar · pausar · retomar · reiniciar após conclusão |
| `R` | **Simulação** | Reiniciar a cena imediatamente para a pose inicial ($t = 0$) |
| `1`, `2`, `3`, `4` | **Fases** | Saltar diretamente para o início da Fase 1, 2, 3 ou 4 |
| `C` | **Câmera** | Câmera em Plano Geral (isométrica orbital) |
| `W` / `S` | **Câmera** | Câmera Superior (nadir) / Câmera Inferior (zênite) |
| `A` / `D` | **Câmera** | Flanco Esquerdo / Flanco Direito da estação |
| `F` | **Câmera** | Câmera de Foco Animado (persegue dinamicamente o cargueiro Vega-7) |
| `T` | **Câmera** | Modo Tour (alterna o enquadramento ideal a cada fase) |
| `Z` / `X` | **Zoom** | Aproximar / Afastar: Cúpula $\rightarrow$ Corredor $\rightarrow$ Doca $\rightarrow$ Estação $\rightarrow$ Órbita $\rightarrow$ Sistema Solar $\rightarrow$ Cinturão de Kuiper |
| `P` / `Shift+P` | **Foco** | Percorrer corpos e naves, do Sol para fora, com ficha de dados |
| `K` | **Telescópio** | Olho do telescópio: a câmera vê pelo James Webb e pelo Hubble |
| `V` | **Exibição** | Fundo: estrelas reais, imagem do James Webb ou do Hubble |
| `,` / `.` | **Tempo** | Relógio orbital: de tempo real a 1 ano por segundo |
| `+` / `-` | **Velocidade** | Ajustar velocidade do tempo da simulação (de $0{,}25\times$ a $3{,}0\times$) |
| `L` | **Execução** | Modo Loop contínuo (reinicia a sequência automaticamente) |
| `O` | **Inspeção** | Órbita de inspeção estendida (três voltas completas dos robôs) |
| `B` | **Exibição** | Alternar renderização dos traçados das órbitas |
| `N` | **Exibição** | Exibir/ocultar rótulos dos objetos (papéis do Requisito 3) |
| `H` | **Diagnóstico** | Painel de telemetria: FPS medido, contagem de faces, culling, tempo de quadro, próximo eclipse e próxima passagem da ISS |
| `F1` | **Ajuda** | Tela de ajuda com todos os comandos |
| `F2` | **Avaliação** | Modo avaliação: mostra na cena onde está cada requisito obrigatório |
| `F9` | **Apresentação** | Roteiro automático de doze passos, com legendas |
| `F11` | **Janela** | Tela cheia na resolução do monitor |
| `F12` | **Captura** | Salvar captura de tela em alta definição em `docs/img/` |
| `TAB` | **Créditos** | Exibir overlay de créditos da equipe e referências |
| `ESC` | **Sistema** | Encerrar a aplicação com liberação de recursos |

> Dentro da cabine, `C`, `W`, `S`, `A` e `D` passam a ser pontos de vista internos.

---

## 🎬 As 4 Fases da Simulação

A narrativa técnica da simulação é governada por uma **Máquina de Estados Finitos (FSM)** que divide os 14 segundos da animação em quatro fases rigorosamente sincronizadas:

### Fase 1: Aproximação e Alinhamento de Atitude (0 s – 4 s)
![Fase 1 - Aproximação](docs/img/fase-1-aproximacao.gif)

- **Dinâmica:** O cargueiro Vega-7 se desloca pelo eixo $+X$ em direção à doca de acoplamento da estação. Durante a trajetória, o sistema corrige o erro de atitude angular residual através de interpolação não linear (`smoothstep`), estabilizando a rotação antes de atingir o limiar da doca.
- **Sinalização Visual:** As seis balizas de alerta piscam em padrão âmbar sequencial de rodízio, indicando área de manobra ativa.
- **Estado da Doca:** Comporta firmemente `FECHADA`.

---

### Fase 2: Abertura da Doca e Propulsão Reversa (4 s – 7 s)
![Fase 2 - Abertura da Doca](docs/img/fase-2-abertura-doca.gif)

- **Dinâmica:** A comporta da doca executa sua FSM dedicada (`FECHADA` $\rightarrow$ `ABRINDO` $\rightarrow$ `ABERTA`), deslizando suas duas folhas poligonais em sentidos opostos ao longo do trilho.
- **Retrofoguetes:** O cargueiro inicia a manobra de desaceleração fina, disparando um emissor de partículas estocásticas de retrofoguete no sentido contrário ao movimento.
- **Deformação por Escala:** Uma pulsação harmônica suave de escala ($\pm 3\%$) é aplicada à malha da nave para simular a compressão estrutural da queima de propulsão.

---

### Fase 3: Acoplamento Físico e Travamento (7 s – 10 s)
![Fase 3 - Acoplamento](docs/img/fase-3-acoplamento.gif)

- **Dinâmica:** A ponta do cargueiro penetra o colar de captura do anel de ancoragem da estação. Ao atingir o contato cinemático, um micro-tremor de câmera (*camera shake*) não acumulativo simula o engate mecânico.
- **Ciclo da Comporta:** A comporta faz a transição `FECHANDO` $\rightarrow$ `FECHADA`.
- **Confirmação:** As balizas de alerta mudam simultaneamente de âmbar pulsante para **verde estático**, indicando acoplamento estanque bem-sucedido.
- **Ponto de vista interno:** pelo visor da escotilha de doca (`Z` até `Cabine`, depois `D`), a mesma manobra vista de dentro da estação.

---

### Fase 4: Órbita de Inspeção e Sensor de Linha de Visada (10 s – 14 s)
![Fase 4 - Robôs e Inspeção](docs/img/fase-4-inspecao-robos.gif)

- **Dinâmica dos Robôs:** Os quatro robôs de manutenção (**MR-1** a **MR-4**), cada um com tamanho, cor, raio orbital e plano de inclinação distintos, desatracam e descrevem órbitas helicoidais de patrulha ao redor da estação, desviando do envelope de segurança da antena.
- **Cinemática Articulada:** Cada robô move independentemente os dois segmentos de seu braço mecânico articulado via transformações hierárquicas compostas.
- **Sensor de Linha de Visada (*Ray-Sphere*):** O sensor principal no topo da torre dispara raios em direção a cada robô:
  - 🟢 **Verde:** Linha de visada livre.
  - 🔴 **Vermelho:** Raio interceptado pela geometria do núcleo da estação ou pelo cinturão de detritos, marcando o ponto de impacto exato e identificando o obstáculo no HUD.

A pose de cada objeto é **função pura do tempo**: pausar, reiniciar e saltar de fase reconstroem exatamente o mesmo estado. O relógio orbital corre em paralelo e pode ser acelerado sem afetar a sequência.

---

## 🎥 Sistema de Câmeras e Interpolação

![Tour de Câmeras](docs/img/camera-tour.gif)

O sistema de visualização foi projetado em torno de uma **câmera Look-At tridimensional**:
- **Base Ortonormal:** A cada quadro, a câmera reconstrói sua base vetorial ortonormal $(\vec{r}, \vec{u}, \vec{f})$ garantindo:
  $$\vec{f} = \frac{\vec{T} - \vec{E}}{\|\vec{T} - \vec{E}\|}, \quad \vec{r} = \frac{\vec{f} \times \vec{up}}{\|\vec{f} \times \vec{up}\|}, \quad \vec{u} = \vec{r} \times \vec{f}$$
- **Transição Suave (LERP Logarítmico):** Ao alternar entre presets de visualização (ex: Geral, Superior, Flancos), a câmera não efetua cortes secos; ela interpola suavemente a posição do olho e do alvo usando interpolação logarítmica de distância, tornando natural tanto o movimento a 40 metros da doca quanto o afastamento para 190 UA.
- **Foco Animado (`F`):** Trava a âncora de alvo no cargueiro Vega-7, acompanhando dinamicamente sua trajetória em tempo real.
- **Olho do Telescópio (`K`):** A câmera senta atrás do espelho do James Webb ou do Hubble, apontada para o alvo real que o telescópio observa naquele momento, segundo a agenda do STScI.

---

## 🚪 Por Dentro da Estação

O zoom não para no casco: `Z` continua entrando até a **Cúpula** e o **Corredor do núcleo**, com olho e alvo no referencial da estação e plano próximo reduzido de 1,6 m para 20 cm.

- **Casca interna com *winding* invertido:** as normais apontam para dentro, então o mesmo *back-face culling* que descarta o interior visto de fora descarta o casco visto de dentro.
- **Janelas sem geometria extra:** onde há janela, a casca simplesmente não tem face. O buraco mostra o espaço de verdade — pela cúpula dá para ver a Terra passando embaixo e, na Fase 3, o cargueiro encostando.
- **Iluminação de bordo:** dentro do módulo a luz não pode vir do Sol, então as malhas internas carregam direção de luz e ambiente próprios, fixos no referencial da estação.
- **Detalhes:** piso em grade, racks laterais com painéis acesos, corrimãos, o anel de doca visto por dentro e o painel da comporta refletindo o estado da `DoorFSM`.

---

## ⚙️ Arquitetura do Pipeline Gráfico Analítico

O motor gráfico renderiza a cena tridimensional calculando cada transformação de forma analítica no processador:

```mermaid
flowchart TD
    A["Vértices no Espaço do Objeto (Local)"] --> B["Transformação de Modelo (Translação, Rotação Euler, Escala)"]
    B --> C["Espaço do Mundo (Referencial Orbital LVLH e ICRF)"]
    C --> D["Transformação de Visão (Câmera Look-At: Eye, Target, Up)"]
    D --> E["Espaço de Câmera (Eye-Space)"]
    E --> F{"Teste de Recorte no Plano Próximo (Near Plane Clip: z >= NEAR)"}
    F -- "Fora / Atrás" --> G["Descarte do Vértice / Face"]
    F -- "Intersecção" --> H["Algoritmo Sutherland-Hodgman (Divide Face)"]
    F -- "Dentro" --> I["Projeção em Perspectiva: x' = f·x/z, y' = f·y/z"]
    I --> J{"Back-Face Culling (Normal · Vetor Visão <= 0)"}
    J -- "Face Traseira" --> G
    J -- "Face Frontal" --> K["Cálculo de Iluminação Lambertiana + Especular"]
    K --> L["Ordenação por Profundidade (Painter's Algorithm)"]
    L --> M["Rasterização no Pygame (pygame.draw.polygon)"]
```

### Fundamentos Matemáticos Implementados:
1. **Projeção em Perspectiva Analítica:**
   $$x_{screen} = x_c + \frac{f \cdot x_{cam}}{z_{cam}}, \quad y_{screen} = y_c - \frac{f \cdot y_{cam}}{z_{cam}}$$
2. **Back-Face Culling:**
   Elimina faces poligonais voltadas para longe do observador antes do preenchimento:
   $$\vec{N} = (\vec{v}_1 - \vec{v}_0) \times (\vec{v}_2 - \vec{v}_0), \quad \text{visível se } \vec{N} \cdot \vec{v}_0 < 0$$
3. **Iluminação Lambertiana com Luz de Preenchimento:**
   A intensidade de cor de cada face combina luz ambiente, componente difusa do Sol e luz de preenchimento refletida da Terra:
   $$I = I_{amb} + k_d \max(0, \vec{N} \cdot \vec{L}_{sol}) + k_{fill} \max(0, \vec{N} \cdot \vec{L}_{terra}) + k_s (\vec{R} \cdot \vec{V})^n$$
4. **Interseção Raio-Esfera (Traçado de Visibilidade):**
   Utilizada pelo sensor no topo da antena para testar oclusão:
   $$\|\vec{O} + t\vec{D} - \vec{C}\|^2 = R^2 \implies a t^2 + b t + c = 0$$

### Como 190 UA cabem em 60 FPS

- **Marcadores:** todo corpo cuja projeção fica abaixo de 1,6 px deixa de ser malha e vira um ponto com rótulo.
- **Níveis de detalhe:** cada malha tem versões por tamanho projetado; a esfera da Terra vai de 16 a 512 faces conforme a distância.
- **Calota do horizonte:** vista de perto, a Terra é reconstruída apenas na janela de azimute que a câmera enxerga.
- ***Frustum culling*** com esfera envolvente antes de qualquer transformação de vértice, e órbitas desenhadas só no contexto em que fazem sentido.

---

## ☀️ Efemérides Astronômicas e Órbitas Reais

Diferente de simulações estáticas convencionais, a estação orbita uma Terra com **relógio astronômico UTC real**, e tudo ao redor está na posição do instante em que o programa roda:

- os **oito planetas**, pelos elementos keplerianos do JPL, e a **Lua** pela fórmula de baixa precisão do *Astronomical Almanac*;
- **cinco planetas anões**, **25 luas**, asteroides e cometas notáveis, com elementos do JPL Horizons;
- cerca de **4.100 asteroides e cometas reais** do JPL Small-Body Database, desenhados como pontos, incluindo os enxames de troianos rotulados em **L4 e L5**;
- **satélites artificiais reais** com elementos do CelesTrak: ISS, Hubble, Tiangong, GOES e a constelação GPS com modelo 3D próprio, mais estações, GNSS, geoestacionários e Starlink amostrado como pontos — cerca de **1.800 objetos**;
- o **James Webb** no ponto L2, a 1,5 milhão de km, pelos vetores do JPL Horizons;
- o céu com as **estrelas reais** do Yale Bright Star Catalogue, nas posições e cores verdadeiras;
- o **lado noturno da Terra** aceso com as luzes das cidades, o rastro da órbita projetado no solo, o terminador e as caudas anti-solares dos cometas;
- avisos calculados: o **próximo eclipse** (a busca acerta o eclipse solar de 6 de fevereiro de 2027 às 15:59 UTC) e a **próxima passagem da ISS** sobre uma cidade configurável.

**Referencial LVLH:** a estação translada orientando sua arfagem (*pitch*) ao vetor de velocidade orbital local, e a cada volta entra e sai da sombra cilíndrica da Terra — cerca de 36% do tempo em eclipse.

**Painéis solares articulados:** as juntas calculam a cada quadro o ângulo que maximiza a incidência solar. A ISS combina a junta da treliça com a de cada asa, o GPS gira o corpo (*yaw steering*) e depois a asa, o Hubble mantém o eixo das asas perpendicular ao Sol e o James Webb mantém o escudo de frente para ele. Na sombra, as juntas voltam a zero.

### Precisão do modelo

Medida contra o JPL Horizons; o método está em [docs/03-decisoes-tecnicas.md](docs/03-decisoes-tecnicas.md).

| Corpo | Erro |
|---|---|
| Terra | 0,003° |
| Marte | 0,008° |
| Netuno | 0,009° |
| Júpiter | 0,02° |
| Lua | 0,07° e 630 km na distância |
| ISS, na época dos elementos | ~10 km |
| ISS, com elementos de um dia | algumas dezenas de km |

A propagação dos satélites é Kepler com o efeito secular do achatamento da Terra (J2), e não o SGP4 completo: por isso o erro cresce com a idade dos elementos.

![Sistema Solar na data de geração](docs/img/sistema-solar-hoje.png)

---

## 📡 Fontes dos Dados e Licenças

| Fonte | O que fornece | Licença |
|---|---|---|
| JPL — *Approximate Positions of the Planets* | Elementos dos oito planetas | Domínio público (NASA) |
| JPL Horizons | Luas, anões, asteroides, cometas e o James Webb | Domínio público (NASA) |
| JPL Small-Body Database | ~4.100 asteroides e cometas | Domínio público (NASA) |
| CelesTrak | Elementos dos satélites artificiais (GP/OMM) | Uso livre com atribuição |
| VizieR — Yale Bright Star Catalogue (V/50) | Estrelas a olho nu | Uso acadêmico livre |
| Solar System Scope | Mapas de cor dos planetas e o mapa noturno da Terra | CC BY 4.0 |
| ESA/Webb e ESA/Hubble | Imagens de fundo | CC BY 4.0 |
| STScI | Agenda de observação do James Webb | Domínio público (NASA) |

Os créditos completos das imagens aparecem na própria aplicação, ao lado do fundo e na tela de créditos (`TAB`), como a licença CC BY 4.0 exige. Os downloads usam apenas `urllib`, da biblioteca padrão, sempre em thread e com cache em disco.

---

## 📋 Conformidade com os Requisitos da AP1

| # | Requisito Obrigatório do Enunciado | Implementação no Código (`ap1.py`) |
|---|---|---|
| **1** | Janela configurável, laço principal, FPS, $\Delta t$ e encerramento | `App.run()` com `clock.tick(60)`, `dt` suavizado, tela cheia por `F11` e saída limpa via `ESC` ou fechamento da janela. |
| **2** | $\ge 3$ tipos de primitivas visuais | Polígonos (faces 3D), linhas (raios do sensor, órbitas, caudas de cometa), círculos (partículas e balizas), pontos (campo estelar e enxames), retângulos e textos rasterizados (HUD). |
| **3** | $\ge 5$ objetos: instâncias, sem partes e composto | **Instâncias:** robôs MR-1 a MR-4 e os 31 satélites da constelação GPS, do mesmo tipo com parâmetros distintos. **Sem partes:** Terra, Lua e planetas (esferas puras). **Compostos:** Núcleo Órbita-2, Módulo Laboratório, Cargueiro Vega-7 e os satélites reais com painéis articulados. |
| **4** | Translação, rotação e escala com variação | **Translação:** cargueiro, robôs e corpos celestes em órbitas reais. **Rotação:** articulação dos braços, detritos, painéis solares e rotação própria dos planetas pela orientação IAU. **Escala:** pulsação harmônica do cargueiro na Fase 2. |
| **5** | Câmera com $\ge 2$ modos alternados por tecla | Presets discretos (`C`, `W`, `S`, `A`, `D`), **Foco Animado** (`F`), **Modo Tour** (`T`), oito níveis de zoom (`Z`/`X`), foco por corpo (`P`) e o olho do telescópio (`K`). |
| **6** | $\ge 3$ animações distintas | Translação com interpolação não linear (aproximação do cargueiro), máquina de estados aninhada (`DoorFSM`) e trajetória sincronizada multi-objeto (robôs em órbita com evitação de mastro). |
| **7** | Comandos de teclado discretos documentados | Tratamento exclusivo de eventos `KEYDOWN` em `App.handle_event()`, sem comandos contínuos, documentados na tela `F1`. |
| **8** | Interface sobreposta (HUD) informativa | Título, máquina de estados, fase ativa, temporizador, barra de progresso com marcos, status dos sensores, ficha do corpo em foco, próximo eclipse e próxima passagem da ISS. Escala com a resolução. |
| **9** | Recurso de visibilidade por traçado de raios | `Scene.line_of_sight()` calcula interseção analítica raio-esfera contra os detritos e o núcleo; a mesma rotina oculta o Sol atrás da Terra e escurece as faces cobertas pela sombra da Lua durante um eclipse. |
| **10** | Tela de créditos e identificação | Acionada por `TAB`, exibindo os quatro integrantes, seus respectivos RAs, divisão de papéis, fontes bibliográficas e créditos das imagens. |

> O modo `F2` marca na própria cena onde cada um destes dez requisitos aparece.

---

## 🧪 Testes Automatizados e Diagnóstico

O projeto inclui uma suíte completa de testes automatizados executáveis em ambiente *headless* (driver de vídeo `dummy` do SDL), **sem rede e sem janela**:

```bash
# Execução da suíte completa de testes unitários
python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v

# Teste de fumaça (smoke test) de ponta a ponta com relatório de conformidade
python "Atividade AP1/test_ap1.py" --smoke

# Benchmark de performance do pipeline gráfico
python "Atividade AP1/test_ap1.py" --bench --res 1080x720 --max-ms 60
```

São **228 testes** em dois arquivos: `test_ap1.py` cobre o motor, a cena, a cabine, a câmera, o HUD e o roteiro do checklist; `test_sistema_solar.py` cobre as efemérides contra valores do JPL Horizons, o catálogo e os leitores das fontes online. Um teste de **quadros-ouro** compara a assinatura visual de cada enquadramento com uma referência guardada em `dados/assinaturas.json`; depois de uma mudança visual deliberada, regrave-a com `python "Atividade AP1/test_ap1.py" --assinaturas`.

### Orçamento de Performance
- **Meta:** 60 FPS estáveis ($\le 16{,}7\text{ ms}$ por quadro).
- **Medido em 1080×720, com a sequência rodando:** Terra-Lua-L2 4 ms, Terra e satélites 9 ms, órbita baixa 10 ms, Sistema Solar 13 ms, vizinhança 15 ms, cabine 18 ms, estação 19 ms e doca 22 ms. As vistas de acoplamento, as mais densas, ficam entre 45 e 55 FPS; em 1920×1080 o custo sobe cerca de 20%.
- **No CI:** `--bench --res LxA --max-ms N` devolve erro acima do limite, o que transforma uma regressão de desempenho em build quebrado.

---

## 📁 Estrutura do Repositório

```text
space-station-pygame/
├── Atividade AP1/              # Entrega acadêmica principal
│   ├── ap1.py                  # Motor gráfico 3D, FSM, cena e aplicação principal
│   ├── catalogo.py             # Parâmetros e dados físicos dos corpos celestes
│   ├── efemerides.py           # Mecânica celeste analítica e rotinas do JPL
│   ├── fontes_online.py        # Integração e consulta de dados astronômicos
│   ├── ferramentas/
│   │   └── baixar_dados.py     # Gera os snapshots versionados de dados/
│   ├── dados/                  # Estrelas, luas, pequenos corpos, satélites e mapas de cor
│   ├── test_ap1.py             # Suíte de testes unitários, smoke e benchmark
│   ├── test_sistema_solar.py   # Validação astronômica do sistema solar
│   ├── requirements.txt        # Especificação de dependências
│   ├── Atividade-AP_1.pdf      # Enunciado oficial da disciplina
│   └── README.md               # Documento complementar do módulo acadêmico
├── docs/                       # Documentação técnica e entregas das etapas
│   ├── 01-proposta.md
│   ├── 02-esboco-da-cena.md
│   ├── 03-decisoes-tecnicas.md
│   ├── 04-roteiro-animacoes.md
│   ├── 05-roteiro-apresentacao.md
│   ├── gerar_figuras.py        # Gerador das figuras esquemáticas de apoio
│   └── img/                    # GIFs e diagramas visuais da documentação
│       ├── visao-geral.gif
│       ├── fase-1-aproximacao.gif
│       ├── fase-2-abertura-doca.gif
│       ├── fase-3-acoplamento.gif
│       ├── fase-4-inspecao-robos.gif
│       ├── camera-tour.gif
│       ├── esboco-planta.png
│       ├── fases.png
│       └── sistema-solar-hoje.png
└── Materiais de aula/          # Apostilas e exercícios da disciplina
```

Dentro do `ap1.py`, doze seções numeradas: configurações, matemática vetorial (vetores e matrizes), referenciais orbitais, câmera, projeção e recorte, malha poligonal, modelagem geométrica, sistemas de apoio, cena e sequência, renderização, HUD e aplicação. Importar o módulo **não** abre janela nem inicializa o Pygame: a inicialização acontece apenas dentro de `main()`, o que permite testar tudo sem tela.

---

## 📚 Referências Bibliográficas e Recursos
- **Aulas de Computação Gráfica:** Aulas 01 a 08 (Transformações geométricas 2D/3D, Projeção perspectiva, Pipeline gráfico, Câmeras sintéticas e Visibilidade).
- **Foley, J. D. et al.:** *Computer Graphics: Principles and Practice*. Addison-Wesley.
- **Shirley, P. & Marschner, S.:** *Fundamentals of Computer Graphics*. A K Peters / CRC Press.
- **NASA / JPL Horizons On-Line Ephemeris System:** Vetores de estado planetários e elementos orbitais keplerianos para validação celeste.
- **Standish, E. M.:** *Keplerian Elements for Approximate Positions of the Major Planets*. JPL Solar System Dynamics.
- **CelesTrak (Dr. T. S. Kelso):** Elementos orbitais GP/OMM dos satélites artificiais.
