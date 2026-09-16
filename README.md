# Projeto AP1 — Computação Gráfica e RA/RV
## Mundo Virtual Animado: Estação Orbital Órbita-2, no Sistema Solar real

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

Ambiente virtual tridimensional animado, escrito inteiramente em **Python** com
**Pygame**, sem OpenGL, sem motores 3D, sem `numpy` e sem bibliotecas externas de
modelagem — atendendo à restrição didática do enunciado.

A estação **Órbita-2** é fictícia, mas voa numa órbita baixa física de 420 km e 92
minutos, com atitude LVLH: a Terra fica sempre embaixo, como nas fotos da ISS. Tudo ao
redor dela é real e está na posição **do instante em que o programa roda**:

- os **oito planetas**, pelos elementos keplerianos do JPL, e a **Lua** pela fórmula de
  baixa precisão do *Astronomical Almanac*;
- **cinco planetas anões**, **25 luas**, asteroides e cometas notáveis, com elementos do
  JPL Horizons;
- cerca de **4.100 asteroides e cometas reais** do JPL Small-Body Database, como pontos;
- **satélites artificiais reais** com elementos do CelesTrak: ISS, Hubble, Tiangong,
  GOES e a constelação GPS com modelo 3D próprio, mais estações, GNSS, geoestacionários
  e Starlink amostrado como pontos — cerca de 1.800 objetos;
- o **James Webb** no ponto L2, a 1,5 milhão de km, pelos vetores do JPL Horizons;
- o céu com as **estrelas reais** do Yale Bright Star Catalogue, nas posições e cores
  verdadeiras;
- o **lado noturno da Terra** aceso com as luzes das cidades, o rastro da órbita no solo,
  o terminador, as caudas dos cometas e os enxames de troianos em L4 e L5;
- avisos calculados: o **próximo eclipse** (a busca acerta o eclipse solar de 6 de
  fevereiro de 2027 às 15:59 UTC) e a **próxima passagem da ISS** sobre uma cidade
  configurável.

Tudo em **escala real**: 1 unidade de mundo = 0,2 m, a estação tem ~100 m e a Terra,
6.371 km. O que fica menor que um pixel e meio vira marcador com nome, e o zoom vai da
**cabine da estação** ao **Cinturão de Kuiper**, a 190 UA.

O pipeline gráfico continua calculado à mão: transformações de modelo por ângulos de
Euler ou base ortonormal, câmera *look-at*, recorte no plano próximo, projeção em
perspectiva, *back-face culling*, *frustum culling*, algoritmo do pintor, sombreamento
Lambertiano com realce Blinn-Phong e níveis de detalhe pelo tamanho projetado.

---

### 2. Como executar

**Pré-requisitos:** Python 3.10 ou superior e o Pygame.

```bash
pip install -r "Atividade AP1/requirements.txt"
python "Atividade AP1/ap1.py"                 # janela 1080x720
python "Atividade AP1/ap1.py" --tela-cheia    # abre direto em tela cheia
python "Atividade AP1/ap1.py" --offline       # não toca na rede
```

No **Python 3.14** o `pygame` clássico ainda não publica wheel e falha ao compilar;
instale `pygame-ce`, que é compatível e também se importa como `pygame`.

**A aplicação funciona sem internet.** Os dados reais ficam versionados em
`Atividade AP1/dados/`. Havendo rede, uma thread em segundo plano busca o que envelhece
— elementos dos satélites, vetores do James Webb, agenda do telescópio e as imagens mais
recentes — sem nunca bloquear a animação.

---

### 3. Controles

Todas as teclas são **comandos discretos**: não há navegação livre nem mouse.
A tela `F1` lista tudo dentro da aplicação.

| Tecla | Ação |
|---|---|
| `ESPAÇO` | Iniciar · pausar · retomar · reiniciar quando concluída |
| `R` | Reiniciar a cena no estado inicial |
| `1` `2` `3` `4` | Saltar para o início de cada fase |
| `C` `W` `S` `A` `D` | Câmeras; dentro da cabine viram pontos de vista internos |
| `F` | Foco animado, acompanha o cargueiro |
| `T` | Tour: um enquadramento por fase |
| `Z` / `X` | Aproximar e afastar: da cabine ao Cinturão de Kuiper |
| `P` / `Shift+P` | Percorre corpos e naves, do Sol para fora |
| `,` / `.` | Relógio orbital: de tempo real a 1 ano por segundo |
| `+` / `-` | Velocidade da sequência, de 0,25x a 3x |
| `L` | Repetir a sequência sem parar |
| `O` | Órbita de inspeção estendida (três voltas) |
| `B` | Traçado das órbitas |
| `N` | Rótulos dos objetos |
| `V` | Fundo: estrelas reais, James Webb ou Hubble |
| `K` | Olho do telescópio: a câmera vê pelo James Webb e pelo Hubble |
| `H` | Painel de dados do pipeline e das órbitas |
| `F1` | Ajuda com todos os comandos |
| `F2` | Modo avaliação: onde está cada requisito obrigatório |
| `F9` | Modo apresentação automático |
| `F11` | Tela cheia na resolução do monitor |
| `F12` | Captura de tela, salva em `docs/img` |
| `TAB` | Tela de créditos |
| `ESC` | Encerrar |

---

### 4. Sequência de animação

A simulação percorre quatro estados (`PARADO`, `EXECUTANDO`, `PAUSADO`, `CONCLUIDO`) e,
dentro de `EXECUTANDO`, quatro fases somando 14 segundos:

1. **Aproximação (0 s – 4 s)** — o cargueiro Vega-7 se desloca em direção à doca
   corrigindo a atitude. Balizas em alerta âmbar sequencial; comporta `FECHADA`.
2. **Abertura da doca (4 s – 7 s)** — a comporta percorre `ABRINDO → ABERTA`; o
   cargueiro desacelera com pulsação de escala e emite partículas de retrofoguete.
3. **Acoplamento (7 s – 10 s)** — o nariz encaixa no anel, a comporta faz
   `FECHANDO → FECHADA` e as balizas passam de âmbar a verde. Da cabine, dá para
   assistir pelo visor da escotilha de doca.
4. **Órbita de inspeção (10 s – 14 s)** — os quatro robôs deixam a ancoragem e entram em
   trajetória helicoidal, desviando do mastro da antena. O sensor traça a linha de visão
   até cada um; quando um passa atrás do núcleo ou de um detrito, a linha fica vermelha.

A pose de cada objeto é **função pura do tempo**: pausar, reiniciar e saltar de fase
reconstroem exatamente o mesmo estado. O relógio orbital corre em paralelo e pode ser
acelerado sem afetar a sequência.

---

### 5. Arquitetura

| Arquivo | Papel |
|---|---|
| `Atividade AP1/ap1.py` | Motor gráfico, cena, HUD e aplicação. É o ponto de entrada |
| `Atividade AP1/efemerides.py` | Tempo, equação de Kepler, elementos do JPL, Lua, satélites com J2, orientação IAU. Sem pygame |
| `Atividade AP1/catalogo.py` | Tabelas físicas dos corpos e leitura dos snapshots. Sem pygame |
| `Atividade AP1/fontes_online.py` | Downloads com cache e thread: CelesTrak, Horizons, SBDB, STScI, ESA |
| `Atividade AP1/ferramentas/baixar_dados.py` | Gera os snapshots de `dados/` |
| `Atividade AP1/dados/` | Estrelas, luas, pequenos corpos, satélites, vetores do Webb e mapas de cor |

Dentro do `ap1.py`, doze seções numeradas: configurações, matemática vetorial (vetores e
matrizes), referenciais orbitais, câmera, projeção e recorte, malha poligonal, modelagem
geométrica, sistemas de apoio, cena e sequência, renderização, HUD e aplicação.

Importar o módulo **não** abre janela nem inicializa o Pygame: a inicialização acontece
apenas dentro de `main()`, o que permite testar tudo sem tela.

---

### 6. Precisão do modelo

Medida contra o JPL Horizons; o método está em
[docs/03-decisoes-tecnicas.md](docs/03-decisoes-tecnicas.md).

| Corpo | Erro |
|---|---|
| Terra | 0,003° |
| Marte | 0,008° |
| Netuno | 0,009° |
| Júpiter | 0,02° |
| Lua | 0,07° e 630 km na distância |
| ISS, na época dos elementos | ~10 km |
| ISS, com elementos de um dia | algumas dezenas de km |

A propagação dos satélites é Kepler com o efeito secular do achatamento da Terra (J2),
e não o SGP4 completo: por isso o erro cresce com a idade dos elementos.

---

### 7. Testes

```bash
# suíte automatizada, sem rede e sem janela
python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v

# roteiro do checklist de ponta a ponta, com relatório
python "Atividade AP1/test_ap1.py" --smoke

# custo por quadro
python "Atividade AP1/test_ap1.py" --bench
```

São **228 testes** em dois arquivos: `test_ap1.py` cobre o motor, a cena, a cabine, a
câmera, o HUD e o roteiro do checklist; `test_sistema_solar.py` cobre as efemérides
contra valores do JPL Horizons, o catálogo e os leitores das fontes online. Um teste de
**quadros-ouro** compara a assinatura visual de cada enquadramento com uma referência
guardada em `dados/assinaturas.json`; depois de uma mudança visual deliberada, regrave-a
com `python "Atividade AP1/test_ap1.py" --assinaturas`.

O orçamento a 60 FPS é de 16,7 ms por quadro. Medido em 1080×720, com a sequência
rodando: Terra-Lua-L2 4 ms, Terra e satélites 9 ms, órbita baixa 10 ms, Sistema Solar
13 ms, vizinhança 15 ms, cabine 18 ms, estação 19 ms e doca 22 ms. As vistas de
acoplamento, que são as mais densas, ficam entre 45 e 55 FPS; em 1920×1080 o custo sobe
cerca de 20%. `--bench --res LxA --max-ms N` devolve erro acima do limite, e é o que o CI
usa para pegar regressão de desempenho.

---

### 8. Estrutura do repositório

```
space-station-pygame/
├── Atividade AP1/            # Entrega avaliativa
│   ├── ap1.py                # aplicação e motor
│   ├── efemerides.py         # onde cada corpo está
│   ├── catalogo.py           # o que cada corpo é
│   ├── fontes_online.py      # dados que envelhecem, em thread
│   ├── ferramentas/          # geração dos snapshots
│   ├── dados/                # snapshots versionados e mapas de cor
│   ├── test_ap1.py           # motor, cena e checklist (+ --smoke e --bench)
│   ├── test_sistema_solar.py # efemérides, catálogo e fontes
│   ├── requirements.txt
│   ├── Atividade-AP_1.pdf    # enunciado oficial
│   └── README.md             # enunciado resumido, conformidade e roteiro de testes
├── docs/                     # Entregas documentais das etapas 1 a 3
└── Materiais de aula/        # Material de apoio da disciplina
```

---

### 9. Fontes dos dados e licenças

| Fonte | O que fornece | Licença |
|---|---|---|
| JPL — *Approximate Positions of the Planets* | Elementos dos oito planetas | Domínio público (NASA) |
| JPL Horizons | Luas, anões, asteroides, cometas e o James Webb | Domínio público (NASA) |
| JPL Small-Body Database | ~4.100 asteroides e cometas | Domínio público (NASA) |
| CelesTrak | Elementos dos satélites artificiais (GP/OMM) | Uso livre com atribuição |
| VizieR — Yale Bright Star Catalogue (V/50) | Estrelas a olho nu | Uso acadêmico livre |
| Solar System Scope | Mapas de cor dos planetas | CC BY 4.0 |
| ESA/Webb e ESA/Hubble | Imagens de fundo | CC BY 4.0 |
| STScI | Agenda de observação do James Webb | Domínio público (NASA) |

Os créditos completos das imagens aparecem na própria aplicação, ao lado do fundo e na
tela de créditos (`TAB`), como a licença CC BY 4.0 exige.
