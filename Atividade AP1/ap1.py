"""
AP1 - Computação Gráfica e RA/RV
Mundo Virtual Animado: Estação Orbital Órbita-2 (Equipe 2 - Estação Espacial)

Renderizador 3D escrito do zero sobre Pygame, sem OpenGL, sem numpy e sem
bibliotecas de modelagem. Todo o pipeline é calculado neste arquivo:
transformações de modelo (ângulos de Euler ou base ortonormal), câmera look-at,
recorte no plano próximo, projeção em perspectiva, back-face culling, ordenação
por profundidade (algoritmo do pintor), sombreamento Lambertiano plano e níveis
de detalhe pelo tamanho projetado na tela.

A estação é fictícia, mas o resto do Sistema Solar é real, em escala real e na
posição do instante atual: `efemerides.py` calcula onde cada corpo está,
`catalogo.py` descreve os corpos e lê os snapshots de dados/, e
`fontes_online.py` busca em segundo plano o que envelhece (elementos dos
satélites, vetores do James Webb, imagens e agenda dos telescópios).

Execução:  python "Atividade AP1/ap1.py" [--tela-cheia] [--offline]
Testes:    python -m unittest discover -s "Atividade AP1" -p "test_*.py"

Importar este módulo NÃO abre janela nem inicializa o Pygame: a inicialização
acontece apenas dentro de main().
"""

import io
import math
import os
import random
import sys
import time
from datetime import datetime, timezone

import pygame

import catalogo
import efemerides as ef
import fontes_online

# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================
BASE_WIDTH, BASE_HEIGHT = 1080, 720
# WIDTH, HEIGHT, FOV, VIEW_CENTER_* e FRUSTUM_PLANES são reatribuídos por
# configurar_viewport quando a superfície de desenho muda de tamanho: é o que
# faz a tela cheia usar a resolução nativa em vez de ampliar a janela.
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
FPS = 60
FOV_BASE = 620.0     # distância focal na altura de referência, em pixels
FOV = FOV_BASE
NEAR = 8.0           # plano próximo: nada mais perto que isso é desenhado
BG_COLOR = (6, 8, 14)

VIEW_CENTER_X = WIDTH * 0.5
VIEW_CENTER_Y = HEIGHT * 0.53    # desloca a cena para baixo do painel do HUD

WORLD_UP = (0.0, 1.0, 0.0)
AMBIENT = 0.22       # luz ambiente; evita faces completamente pretas

# Multiplicador global de resolução das malhas. Serve para calibrar a cena
# inteira de uma vez: 1.0 é a densidade de referência, valores menores aliviam
# o custo por quadro sem reescrever nenhum construtor.
DETAIL = 0.72


def resolucao(base, minimo=3):
    """Resolução efetiva de uma malha, escalada por DETAIL."""
    return max(minimo, int(round(base * DETAIL)))


# Linha do tempo da sequência (segundos)
PHASE_BOUNDS = (4.0, 7.0, 10.0, 14.0)
TOTAL_SEQUENCE_TIME = PHASE_BOUNDS[-1]
# Modo de órbita estendida: a fase de inspeção passa a durar o suficiente para
# o robô de referência (1 rad/s) completar três voltas inteiras.
ORBIT_TURNS = 3.0
EXTENDED_ORBIT_TIME = 2.0 * math.pi * ORBIT_TURNS

SPEED_STEPS = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)
DEFAULT_SPEED_INDEX = 2

# Escala de tempo do ambiente orbital: quanto tempo simulado passa a cada
# segundo de relógio. A sequência de acoplamento tem relógio próprio e não muda.
TIME_SCALES = (
    (1.0, "tempo real"), (60.0, "1 min/s"), (3600.0, "1 h/s"), (86400.0, "1 dia/s"),
    (604800.0, "1 semana/s"), (2629746.0, "1 mês/s"), (31556952.0, "1 ano/s"),
)
DEFAULT_TIME_SCALE = 0

PHASE_NAMES = (
    "Fase 1: Aproximação do Cargueiro",
    "Fase 2: Abertura da Comporta de Doca",
    "Fase 3: Acoplamento do Módulo",
    "Fase 4: Órbita de Inspeção dos Robôs",
)

# Âncora da câmera antes da primeira atualização da cena
STATION_ORIGIN = (0.0, 0.0, 560.0)
KM = ef.KM                       # unidades de mundo por km: 1 u = 0,2 m


# ============================================================
# 2. MATEMÁTICA VETORIAL
# ============================================================
def vec_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vec_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vec_scale(v, s): return (v[0] * s, v[1] * s, v[2] * s)
def dot_product(u, v): return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def cross_product(u, v):
    return (u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0])


def length(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def normalize(v):
    n = length(v)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(t):
    """Interpolação suave em [0, 1]: começa e termina com derivada nula."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def face_normal(pts):
    """Normal unitária de um polígono; None se a face for degenerada."""
    p0 = pts[0]
    for i in range(1, len(pts) - 1):
        n = cross_product(vec_sub(pts[i], p0), vec_sub(pts[i + 1], p0))
        if length(n) > 1e-9:
            return normalize(n)
    return None


def rotate_xyz(point, rot):
    """Rotaciona um ponto na ordem X -> Y -> Z. Ângulos em graus."""
    x, y, z = point
    rx, ry, rz = rot
    if rx:
        c, s = math.cos(math.radians(rx)), math.sin(math.radians(rx))
        y, z = y * c - z * s, y * s + z * c
    if ry:
        c, s = math.cos(math.radians(ry)), math.sin(math.radians(ry))
        x, z = x * c + z * s, -x * s + z * c
    if rz:
        c, s = math.cos(math.radians(rz)), math.sin(math.radians(rz))
        x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


# --- Matrizes de rotação 3x3 ------------------------------------------------
# Uma base é guardada como três colunas: as imagens dos eixos X, Y e Z locais.
# Aplicar a base é combinar as colunas; compor duas bases é aplicar a da
# esquerda em cada coluna da direita. Com isso a hierarquia pai -> filho vira
# multiplicação de matrizes, sem o truque de canais de Euler que o braço dos
# robôs precisou antes.
IDENTIDADE = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def mat_apply(m, v):
    """Base aplicada a um vetor: x·col0 + y·col1 + z·col2."""
    a, b, c = m
    x, y, z = v
    return (a[0] * x + b[0] * y + c[0] * z,
            a[1] * x + b[1] * y + c[1] * z,
            a[2] * x + b[2] * y + c[2] * z)


def mat_apply_t(m, v):
    """Transposta aplicada: leva do mundo para o referencial da base (a inversa de uma rotação)."""
    return (dot_product(m[0], v), dot_product(m[1], v), dot_product(m[2], v))


def mat_mul(a, b):
    """Composição a · b: primeiro gira por b, depois por a."""
    return (mat_apply(a, b[0]), mat_apply(a, b[1]), mat_apply(a, b[2]))


def mat_from_euler(rot):
    """A mesma rotação de rotate_xyz, como base."""
    return (rotate_xyz((1.0, 0.0, 0.0), rot), rotate_xyz((0.0, 1.0, 0.0), rot),
            rotate_xyz((0.0, 0.0, 1.0), rot))


def mat_axis_angle(eixo, graus):
    """
    Rotação em torno de um eixo qualquer (fórmula de Rodrigues). Com os eixos
    coordenados, dá exatamente o mesmo sentido de rotate_xyz.
    """
    k = normalize(eixo)
    c, s = math.cos(math.radians(graus)), math.sin(math.radians(graus))

    def gira(v):
        kv = cross_product(k, v)
        kd = dot_product(k, v) * (1.0 - c)
        return (v[0] * c + kv[0] * s + k[0] * kd,
                v[1] * c + kv[1] * s + k[1] * kd,
                v[2] * c + kv[2] * s + k[2] * kd)

    return (gira((1.0, 0.0, 0.0)), gira((0.0, 1.0, 0.0)), gira((0.0, 0.0, 1.0)))


def mat_from_axes(eixo_x, eixo_y):
    """Base ortonormal com X na direção dada e Y o mais próximo possível da segunda."""
    x = normalize(eixo_x)
    y = normalize(vec_sub(eixo_y, vec_scale(x, dot_product(x, eixo_y))))
    if length(y) < 0.5:
        y = normalize(cross_product((0.0, 0.0, 1.0) if abs(x[2]) < 0.9 else (1.0, 0.0, 0.0), x))
    return (x, y, cross_product(x, y))


def angulo_de_rastreio(base, eixo_local, normal_local, direcao, dupla_face=False):
    """
    Ângulo, em graus, que uma junta de um eixo precisa girar para a normal do
    painel apontar o mais perto possível de `direcao` (o Sol).

    Girar a normal n0 em torno de um eixo a perpendicular a ela dá
    n(θ) = n0·cos θ + (a × n0)·sen θ; o máximo de n(θ)·s está em
    θ = atan2(s·(a × n0), s·n0). A componente de s ao longo do eixo não se
    alcança com uma junta só — é o "ângulo beta" que o painel [H] mostra.
    Com células nas duas faces, basta girar até ±90°.
    """
    a = mat_apply(base, eixo_local)
    n0 = mat_apply(base, normal_local)
    b = cross_product(a, n0)
    theta = math.degrees(math.atan2(dot_product(direcao, b), dot_product(direcao, n0)))
    if dupla_face:
        if theta > 90.0:
            theta -= 180.0
        elif theta < -90.0:
            theta += 180.0
    return theta


def ray_sphere(origin, direction, center, radius):
    """
    Interseção raio-esfera. `direction` deve estar normalizado.
    Devolve o menor t > 0 do ponto de entrada, ou None se não houver acerto
    à frente da origem. É a base do teste de linha de visão (requisito 9).
    """
    oc = vec_sub(origin, center)
    b = 2.0 * dot_product(oc, direction)
    c = dot_product(oc, oc) - radius * radius
    disc = b * b - 4.0 * c
    if disc < 0.0:
        return None
    raiz = math.sqrt(disc)
    t1 = (-b - raiz) * 0.5
    t2 = (-b + raiz) * 0.5
    for t in (t1, t2):
        if t > 1e-4:
            return t
    return None


LIGHT_DIR = normalize((0.44, 0.70, -0.56))   # direção de referência do sol para shade()
FILL_DIR = normalize((-0.62, -0.34, 0.70))   # preenchimento frio, refletido do planeta
FILL_WEIGHT = (0.10, 0.15, 0.26)             # mais azul que vermelho
DIFFUSE_WEIGHT = 0.78


def shade(color, normal, gloss=0.0):
    """
    Sombreamento de uma face: ambiente, difusa Lambertiana do sol, uma luz de
    preenchimento fria vinda do planeta e um realce especular Blinn-Phong.
    `collect` reproduz esta mesma conta embutida no laço, por desempenho; esta
    função é a referência legível e a que os testes exercitam.
    """
    dif = max(0.0, dot_product(normal, LIGHT_DIR)) * DIFFUSE_WEIGHT
    fill = max(0.0, dot_product(normal, FILL_DIR))
    esp = 0.0
    if gloss:
        h = normalize(vec_add(LIGHT_DIR, (0.0, 0.0, -1.0)))
        s = max(0.0, dot_product(normal, h))
        esp = gloss * (s ** 16)
    return tuple(int(c * clamp(AMBIENT + dif + FILL_WEIGHT[i] * fill + esp, 0.0, 1.0))
                 for i, c in enumerate(color[:3]))


# ============================================================
# 3. REFERENCIAIS ORBITAIS
# ============================================================
# O mundo é heliocêntrico: o Sol fica na origem e as posições vêm de
# efemerides.py, em escala real (1 unidade = 0,2 m). Com números de ponto
# flutuante duplos a precisão sobra: a 50 UA um passo de arredondamento ainda é
# menor que um milímetro, e toda projeção trabalha com diferenças até a câmera.
SUN_POS = (0.0, 0.0, 0.0)
STARFIELD_DISTANCE = 1.0e5             # casca de estrelas, praticamente no infinito

# A Órbita-2 é fictícia, mas voa numa órbita baixa física, como a da ISS
STATION_ALTITUDE_KM = 420.0
STATION_INCLINATION = 51.6
# Arfagem fixa sobre o referencial LVLH: põe a Terra atrás e abaixo da estação
# no plano geral, como nas fotos de acoplamento da ISS. Sem ela, o horizonte
# ficaria na borda de baixo da tela, escondido pelo rodapé do HUD.
STATION_PITCH = 32.0


def orbit_point(centro, raio, angulo, inclinacao):
    """
    Ponto de uma órbita circular em torno de `centro`. A órbita nasce no plano
    XZ e é inclinada em torno do eixo X. Serve às órbitas locais em torno da
    estação (o campo de detritos).
    """
    local = (raio * math.cos(angulo), 0.0, raio * math.sin(angulo))
    return vec_add(centro, rotate_xyz(local, (inclinacao, 0.0, 0.0)))


def lvlh_basis(radial, velocidade):
    """
    Referencial orbital local (LVLH): X ao longo da velocidade, Y para o zênite
    e Z completando a base. É a atitude das estações reais: a Terra fica sempre
    "embaixo", por mais que a órbita dê a volta no planeta.
    """
    return mat_from_axes(velocidade, radial)


# ============================================================
# 4. CÂMERA (look-at)
# ============================================================
# Os presets são deslocamentos em relação ao ponto ancorado, não posições
# absolutas, e ficam no referencial da âncora: na estação, o referencial LVLH;
# nos enquadramentos orbitais, a eclíptica.
CAMERA_PRESETS = {
    "geral":    {"name": "Plano Geral [C]",     "eye": (20.0, 60.0, -700.0),   "target": (20.0, 0.0, 0.0)},
    "superior": {"name": "Visão Superior [W]",  "eye": (30.0, 540.0, -300.0),  "target": (20.0, 0.0, 0.0)},
    "inferior": {"name": "Visão Inferior [S]",  "eye": (10.0, -430.0, -330.0), "target": (20.0, 10.0, 0.0)},
    "esquerda": {"name": "Flanco Esquerdo [A]", "eye": (-560.0, 170.0, -420.0), "target": (30.0, 0.0, 30.0)},
    "direita":  {"name": "Flanco Direito [D]",  "eye": (600.0, 180.0, -360.0),  "target": (20.0, 0.0, 30.0)},
}
# Nos enquadramentos do Sistema Solar o plano geral fica elevado: vistas quase de
# perfil achatariam as órbitas em linhas
ORBITAL_PRESETS = {
    "geral":    {"eye": (0.0, 300.0, -640.0),  "target": (0.0, 0.0, 0.0)},
    "superior": {"eye": (0.0, 700.0, -50.0),   "target": (0.0, 0.0, 0.0)},
    "inferior": {"eye": (0.0, -700.0, -50.0),  "target": (0.0, 0.0, 0.0)},
    "esquerda": {"eye": (-660.0, 150.0, -160.0), "target": (0.0, 0.0, 0.0)},
    "direita":  {"eye": (660.0, 150.0, -160.0),  "target": (0.0, 0.0, 0.0)},
}
PRESET_DISTANCE = 703.0                 # comprimento do olho do plano geral
DEFAULT_CAMERA = "geral"
FOLLOW_CAMERA = "foco"
FOLLOW_NAME = "Foco Animado no Cargueiro [F]"
FOLLOW_OFFSET = (250.0, 130.0, -430.0)  # deslocamento do olho em relação ao alvo
# Tour de câmera (tecla T): um enquadramento por fase da sequência
TOUR_CAMERAS = ("direita", FOLLOW_CAMERA, "geral", "superior")


def escala_para_km(distancia_km):
    """Fator de zoom que põe o olho do plano geral a esta distância da âncora."""
    return distancia_km * KM / PRESET_DISTANCE


# Níveis de zoom: cada um escolhe o que fica no centro do quadro e a distância.
# Da comporta de doca, a 40 m, até o Cinturão de Kuiper, a 190 UA — sem mudar a
# escala do mundo, só a da câmera.
ZOOM_LEVELS = (
    {"name": "Doca",               "anchor": "station", "scale": 0.30},
    {"name": "Estação",            "anchor": "station", "scale": 1.00},
    {"name": "Vizinhança (3 km)",  "anchor": "station", "scale": escala_para_km(3.0)},
    {"name": "Órbita baixa",       "anchor": "station", "scale": escala_para_km(2600.0)},
    {"name": "Terra e satélites",  "anchor": "earth",   "scale": escala_para_km(160000.0)},
    {"name": "Terra, Lua e L2",    "anchor": "earth",   "scale": escala_para_km(2.9e6)},
    {"name": "Sistema interno",    "anchor": "sun",     "scale": escala_para_km(4.2 * ef.UA_KM)},
    {"name": "Sistema Solar",      "anchor": "sun",     "scale": escala_para_km(68.0 * ef.UA_KM)},
    {"name": "Kuiper e além",      "anchor": "sun",     "scale": escala_para_km(190.0 * ef.UA_KM)},
)
DEFAULT_ZOOM = 1


def _interpolar_deslocamento(atual, meta, k):
    """
    Aproxima um deslocamento da meta interpolando direção e o logaritmo do
    comprimento. Entre a doca (40 m) e o Sistema Solar (10 bilhões de km) um
    lerp comum saltaria quase tudo no primeiro quadro e rastejaria no resto;
    em escala logarítmica cada quadro percorre a mesma fração de ordens de
    grandeza, e a viagem de zoom fica visível.
    """
    la, lm = length(atual), length(meta)
    if la < 1e-6 or lm < 1e-6:
        return [lerp(atual[i], meta[i], k) for i in range(3)]
    comprimento = math.exp(lerp(math.log(la), math.log(lm), k))
    d = [lerp(atual[i] / la, meta[i] / lm, k) for i in range(3)]
    n = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
    if n < 1e-6:                             # direções opostas: sem meio-termo
        return [lerp(atual[i], meta[i], k) for i in range(3)]
    return [d[i] / n * comprimento for i in range(3)]


class Camera:
    """
    Câmera look-at ancorada num ponto móvel com referencial próprio. Olho e
    alvo são guardados como deslocamentos no referencial da âncora e
    interpolados ali; a base ortonormal é reconstruída a cada quadro. O preset
    define o deslocamento; o nível de zoom multiplica esse deslocamento e
    escolhe quem é a âncora.
    """

    def __init__(self, preset=DEFAULT_CAMERA, anchor=None):
        self.presets = CAMERA_PRESETS
        self.key = preset
        self.name = CAMERA_PRESETS[preset]["name"]
        self.eye_offset = CAMERA_PRESETS[preset]["eye"]
        self.target_offset = CAMERA_PRESETS[preset]["target"]
        self.anchor = list(anchor if anchor is not None else STATION_ORIGIN)
        self.anchor_basis = IDENTIDADE
        self.anchor_source = None
        self.zoom = 1.0
        self.follow_mesh = None
        # tremor somado por cima da pose (efeito de acoplamento); fica fora da
        # interpolação, então não acumula deriva
        self.shake = (0.0, 0.0, 0.0)
        # direção de onde vem a luz de preenchimento (a Terra, perto dela)
        self.fill_dir = FILL_DIR
        self._assentar()
        self._rebuild_basis()

    def _world(self, rel):
        return vec_add(self.anchor, mat_apply(self.anchor_basis, rel))

    def _fonte(self):
        """Quem é a âncora agora: muda ao entrar ou sair do foco e ao trocar de zoom."""
        if self.follow_mesh is not None:
            return ("malha", id(self.follow_mesh))
        return ("ancora", self.anchor_source)

    def _assentar(self):
        """Coloca a câmera exatamente no preset atual, sem transição."""
        self._eye_rel = [c * self.zoom for c in self.eye_offset]
        self._target_rel = [c * self.zoom for c in self.target_offset]
        self._fonte_vista = self._fonte()
        self._shake_aplicado = (0.0, 0.0, 0.0)
        self.eye = list(self._world(self._eye_rel))
        self.target = list(self._world(self._target_rel))
        self.eye_goal = list(self.eye)
        self.target_goal = list(self.target)

    def _aplicar_preset(self):
        if self.key == FOLLOW_CAMERA:
            return
        p = self.presets[self.key]
        self.name = CAMERA_PRESETS[self.key]["name"]
        self.eye_offset = p["eye"]
        self.target_offset = p["target"]

    def usar_presets_orbitais(self, orbital):
        """Troca a tabela de presets entre a da estação e a dos enquadramentos orbitais."""
        tabela = ORBITAL_PRESETS if orbital else CAMERA_PRESETS
        if tabela is not self.presets:
            self.presets = tabela
            self._aplicar_preset()

    def go_to(self, preset):
        """Agenda a transição suave para um preset."""
        self.key = preset
        self.follow_mesh = None
        self._aplicar_preset()

    def follow(self, mesh):
        """Entra no modo de foco animado: a âncora passa a ser um objeto móvel."""
        self.key = FOLLOW_CAMERA
        self.name = FOLLOW_NAME
        self.eye_offset = FOLLOW_OFFSET
        self.target_offset = (0.0, 0.0, 0.0)
        self.follow_mesh = mesh

    def set_anchor(self, pos, zoom=None, fonte=None, basis=None):
        """
        Ponto que a câmera acompanha, atualizado pela cena a cada quadro.
        `fonte` diz quem é a âncora ("station", "earth", "sun", um corpo);
        quando ela troca, `update` recalcula o deslocamento para não saltar.
        `basis` é o referencial em que os presets são lidos.
        """
        self.anchor = list(pos)
        if zoom is not None:
            self.zoom = zoom
        if fonte is not None:
            self.anchor_source = fonte
        if basis is not None:
            self.anchor_basis = basis

    def snap_to(self, preset):
        """Salta instantaneamente para um preset (usado no reset)."""
        self.go_to(preset)
        self._assentar()
        self._rebuild_basis()

    def update(self, dt):
        """
        Interpola o deslocamento no referencial da âncora, e não a posição
        absoluta. A estação orbita a Terra a 7,7 km/s e a Terra orbita o Sol a
        30 km/s: um lerp em coordenadas de mundo deixaria a câmera para trás, e
        um lerp fora do referencial LVLH faria o horizonte oscilar.
        """
        if self.follow_mesh is not None:
            self.anchor = list(self.follow_mesh.pos)
        fonte = self._fonte()
        if fonte != self._fonte_vista:
            # a âncora trocou de dono: o deslocamento parte da pose atual, então a
            # troca continua sendo uma transição suave, e não um corte
            sx, sy, sz = self._shake_aplicado
            olho = (self.eye[0] - sx, self.eye[1] - sy, self.eye[2] - sz)
            alvo = (self.target[0] - sx, self.target[1] - sy, self.target[2] - sz)
            self._eye_rel = list(mat_apply_t(self.anchor_basis, vec_sub(olho, self.anchor)))
            self._target_rel = list(mat_apply_t(self.anchor_basis, vec_sub(alvo, self.anchor)))
            self._fonte_vista = fonte
        z = self.zoom
        meta_olho = [c * z for c in self.eye_offset]
        meta_alvo = [c * z for c in self.target_offset]
        k = min(1.0, 5.0 * dt)
        self._eye_rel = _interpolar_deslocamento(self._eye_rel, meta_olho, k)
        self._target_rel = _interpolar_deslocamento(self._target_rel, meta_alvo, k)
        self.eye_goal = list(self._world(meta_olho))
        self.target_goal = list(self._world(meta_alvo))
        olho = self._world(self._eye_rel)
        alvo = self._world(self._target_rel)
        for i in range(3):
            self.eye[i] = olho[i] + self.shake[i]
            self.target[i] = alvo[i] + self.shake[i]
        self._shake_aplicado = tuple(self.shake)
        self._rebuild_basis()

    def _rebuild_basis(self):
        """Base ortonormal (right, up, forward) do espaço de câmera."""
        fwd = normalize(vec_sub(self.target, self.eye))
        if length(fwd) < 0.5:                       # alvo coincide com o olho
            fwd = self.anchor_basis[2]
        up_ref = self.anchor_basis[1]
        if abs(dot_product(fwd, up_ref)) > 0.999:   # olhando reto para cima/baixo
            up_ref = self.anchor_basis[2]
        right = normalize(cross_product(up_ref, fwd))
        up = cross_product(fwd, right)
        self.forward = fwd
        self.right = right
        self.up = up
        # direção da luz já no espaço de câmera: como a transformação é uma
        # rotação, o produto escalar com a normal dá o mesmo resultado que no
        # mundo, e o sombreamento deixa de precisar das normais em coordenadas
        # de mundo
        self.light_view = (dot_product(LIGHT_DIR, right),
                           dot_product(LIGHT_DIR, up),
                           dot_product(LIGHT_DIR, fwd))
        self.fill_view = (dot_product(self.fill_dir, right),
                          dot_product(self.fill_dir, up),
                          dot_product(self.fill_dir, fwd))
        # vetor intermediário de Blinn-Phong. A direção de vista é tomada como
        # constante (-Z da câmera), aproximação usual para campos de visão
        # moderados: assim o realce custa um produto escalar por face.
        self.half_view = normalize((self.light_view[0],
                                    self.light_view[1],
                                    self.light_view[2] - 1.0))

    def to_view(self, p):
        """Ponto do mundo -> espaço de câmera. z positivo = à frente do olho."""
        d = vec_sub(p, self.eye)
        return (dot_product(d, self.right),
                dot_product(d, self.up),
                dot_product(d, self.forward))


# ============================================================
# 5. PROJEÇÃO E RECORTE
# ============================================================
def project_view(v):
    """Espaço de câmera -> pixels. Assume v[2] >= NEAR (já recortado)."""
    z = v[2] if v[2] > NEAR else NEAR
    return (int(v[0] * FOV / z + VIEW_CENTER_X),
            int(-v[1] * FOV / z + VIEW_CENTER_Y))


def frustum_planes():
    """
    Os quatro planos laterais do tronco de visão, em espaço de câmera. Todos
    passam pela origem (o olho), então bastam as normais apontando para dentro.
    O centro óptico é deslocado verticalmente, por isso os limites de cima e de
    baixo não são simétricos.
    """
    return tuple(normalize(n) for n in (
        (FOV, 0.0, VIEW_CENTER_X),                    # esquerda
        (-FOV, 0.0, WIDTH - VIEW_CENTER_X),           # direita
        (0.0, -FOV, VIEW_CENTER_Y),                   # topo
        (0.0, FOV, HEIGHT - VIEW_CENTER_Y),           # base
    ))


FRUSTUM_PLANES = frustum_planes()


def configurar_viewport(largura, altura):
    """
    Ajusta a projeção a uma superfície de outro tamanho. A distância focal
    acompanha a altura, então o enquadramento vertical é o mesmo em qualquer
    resolução e uma tela mais larga só ganha campo nas laterais. Devolve True
    se algo mudou.
    """
    global WIDTH, HEIGHT, FOV, VIEW_CENTER_X, VIEW_CENTER_Y, FRUSTUM_PLANES
    largura, altura = int(largura), int(altura)
    if (largura, altura) == (WIDTH, HEIGHT):
        return False
    WIDTH, HEIGHT = largura, altura
    FOV = FOV_BASE * altura / BASE_HEIGHT
    VIEW_CENTER_X = largura * 0.5
    VIEW_CENTER_Y = altura * 0.53
    FRUSTUM_PLANES = frustum_planes()
    return True


def clip_near(poly):
    """
    Recorta um polígono do espaço de câmera contra o plano z = NEAR
    (Sutherland-Hodgman com um único plano). Substitui o antigo grampeamento
    de z, que deformava polígonos próximos em vez de cortá-los.
    """
    out = []
    n = len(poly)
    for i in range(n):
        cur = poly[i]
        nxt = poly[(i + 1) % n]
        cur_in = cur[2] >= NEAR
        nxt_in = nxt[2] >= NEAR
        if cur_in:
            out.append(cur)
        if cur_in != nxt_in:
            t = (NEAR - cur[2]) / (nxt[2] - cur[2])
            out.append((lerp(cur[0], nxt[0], t), lerp(cur[1], nxt[1], t), NEAR))
    return out


# Margem além da borda da janela para o recorte 2D. Uma face cortada no plano
# próximo projeta para dezenas de milhares de pixels, e o Pygame percorre cada
# linha do polígono mesmo quando nada dele cai na tela.
SCREEN_GUARD = 64


def clip_screen(pontos):
    """
    Recorta um polígono já projetado contra a janela ampliada pela margem de
    guarda (Sutherland-Hodgman com os quatro lados do retângulo). O que sai fica
    fora da tela: a imagem não muda, só o custo de rasterização.
    """
    for eixo, limite, sentido in ((0, -SCREEN_GUARD, 1.0), (0, WIDTH + SCREEN_GUARD, -1.0),
                                  (1, -SCREEN_GUARD, 1.0), (1, HEIGHT + SCREEN_GUARD, -1.0)):
        n = len(pontos)
        if n < 3:
            return []
        out = []
        for i in range(n):
            cur = pontos[i]
            nxt = pontos[(i + 1) % n]
            cur_in = (cur[eixo] - limite) * sentido >= 0.0
            nxt_in = (nxt[eixo] - limite) * sentido >= 0.0
            if cur_in:
                out.append(cur)
            if cur_in != nxt_in:
                t = (limite - cur[eixo]) / (nxt[eixo] - cur[eixo])
                out.append((lerp(cur[0], nxt[0], t), lerp(cur[1], nxt[1], t)))
        pontos = out
    return [(int(x), int(y)) for x, y in pontos]


def project_point(p, camera):
    """Projeta um ponto isolado; None se estiver atrás do plano próximo."""
    v = camera.to_view(p)
    if v[2] < NEAR:
        return None
    return project_view(v)


# ============================================================
# 6. MALHA POLIGONAL
# ============================================================
class PolyMesh:
    """
    Malha de polígonos com transformação própria (escala -> rotação ->
    translação). A rotação vem de ângulos de Euler ou, quando `basis` está
    definida, de uma base ortonormal — é o que a hierarquia de juntas e os
    corpos celestes usam. Guarda uma cor por face, o que permite detalhar um
    objeto composto sem multiplicar o número de malhas.

    Duas otimizações sustentam a densidade de malha da cena:
    o resultado da transformação de modelo é reaproveitado enquanto a pose não
    muda, e `collect` leva cada vértice para o espaço de câmera uma única vez,
    em vez de uma vez por face que o utiliza.

    Em escala real quase tudo fica menor que um pixel: `marker_color` faz a
    malha virar um marcador nessa situação, e `lods` troca a geometria pelo
    tamanho projetado.
    """

    def __init__(self, vertices, faces, face_colors, position=(0, 0, 0),
                 rotation=(0, 0, 0), scale=1.0, name="", gloss=0.30, basis=None,
                 marker_color=None, marker_size=2, edges=True):
        self.base_vertices = list(vertices)
        self.faces = list(faces)
        self.face_colors = list(face_colors)
        self.pos = list(position)
        self.rotation = list(rotation)
        self.scale = scale
        self.basis = basis
        self.name = name
        self.gloss = gloss          # 0 para superfícies foscas (rocha, painel)
        self.shadow = 0.0           # 0 em pleno sol, 1 no centro do eclipse
        self.visible = True
        self.marker_color = marker_color
        self.marker_size = marker_size
        # contorno claro nas faces grandes: dá leitura de facetas às naves, mas
        # num planeta desenharia a grade da malha por cima do mapa
        self.edges = edges
        # raio da esfera envolvente em espaço local (multiplicado pela escala
        # no acesso), usado pelo teste de linha de visão
        self.local_radius = max((length(v) for v in self.base_vertices), default=0.0)
        self.lods = None
        self._lod_atual = None
        self._pose_cache = None
        self._world_cache = None

    @property
    def bounding_radius(self):
        return self.local_radius * self.scale

    def update(self, pos=None, rot=None, scale=None, basis=None):
        if pos is not None:
            self.pos = list(pos)
        if rot is not None:
            self.rotation = list(rot)
        if scale is not None:
            self.scale = scale
        if basis is not None:
            self.basis = basis

    def pose(self):
        """Assinatura da transformação atual; controla o cache de vértices."""
        return (self.pos[0], self.pos[1], self.pos[2],
                self.rotation[0], self.rotation[1], self.rotation[2], self.scale,
                self.basis, self._lod_atual)

    def set_geometry(self, vertices, faces, face_colors):
        """Troca a geometria (nível de detalhe, calota do horizonte) e invalida o cache."""
        self.base_vertices = vertices
        self.faces = faces
        self.face_colors = face_colors
        self.local_radius = max((length(v) for v in vertices), default=0.0)
        self._pose_cache = None

    def set_lods(self, niveis):
        """
        `niveis`: [(raio mínimo em pixels, geometria)], onde a geometria é
        (vértices, faces, cores) ou uma função que a constrói na primeira vez
        que for usada. A cena cria dezenas de corpos; construir de antemão as
        versões finas de todos custaria segundos a cada cena.
        """
        self.lods = sorted(([limiar, dados] for limiar, dados in niveis),
                           key=lambda n: -n[0])
        self.use_lod(0.0)

    def use_lod(self, raio_px):
        if not self.lods:
            return
        for nivel in self.lods:
            if raio_px >= nivel[0]:
                break
        if callable(nivel[1]):
            nivel[1] = nivel[1]()
        if nivel[1] is not self._lod_atual:
            self._lod_atual = nivel[1]
            self.set_geometry(*nivel[1])

    def world_vertices(self):
        """
        Vértices em coordenadas de mundo. O resultado fica em cache e só é
        recalculado quando a pose muda — comparar a pose, em vez de confiar em
        quem chama `update`, mantém o cache correto mesmo se alguém alterar
        `pos`, `rotation` ou `scale` diretamente.
        """
        assinatura = self.pose()
        if assinatura == self._pose_cache:
            return self._world_cache

        s = self.scale
        px, py, pz = self.pos
        # a rotação é linear: basta transformar os três vetores da base e
        # combiná-los, em vez de recalcular seno e cosseno por vértice
        if self.basis is not None:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (vec_scale(c, s) for c in self.basis)
        else:
            ax, ay, az = rotate_xyz((s, 0.0, 0.0), self.rotation)
            bx, by, bz = rotate_xyz((0.0, s, 0.0), self.rotation)
            cx, cy, cz = rotate_xyz((0.0, 0.0, s), self.rotation)
        saida = [(vx * ax + vy * bx + vz * cx + px,
                  vx * ay + vy * by + vz * cy + py,
                  vx * az + vy * bz + vz * cz + pz)
                 for vx, vy, vz in self.base_vertices]

        self._pose_cache = assinatura
        self._world_cache = saida
        return saida

    def frustum_test(self, camera):
        """
        Esfera envolvente contra o tronco de visão: 0 fora, 1 cruzando alguma
        borda, 2 inteira dentro. Descarta a malha inteira antes de transformar
        qualquer vértice — é o que sustenta uma cena com muitos objetos sem
        estourar o orçamento por quadro. Só uma malha que cruza a borda pode ter
        faces projetadas fora da janela, então só ela paga o teste por face.
        """
        cx, cy, cz = camera.to_view(self.pos)
        r = self.bounding_radius
        if cz + r < NEAR:
            return 0
        resultado = 2 if cz - r >= NEAR else 1
        for nx, ny, nz in FRUSTUM_PLANES:
            d = nx * cx + ny * cy + nz * cz
            if d < -r:
                return 0
            if d < r:
                resultado = 1
        return resultado

    def in_frustum(self, camera):
        return self.frustum_test(camera) > 0

    def collect(self, camera, emissivo=False):
        """
        Devolve (faces_visiveis, descartadas). Cada face visível é a tupla
        (profundidade, pontos_2d, cor). A profundidade é medida em espaço de
        câmera — usar o z de mundo, como na versão anterior, produzia ordem
        errada em qualquer vista que não fosse a frontal.
        """
        if not self.visible:
            return [], 0
        enquadramento = self.frustum_test(camera)
        if not enquadramento:
            return [], len(self.faces)
        testar_tela = enquadramento == 1

        mundo = self.world_vertices()
        ex, ey, ez = camera.eye
        rx, ry, rz = camera.right
        ux, uy, uz = camera.up
        fx, fy, fz = camera.forward
        # a luz vem da posição do Sol, então a direção muda de objeto para
        # objeto; basta calculá-la uma vez por malha e levá-la ao espaço de
        # câmera junto com o vetor intermediário do realce especular
        luz = normalize(vec_sub(SUN_POS, self.pos))
        if luz == (0.0, 0.0, 0.0):
            luz = LIGHT_DIR
        lvx = luz[0] * rx + luz[1] * ry + luz[2] * rz
        lvy = luz[0] * ux + luz[1] * uy + luz[2] * uz
        lvz = luz[0] * fx + luz[1] * fy + luz[2] * fz
        hvx, hvy, hvz = normalize((lvx, lvy, lvz - 1.0))
        fvx, fvy, fvz = camera.fill_view
        # o eclipse apaga a luz direta, mas não o ambiente
        direta = DIFFUSE_WEIGHT * (1.0 - 0.94 * self.shadow)
        gloss = self.gloss * (1.0 - self.shadow)
        peso_r, peso_g, peso_b = FILL_WEIGHT
        largura, altura = WIDTH, HEIGHT
        cx0, cy0, foco = VIEW_CENTER_X, VIEW_CENTER_Y, FOV

        # mundo -> espaço de câmera, uma única vez por vértice
        vista = []
        z_minimo = 1e30
        for wx, wy, wz in mundo:
            dx = wx - ex
            dy = wy - ey
            dz = wz - ez
            vz = dx * fx + dy * fy + dz * fz
            if vz < z_minimo:
                z_minimo = vz
            vista.append((dx * rx + dy * ry + dz * rz,
                          dx * ux + dy * uy + dz * uz,
                          vz))
        # se a malha inteira está à frente do plano próximo, nenhuma face
        # precisa ser testada para recorte
        testar_recorte = z_minimo < NEAR

        cores = self.face_colors
        prontas = []
        descartadas = 0
        for idx, face in enumerate(self.faces):
            if testar_recorte:
                # face inteira atrás do olho: nem normal nem recorte
                for i in face:
                    if vista[i][2] >= NEAR:
                        break
                else:
                    descartadas += 1
                    continue
            i0 = face[0]
            px0, py0, pz0 = vista[i0]

            # normal da face, pelo primeiro par de arestas não degenerado
            nx = ny = nz = 0.0
            for k in range(1, len(face) - 1):
                qx, qy, qz = vista[face[k]]
                sx, sy, sz = vista[face[k + 1]]
                e1x, e1y, e1z = qx - px0, qy - py0, qz - pz0
                e2x, e2y, e2z = sx - px0, sy - py0, sz - pz0
                nx = e1y * e2z - e1z * e2y
                ny = e1z * e2x - e1x * e2z
                nz = e1x * e2y - e1y * e2x
                if nx * nx + ny * ny + nz * nz > 1e-18:
                    break
            else:
                descartadas += 1
                continue
            comp = math.sqrt(nx * nx + ny * ny + nz * nz)
            nx /= comp
            ny /= comp
            nz /= comp

            # back-face culling: no espaço de câmera o olho está na origem,
            # então o próprio vértice já é o vetor que aponta para a face
            if nx * px0 + ny * py0 + nz * pz0 >= 0.0:
                descartadas += 1
                continue

            poly = [vista[i] for i in face]
            if testar_recorte:
                for v in poly:
                    if v[2] < NEAR:
                        poly = clip_near(poly)
                        break
                if len(poly) < 3:
                    descartadas += 1
                    continue

            soma = 0.0
            pontos = []
            for vx, vy, vz in poly:
                soma += vz
                k = foco / (vz if vz > NEAR else NEAR)
                pontos.append((int(vx * k + cx0), int(-vy * k + cy0)))
            if testar_tela:
                xs = [p[0] for p in pontos]
                ys = [p[1] for p in pontos]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if x1 < 0 or y1 < 0 or x0 >= largura or y0 >= altura:
                    descartadas += 1          # nenhum pixel da face cai na janela
                    continue
                if (x0 < -SCREEN_GUARD or y0 < -SCREEN_GUARD
                        or x1 > largura + SCREEN_GUARD or y1 > altura + SCREEN_GUARD):
                    pontos = clip_screen(pontos)
                    if len(pontos) < 3:
                        descartadas += 1
                        continue
            if emissivo:                      # o Sol emite: não recebe sombreamento
                prontas.append((soma / len(poly), pontos, cores[idx]))
                continue
            difusa = nx * lvx + ny * lvy + nz * lvz
            base = AMBIENT + direta * difusa if difusa > 0.0 else AMBIENT
            if gloss:
                s = nx * hvx + ny * hvy + nz * hvz
                if s > 0.0:
                    s *= s
                    s *= s
                    s *= s
                    s *= s                      # s elevado a 16, sem pow()
                    base += gloss * s
            preenche = nx * fvx + ny * fvy + nz * fvz
            if preenche > 0.0:
                kr = base + peso_r * preenche
                kg = base + peso_g * preenche
                kb = base + peso_b * preenche
            else:
                kr = kg = kb = base
            cor = cores[idx]
            prontas.append((soma / len(poly), pontos,
                            (int(cor[0] * kr) if kr < 1.0 else cor[0],
                             int(cor[1] * kg) if kg < 1.0 else cor[1],
                             int(cor[2] * kb) if kb < 1.0 else cor[2])))
        return prontas, descartadas


# ============================================================
# 7. MODELAGEM GEOMÉTRICA
# ============================================================
class MeshBuilder:
    """
    Acumula vértices, faces e cores. Os helpers já entregam as faces com o
    winding correto (normal apontando para fora), o que é verificado pelos
    testes em test_ap1.py.
    """

    def __init__(self):
        self.verts = []
        self.faces = []
        self.colors = []

    def data(self):
        return self.verts, self.faces, self.colors

    def add_face(self, pontos, color):
        i = len(self.verts)
        self.verts.extend(pontos)
        self.faces.append(tuple(range(i, i + len(pontos))))
        self.colors.append(color)

    def add_two_sided(self, pontos, cor_frente, cor_verso=None):
        """Chapa fina visível dos dois lados: a mesma face nos dois sentidos de winding."""
        self.add_face(pontos, cor_frente)
        self.add_face(list(reversed(pontos)), cor_verso or cor_frente)

    def add_box(self, lo, hi, color, top_color=None):
        """Caixa alinhada aos eixos, de `lo` (mínimo) a `hi` (máximo)."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        i = len(self.verts)
        self.verts.extend([
            (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
            (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1),
        ])
        quads = [
            ((0, 1, 2, 3), color),              # base   (-Y)
            ((4, 7, 6, 5), top_color or color), # topo   (+Y)
            ((0, 4, 5, 1), color),              # frente (-Z)
            ((3, 2, 6, 7), color),              # fundo  (+Z)
            ((0, 3, 7, 4), color),              # esq.   (-X)
            ((1, 5, 6, 2), color),              # dir.   (+X)
        ]
        for q, c in quads:
            self.faces.append(tuple(i + k for k in q))
            self.colors.append(c)

    def add_prism(self, axis, center, radius, half_len, sides, color,
                  cap_color=None, taper=1.0):
        """
        Prisma regular de `sides` lados ao longo de `axis` ('x', 'y' ou 'z').
        `taper` multiplica o raio da tampa positiva: 1.0 = cilindro,
        0.0 = cone. Serve para hub, cascos, bocais e narizes.
        """
        cap_color = cap_color or color
        sides = resolucao(sides)
        anel_neg, anel_pos = [], []
        for k in range(sides):
            a = 2.0 * math.pi * k / sides
            cx, cz = math.cos(a), math.sin(a)
            anel_neg.append(_axis_map(axis, (radius * cx, -half_len, radius * cz)))
            anel_pos.append(_axis_map(axis, (radius * taper * cx, half_len, radius * taper * cz)))
        base = len(self.verts)
        self.verts.extend([vec_add(center, p) for p in anel_neg])
        self.verts.extend([vec_add(center, p) for p in anel_pos])

        if taper < 1e-6:
            # degenera em cone: um triângulo por lado, evitando faces nulas
            apex = base + sides
            for k in range(sides):
                nk = (k + 1) % sides
                self.faces.append((base + k, apex, base + nk))
                self.colors.append(color)
        else:
            for k in range(sides):
                nk = (k + 1) % sides
                self.faces.append((base + k, base + sides + k,
                                   base + sides + nk, base + nk))
                self.colors.append(color)
            self.faces.append(tuple(range(base + 2 * sides - 1, base + sides - 1, -1)))
            self.colors.append(cap_color)
        self.faces.append(tuple(range(base, base + sides)))
        self.colors.append(cap_color)

    def add_bar(self, p0, p1, thickness, color, cap_color=None):
        """
        Barra reta de `p0` a `p1`, com seção quadrada. Como a orientação vem de
        uma base ortonormal destra, o winding da caixa canônica se preserva e as
        normais continuam apontando para fora. É a peça das treliças e mastros.
        """
        d = vec_sub(p1, p0)
        comp = length(d)
        if comp < 1e-6:
            return
        f = normalize(d)
        ref = (0.0, 1.0, 0.0) if abs(f[1]) < 0.9 else (1.0, 0.0, 0.0)
        r = normalize(cross_product(ref, f))
        u = cross_product(f, r)
        h = thickness * 0.5

        def ponto(a, b, c):
            return (p0[0] + r[0] * a + u[0] * b + f[0] * c,
                    p0[1] + r[1] * a + u[1] * b + f[1] * c,
                    p0[2] + r[2] * a + u[2] * b + f[2] * c)

        i = len(self.verts)
        self.verts.extend([
            ponto(-h, -h, 0.0), ponto(h, -h, 0.0), ponto(h, -h, comp), ponto(-h, -h, comp),
            ponto(-h, h, 0.0), ponto(h, h, 0.0), ponto(h, h, comp), ponto(-h, h, comp),
        ])
        tampa = cap_color or color
        for q, c in (((0, 1, 2, 3), color), ((4, 7, 6, 5), color),
                     ((0, 4, 5, 1), tampa), ((3, 2, 6, 7), tampa),
                     ((0, 3, 7, 4), color), ((1, 5, 6, 2), color)):
            self.faces.append(tuple(i + k for k in q))
            self.colors.append(c)

    def add_truss(self, p0, p1, largura, secoes, color, diag_color=None):
        """
        Treliça entre dois pontos: quatro montantes, travessas a cada seção e
        diagonais alternadas. Lê como estrutura de verdade, e não como uma
        caixa lisa, ao custo de geometria simples.
        """
        diag_color = diag_color or color
        d = vec_sub(p1, p0)
        comp = length(d)
        if comp < 1e-6:
            return
        f = normalize(d)
        ref = (0.0, 1.0, 0.0) if abs(f[1]) < 0.9 else (1.0, 0.0, 0.0)
        r = normalize(cross_product(ref, f))
        u = cross_product(f, r)
        h = largura * 0.5
        esp = max(2.0, largura * 0.16)

        def ponto(a, b, c):
            return (p0[0] + r[0] * a + u[0] * b + f[0] * c,
                    p0[1] + r[1] * a + u[1] * b + f[1] * c,
                    p0[2] + r[2] * a + u[2] * b + f[2] * c)

        cantos = ((-h, -h), (h, -h), (h, h), (-h, h))
        for a, b in cantos:                                   # montantes
            self.add_bar(ponto(a, b, 0.0), ponto(a, b, comp), esp, color)

        secoes = max(1, secoes)
        passo = comp / secoes
        for s in range(secoes + 1):                           # travessas
            c = s * passo
            for k in range(4):
                a0, b0 = cantos[k]
                a1, b1 = cantos[(k + 1) % 4]
                self.add_bar(ponto(a0, b0, c), ponto(a1, b1, c), esp * 0.8, color)
        for s in range(secoes):                               # diagonais
            c0, c1 = s * passo, (s + 1) * passo
            k = s % 4
            a0, b0 = cantos[k]
            a1, b1 = cantos[(k + 2) % 4]
            self.add_bar(ponto(a0, b0, c0), ponto(a1, b1, c1), esp * 0.62, diag_color)

    def add_solar_panel(self, centro, largura, comprimento, cols, rows,
                        cor_celula, cor_alterna, cor_moldura):
        """
        Painel solar como grade de células no plano XZ, com moldura e as duas
        faces cobertas. A grade custa só geometria e muda completamente a
        leitura do objeto em relação a uma placa de cor única.
        """
        cx, cy, cz = centro
        esp = 3.2
        self.add_box((cx - largura * 0.5, cy - esp, cz - comprimento * 0.5),
                     (cx + largura * 0.5, cy + esp, cz + comprimento * 0.5),
                     cor_moldura)
        cols = max(2, resolucao(cols, 2))
        rows = max(2, resolucao(rows, 2))
        px = largura / cols
        pz = comprimento / rows
        borda = min(px, pz) * 0.12
        for i in range(cols):
            for j in range(rows):
                x0 = cx - largura * 0.5 + i * px + borda
                x1 = x0 + px - 2 * borda
                z0 = cz - comprimento * 0.5 + j * pz + borda
                z1 = z0 + pz - 2 * borda
                cor = cor_celula if (i + j) % 2 == 0 else cor_alterna
                y = cy + esp + 0.45
                self.add_face([(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)], cor)
                y = cy - esp - 0.45
                self.add_face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], cor)

    def add_wing(self, comprimento, largura, sinal, cols, rows, cor_celula, cor_alterna,
                 cor_moldura, raiz=0.0, espessura=1.2, ao_longo="y"):
        """
        Asa de painel solar que nasce na junta (a origem) e se estende ao longo
        de ±Y, com a largura em Z e a normal em ±X. Girar a malha em torno de Y
        é girar a asa em torno do próprio mastro — é assim que as juntas BGA da
        ISS e o acionador dos painéis do GPS funcionam. Com `ao_longo="z"` a asa
        inteira é girada 90° em torno de X e passa a se estender ao longo de ±Z.
        """
        inicio = len(self.verts)
        y_a, y_b = sorted((raiz * sinal, (raiz + comprimento) * sinal))
        h = largura * 0.5
        e = espessura * 0.5
        self.add_box((-e, y_a, -h), (e, y_b, h), cor_moldura)
        self.add_bar((0.0, 0.0, 0.0), (0.0, y_a if sinal > 0 else y_b, 0.0),
                     max(1.0, espessura * 1.6), cor_moldura)
        cols = max(1, cols)
        rows = max(2, resolucao(rows, 2))
        passo_z = largura / cols
        passo_y = (y_b - y_a) / rows
        borda = min(passo_z, passo_y) * 0.08
        for i in range(cols):
            for j in range(rows):
                za = -h + i * passo_z + borda
                zb = za + passo_z - 2.0 * borda
                ya = y_a + j * passo_y + borda
                yb = ya + passo_y - 2.0 * borda
                cor = cor_celula if (i + j) % 2 == 0 else cor_alterna
                x = e + 0.3
                self.add_face([(x, ya, za), (x, yb, za), (x, yb, zb), (x, ya, zb)], cor)
                x = -e - 0.3
                self.add_face([(x, ya, za), (x, ya, zb), (x, yb, zb), (x, yb, za)], cor)
        if ao_longo == "z":
            for k in range(inicio, len(self.verts)):
                self.verts[k] = rotate_xyz(self.verts[k], (90.0, 0.0, 0.0))

    def add_dish(self, centro, axis, raio, profundidade, sides, cor_interna, cor_externa):
        """Antena parabólica: uma concha rasa, com as duas faces coloridas."""
        sides = resolucao(sides, 6)
        anel = []
        for k in range(sides):
            a = 2.0 * math.pi * k / sides
            anel.append(vec_add(centro, _axis_map(
                axis, (raio * math.cos(a), profundidade, raio * math.sin(a)))))
        fundo = vec_add(centro, _axis_map(axis, (0.0, 0.0, 0.0)))
        i = len(self.verts)
        self.verts.append(fundo)
        self.verts.extend(anel)
        for k in range(sides):
            nk = (k + 1) % sides
            self.faces.append((i, i + 1 + nk, i + 1 + k))       # face côncava
            self.colors.append(cor_interna)
            self.faces.append((i, i + 1 + k, i + 1 + nk))       # costas
            self.colors.append(cor_externa)


def _axis_map(axis, p):
    """
    Leva um ponto gerado em torno do eixo Y para o eixo pedido, usando
    rotações puras (determinante +1) para não inverter o winding.
    """
    x, y, z = p
    if axis == "y":
        return (x, y, z)
    if axis == "x":
        return (y, -x, z)
    return (x, -z, y)          # 'z'


def build_sphere(radius=120.0, rings=10, sectors=16, color=(205, 210, 220),
                 pole_color=None, lumps=None, exato=False):
    """
    Esfera com polos únicos (a versão anterior repetia vértices no polo e
    gerava faces degeneradas). `lumps` é uma lista de harmônicos que deforma
    o raio de acordo com a direção, produzindo detritos irregulares. Com
    `exato`, a resolução não passa por DETAIL: os níveis de detalhe dos
    planetas já são escolhidos pelo tamanho na tela.
    """
    pole_color = pole_color or color
    if not exato:
        rings = resolucao(rings, 4)
        sectors = resolucao(sectors, 5)

    def deform(direcao):
        if not lumps:
            return vec_scale(direcao, radius)
        f = 1.0
        for fx, fy, fz, amp, ph in lumps:
            f += amp * math.sin(fx * direcao[0] + fy * direcao[1] + fz * direcao[2] + ph)
        return vec_scale(direcao, radius * f)

    verts = [deform((0.0, 1.0, 0.0))]
    for r in range(1, rings):
        lat = math.pi * 0.5 - math.pi * r / rings
        cy, cr = math.sin(lat), math.cos(lat)
        for s in range(sectors):
            lon = 2.0 * math.pi * s / sectors
            verts.append(deform((cr * math.cos(lon), cy, cr * math.sin(lon))))
    verts.append(deform((0.0, -1.0, 0.0)))

    topo = 0
    base = len(verts) - 1

    def idx(r, s):
        return 1 + (r - 1) * sectors + (s % sectors)

    faces, colors = [], []
    for s in range(sectors):
        faces.append((topo, idx(1, s + 1), idx(1, s)))
        colors.append(pole_color)
    for r in range(1, rings - 1):
        for s in range(sectors):
            faces.append((idx(r, s), idx(r, s + 1), idx(r + 1, s + 1), idx(r + 1, s)))
            colors.append(color)
    for s in range(sectors):
        faces.append((base, idx(rings - 1, s), idx(rings - 1, s + 1)))
        colors.append(pole_color)
    return verts, faces, colors


# --- Paleta da cena ------------------------------------------------------
C_CASCO = (188, 194, 206)
C_CASCO_ESC = (120, 127, 142)
C_ANEL = (96, 170, 196)
C_PAINEL = (36, 62, 128)
C_PAINEL_BORDA = (150, 158, 176)
C_DOCA = (214, 146, 52)
C_PORTA = (196, 202, 214)
C_CARGA = (208, 212, 220)
C_CARGA_DET = (206, 86, 38)
C_ROBO = (226, 226, 232)
C_DETRITO = (128, 118, 110)
C_PLANETA = (86, 106, 150)
C_PAINEL_ALT = (26, 46, 102)
C_RADIADOR = (232, 234, 240)
C_JANELA = (118, 206, 226)
C_PRATO = (216, 220, 228)
C_BOCAL = (72, 76, 86)
C_LUZ_VERDE = (74, 240, 150)
C_LUZ_VERM = (250, 92, 92)
C_OURO = (236, 186, 76)
C_MLI = (222, 204, 150)          # manta térmica dourada dos satélites
C_KAPTON = (200, 176, 212)       # escudo solar do James Webb
C_PAINEL_ISS = (168, 124, 60)    # asas da ISS: células de tom cobre
C_PAINEL_ISS_ALT = (126, 92, 50)

C_OCEANO = (28, 74, 148)
C_OCEANO_RASO = (46, 108, 184)
C_TERRA = (74, 126, 66)
C_TERRA_SECA = (146, 130, 82)
C_GELO = (238, 244, 250)


def build_earth(radius, rings=16, sectors=28, seed=77):
    """
    Terra procedural: cor por face vinda de um ruído de direção. É o plano B
    quando o mapa de dados/mapas não foi baixado.
    """
    verts, faces, _ = build_sphere(radius, rings=rings, sectors=sectors)
    rng = random.Random(seed)
    harmonicos = [(rng.uniform(1.1, 2.8), rng.uniform(1.1, 2.8), rng.uniform(1.1, 2.8),
                   rng.uniform(0.0, 6.28)) for _ in range(5)]
    cores = []
    for face in faces:
        n = len(face)
        centro = (sum(verts[i][0] for i in face) / n,
                  sum(verts[i][1] for i in face) / n,
                  sum(verts[i][2] for i in face) / n)
        d = normalize(centro)
        altura = 0.0
        for fx, fy, fz, ph in harmonicos:
            altura += math.sin(fx * d[0] * 2.0 + fy * d[1] * 2.0 + fz * d[2] * 2.0 + ph)
        altura /= len(harmonicos)
        if abs(d[1]) > 0.93:
            cores.append(C_GELO)
        elif altura > 0.34:
            cores.append(C_TERRA_SECA)
        elif altura > 0.06:
            cores.append(C_TERRA)
        elif altura > -0.04:
            cores.append(C_OCEANO_RASO)
        else:
            cores.append(C_OCEANO)
    return verts, faces, cores


# --- Corpos celestes com mapas de cor ------------------------------------
class ColorMap:
    """
    Mapa equirretangular (longitude na horizontal, latitude na vertical). Não é
    textura: a malha continua com uma cor por face, só que amostrada do mapa na
    direção do centro da face — sombreamento plano, como o resto da cena.
    """

    _cache = {}

    def __init__(self, superficie):
        self.surface = superficie
        self.w, self.h = superficie.get_size()

    @classmethod
    def load(cls, nome):
        """Mapa de dados/mapas, lido uma vez por processo; None se ausente."""
        if nome in cls._cache:
            return cls._cache[nome]
        mapa = None
        caminho = catalogo.caminho_mapa(nome) if nome else None
        if caminho:
            try:
                mapa = cls(pygame.image.load(caminho))
            except (pygame.error, OSError):
                mapa = None
        cls._cache[nome] = mapa
        return mapa

    def at(self, direcao):
        """Cor (e alfa) na direção local: polo em +Y, longitude de +X para +Z."""
        x, y, z = direcao
        lat = math.asin(clamp(y, -1.0, 1.0))
        lon = math.atan2(z, x)
        u = int((lon / (2.0 * math.pi) + 0.5) * self.w) % self.w
        v = int(clamp(0.5 - lat / math.pi, 0.0, 0.9999) * self.h)
        return self.surface.get_at((u, v))

    def mean(self, direcoes):
        r = g = b = 0
        for d in direcoes:
            c = self.at(d)
            r += c[0]
            g += c[1]
            b += c[2]
        n = len(direcoes)
        return (r // n, g // n, b // n)


def _cores_por_mapa(verts, faces, cor_base, mapa, nuvens=None):
    """Uma cor por face: média do mapa no centro e nos vértices, com nuvens por cima."""
    cores = []
    for face in faces:
        pts = [verts[i] for i in face]
        n = len(pts)
        centro = normalize((sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n,
                            sum(p[2] for p in pts) / n))
        if mapa is None:
            cores.append(cor_base)
            continue
        amostras = [centro] + [normalize(vec_add(centro, normalize(p))) for p in pts]
        cor = mapa.mean(amostras)
        if nuvens is not None:
            # só as nuvens densas: o mapa tem um véu cinza que clarearia o planeta inteiro
            k = clamp((nuvens.at(centro)[0] / 255.0 - 0.3) / 0.7, 0.0, 1.0) * 0.7
            cor = tuple(int(lerp(c, 244, k)) for c in cor)
        cores.append(cor)
    return cores


def build_body_sphere(raio, aneis, setores, cor, mapa=None, nuvens=None):
    """Esfera de um corpo celeste, colorida pelo mapa quando houver."""
    verts, faces, _ = build_sphere(raio, rings=aneis, sectors=setores, color=cor, exato=True)
    return verts, faces, _cores_por_mapa(verts, faces, cor, mapa, nuvens)


def build_horizon_cap(raio, centro, alfa, aneis, setores, cor, mapa=None, nuvens=None,
                      frente=None, meia_abertura=math.pi, theta_min=0.0):
    """
    Calota esférica em torno de `centro` (direção local), até o ângulo `alfa`
    — o horizonte visto de onde a câmera está. Da órbita baixa só 3% da Terra
    aparece: uma esfera inteira fina gastaria o orçamento transformando o lado
    oculto; a calota põe a resolução no pedaço visível, mais densa perto do
    horizonte, onde a curvatura aparece.

    Com `frente`, a calota vira uma janela: só o setor de azimute de
    ±meia_abertura em torno da direção do olhar, a partir do anel theta_min.
    Olhando para o horizonte, o chão logo abaixo da câmera e o que fica atrás
    dela nunca entram no quadro, e não precisam virar faces.
    """
    c = normalize(centro)
    u = None
    if frente is not None:
        u = vec_sub(frente, vec_scale(c, dot_product(frente, c)))
        u = normalize(u) if length(u) > 1e-3 else None
    if u is None:
        auxiliar = (0.0, 1.0, 0.0) if abs(c[1]) < 0.9 else (1.0, 0.0, 0.0)
        u = normalize(cross_product(auxiliar, c))
        meia_abertura, theta_min = math.pi, 0.0
    w = cross_product(c, u)
    limite = min(math.pi * 0.98, alfa * 1.04)
    fechada = meia_abertura >= math.pi - 1e-6
    theta_min = clamp(theta_min, 0.0, limite * 0.92)
    com_polo = theta_min <= 1e-9
    colunas = setores if fechada else setores + 1

    verts = [vec_scale(c, raio)] if com_polo else []
    base = len(verts)
    linhas = 0
    for k in range(1 if com_polo else 0, aneis + 1):
        f = k / aneis
        theta = theta_min + (limite - theta_min) * (1.0 - (1.0 - f) ** 2)   # aperta no horizonte
        st, ct = math.sin(theta), math.cos(theta)
        for j in range(colunas):
            phi = (2.0 * math.pi * j / setores if fechada
                   else -meia_abertura + 2.0 * meia_abertura * j / setores)
            cp, sp = math.cos(phi), math.sin(phi)
            verts.append(vec_scale((c[0] * ct + (u[0] * cp + w[0] * sp) * st,
                                    c[1] * ct + (u[1] * cp + w[1] * sp) * st,
                                    c[2] * ct + (u[2] * cp + w[2] * sp) * st), raio))
        linhas += 1

    def idx(linha, j):
        return base + linha * colunas + (j % colunas)

    faces = []
    if com_polo:
        for j in range(setores):
            faces.append((0, idx(0, j), idx(0, j + 1)))
    for linha in range(linhas - 1):
        for j in range(setores):
            faces.append((idx(linha, j), idx(linha + 1, j), idx(linha + 1, j + 1), idx(linha, j + 1)))
    # o sentido de u e w depende do centro: acerta o winding face a face
    corrigidas = []
    for face in faces:
        pts = [verts[i] for i in face]
        n = face_normal(pts)
        if n is not None and dot_product(n, pts[0]) < 0.0:
            face = tuple(reversed(face))
        corrigidas.append(face)
    return verts, corrigidas, _cores_por_mapa(verts, corrigidas, cor, mapa, nuvens)


def build_ring(r_interno, r_externo, setores, faixas, cor, mapa=None):
    """
    Anéis planetários: coroa no plano XZ, visível dos dois lados. As faixas
    transparentes do mapa (a Divisão de Cassini) simplesmente não viram faces.
    """
    b = MeshBuilder()
    for i in range(faixas):
        r0 = lerp(r_interno, r_externo, i / faixas)
        r1 = lerp(r_interno, r_externo, (i + 1) / faixas)
        tom = cor
        if mapa is not None:
            amostra = mapa.surface.get_at((int((i + 0.5) / faixas * mapa.w), mapa.h // 2))
            alfa = amostra[3] / 255.0 if len(amostra) > 3 else 1.0
            if alfa < 0.12:
                continue
            tom = tuple(int(c * (0.35 + 0.65 * alfa)) for c in amostra[:3])
        for j in range(setores):
            a0 = 2.0 * math.pi * j / setores
            a1 = 2.0 * math.pi * (j + 1) / setores
            b.add_two_sided([(r0 * math.cos(a0), 0.0, r0 * math.sin(a0)),
                             (r1 * math.cos(a0), 0.0, r1 * math.sin(a0)),
                             (r1 * math.cos(a1), 0.0, r1 * math.sin(a1)),
                             (r0 * math.cos(a1), 0.0, r0 * math.sin(a1))], tom)
    return b.data()


# --- Estação Órbita-2 (fictícia) -----------------------------------------
def build_station_core():
    """
    Objeto COMPOSTO (requisito 3). Reúne estruturas de tipos diferentes: casco
    cilíndrico, colares de reforço, anel de doca, mastros, treliça da antena,
    radiadores térmicos, escotilhas, propulsores de atitude e a antena
    parabólica. Os painéis solares saíram daqui: agora são filhos articulados
    (build_station_array), presos na ponta dos mastros.
    """
    b = MeshBuilder()

    # casco principal e reforços, ao longo do eixo X
    b.add_prism("x", (-20.0, 0.0, 0.0), 42.0, 80.0, 14, C_CASCO, C_CASCO_ESC)
    for cx in (-70.0, -24.0, 10.0):
        b.add_prism("x", (cx, 0.0, 0.0), 46.0, 4.0, 14, C_CASCO_ESC)
    # anel de acoplamento (lado +X)
    b.add_prism("x", (76.0, 0.0, 0.0), 30.0, 16.0, 12, C_ANEL, C_DOCA)
    b.add_prism("x", (58.0, 0.0, 0.0), 36.0, 4.0, 12, C_DOCA)

    # escotilhas ao longo do casco
    for cx in (-58.0, -30.0, -2.0):
        for ang in (48.0, -48.0):
            rad = math.radians(ang)
            b.add_prism("y", (cx, 42.0 * math.cos(rad), 42.0 * math.sin(rad)),
                        9.0, 3.0, 6, C_JANELA, C_CASCO_ESC)

    # propulsores de atitude (RCS) nas extremidades
    for cx in (-92.0, 40.0):
        for ang in (35.0, 145.0, 215.0, 325.0):
            rad = math.radians(ang)
            base = (cx, 40.0 * math.cos(rad), 40.0 * math.sin(rad))
            ponta = (cx, 54.0 * math.cos(rad), 54.0 * math.sin(rad))
            b.add_bar(base, ponta, 9.0, C_CASCO_ESC, C_CARGA_DET)

    # mastros dos painéis, abertos ao longo de Z; a junta fica na ponta
    for sinal in (1.0, -1.0):
        b.add_bar((-20.0, 0.0, 38.0 * sinal), (-20.0, 0.0, 126.0 * sinal),
                  14.0, C_CASCO_ESC)
        b.add_prism("z", (-20.0, 0.0, 128.0 * sinal), 10.0, 4.0, 8, C_DOCA)

    # radiadores térmicos, perpendiculares aos painéis
    for sinal in (1.0, -1.0):
        b.add_bar((-58.0, 30.0 * sinal, 0.0), (-58.0, 72.0 * sinal, 0.0),
                  8.0, C_CASCO_ESC)
        b.add_box((-104.0, 72.0 * sinal - 2.5, -34.0),
                  (-16.0, 72.0 * sinal + 2.5, 34.0), C_RADIADOR, C_CASCO_ESC)

    # treliça da antena, vertical, com o sensor no topo
    b.add_truss((-77.0, 34.0, 0.0), (-77.0, 186.0, 0.0), 32.0, 2,
                C_CASCO, C_ANEL)
    b.add_prism("y", (-77.0, 196.0, 0.0), 14.0, 10.0, 10, C_ANEL, C_DOCA)

    # antena parabólica no flanco do casco
    b.add_bar((-46.0, 44.0, 0.0), (-46.0, 74.0, -26.0), 7.0, C_CASCO_ESC)
    b.add_dish((-46.0, 80.0, -30.0), "y", 30.0, -14.0, 12, C_PRATO, C_CASCO_ESC)

    return b.data()


def build_station_array(sinal):
    """
    Painel solar da Órbita-2, com a origem na junta da ponta do mastro. Gira em
    torno do eixo do mastro (Z local) para seguir o Sol: a ideia do satélite
    articulado aplicada à própria estação.
    """
    b = MeshBuilder()
    b.add_bar((0.0, 0.0, 0.0), (0.0, 0.0, 124.0 * sinal), 7.0, C_PAINEL_BORDA)
    b.add_solar_panel((0.0, 0.0, 62.0 * sinal), 152.0, 116.0, 6, 4,
                      C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA)
    return b.data()


def build_lab_module():
    """
    Módulo-laboratório acoplado ao núcleo: o "acoplamento de módulos" do tema
    da Equipe 2. É construído ao longo do eixo X, o mesmo do núcleo, e herda a
    base da estação.
    """
    b = MeshBuilder()
    b.add_prism("x", (0.0, 0.0, 0.0), 30.0, 56.0, 12, C_CASCO, C_CASCO_ESC)
    for cx in (-30.0, 26.0):
        b.add_prism("x", (cx, 0.0, 0.0), 33.0, 4.0, 12, C_CASCO_ESC)
    b.add_prism("x", (-70.0, 0.0, 0.0), 18.0, 16.0, 10, C_JANELA, C_ANEL)   # cúpula
    for ang in (30.0, 150.0, 270.0):                                        # escotilhas
        rad = math.radians(ang)
        b.add_prism("y", (-8.0, 30.0 * math.cos(rad), 30.0 * math.sin(rad)),
                    8.0, 3.0, 6, C_JANELA, C_CASCO_ESC)
    for sinal in (1.0, -1.0):                                               # radiador
        b.add_box((-46.0, 30.0 * sinal - 2.0, -22.0),
                  (10.0, 30.0 * sinal + 2.0, 22.0), C_RADIADOR, C_CASCO_ESC)
    b.add_bar((34.0, 0.0, 0.0), (86.0, 0.0, 0.0), 26.0, C_CASCO_ESC, C_DOCA)
    return b.data()


def build_door_leaf(inferior):
    """Uma das duas folhas da comporta de doca."""
    b = MeshBuilder()
    if inferior:
        b.add_box((-6.0, -30.0, -30.0), (6.0, -1.0, 30.0), C_DOCA, C_PORTA)
    else:
        b.add_box((-6.0, 1.0, -30.0), (6.0, 30.0, 30.0), C_DOCA, C_PORTA)
    return b.data()


def build_cargo_ship():
    """Objeto COMPOSTO: nariz cônico, casco em gomos, cintas, bocal com
    garganta, quatro aletas, antena e luzes de navegação."""
    b = MeshBuilder()
    b.add_prism("x", (-74.0, 0.0, 0.0), 26.0, 22.0, 14, C_CARGA, taper=0.0)
    b.add_prism("x", (-14.0, 0.0, 0.0), 26.0, 38.0, 14, C_CARGA, C_CASCO_ESC)
    b.add_prism("x", (36.0, 0.0, 0.0), 25.0, 12.0, 14, C_CASCO, C_CASCO_ESC)
    for cx in (-46.0, -30.0, 22.0):
        b.add_prism("x", (cx, 0.0, 0.0), 28.0, 4.0, 14, C_CARGA_DET)
    # painéis de carga no costado
    for ang in (52.0, -52.0, 128.0, -128.0):
        rad = math.radians(ang)
        c, s = math.cos(rad), math.sin(rad)
        b.add_bar((-38.0, 24.0 * c, 24.0 * s), (14.0, 24.0 * c, 24.0 * s),
                  13.0, C_CASCO_ESC)
    # bocal: garganta estreita seguida do sino
    b.add_prism("x", (54.0, 0.0, 0.0), 14.0, 8.0, 12, C_CASCO_ESC)
    b.add_prism("x", (70.0, 0.0, 0.0), 14.0, 10.0, 12, C_CARGA_DET, C_BOCAL, taper=1.7)
    # aletas: chapas finas, visíveis dos dois lados
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        c, s = math.cos(rad), math.sin(rad)
        b.add_two_sided([(52.0, 26.0 * c, 26.0 * s), (18.0, 26.0 * c, 26.0 * s),
                         (58.0, 38.0 * c, 38.0 * s)], C_CARGA_DET)
    # antena e luzes de navegação
    b.add_bar((-20.0, 26.0, 0.0), (-26.0, 44.0, 0.0), 4.0, C_CASCO_ESC)
    b.add_prism("y", (-50.0, 0.0, 26.0), 5.0, 3.0, 6, C_LUZ_VERDE)
    b.add_prism("y", (-50.0, 0.0, -26.0), 5.0, 3.0, 6, C_LUZ_VERM)
    return b.data()


def build_robot_body(cor_detalhe):
    """Corpo do robô de manutenção: casco, cúpula, radiadores e propulsor."""
    b = MeshBuilder()
    b.add_box((-15.0, -12.0, -12.0), (15.0, 12.0, 12.0), C_ROBO, cor_detalhe)
    b.add_prism("y", (0.0, 16.0, 0.0), 8.0, 5.0, 8, C_JANELA, cor_detalhe)
    for sinal in (1.0, -1.0):
        b.add_bar((0.0, 0.0, 12.0 * sinal), (0.0, 0.0, 22.0 * sinal), 6.0, C_CASCO_ESC)
        z0, z1 = sorted((22.0 * sinal, 30.0 * sinal))
        b.add_box((-11.0, -9.0, z0), (11.0, 9.0, z1), cor_detalhe, C_PAINEL)
    b.add_prism("x", (-20.0, 0.0, 0.0), 6.0, 6.0, 8, cor_detalhe, C_BOCAL)
    return b.data()


def build_robot_arm(cor_detalhe, comprimento, garra=False):
    """
    Segmento do braço, com a origem na junta e crescendo em +Z local. Assim a
    cadeia ombro -> cotovelo -> garra é só uma composição de transformações.
    """
    b = MeshBuilder()
    b.add_prism("z", (0.0, 0.0, 0.0), 5.0, 4.0, 8, cor_detalhe)          # junta
    b.add_bar((0.0, 0.0, 0.0), (0.0, 0.0, comprimento), 7.0, C_ROBO, cor_detalhe)
    if garra:
        for sinal in (1.0, -1.0):
            b.add_bar((0.0, 4.0 * sinal, comprimento),
                      (0.0, 9.0 * sinal, comprimento + 11.0), 4.0, cor_detalhe)
    return b.data()


def build_debris(seed, radius, rings=8, sectors=12):
    """
    Detrito rochoso. Cada instância usa um gerador próprio
    (random.Random local) — a versão anterior chamava random.seed() global,
    o que contaminava as partículas e o campo estelar. Também é a forma dos
    asteroides e cometas pequenos, que não têm mapa.
    """
    rng = random.Random(seed)
    lumps = [(rng.uniform(1.2, 3.4), rng.uniform(1.2, 3.4), rng.uniform(1.2, 3.4),
              rng.uniform(0.07, 0.17), rng.uniform(0.0, 6.28)) for _ in range(4)]
    tom = rng.randint(-24, 24)
    cor = tuple(clamp(c + tom, 0, 255) for c in C_DETRITO)
    return build_sphere(radius, rings=rings, sectors=sectors, color=cor,
                        pole_color=tuple(clamp(c - 18, 0, 255) for c in cor),
                        lumps=lumps)


# --- Satélites reais -----------------------------------------------------
# Medidas aproximadas das naves, em metros, convertidas a 5 unidades por metro
# (a mesma escala da Órbita-2). A asa de cada painel é uma malha separada,
# presa por juntas: o corpo carrega a atitude e as juntas seguem o Sol.
M = KM / 1000.0


def build_iss_core():
    """ISS: módulos pressurizados ao longo da velocidade, treliça integrada perpendicular."""
    b = MeshBuilder()
    b.add_truss((0.0, 5.0 * M, -50.0 * M), (0.0, 5.0 * M, 50.0 * M), 4.5 * M, 12,
                C_CASCO, C_CASCO_ESC)
    modulos = (                          # (centro x, raio, meio comprimento)
        (-19.5 * M, 2.1 * M, 6.5 * M),   # Zvezda
        (-6.5 * M, 2.05 * M, 6.3 * M),   # Zarya
        (1.5 * M, 2.2 * M, 2.7 * M),     # Unity
        (8.5 * M, 2.1 * M, 4.3 * M),     # Destiny
        (15.5 * M, 2.2 * M, 3.6 * M),    # Harmony
    )
    for cx, r, meio in modulos:
        b.add_prism("x", (cx, 0.0, 0.0), r, meio, 10, C_CASCO, C_CASCO_ESC)
    b.add_prism("z", (15.5 * M, 0.0, 5.8 * M), 2.2 * M, 3.4 * M, 10, C_CASCO, C_CASCO_ESC)  # Columbus
    b.add_prism("z", (15.5 * M, 0.0, -8.0 * M), 2.2 * M, 5.6 * M, 10, C_CASCO, C_CASCO_ESC)  # Kibo
    b.add_bar((8.5 * M, 2.1 * M, 0.0), (8.5 * M, 5.0 * M, 0.0), 1.4 * M, C_CASCO_ESC)
    for sinal in (1.0, -1.0):
        b.add_box((-11.0 * M, 3.2 * M, 11.0 * sinal * M - 5.0 * M),
                  (11.0 * M, 3.5 * M, 11.0 * sinal * M + 5.0 * M), C_RADIADOR)
        # asas pequenas e fixas do Zvezda, na traseira do módulo de serviço
        inicio = len(b.verts)
        b.add_wing(10.0 * M, 3.0 * M, sinal, 1, 3, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
                   raiz=2.2 * M, ao_longo="z")
        _transladar(b, inicio, (-22.0 * M, 0.0, 0.0))
    return b.data()


def _transladar(builder, inicio, deslocamento):
    """Desloca as peças criadas a partir do vértice `inicio` (montadas na origem)."""
    for k in range(inicio, len(builder.verts)):
        builder.verts[k] = vec_add(builder.verts[k], deslocamento)


def build_iss_wing(sinal):
    """Asa fotovoltaica da ISS: 34 m por 12 m, girada pela junta BGA em torno do mastro."""
    b = MeshBuilder()
    b.add_wing(34.0 * M, 11.6 * M, sinal, 2, 10, C_PAINEL_ISS, C_PAINEL_ISS_ALT,
               C_PAINEL_BORDA, raiz=2.4 * M, espessura=0.3 * M)
    return b.data()


def build_tiangong_core():
    """Tiangong: Tianhe ao longo da velocidade, Wentian e Mengtian em T, e o cargueiro Tianzhou."""
    b = MeshBuilder()
    b.add_prism("x", (-2.0 * M, 0.0, 0.0), 2.1 * M, 5.0 * M, 10, C_CASCO, C_CASCO_ESC)
    b.add_prism("x", (6.0 * M, 0.0, 0.0), 1.4 * M, 3.0 * M, 10, C_CASCO, C_CASCO_ESC)
    b.add_prism("x", (9.5 * M, 0.0, 0.0), 1.5 * M, 1.1 * M, 10, C_CASCO_ESC)
    for sinal in (1.0, -1.0):
        b.add_prism("z", (9.5 * M, 0.0, 9.6 * M * sinal), 2.1 * M, 8.5 * M, 10, C_CASCO,
                    C_CASCO_ESC)
    b.add_prism("x", (-12.0 * M, 0.0, 0.0), 1.7 * M, 5.0 * M, 10, C_MLI, C_CASCO_ESC)  # Tianzhou
    return b.data()


def build_tiangong_wing(sinal, grande=True):
    b = MeshBuilder()
    if grande:
        b.add_wing(26.0 * M, 4.2 * M, sinal, 1, 10, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
                   raiz=1.5 * M, espessura=0.25 * M)
    else:
        b.add_wing(11.0 * M, 2.6 * M, sinal, 1, 5, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
                   raiz=1.8 * M, espessura=0.25 * M)
    return b.data()


def build_hubble_body():
    """Hubble: tubo óptico de 13,2 m com a porta da abertura, antenas de alto ganho."""
    b = MeshBuilder()
    b.add_prism("x", (0.8 * M, 0.0, 0.0), 2.1 * M, 5.8 * M, 12, C_PRATO, C_CASCO_ESC)
    b.add_prism("x", (-5.6 * M, 0.0, 0.0), 2.2 * M, 1.4 * M, 12, C_CASCO, C_CASCO_ESC)
    b.add_prism("x", (6.75 * M, 0.0, 0.0), 1.95 * M, 0.15 * M, 12, C_BOCAL)
    # porta da abertura, entreaberta
    b.add_two_sided([(6.6 * M, 2.1 * M, -1.9 * M), (6.6 * M, 2.1 * M, 1.9 * M),
                     (9.8 * M, 3.3 * M, 1.9 * M), (9.8 * M, 3.3 * M, -1.9 * M)],
                    C_PRATO, C_CASCO_ESC)
    for sinal in (1.0, -1.0):
        b.add_bar((-1.0 * M, 2.1 * M * sinal, 0.0), (-1.0 * M, 4.6 * M * sinal, 0.0),
                  0.25 * M, C_CASCO_ESC)
        b.add_dish((-1.0 * M, 4.8 * M * sinal, 0.0), "y", 0.65 * M, -0.25 * M * sinal, 8,
                   C_PRATO, C_CASCO_ESC)
    return b.data()


def build_hubble_wing(sinal):
    """Painel do Hubble (SA3, 7,1 m por 2,6 m), estendido ao longo de ±Z."""
    b = MeshBuilder()
    b.add_wing(7.1 * M, 2.6 * M, sinal, 2, 6, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
               raiz=2.4 * M, espessura=0.2 * M, ao_longo="z")
    return b.data()


def build_jwst():
    """
    James Webb: escudo solar de cinco camadas (21 m × 14 m) virado para o Sol
    (+Z local), espelho primário de 18 segmentos hexagonais dourados olhando
    para +X, secundário na ponta de três hastes, e o painel solar fixo no
    lado quente.
    """
    b = MeshBuilder()
    contorno = [(10.6, 0.0), (5.3, 7.1), (-5.3, 7.1), (-10.6, 0.0), (-5.3, -7.1), (5.3, -7.1)]
    for camada in range(5):
        z = -(0.3 + 0.32 * camada) * M
        tom = tuple(int(c * (1.0 - 0.07 * camada)) for c in C_KAPTON)
        escala = 1.0 - 0.03 * camada
        b.add_two_sided([(x * M * escala, y * M * escala, z) for x, y in contorno], tom)
    b.add_box((-1.6 * M, -1.6 * M, 0.0), (1.6 * M, 1.6 * M, 1.5 * M), C_MLI, C_CASCO_ESC)
    b.add_face([(-1.3 * M, -7.2 * M, 1.62 * M), (1.3 * M, -7.2 * M, 1.62 * M),
                (1.3 * M, -1.7 * M, 1.62 * M), (-1.3 * M, -1.7 * M, 1.62 * M)], C_PAINEL)
    b.add_face([(-1.3 * M, -7.2 * M, 1.58 * M), (-1.3 * M, -1.7 * M, 1.58 * M),
                (1.3 * M, -1.7 * M, 1.58 * M), (1.3 * M, -7.2 * M, 1.58 * M)], C_CASCO_ESC)
    b.add_bar((0.0, 0.0, -1.8 * M), (0.0, 0.0, -3.4 * M), 0.8 * M, C_CASCO_ESC)
    # espelho primário: 18 hexágonos em dois anéis, no plano x = constante
    xm, zc = -0.6 * M, -5.2 * M
    raio, passo = 0.74 * M, 1.32 * M
    for q in range(-2, 3):
        for r in range(-2, 3):
            if abs(q + r) > 2 or (q == 0 and r == 0):
                continue
            yc = passo * (q + r * 0.5)
            zc_seg = zc + passo * r * math.sqrt(3.0) * 0.5
            hexagono = [(xm - 0.02 * (yc * yc + (zc_seg - zc) ** 2) / M,
                         yc + raio * math.cos(math.radians(30 + 60 * k)),
                         zc_seg + raio * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
            b.add_two_sided(hexagono, C_OURO, C_CASCO_ESC)
    b.add_box((-2.6 * M, -1.4 * M, -6.4 * M), (-0.9 * M, 1.4 * M, -3.9 * M), C_CASCO_ESC)
    # secundário e as três hastes
    sec = (6.8 * M, 0.0, zc)
    b.add_prism("x", sec, 0.4 * M, 0.1 * M, 6, C_OURO, C_CASCO_ESC)
    for ang in (90.0, 210.0, 330.0):
        a = math.radians(ang)
        b.add_bar((xm, 3.2 * M * math.cos(a), zc + 3.2 * M * math.sin(a)), sec, 0.14 * M,
                  C_CASCO_ESC)
    return b.data()


def build_gps_body():
    """GPS: barramento com a antena de navegação voltada para a Terra (-Y)."""
    b = MeshBuilder()
    b.add_box((-1.2 * M, -1.0 * M, -1.0 * M), (1.2 * M, 1.0 * M, 1.0 * M), C_MLI, C_CASCO)
    b.add_box((-0.9 * M, -1.2 * M, -0.9 * M), (0.9 * M, -1.0 * M, 0.9 * M), C_CASCO_ESC)
    for k in range(6):
        a = math.radians(60.0 * k)
        b.add_prism("y", (0.55 * M * math.cos(a), -1.45 * M, 0.55 * M * math.sin(a)),
                    0.12 * M, 0.25 * M, 6, C_PRATO)
    return b.data()


def build_gps_wing(sinal):
    b = MeshBuilder()
    b.add_wing(5.2 * M, 2.3 * M, sinal, 2, 4, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
               raiz=1.2 * M, espessura=0.2 * M, ao_longo="z")
    return b.data()


def build_goes_body():
    """GOES-R: barramento, instrumentos voltados para a Terra e a haste do magnetômetro."""
    b = MeshBuilder()
    b.add_box((-1.8 * M, -2.3 * M, -1.8 * M), (1.8 * M, 2.3 * M, 1.8 * M), C_MLI, C_CASCO)
    b.add_box((-1.2 * M, -3.2 * M, -1.0 * M), (1.2 * M, -2.3 * M, 1.2 * M), C_CASCO, C_CASCO_ESC)
    b.add_bar((1.8 * M, 1.5 * M, 0.0), (9.0 * M, 1.5 * M, 0.0), 0.12 * M, C_CASCO_ESC)
    b.add_dish((0.0, 2.3 * M, 1.8 * M), "z", 0.9 * M, 0.3 * M, 8, C_PRATO, C_CASCO_ESC)
    return b.data()


def build_goes_array():
    """Painel único do GOES, no braço que aponta para o sul; gira uma vez por dia."""
    b = MeshBuilder()
    b.add_wing(8.0 * M, 4.0 * M, -1.0, 2, 5, C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA,
               raiz=2.6 * M, espessura=0.25 * M, ao_longo="z")
    return b.data()


# ============================================================
# 8. SISTEMAS DE APOIO
# ============================================================
class ExhaustParticles:
    """
    Partículas dos retrofoguetes: vida decrescente e cor esfriando. Posição e
    velocidade ficam no referencial da estação — no mundo, a estação anda a
    7,7 km/s e as partículas ficariam para trás no mesmo quadro.
    """

    def __init__(self, rng=None):
        self.particles = []
        self.rng = rng or random.Random(2024)

    def clear(self):
        self.particles.clear()

    def emit(self, origem, direcao, count=5, speed=150.0):
        d = normalize(direcao)
        for _ in range(count):
            desvio = (self.rng.uniform(-0.22, 0.22),
                      self.rng.uniform(-0.22, 0.22),
                      self.rng.uniform(-0.22, 0.22))
            vel = vec_scale(normalize(vec_add(d, desvio)),
                            speed * self.rng.uniform(0.6, 1.35))
            self.particles.append({
                "pos": list(origem),
                "vel": vel,
                "life": 1.0,
                "size": self.rng.uniform(3.0, 7.5),
            })

    def update(self, dt):
        vivas = []
        for p in self.particles:
            p["life"] -= dt * 1.9
            if p["life"] <= 0.0:
                continue
            p["pos"][0] += p["vel"][0] * dt
            p["pos"][1] += p["vel"][1] * dt
            p["pos"][2] += p["vel"][2] * dt
            vivas.append(p)
        self.particles = vivas

    @staticmethod
    def color_of(p):
        v = p["life"]
        if v > 0.55:
            return (255, int(120 + 120 * v), 40)
        if v > 0.3:
            return (210, 110, 60)
        return (int(120 * v + 40), int(110 * v + 40), int(120 * v + 45))


class Starfield:
    """
    Céu estrelado. Com o snapshot do Yale Bright Star Catalogue, são as
    estrelas reais até a magnitude 5, nas posições e cores verdadeiras — as
    constelações aparecem onde deveriam. Sem ele, um campo procedural. As
    estrelas ficam no infinito: só a orientação da câmera as move.
    """

    VMAG_MAX = 5.0

    def __init__(self, count=420, seed=7):
        rng = random.Random(seed)
        self.stars = []
        reais = catalogo.estrelas(self.VMAG_MAX)
        self.reais = bool(reais)
        if reais:
            for direcao, vmag, cor, nome in reais:
                self.stars.append({
                    "dir": direcao,
                    "fase": rng.uniform(0.0, 6.28),
                    "vel": rng.uniform(0.6, 2.1),
                    "brilho": clamp(1.12 - 0.15 * vmag, 0.34, 1.0),
                    "size": 3 if vmag < 0.3 else (2 if vmag < 1.8 else 1),
                    "tom": cor,
                    "nome": nome,
                })
            return
        for _ in range(count):
            d = normalize((rng.uniform(-1, 1), rng.uniform(-0.75, 0.9), rng.uniform(-1, 1)))
            if d == (0.0, 0.0, 0.0):
                continue
            sorte = rng.random()
            tamanho = 3 if sorte > 0.975 else (2 if sorte > 0.90 else 1)
            tom = rng.choice(((198, 214, 255), (255, 240, 214), (226, 232, 244),
                              (255, 214, 196), (208, 236, 255)))
            self.stars.append({
                "dir": d,
                "fase": rng.uniform(0.0, 6.28),
                "vel": rng.uniform(0.6, 2.1),
                "brilho": rng.uniform(0.45, 1.0),
                "size": tamanho,
                "tom": tom,
                "nome": "",
            })

    def brightness(self, star, t):
        pulso = 0.9 + 0.1 * math.sin(t * star["vel"] + star["fase"])
        return clamp(star["brilho"] * pulso, 0.0, 1.0)


# --- Comporta de doca: máquina de estados própria (requisito 6b) ---------
DOOR_CLOSED = "FECHADA"
DOOR_OPENING = "ABRINDO"
DOOR_OPEN = "ABERTA"
DOOR_CLOSING = "FECHANDO"

DOOR_OPEN_START = 4.0
DOOR_OPEN_END = 6.0
DOOR_CLOSE_START = 8.5
DOOR_CLOSE_END = 10.0

# Trava do acoplamento: o cargueiro chega ao fim do trilho no instante em que a
# comporta termina de fechar. O pulso comanda o tremor da câmera e o clarão.
DOCKING_LATCH_TIME = DOOR_CLOSE_END
DOCKING_PULSE = 0.7


def docking_pulse(t):
    """Intensidade do efeito de acoplamento: 1 na trava, caindo a 0 ao fim da janela."""
    # os limites são comparados em t, e não na fração: (10,7 - 10) / 0,7 dá
    # 0,999..., e o fim exato da janela deixaria um pulso residual
    if t < DOCKING_LATCH_TIME or t >= DOCKING_LATCH_TIME + DOCKING_PULSE:
        return 0.0
    u = (t - DOCKING_LATCH_TIME) / DOCKING_PULSE
    return (1.0 - u) * (1.0 - u)


class DoorFSM:
    """
    Comporta com quatro estados. A abertura é função do tempo de simulação,
    então pausar, reiniciar ou saltar de fase sempre reconstrói o estado certo.
    """

    def __init__(self):
        self.state = DOOR_CLOSED
        self.opening = 0.0

    def set_from_time(self, t):
        if t < DOOR_OPEN_START:
            self.state, self.opening = DOOR_CLOSED, 0.0
        elif t < DOOR_OPEN_END:
            self.state = DOOR_OPENING
            self.opening = smoothstep((t - DOOR_OPEN_START) / (DOOR_OPEN_END - DOOR_OPEN_START))
        elif t < DOOR_CLOSE_START:
            self.state, self.opening = DOOR_OPEN, 1.0
        elif t < DOOR_CLOSE_END:
            self.state = DOOR_CLOSING
            self.opening = 1.0 - smoothstep((t - DOOR_CLOSE_START) / (DOOR_CLOSE_END - DOOR_CLOSE_START))
        else:
            self.state, self.opening = DOOR_CLOSED, 0.0
        return self.state


class AlertBeacons:
    """Alerta sequencial: seis balizas no anel de doca acendem em rodízio."""

    COUNT = 6
    AMBER = (255, 176, 42)
    GREEN = (60, 232, 150)

    def __init__(self):
        self.local = []
        for k in range(self.COUNT):
            a = 2.0 * math.pi * k / self.COUNT
            self.local.append((92.0, 38.0 * math.cos(a), 38.0 * math.sin(a)))
        self.active = 0
        self.color = self.AMBER

    def set_from_time(self, t, acoplado):
        self.active = int(t * 4.0) % self.COUNT
        self.color = self.GREEN if acoplado else self.AMBER
        return self.active


# --- Juntas articuladas: painéis que seguem o Sol ------------------------
class Joint:
    """
    Junta rotacional: onde fica no referencial do elo anterior, em torno de que
    eixo gira e — se rastreia o Sol — qual é a normal do painel no ângulo zero.
    """

    __slots__ = ("anchor", "axis", "normal", "two_sided", "angle")

    def __init__(self, anchor, axis, normal=None, two_sided=False):
        self.anchor = anchor
        self.axis = axis
        self.normal = normal
        self.two_sided = two_sided
        self.angle = 0.0


class ArticulatedPanel:
    """
    Cadeia corpo -> juntas -> painel (a ideia do satélite articulado). Cada
    junta compõe a própria rotação sobre a base acumulada do pai — hierarquia
    por multiplicação de matrizes — e as que rastreiam giram para maximizar a
    luz do Sol. Na sombra da Terra o ângulo volta a zero na proporção da sombra:
    continua função pura do instante, sem estado acumulado.
    """

    def __init__(self, mesh, joints, panel_normal):
        self.mesh = mesh
        self.joints = joints
        self.panel_normal = panel_normal
        self.incidence = 0.0

    def place(self, pos, base, to_sun, shadow=0.0):
        for junta in self.joints:
            pos = vec_add(pos, mat_apply(base, junta.anchor))
            if junta.normal is not None:
                junta.angle = angulo_de_rastreio(base, junta.axis, junta.normal, to_sun,
                                                 junta.two_sided) * (1.0 - shadow)
            base = mat_mul(base, mat_axis_angle(junta.axis, junta.angle))
        self.mesh.update(pos=pos, basis=base)
        d = dot_product(mat_apply(base, self.panel_normal), to_sun)
        ultima = self.joints[-1] if self.joints else None
        self.incidence = abs(d) if ultima is not None and ultima.two_sided else max(0.0, d)
        return base


# --- Nuvens de pontos: milhares de corpos reais --------------------------
class PointCloud:
    """
    Pequenos corpos e satélites como pontos. Propagar milhares de órbitas a
    cada quadro custaria dezenas de milissegundos em Python; a nuvem avança um
    lote por quadro, em rodízio. Em tempo real um asteroide anda menos de um
    pixel por hora, e o rodízio não aparece; com o tempo acelerado, o lote
    cresce. Posições relativas ao pai (Sol ou Terra), em km.
    """

    def __init__(self, name, orbits, color, parent="sol"):
        self.name = name
        self.orbits = orbits
        self.color = color
        self.parent = parent
        self.positions = [None] * len(orbits)
        self.cursor = 0
        self.visible = False
        self._pronta = False

    def __len__(self):
        return len(self.orbits)

    def update(self, jd, lote):
        n = len(self.orbits)
        if n == 0:
            return
        if not self._pronta:
            lote = n                      # a primeira passada é completa
        for _ in range(min(lote, n)):
            k = self.cursor
            self.positions[k] = self.orbits[k].posicao(jd)
            self.cursor = (k + 1) % n
        self._pronta = True
# ============================================================
# 9. CENA E SEQUÊNCIA DE ANIMAÇÃO
# ============================================================
STATE_PARADO = "PARADO"
STATE_EXECUTANDO = "EXECUTANDO"
STATE_PAUSADO = "PAUSADO"
STATE_CONCLUIDO = "CONCLUIDO"

CARGO_X = (470.0, 300.0, 222.0, 178.0)       # trajetória do cargueiro por fase

# Campo de detritos em órbita relativa da própria estação (referencial local):
# (semente, raio da rocha, raio da órbita, fase, inclinação, velocidade, malha cheia)
DEBRIS_FIELD = (
    (101, 46.0, 760.0, 0.4, 22.0, 0.055, True),
    (202, 30.0, 880.0, 2.1, -16.0, 0.048, True),
    (303, 58.0, 1000.0, 4.0, 40.0, 0.041, True),
    (404, 62.0, 1150.0, 1.2, -34.0, 0.034, False),
    (505, 44.0, 1300.0, 3.4, 12.0, 0.030, False),
    (606, 80.0, 1450.0, 5.6, 54.0, 0.026, False),
    (707, 38.0, 1600.0, 0.9, -48.0, 0.023, False),
    (808, 54.0, 1750.0, 2.7, 28.0, 0.021, False),
    (909, 68.0, 1950.0, 4.8, -8.0, 0.018, False),
)
SENSOR_LOCAL = (-77.0, 208.0, 0.0)           # topo do mastro da antena
ROBOT_DOCK_LOCAL = ((-58.0, 56.0, 12.0), (-8.0, -58.0, 20.0),
                    (34.0, 54.0, -30.0), (-104.0, -50.0, -18.0))
MAST_X, MAST_Z = -77.0, 0.0                  # eixo do mastro, em coords locais
MAST_SAFE_RADIUS = 56.0
STATION_ARRAY_JOINTS = ((-20.0, 0.0, 128.0), (-20.0, 0.0, -128.0))
STATION_PITCH_BASIS = mat_axis_angle((1.0, 0.0, 0.0), STATION_PITCH)
ECLIPTIC_NORTH = (0.0, 1.0, 0.0)             # polo norte da eclíptica, no mundo
UM_SEGUNDO = 1.0 / ef.SEGUNDOS_DIA


class MaintenanceRobot:
    """
    Robô de manutenção com braço de dois segmentos. Demonstra a cadeia
    hierárquica estação -> corpo -> braço -> antebraço: cada junta é
    posicionada pela transformação do elo anterior, por multiplicação de bases.
    """

    SHOULDER_LOCAL = (0.0, 12.0, 14.0)
    UPPER_LEN = 28.0
    FORE_LEN = 20.0

    def __init__(self, indice, cor, escala, params):
        self.name = "Robô MR-%d" % indice
        self.cor = cor
        self.scale = escala
        self.params = params
        self.body = PolyMesh(*build_robot_body(cor), scale=escala, name=self.name)
        self.upper = PolyMesh(*build_robot_arm(cor, self.UPPER_LEN),
                              scale=escala, name=self.name + " braço", gloss=0.24)
        self.fore = PolyMesh(*build_robot_arm(cor, self.FORE_LEN, garra=True),
                             scale=escala, name=self.name + " antebraço", gloss=0.24)
        self.avoided = False

    @property
    def meshes(self):
        return (self.body, self.upper, self.fore)

    @property
    def pos(self):
        return self.body.pos

    @property
    def bounding_radius(self):
        return self.body.bounding_radius

    def place(self, pos, giro, incl, ombro, cotovelo, base_pai=IDENTIDADE):
        """
        Posiciona a cadeia inteira. Ombro e cotovelo giram em torno do X local
        do elo, composto à direita da base do pai: base_braço = base_corpo · Rx.
        """
        base = mat_mul(base_pai, mat_from_euler((0.0, giro, incl)))
        self.body.update(pos=pos, basis=base)
        s = self.scale
        junta = vec_add(pos, mat_apply(base, vec_scale(self.SHOULDER_LOCAL, s)))
        base_sup = mat_mul(base, mat_axis_angle((1.0, 0.0, 0.0), ombro))
        self.upper.update(pos=junta, basis=base_sup)
        cotov = vec_add(junta, mat_apply(base_sup, (0.0, 0.0, self.UPPER_LEN * s)))
        self.fore.update(pos=cotov,
                         basis=mat_mul(base, mat_axis_angle((1.0, 0.0, 0.0), ombro + cotovelo)))


# --- Corpos celestes -----------------------------------------------------
_GEOMETRIAS = {}


def _geometria(chave, construtor):
    """Geometria compartilhada entre cenas: a suíte de testes cria dezenas delas."""
    dados = _GEOMETRIAS.get(chave)
    if dados is None:
        dados = _GEOMETRIAS[chave] = construtor()
    return dados


def _semente(nome):
    # hash() de texto muda a cada processo; esta soma é estável
    return sum(ord(c) * (i + 1) for i, c in enumerate(nome))


class CelestialBody:
    """
    Corpo natural real: malha com níveis de detalhe, órbita e rotação. A
    posição heliocêntrica (km) é recalculada a cada quadro pelo relógio UTC.
    """

    def __init__(self, nome, tipo, raio_km, cor, pai=None, orbita=None, mapa=None,
                 nuvens=None, gloss=0.0):
        self.name = nome
        self.kind = tipo
        self.radius_km = raio_km
        self.radius = raio_km * KM
        self.color = cor
        self.parent = pai
        self.orbit = orbita
        self.map = ColorMap.load(mapa) if mapa else None
        self.clouds = ColorMap.load(nuvens) if nuvens else None
        self.pos_km = (0.0, 0.0, 0.0)
        self.cap = None                    # (centro, alfa) da calota ativa
        tamanho = 3 if tipo in ("estrela", "planeta") else 2
        if self.map is None and raio_km < 150.0:
            # corpo pequeno e irregular: a mesma forma dos detritos, na cor dele
            verts, faces, _ = _geometria(("rocha", nome), lambda: build_debris(
                _semente(nome), self.radius, rings=7, sectors=10))
            cores = [cor] * len(faces)
            self.mesh = PolyMesh(verts, faces, cores, name=nome, gloss=0.0,
                                 marker_color=cor, marker_size=tamanho, edges=False)
            return
        self.mesh = PolyMesh([], [], [], name=nome, gloss=gloss, marker_color=cor,
                             marker_size=tamanho, edges=False)
        niveis = [(0.0, self._nivel(6, 10)), (18.0, self._nivel(12, 22)),
                  (90.0, self._nivel(22, 42))]
        if self.map is not None:
            niveis.append((320.0, self._nivel(36, 68)))
        self.mesh.set_lods(niveis)
        self.lods = self.mesh.lods

    def _nivel(self, aneis, setores):
        chave = ("corpo", self.name, aneis, setores)
        return lambda: _geometria(chave, lambda: build_body_sphere(
            self.radius, aneis, setores, self.color, self.map, self.clouds))

    def update_horizon_cap(self, olho, frente=None):
        """
        Perto do corpo (menos de três raios), troca a esfera pela calota até o
        horizonte, limitada à janela que a câmera enxerga. Ela só é refeita
        quando o ponto sob a câmera anda uma fração de célula ou o olhar gira;
        longe, o corpo volta aos níveis de detalhe.
        """
        if self.map is None or self.mesh.basis is None:
            return
        rel = vec_sub(olho, self.mesh.pos)
        d = length(rel)
        if d > 3.0 * self.radius:
            if self.cap is not None:
                self.cap = None
                self.mesh.lods = self.lods
                self.mesh._lod_atual = None
                self.mesh.use_lod(0.0)
            return
        base = self.mesh.basis
        centro = normalize(mat_apply_t(base, rel))
        alfa = math.acos(clamp(self.radius / max(d, self.radius * 1.0001), -1.0, 1.0))
        janela = None
        if frente is not None:
            f = mat_apply_t(base, frente)
            depressao = math.asin(clamp(-dot_product(f, centro), -1.0, 1.0))
            mais_baixo = depressao + math.atan((HEIGHT - VIEW_CENTER_Y) / FOV) + math.radians(6.0)
            if mais_baixo < math.radians(78.0):
                # raio mais baixo do quadro: onde ele toca o planeta começa a janela
                beta = math.pi * 0.5 - mais_baixo
                s = d * math.sin(beta) / self.radius
                theta_min = (math.asin(s) - beta) * 0.85 if s < 1.0 else alfa * 0.9
                meia_h = math.atan(max(VIEW_CENTER_X, WIDTH - VIEW_CENTER_X) / FOV)
                janela = (f, min(math.pi, 1.5 * meia_h + math.radians(25.0)), max(0.0, theta_min))
        if self.cap is not None:
            c0, a0, j0 = self.cap
            desvio = math.acos(clamp(dot_product(c0, centro), -1.0, 1.0))
            mesma_janela = ((j0 is None) == (janela is None)
                            and (janela is None or dot_product(j0[0], janela[0]) > 0.9945))
            if desvio < a0 * 0.012 and abs(alfa - a0) < a0 * 0.04 and mesma_janela:
                return
        self.cap = (centro, alfa, janela)
        self.mesh.lods = None
        self.mesh._lod_atual = None
        extra = {} if janela is None else {"frente": janela[0], "meia_abertura": janela[1],
                                           "theta_min": janela[2]}
        self.mesh.set_geometry(*build_horizon_cap(self.radius, centro, alfa, 14, 40, self.color,
                                                  self.map, self.clouds, **extra))


# --- Satélites reais -----------------------------------------------------
SATELLITE_COLORS = {"iss": (255, 255, 255), "tiangong": (255, 236, 200),
                    "hubble": (126, 236, 196), "jwst": (236, 186, 76),
                    "gps": (255, 206, 96), "goes": (126, 196, 255)}


def satellite_attitude(modelo, radial, velocidade, para_o_sol):
    """
    Atitude de cada nave, como ela voa de verdade:
    - estações e GOES: LVLH, com a Terra embaixo;
    - GPS: "yaw steering" — antena para a Terra e giro em torno do nadir que
      deixa o Sol perpendicular ao eixo dos painéis, então uma junta basta;
    - Hubble: apontamento inercial, com o eixo dos painéis perpendicular ao Sol;
    - James Webb: escudo solar sempre de frente para o Sol.
    """
    if modelo == "gps":
        y = normalize(radial)
        z = normalize(cross_product(y, para_o_sol))
        if length(z) < 0.5:
            z = normalize(cross_product(y, velocidade))
        return (cross_product(y, z), y, z)
    if modelo == "hubble":
        x = normalize(cross_product(para_o_sol, ECLIPTIC_NORTH))
        z = normalize(cross_product(x, para_o_sol))
        return (x, cross_product(z, x), z)
    if modelo == "jwst":
        z = para_o_sol
        x = normalize(cross_product(ECLIPTIC_NORTH, z))
        return (x, cross_product(z, x), z)
    return lvlh_basis(radial, velocidade)


def _satellite_panels(modelo, nome):
    """Asas de cada modelo: geometria, cadeia de juntas e normal do painel."""
    paineis = []

    def asa(chave, construtor, juntas, normal=(1.0, 0.0, 0.0)):
        malha = PolyMesh(*_geometria(chave, construtor), name=nome + " painel", gloss=0.2)
        paineis.append(ArticulatedPanel(malha, juntas, normal))

    if modelo == "iss":
        for lado in (1.0, -1.0):
            for z in (38.0, 46.0):
                for sinal in (1.0, -1.0):
                    # SARJ gira a treliça externa em torno do eixo dela; BGA gira a asa
                    asa(("iss-asa", sinal), lambda s=sinal: build_iss_wing(s),
                        [Joint((0.0, 5.0 * M, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
                         Joint((0.0, 0.0, lado * z * M), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))])
    elif modelo == "tiangong":
        for lado in (1.0, -1.0):
            for sinal in (1.0, -1.0):
                asa(("tiangong-asa", sinal, True), lambda s=sinal: build_tiangong_wing(s),
                    [Joint((9.5 * M, 0.0, lado * 18.6 * M), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))])
        for sinal in (1.0, -1.0):
            asa(("tiangong-asa", sinal, False), lambda s=sinal: build_tiangong_wing(s, False),
                [Joint((-3.0 * M, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))])
    elif modelo == "hubble":
        for sinal in (1.0, -1.0):
            asa(("hubble-asa", sinal), lambda s=sinal: build_hubble_wing(s),
                [Joint((-1.5 * M, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), two_sided=True)])
    elif modelo == "gps":
        for sinal in (1.0, -1.0):
            asa(("gps-asa", sinal), lambda s=sinal: build_gps_wing(s),
                [Joint((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))])
    elif modelo == "goes":
        asa(("goes-asa",), build_goes_array,
            [Joint((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))])
    return paineis


_CORPOS_MODELO = {"iss": build_iss_core, "tiangong": build_tiangong_core,
                  "hubble": build_hubble_body, "jwst": build_jwst,
                  "gps": build_gps_body, "goes": build_goes_body}


class RealSatellite:
    """
    Nave real: corpo com a atitude do modelo e painéis presos por juntas que
    seguem o Sol. A órbita vem dos elementos do CelesTrak (ou, no James Webb,
    da tabela do Horizons). Longe da câmera só a posição é calculada: atitude e
    juntas de 31 satélites GPS invisíveis custariam milissegundos por quadro.
    """

    def __init__(self, nome, modelo, orbita=None):
        self.name = nome
        self.model = modelo
        self.orbit = orbita
        self.body = PolyMesh(*_geometria(("corpo-modelo", modelo), _CORPOS_MODELO[modelo]),
                             name=nome, gloss=0.35, marker_color=SATELLITE_COLORS[modelo])
        self.panels = _satellite_panels(modelo, nome)
        self.geo_km = (0.0, 0.0, 0.0)
        self.pos_km = (0.0, 0.0, 0.0)
        self.incidence = 0.0

    @property
    def meshes(self):
        return [self.body] + [p.mesh for p in self.panels]

    def place(self, jd, terra_km, terra_mundo, geo_km, detalhe):
        self.geo_km = geo_km
        self.pos_km = vec_add(terra_km, geo_km)
        pos = vec_add(terra_mundo, vec_scale(ef.direcao_para_mundo(geo_km), KM))
        self.body.update(pos=pos)
        sombra = ef.na_sombra_da_terra(self.pos_km, terra_km)
        self.body.shadow = sombra
        if not detalhe:
            for p in self.panels:
                p.mesh.visible = False
            return
        para_o_sol = normalize(vec_scale(ef.direcao_para_mundo(self.pos_km), -1.0))
        if self.orbit is not None:
            depois = self.orbit.posicao(jd + UM_SEGUNDO)
            velocidade = ef.direcao_para_mundo(vec_sub(depois, geo_km))
        else:
            velocidade = (1.0, 0.0, 0.0)
        base = satellite_attitude(self.model, ef.direcao_para_mundo(geo_km), velocidade,
                                  para_o_sol)
        self.body.update(basis=base)
        soma = 0.0
        for p in self.panels:
            p.mesh.visible = True
            p.mesh.shadow = sombra
            p.place(pos, base, para_o_sol, sombra)
            soma += p.incidence
        self.incidence = soma / len(self.panels) if self.panels else 0.0


# --- Dados dos snapshots, carregados uma vez por processo ------------------
_SATELITES_CARREGADOS = {}


def _satellite_orbits(grupos):
    """Converte os OMM em órbitas uma única vez por conjunto de elementos."""
    chave = id(grupos)
    if chave not in _SATELITES_CARREGADOS:
        saida = {}
        for grupo, lista in grupos.items():
            orbitas = []
            for omm in lista:
                try:
                    orbitas.append(ef.OrbitaTerrestre(omm, grupo))
                except (KeyError, TypeError, ValueError):
                    continue
            saida[grupo] = orbitas
        _SATELITES_CARREGADOS.clear()
        _SATELITES_CARREGADOS[chave] = saida
    return _SATELITES_CARREGADOS[chave]


# Pequenos corpos com traçado de órbita. Sedna (540 UA) e Hale-Bopp (181 UA)
# ficam de fora: as elipses deles atravessariam a tela em qualquer enquadramento.
ORBIT_LINE_EXTRAS = ("Vesta", "Halley", "Encke", "Churyumov-Gerasimenko", "Arrokoth")


class Scene:
    """
    Todo o estado da simulação. Não desenha nada: é esta classe que a suíte de
    testes exercita (do Pygame ela só usa a leitura dos mapas de cor). A pose
    de cada objeto é função pura do tempo de simulação e do relógio UTC, então
    pausar, reiniciar e saltar de fase são consistentes.
    """

    def __init__(self, inicio_utc=None):
        self.start_utc = inicio_utc or datetime.now(timezone.utc)
        self.jd_start = ef.jd_de_datetime(self.start_utc)

        self.station = PolyMesh(*build_station_core(), position=STATION_ORIGIN,
                                name="Núcleo Órbita-2", marker_color=(86, 226, 198))
        self.lab = PolyMesh(*build_lab_module(), name="Módulo Laboratório")
        self.door_hi = PolyMesh(*build_door_leaf(False), name="Comporta superior")
        self.door_lo = PolyMesh(*build_door_leaf(True), name="Comporta inferior")
        self.cargo = PolyMesh(*build_cargo_ship(), name="Cargueiro Vega-7")
        self.station_arrays = [
            ArticulatedPanel(PolyMesh(*build_station_array(1.0 if z > 0 else -1.0),
                                      name="Painel solar Órbita-2", gloss=0.12),
                             [Joint(ancora, (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), two_sided=True)],
                             (0.0, 1.0, 0.0))
            for ancora in STATION_ARRAY_JOINTS for z in (ancora[2],)]

        # quatro instâncias do mesmo tipo, com parâmetros diferentes (requisito 3)
        especificacao = (
            ((232, 128, 46), 0.95, (186.0, 62.0, 1.00, 0.00, 18.0)),
            ((86, 196, 224), 0.66, (238.0, -44.0, 1.38, 1.57, -26.0)),
            ((198, 108, 206), 1.25, (150.0, -132.0, 0.74, 3.14, 34.0)),
            ((236, 220, 96), 0.84, (272.0, 18.0, 1.12, 4.71, -12.0)),
        )
        self.robots = [MaintenanceRobot(i + 1, cor, escala, params)
                       for i, (cor, escala, params) in enumerate(especificacao)]

        # campo de detritos em torno da estação: os de dentro em malha cheia,
        # os de fora em LOD grosso
        self.debris = []
        self.debris_orbits = []
        for i, (seed, raio, orbita, fase, incl, veloc, fino) in enumerate(DEBRIS_FIELD):
            dados = build_debris(seed, raio) if fino else build_debris(seed, raio, rings=5, sectors=8)
            self.debris.append(PolyMesh(*dados, name="Detrito %s" % chr(65 + i), gloss=0.0))
            self.debris_orbits.append((orbita, fase, incl, veloc))

        self._build_solar_system()
        self._build_satellites(*catalogo.satelites())
        self.jwst_table = catalogo.tabela_jwst()

        self.meshes = ([b.mesh for b in self.bodies.values()] + self.rings_meshes()
                       + [m for s in self.satellites for m in s.meshes] + self.debris
                       + [self.station] + [p.mesh for p in self.station_arrays]
                       + [self.lab, self.door_hi, self.door_lo]
                       + [m for r in self.robots for m in r.meshes]
                       + [self.cargo])

        self.camera = Camera()
        self.particles = ExhaustParticles()
        self.starfield = Starfield()
        self.door = DoorFSM()
        self.beacons = AlertBeacons()
        self.sight = []
        self.loop = False              # repete a sequência sem parar
        self.tour = False              # câmera troca sozinha a cada fase (tecla T)
        self.extended_orbit = False    # fase de inspeção com três voltas
        self.speed_index = DEFAULT_SPEED_INDEX
        self.time_scale_index = DEFAULT_TIME_SCALE
        self.cycles = 0
        self.anim_time = 0.0           # segundos simulados do relógio orbital
        self.wall_time = 0.0           # relógio das animações locais (detritos)
        self.zoom_index = DEFAULT_ZOOM
        self.focus_index = None
        self.station_pos = STATION_ORIGIN
        self.station_basis = IDENTIDADE
        self.station_km = (0.0, 0.0, 0.0)
        self._orbit_cache = None
        self.station_orbit = self._choose_station_orbit()
        self.reset()

    # -- construção do Sistema Solar ---------------------------------------
    def _build_solar_system(self):
        bodies = {}
        nome, raio, cor, mapa = catalogo.SOL
        bodies[nome] = CelestialBody(nome, "estrela", raio, cor, mapa=mapa)
        for nome, raio, cor, mapa in catalogo.PLANETAS:
            bodies[nome] = CelestialBody(nome, "planeta", raio, cor, mapa=mapa,
                                         nuvens="nuvens" if nome == "Terra" else None,
                                         gloss=0.06 if nome == "Terra" else 0.0)
        nome, raio, cor, mapa = catalogo.LUA
        bodies[nome] = CelestialBody(nome, "lua", raio, cor, pai=bodies["Terra"], mapa=mapa)
        pequenos = catalogo.elementos("pequenos_corpos.json")
        for nome, el in pequenos.items():
            raio, cor = catalogo.PEQUENOS.get(nome, (10.0, (170, 170, 170)))
            try:
                orbita = catalogo.orbita_de_elementos(el)
            except (KeyError, ValueError):
                continue
            tipo = "anão" if el.get("tipo") == "anão" else el.get("tipo", "asteroide")
            bodies[nome] = CelestialBody(nome, tipo, raio, cor, orbita=orbita)
        for nome, el in catalogo.elementos("luas.json").items():
            pai, raio, cor = catalogo.LUAS.get(nome, (el.get("pai"), 50.0, (170, 170, 170)))
            if pai not in bodies:
                continue
            try:
                orbita = catalogo.orbita_de_elementos(el)
            except (KeyError, ValueError):
                continue
            bodies[nome] = CelestialBody(nome, "lua", raio, cor, pai=bodies[pai], orbita=orbita)
        self.bodies = bodies
        self.sun = bodies["Sol"].mesh
        self.earth = bodies["Terra"].mesh
        self.moon = bodies["Lua"].mesh

        self.rings = []
        for planeta, (r_in, r_out) in catalogo.ANEIS.items():
            if planeta not in bodies:
                continue
            if planeta == "Saturno":
                dados = _geometria(("anel", planeta), lambda a=r_in, b=r_out: build_ring(
                    a * KM, b * KM, 48, 14, (206, 190, 150), ColorMap.load("aneis_saturno")))
            else:
                dados = _geometria(("anel", planeta), lambda: build_ring(
                    51000.0 * KM, 51300.0 * KM, 48, 1, (96, 100, 110)))
            self.rings.append((bodies[planeta], PolyMesh(*dados, name="Anéis de " + planeta,
                                                         gloss=0.0, edges=False)))

        self.clouds = [PointCloud(grupo, orbitas, catalogo.CORES_NUVENS.get(grupo, (150, 150, 150)))
                       for grupo, orbitas in catalogo.nuvens().items() if orbitas]

    def rings_meshes(self):
        return [malha for _corpo, malha in self.rings]

    def _build_satellites(self, grupos, gerado_em):
        """Modelos 3D das naves notáveis; o resto do catálogo vira nuvem de pontos."""
        self.satellite_data_date = gerado_em
        orbitas = _satellite_orbits(grupos) if grupos else {}
        modelados = set()
        self.satellites = []

        def modelo(nome, tipo, orbita):
            self.satellites.append(RealSatellite(nome, tipo, orbita))
            modelados.add(orbita.norad)

        todas = [o for lista in orbitas.values() for o in lista]
        por_norad = {o.norad: o for o in todas}
        for norad, nome, tipo in ((25544, "ISS", "iss"), (48274, "Tiangong", "tiangong"),
                                  (20580, "Hubble", "hubble")):
            if norad in por_norad:
                modelo(nome, tipo, por_norad[norad])
        for o in sorted(todas, key=lambda o: o.nome):
            if o.nome.startswith("GOES 1") and o.norad not in modelados:
                modelo(o.nome.title(), "goes", o)
            elif o.nome.startswith("GPS ") and o.norad not in modelados:
                modelo(o.nome, "gps", o)
        self.satellites.append(RealSatellite("James Webb", "jwst", None))
        self.jwst = self.satellites[-1]
        self.satellite_clouds = [
            PointCloud(grupo, [o for o in lista if o.norad not in modelados],
                       catalogo.CORES_SATELITES.get(grupo, (200, 200, 200)), parent="terra")
            for grupo, lista in orbitas.items()]

    def update_satellite_elements(self, grupos, gerado_em):
        """Elementos novos do CelesTrak (baixados em segundo plano) substituem o snapshot."""
        antigos = set(id(m) for s in self.satellites for m in s.meshes)
        self._build_satellites(grupos, gerado_em)
        novos = [m for s in self.satellites for m in s.meshes]
        self.meshes = [m for m in self.meshes if id(m) not in antigos]
        indice = len(self.bodies) + len(self.rings)
        self.meshes[indice:indice] = novos
        self._orbit_cache = None
        self.apply_animation(self.sim_time)

    def update_jwst(self, linhas):
        self.jwst_table = ef.TabelaVetores(linhas)
        self._orbit_cache = None

    def _choose_station_orbit(self):
        """
        A Órbita-2 não existe, então a fase e o nó da órbita dela são escolhidos:
        entre algumas combinações, a que começa à luz do Sol, continua iluminada
        por 25 minutos e deixa o Sol do lado da câmera do plano geral. É o
        cenário de uma boa foto — e é determinístico para o mesmo instante.
        """
        jd = self.jd_start
        terra = ef.posicao_terra(jd)
        sol = normalize(ef.direcao_para_mundo(vec_scale(terra, -1.0)))
        preferida = normalize((-0.45, 0.55, -0.70))
        melhor, nota_max = None, -9.0
        for i_no in range(8):
            for i_fase in range(18):
                omm = ef.orbita_circular_leo(STATION_ALTITUDE_KM, STATION_INCLINATION,
                                             45.0 * i_no, 20.0 * i_fase, jd)
                orbita = ef.OrbitaTerrestre(omm)
                geo = orbita.posicao(jd)
                if melhor is None:
                    melhor = orbita
                if (ef.na_sombra_da_terra(vec_add(terra, geo), terra) > 0.0
                        or ef.na_sombra_da_terra(vec_add(terra, orbita.posicao(jd + 25.0 / 1440.0)),
                                                 terra) > 0.0):
                    continue
                nota = dot_product(mat_apply_t(self._station_basis_at(orbita, jd), sol), preferida)
                if nota > nota_max:
                    melhor, nota_max = orbita, nota
        return melhor

    @staticmethod
    def _station_basis_at(orbita, jd):
        geo = orbita.posicao(jd)
        depois = orbita.posicao(jd + UM_SEGUNDO)
        lvlh = lvlh_basis(ef.direcao_para_mundo(geo), ef.direcao_para_mundo(vec_sub(depois, geo)))
        return mat_mul(lvlh, STATION_PITCH_BASIS)

    # -- relógio orbital ----------------------------------------------------
    @property
    def jd(self):
        return self.jd_start + self.anim_time / ef.SEGUNDOS_DIA

    @property
    def utc(self):
        return ef.datetime_de_jd(self.jd)

    @property
    def time_scale(self):
        return TIME_SCALES[self.time_scale_index][0]

    @property
    def time_scale_label(self):
        return TIME_SCALES[self.time_scale_index][1]

    def change_time_scale(self, passo):
        """Teclas , e .: desacelera ou acelera o relógio do Sistema Solar."""
        self.time_scale_index = int(clamp(self.time_scale_index + passo, 0, len(TIME_SCALES) - 1))
        return self.time_scale

    # -- enquadramento ------------------------------------------------------
    @property
    def zoom_level(self):
        return ZOOM_LEVELS[self.zoom_index]

    def change_zoom(self, passo):
        """Teclas Z e X: aproxima ou afasta, trocando também o que fica centrado."""
        self.focus_index = None
        self.zoom_index = int(clamp(self.zoom_index + passo, 0, len(ZOOM_LEVELS) - 1))
        return self.zoom_level

    def focus_targets(self):
        """nome -> (malha, raio em unidades) dos corpos e naves que a tecla P visita."""
        alvos = {nome: (corpo.mesh, corpo.radius) for nome, corpo in self.bodies.items()}
        for s in self.satellites:
            if s.model != "gps":
                alvos[s.name] = (s.body, max(s.body.bounding_radius, 40.0))
        return alvos

    def focus_names(self):
        alvos = self.focus_targets()
        return [n for n in catalogo.ORDEM_FOCO if n in alvos]

    @property
    def focus_name(self):
        nomes = self.focus_names()
        if self.focus_index is None or not nomes:
            return None
        return nomes[self.focus_index % len(nomes)]

    def cycle_focus(self, passo=1):
        """Tecla P (Shift+P volta): percorre Sol, planetas, luas e naves, do Sol para fora."""
        nomes = self.focus_names()
        if not nomes:
            return None
        if self.focus_index is None:
            self.focus_index = 0 if passo > 0 else len(nomes) - 1
        else:
            self.focus_index = (self.focus_index + passo) % len(nomes)
        return nomes[self.focus_index]

    def anchor_position(self, nome):
        """Ponto que a câmera acompanha em cada nível de zoom."""
        if nome == "earth":
            return self.earth.pos
        if nome == "sun":
            return SUN_POS
        return self.station_pos

    def _camera_anchor(self):
        """(posição, zoom, fonte, base, orbital) da âncora atual da câmera."""
        foco = self.focus_name
        if foco is not None:
            malha, raio = self.focus_targets()[foco]
            return (malha.pos, max(raio * 6.5, 120.0) / PRESET_DISTANCE, "foco:" + foco,
                    IDENTIDADE, True)
        nivel = self.zoom_level
        if nivel["anchor"] == "station":
            return self.station_pos, nivel["scale"], "station", self.station_basis, False
        return (self.anchor_position(nivel["anchor"]), nivel["scale"], nivel["anchor"],
                IDENTIDADE, True)

    def _aim_camera(self):
        pos, zoom, fonte, base, orbital = self._camera_anchor()
        self.camera.usar_presets_orbitais(orbital)
        self.camera.set_anchor(pos, zoom, fonte=fonte, basis=base)
        perto_da_terra = length(vec_sub(self.camera.eye, self.earth.pos)) < 30.0 * self.bodies["Terra"].radius
        self.camera.fill_dir = (normalize(vec_sub(self.earth.pos, self.camera.eye))
                                if perto_da_terra else FILL_DIR)

    # -- traçados, rótulos e sombra ------------------------------------------
    def orbit_rings(self):
        """
        Traçados das órbitas para o renderizador: (nome, pontos relativos ao
        centro, centro no mundo, cor, raio em unidades). A forma de cada órbita é
        calculada uma vez; a cada quadro só o centro muda — a Terra percorre
        2,6 milhões de km por dia, e recalcular os pontos custaria mais que desenhá-los.
        """
        if self._orbit_cache is None:
            self._orbit_cache = self._build_orbit_lines()
        permitidos = self._orbit_families_in_view()
        saida = []
        for nome, pontos, pai, cor, raio in self._orbit_cache:
            if pai not in permitidos:
                continue
            centro = SUN_POS if pai is None else self.bodies[pai].mesh.pos
            saida.append((nome, pontos, centro, cor, raio))
        return saida

    def _orbit_families_in_view(self):
        """
        Quais famílias de órbitas fazem sentido no enquadramento (None são as
        heliocêntricas). Vista de dentro, a órbita de Vênus é um arco que corta
        o céu da doca; perto da estação, nenhum traçado aparece.
        """
        foco = self.focus_name
        if foco is not None:
            corpo = self.bodies.get(foco)
            if corpo is None:
                return {"Terra"}                   # nave em órbita da Terra ou em L2
            if corpo.parent is None:
                return {None, foco}
            return {corpo.parent.name}
        nivel = self.zoom_level
        if nivel["anchor"] == "sun":
            return {None}
        if nivel["anchor"] == "earth" or nivel["scale"] > 1000.0:
            return {"Terra"}
        return set()

    def _build_orbit_lines(self):
        jd = self.jd_start

        def mundo(v):
            return vec_scale(ef.direcao_para_mundo(v), KM)

        def escurecer(cor, k=0.55):
            return tuple(int(c * k) for c in cor)

        linhas = []
        for nome, _raio, cor, _mapa in catalogo.PLANETAS:
            nome_el = "Terra-Lua" if nome == "Terra" else nome
            orbita = ef.orbita_planeta(nome_el, jd)
            linhas.append((nome, [mundo(p) for p in orbita.pontos(180)], None, escurecer(cor),
                           orbita.a * KM))
        for nome, corpo in self.bodies.items():
            if corpo.orbit is None:
                continue
            if corpo.parent is None:
                if corpo.kind == "anão" or nome in ORBIT_LINE_EXTRAS:
                    linhas.append((nome, [mundo(p) for p in corpo.orbit.pontos(160)], None,
                                   escurecer(corpo.color, 0.42), corpo.orbit.a * KM))
            else:
                linhas.append((nome, [mundo(p) for p in corpo.orbit.pontos(72)],
                               corpo.parent.name, escurecer(corpo.color, 0.5), corpo.orbit.a * KM))
        lua = [mundo(ef.posicao_lua_geocentrica(jd + 27.32 * k / 90.0)) for k in range(90)]
        linhas.append(("Lua", lua, "Terra", (168, 172, 186), 384400.0 * KM))
        periodo = self.station_orbit.periodo_min / 1440.0
        estacao = [mundo(self.station_orbit.posicao(jd + periodo * k / 96.0)) for k in range(96)]
        linhas.append(("Órbita-2", estacao, "Terra", (86, 226, 198), self.station_orbit.a * KM))
        for s in self.satellites:
            if s.orbit is not None and s.model in ("iss", "hubble", "tiangong", "goes"):
                p = s.orbit.periodo_min / 1440.0
                linhas.append((s.name, [mundo(s.orbit.posicao(jd + p * k / 96.0)) for k in range(96)],
                               "Terra", escurecer(SATELLITE_COLORS[s.model], 0.5), s.orbit.a * KM))
        geo = 42164.0
        anel = [mundo(ef.equatorial_para_ecliptica((geo * math.cos(a), geo * math.sin(a), 0.0)))
                for a in (2.0 * math.pi * k / 120.0 for k in range(120))]
        linhas.append(("Anel geoestacionário", anel, "Terra", (110, 80, 110), geo * KM))
        if self.jwst_table is not None:
            pontos = [self.jwst_table.posicao(jd + d) for d in range(-60, 180, 2)]
            pontos = [mundo(p) for p in pontos if p is not None]
            if len(pontos) > 2:
                linhas.append(("Halo do James Webb", pontos, "Terra", (150, 120, 60),
                               1.5e6 * KM))
        return linhas

    def label_targets(self):
        """
        Rótulos da tecla N: nome e papel de cada objeto no requisito 3 —
        instâncias de um mesmo tipo, objetos sem partes e objetos compostos.
        """
        rotulos = [("%s · instância" % r.name.replace("Robô ", ""), r.pos) for r in self.robots]
        rotulos += [("%s · composto" % m.name, m.pos) for m in (self.station, self.lab, self.cargo)]
        rotulos += [("%s · sem partes" % m.name, m.pos) for m in (self.earth, self.moon)]
        return rotulos

    def body_labels(self):
        """(nome, malha, prioridade) de corpos e naves, para os rótulos automáticos."""
        prioridade = {"estrela": 0, "planeta": 0, "anão": 1, "lua": 2, "cometa": 3,
                      "asteroide": 3, "transnetuniano": 3}
        saida = [(nome, corpo.mesh, prioridade.get(corpo.kind, 3))
                 for nome, corpo in self.bodies.items()]
        saida += [(s.name, s.body, 1 if s.model != "gps" else 4) for s in self.satellites]
        return saida

    def shadow_factor(self, ponto_km):
        """Quanto o ponto (km, heliocêntrico) está eclipsado pela Terra, de 0 a 1."""
        return ef.na_sombra_da_terra(ponto_km, self.bodies["Terra"].pos_km)

    # -- transformação hierárquica pai -> filho ---------------------------
    def to_world(self, local, t=None):
        """
        Converte um ponto do referencial da estação para o mundo. A estação voa
        em LVLH ao redor da Terra, então tanto a origem quanto a orientação
        desse referencial mudam a cada quadro, e tudo que é filho dela acompanha.
        """
        return vec_add(self.station_pos, mat_apply(self.station_basis, local))

    # -- controle ---------------------------------------------------------
    def reset(self):
        self.state = STATE_PARADO
        self.sim_time = 0.0
        self.anim_time = 0.0
        self.wall_time = 0.0
        self.cycles = 0
        self.particles.clear()
        self.apply_animation(0.0, detalhe_total=True)
        self._aim_camera()
        self.camera.snap_to(DEFAULT_CAMERA)
        self.sight = self.line_of_sight()

    def toggle(self):
        """ESPAÇO: iniciar / pausar / retomar / reiniciar ao final."""
        if self.state in (STATE_PARADO, STATE_PAUSADO):
            self.state = STATE_EXECUTANDO
        elif self.state == STATE_EXECUTANDO:
            self.state = STATE_PAUSADO
        else:
            self.sim_time = 0.0
            self.particles.clear()
            self.state = STATE_EXECUTANDO
        return self.state

    def goto_phase(self, n):
        """Teclas 1-4: salta para o início de uma fase (alternar animações)."""
        n = int(clamp(n, 1, len(PHASE_BOUNDS)))
        self.sim_time = 0.0 if n == 1 else PHASE_BOUNDS[n - 2]
        self.state = STATE_EXECUTANDO
        self.particles.clear()
        self.apply_animation(self.sim_time)
        return n

    @property
    def phase_bounds(self):
        """No modo de órbita estendida só a última fase muda de duração."""
        if not self.extended_orbit:
            return PHASE_BOUNDS
        return PHASE_BOUNDS[:-1] + (PHASE_BOUNDS[-2] + EXTENDED_ORBIT_TIME,)

    @property
    def total_time(self):
        return self.phase_bounds[-1]

    @property
    def speed(self):
        return SPEED_STEPS[self.speed_index]

    @property
    def phase_index(self):
        for i, limite in enumerate(self.phase_bounds):
            if self.sim_time < limite:
                return i
        return len(PHASE_BOUNDS) - 1

    @property
    def phase_label(self):
        if self.state == STATE_PARADO:
            return "Em espera - pressione ESPAÇO"
        if self.state == STATE_CONCLUIDO:
            return "Sequência concluída - ESPAÇO reinicia"
        return PHASE_NAMES[self.phase_index]

    @property
    def progress(self):
        return clamp(self.sim_time / self.total_time, 0.0, 1.0)

    # -- controles de observação ------------------------------------------
    def toggle_loop(self):
        """Tecla L: repetir a sequência indefinidamente."""
        self.loop = not self.loop
        if self.loop and self.state == STATE_CONCLUIDO:
            self.sim_time = 0.0
            self.state = STATE_EXECUTANDO
        return self.loop

    def toggle_extended_orbit(self):
        """Tecla O: alonga a fase de inspeção até três voltas dos robôs."""
        self.extended_orbit = not self.extended_orbit
        if self.sim_time > self.total_time:
            self.sim_time = self.total_time
        return self.extended_orbit

    def toggle_tour(self):
        """Tecla T: a câmera troca sozinha a cada fase, seguindo TOUR_CAMERAS."""
        self.tour = not self.tour
        return self.tour

    def change_speed(self, passo):
        """Teclas + e -: escolhe entre os fatores de velocidade previstos."""
        self.speed_index = int(clamp(self.speed_index + passo, 0, len(SPEED_STEPS) - 1))
        return self.speed

    # -- laço de atualização ----------------------------------------------
    def update(self, dt):
        antes = self.sim_time
        # o relógio orbital segue a escala de tempo, com a sequência parada ou não
        self.anim_time += dt * self.time_scale
        if self.state == STATE_EXECUTANDO:
            passo = dt * self.speed
            self.wall_time += passo
            self.sim_time += passo
            if self.sim_time >= self.total_time:
                if self.loop:
                    # guarda o excedente em vez de zerar: o ciclo emenda sem engasgo
                    self.cycles += 1
                    self.sim_time -= self.total_time
                    self.particles.clear()
                else:
                    self.sim_time = self.total_time
                    self.state = STATE_CONCLUIDO
        else:
            self.wall_time += dt          # o ambiente respira mesmo em pausa
        self.apply_animation(self.sim_time, emitir=(self.state == STATE_EXECUTANDO))
        self.particles.update(dt)
        if self.tour:
            chave = TOUR_CAMERAS[self.phase_index]
            if self.camera.key != chave:
                # reaproveita as transições interpoladas das teclas de câmera
                if chave == FOLLOW_CAMERA:
                    self.camera.follow(self.cargo)
                else:
                    self.camera.go_to(chave)
        self._aim_camera()
        if antes < DOCKING_LATCH_TIME <= self.sim_time:
            self._emit_docking_sparks()
        pulso = docking_pulse(self.sim_time) if self.state == STATE_EXECUTANDO else 0.0
        if pulso > 0.0 and self.focus_index is None:
            # tremor curto da trava, somado por cima da pose da câmera
            a = 7.0 * min(self.camera.zoom, 40.0) * pulso
            tau = self.wall_time
            self.camera.shake = (a * math.sin(tau * 47.0), a * math.sin(tau * 61.0),
                                 a * math.sin(tau * 53.0))
        else:
            self.camera.shake = (0.0, 0.0, 0.0)
        self.camera.update(dt)
        self.bodies["Terra"].update_horizon_cap(self.camera.eye, self.camera.forward)
        self._update_clouds()
        self.sight = self.line_of_sight()

    def _update_clouds(self):
        """Avança as nuvens visíveis por lotes; o tamanho do lote cresce com a escala de tempo."""
        jd = self.jd
        acelerado = self.time_scale >= 3600.0
        for nuvem in self.clouds:
            if nuvem.visible:
                nuvem.update(jd, 400 if acelerado else 40)
        for nuvem in self.satellite_clouds:
            if nuvem.visible:
                nuvem.update(jd, 250 if self.time_scale > 1.0 else max(10, len(nuvem) // 90))

    def _emit_docking_sparks(self):
        """Faíscas da trava: quatro jatos radiais saindo do anel de doca (referencial local)."""
        for direcao in ((0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)):
            self.particles.emit((92.0, 0.0, 0.0), direcao, count=6, speed=120.0)

    def apply_animation(self, t, emitir=False, detalhe_total=False):
        jd = self.jd
        self._place_bodies(jd, detalhe_total)
        self._place_station(jd)
        base = self.station_basis
        self.station.update(pos=self.station_pos, basis=base)
        self.lab.update(pos=self.to_world((-184.0, 0.0, 0.0)), basis=base)
        para_o_sol = normalize(vec_scale(ef.direcao_para_mundo(self.station_km), -1.0))
        sombra = self.shadow_factor(self.station_km)
        for painel in self.station_arrays:
            painel.place(self.station_pos, base, para_o_sol, sombra)

        self._animate_door(t)
        self._animate_cargo(t, emitir)
        self._animate_robots(t)
        self._animate_debris(self.wall_time)
        self.beacons.set_from_time(t, acoplado=(t >= PHASE_BOUNDS[1]))
        self._place_satellites(jd, detalhe_total)
        self._update_shadows(sombra)

    def _place_bodies(self, jd, detalhe_total):
        """Posição heliocêntrica de cada corpo; a rotação só é calculada perto da câmera."""
        olho = self.camera.eye if hasattr(self, "camera") else None
        terra_km = ef.posicao_terra(jd)
        for nome, corpo in self.bodies.items():
            if nome == "Sol":
                corpo.pos_km = (0.0, 0.0, 0.0)
            elif nome == "Terra":
                corpo.pos_km = terra_km
            elif corpo.kind == "planeta":
                corpo.pos_km = ef.posicao_planeta(nome, jd)
            elif nome == "Lua":
                corpo.pos_km = vec_add(terra_km, ef.posicao_lua_geocentrica(jd))
            elif corpo.parent is not None:
                corpo.pos_km = vec_add(corpo.parent.pos_km, corpo.orbit.posicao(jd))
            else:
                corpo.pos_km = corpo.orbit.posicao(jd)
            pos = ef.para_mundo(corpo.pos_km)
            corpo.mesh.update(pos=pos)
            if not detalhe_total and olho is not None:
                d = length(vec_sub(olho, pos))
                if corpo.mesh.bounding_radius * FOV < 0.8 * d:
                    continue                      # marcador: a orientação não aparece
            base = ef.base_rotacao(nome, jd)
            if base is None and corpo.parent is not None and corpo.orbit is not None:
                rel = vec_sub(corpo.parent.pos_km, corpo.pos_km)
                base = ef.base_sincrona(rel, corpo.orbit.normal)
            if base is None:
                base = mat_axis_angle(ECLIPTIC_NORTH, (jd - ef.JD_J2000) * 360.0 / 0.4)
            corpo.mesh.update(basis=base)
        for planeta, anel in self.rings:
            alpha0, delta0, _w0, _taxa = ef.ROTACAO_IAU[planeta.name]
            anel.update(pos=planeta.mesh.pos,
                        basis=ef.base_para_mundo(*ef.eixos_iau(alpha0, delta0, 0.0)))

    def _place_station(self, jd):
        terra = self.bodies["Terra"]
        geo = self.station_orbit.posicao(jd)
        self.station_km = vec_add(terra.pos_km, geo)
        self.station_pos = vec_add(terra.mesh.pos, vec_scale(ef.direcao_para_mundo(geo), KM))
        self.station_basis = self._station_basis_at(self.station_orbit, jd)

    def _place_satellites(self, jd, detalhe_total):
        terra = self.bodies["Terra"]
        olho = self.camera.eye if hasattr(self, "camera") else None
        for s in self.satellites:
            if s.orbit is not None:
                geo = s.orbit.posicao(jd)
            else:
                geo = self.jwst_table.posicao(jd) if self.jwst_table is not None else None
                if geo is None:
                    geo = ef.posicao_l2_aproximada(terra.pos_km)
            detalhe = detalhe_total
            if not detalhe and olho is not None:
                pos = vec_add(terra.mesh.pos, vec_scale(ef.direcao_para_mundo(geo), KM))
                detalhe = s.body.bounding_radius * FOV > 0.6 * length(vec_sub(olho, pos))
            s.place(jd, terra.pos_km, terra.mesh.pos, geo, detalhe)

    def _animate_debris(self, t):
        """Detritos em órbita relativa lenta em torno da estação, cada um em ritmo próprio."""
        for i, d in enumerate(self.debris):
            orbita, fase, incl, veloc = self.debris_orbits[i]
            d.update(pos=self.to_world(orbit_point((0.0, 0.0, 0.0), orbita, t * veloc + fase, incl)),
                     rot=(t * (9.0 + i * 5.0), t * (13.0 - i * 3.0), t * 4.0))

    def _update_shadows(self, sombra_estacao):
        """
        Eclipse: o que está no cilindro de sombra da Terra escurece. A estação e
        tudo que é filho dela compartilham a mesma sombra; a Lua testa a própria.
        """
        for m in (self.station, self.lab, self.door_hi, self.door_lo, self.cargo):
            m.shadow = sombra_estacao
        for painel in self.station_arrays:
            painel.mesh.shadow = sombra_estacao
        for m in self.debris:
            m.shadow = sombra_estacao
        for r in self.robots:
            for m in r.meshes:
                m.shadow = sombra_estacao
        self.moon.shadow = self.shadow_factor(self.bodies["Lua"].pos_km)

    def _animate_door(self, t):
        self.door.set_from_time(t)
        desloc = 36.0 * self.door.opening
        base = self.station_basis
        self.door_hi.update(pos=self.to_world((92.0, desloc, 0.0)), basis=base)
        self.door_lo.update(pos=self.to_world((92.0, -desloc, 0.0)), basis=base)

    def cargo_x(self, t):
        """Posição do cargueiro no eixo de aproximação, suavizada por fase."""
        if t < PHASE_BOUNDS[0]:
            return lerp(CARGO_X[0], CARGO_X[1], smoothstep(t / PHASE_BOUNDS[0]))
        if t < PHASE_BOUNDS[1]:
            k = (t - PHASE_BOUNDS[0]) / (PHASE_BOUNDS[1] - PHASE_BOUNDS[0])
            return lerp(CARGO_X[1], CARGO_X[2], smoothstep(k))
        if t < PHASE_BOUNDS[2]:
            k = (t - PHASE_BOUNDS[1]) / (PHASE_BOUNDS[2] - PHASE_BOUNDS[1])
            return lerp(CARGO_X[2], CARGO_X[3], smoothstep(k))
        return CARGO_X[3]

    def _animate_cargo(self, t, emitir):
        x = self.cargo_x(t)
        # quanto mais perto da doca, menor o desalinhamento residual
        aproximacao = clamp((CARGO_X[0] - x) / (CARGO_X[0] - CARGO_X[3]), 0.0, 1.0)
        residual = 1.0 - smoothstep(aproximacao)
        y = 34.0 * residual * math.sin(t * 1.5)
        z = 26.0 * residual * math.sin(t * 1.1 + 1.0)
        roll = t * 46.0 * residual
        pitch = 7.0 * residual * math.sin(t * 2.1)
        escala = 1.0
        if PHASE_BOUNDS[0] <= t < PHASE_BOUNDS[1]:
            escala = 1.0 + 0.035 * math.sin(t * 11.0)    # pulsação dos retros
        local = mat_from_euler((roll, 0.0, pitch))
        self.cargo.update(pos=self.to_world((x, y, z)),
                          basis=mat_mul(self.station_basis, local), scale=escala)
        if emitir and t < PHASE_BOUNDS[2]:
            bocal = vec_add((x, y, z), mat_apply(local, (80.0, 0.0, 0.0)))
            self.particles.emit(bocal, (1.0, 0.0, 0.0), count=4, speed=170.0)

    def _animate_robots(self, t):
        """
        Fases 1 a 3: robôs ancorados no casco. Fase 4: saem em trajetória
        helicoidal, desviando do mastro, com os braços em operação.
        """
        inicio = PHASE_BOUNDS[2]
        saida = smoothstep(clamp((t - inicio) / 1.2, 0.0, 1.0)) if t >= inicio else 0.0
        for i, robo in enumerate(self.robots):
            raio, offset_x, veloc, fase, incl = robo.params
            ancora = ROBOT_DOCK_LOCAL[i]
            ang = (t - inicio) * veloc + fase
            orbita = (offset_x + 26.0 * math.sin(ang * 0.7),
                      raio * math.cos(ang),
                      raio * math.sin(ang))
            orbita = rotate_xyz(orbita, (0.0, 0.0, incl))
            orbita, desviou = self._avoid_mast(orbita)
            local = tuple(lerp(ancora[k], orbita[k], saida) for k in range(3))
            giro = math.degrees(ang) % 360.0 if saida > 0.0 else 0.0
            # braço em operação: ombro e cotovelo oscilam fora de fase
            ombro = -26.0 + 32.0 * math.sin(t * 1.4 + fase)
            cotovelo = 44.0 + 28.0 * math.sin(t * 2.0 + fase * 1.7)
            robo.place(self.to_world(local), giro, 18.0 * math.sin(ang * 1.3), ombro, cotovelo,
                       self.station_basis)
            robo.avoided = desviou and saida > 0.05

    @staticmethod
    def _avoid_mast(local):
        """
        Evitação de colisão com o mastro da antena: se a trajetória entra no
        cilindro de segurança, o ponto é empurrado radialmente para fora.
        """
        if not (20.0 < local[1] < 170.0):
            return local, False
        dx = local[0] - MAST_X
        dz = local[2] - MAST_Z
        dist = math.sqrt(dx * dx + dz * dz)
        if dist >= MAST_SAFE_RADIUS:
            return local, False
        if dist < 1e-6:
            dx, dz, dist = 1.0, 0.0, 1.0
        k = MAST_SAFE_RADIUS / dist
        return (MAST_X + dx * k, local[1], MAST_Z + dz * k), True

    # -- traçado de raio: linha de visão (requisito 9) --------------------
    def occluders(self):
        """Esferas envolventes que podem bloquear o sensor."""
        lista = [(d.pos, d.bounding_radius * 0.82, d.name) for d in self.debris]
        lista.append((self.to_world((-20.0, 0.0, 0.0)), 62.0, "Núcleo"))
        return lista

    def line_of_sight(self):
        """
        Dispara um raio do sensor da antena até cada alvo e testa interseção
        com as esferas envolventes dos obstáculos. Cada item descreve uma
        linha: origem, ponto final, se está livre e quem bloqueou.
        """
        origem = self.to_world(SENSOR_LOCAL)
        alvos = [self.cargo] if self.sim_time < PHASE_BOUNDS[2] else list(self.robots)
        resultado = []
        for alvo in alvos:
            delta = vec_sub(alvo.pos, origem)
            dist = length(delta)
            if dist < 1e-6:
                continue
            direcao = vec_scale(delta, 1.0 / dist)
            bloqueio, quem = None, None
            for centro, raio, nome in self.occluders():
                t_hit = ray_sphere(origem, direcao, centro, raio)
                if t_hit is None or t_hit >= dist - alvo.bounding_radius:
                    continue
                if bloqueio is None or t_hit < bloqueio:
                    bloqueio, quem = t_hit, nome
            if bloqueio is None:
                ponto = vec_sub(alvo.pos, vec_scale(direcao, alvo.bounding_radius))
                livre, bloq = True, None
            else:
                ponto = vec_add(origem, vec_scale(direcao, bloqueio))
                livre, bloq = False, quem
            resultado.append({"alvo": alvo.name, "origem": origem, "ponto": ponto,
                              "livre": livre, "bloqueador": bloq, "dist": dist})
        return resultado


# ============================================================
# 10. RENDERIZAÇÃO DA CENA
# ============================================================
class GlowSprites:
    """
    Halos pré-renderizados. Desenhar um degradê radial a cada quadro seria caro
    em Python; guardar o sprite e somá-lo deixa o trabalho para o código nativo
    do Pygame.

    A soma aditiva do Pygame ignora o canal alpha como atenuação, então a cor de
    cada anel já é gravada multiplicada pela intensidade desejada. Sem isso o
    halo vira um disco chapado em vez de um brilho.

    Memória: nenhum sprite passa de RAIO_BASE. Um halo maior (o Sol ou a Terra
    com a câmera próxima) é ampliado a partir do sprite base, e só no trecho
    que cai dentro da tela. Sem esse teto, um astro a poucas unidades do plano
    próximo pedia um sprite de (2·raio)² pixels, dezenas de GB, e o cache
    chegava a guardar 120 deles.
    """

    PASSO = 4            # raios são quantizados, senão o cache cresce demais
    RAIO_BASE = 256      # maior sprite guardado: 512 x 512 pixels, cerca de 1 MB
    ORCAMENTO = 32 * 1024 * 1024     # teto de memória do cache, em bytes

    def __init__(self):
        self._cache = {}     # o dict preserva a ordem de inserção: vira um LRU
        self._bytes = 0

    def sprite(self, raio, cor, intensidade, queda):
        raio = max(self.PASSO, min(self.RAIO_BASE, int(raio / self.PASSO) * self.PASSO))
        # a cor das partículas varia continuamente; arredondar para múltiplos de
        # 8 é imperceptível no brilho e evita um sprite novo a cada tonalidade
        cor = tuple(min(255, (c + 4) & ~7) for c in cor)
        chave = (raio, cor, intensidade, queda)
        pronto = self._cache.pop(chave, None)
        if pronto is None:
            lado = raio * 2
            pronto = pygame.Surface((lado, lado), pygame.SRCALPHA)
            passos = max(4, min(48, raio // 3))
            for i in range(passos, 0, -1):
                t = i / passos
                f = intensidade * (1.0 - t) ** queda
                if f <= 0.004:
                    continue
                pygame.draw.circle(pronto, (int(cor[0] * f), int(cor[1] * f),
                                            int(cor[2] * f), 255),
                                   (raio, raio), max(1, int(raio * t)))
            self._bytes += lado * lado * 4
            while self._bytes > self.ORCAMENTO and self._cache:
                velho = self._cache.pop(next(iter(self._cache)))
                self._bytes -= velho.get_width() * velho.get_height() * 4
        self._cache[chave] = pronto          # reinserido no fim: usado há pouco
        return pronto, raio

    def blit(self, surface, centro, raio, cor, intensidade=0.55, queda=2.2):
        if raio < 2:
            return
        cx, cy = centro
        clip = surface.get_clip()
        if (cx + raio <= clip.left or cx - raio >= clip.right
                or cy + raio <= clip.top or cy - raio >= clip.bottom):
            return                           # fora da tela: nada a alocar
        if raio <= self.RAIO_BASE:
            sprite, raio = self.sprite(raio, cor, intensidade, queda)
            surface.blit(sprite, (cx - raio, cy - raio),
                         special_flags=pygame.BLEND_RGB_ADD)
            return

        # Halo maior que o sprite base: amplia apenas o recorte visível, de modo
        # que a superfície temporária nunca passa do tamanho da janela.
        base, rb = self.sprite(self.RAIO_BASE, cor, intensidade, queda)
        caixa = pygame.Rect(cx - raio, cy - raio, 2 * raio, 2 * raio)
        visivel = caixa.clip(clip)
        if not visivel:
            return
        k = rb / raio                        # pixels do sprite base por pixel de tela
        fonte = pygame.Rect(round((visivel.x - caixa.x) * k),
                            round((visivel.y - caixa.y) * k),
                            max(1, math.ceil(visivel.w * k)),
                            max(1, math.ceil(visivel.h * k))).clip(base.get_rect())
        if not fonte:
            return
        trecho = pygame.transform.scale(base.subsurface(fonte), visivel.size)
        surface.blit(trecho, visivel.topleft, special_flags=pygame.BLEND_RGB_ADD)


MARKER_THRESHOLD_PX = 1.6      # abaixo deste raio projetado, a malha vira marcador
BACKDROP_MODES = ("estrelas", "webb", "hubble")
BACKDROP_NAMES = {"estrelas": "estrelas reais", "webb": "James Webb", "hubble": "Hubble"}
BACKDROP_VEIL = 88             # escurecimento da imagem de fundo, de 0 a 255


class Renderer:
    """
    Desenha a cena numa Surface qualquer (funciona fora da tela, o que permite
    testar a renderização sem abrir janela). Polígonos, partículas, balizas e
    marcadores entram num único buffer ordenado por profundidade: é o algoritmo
    do pintor aplicado a todos os elementos, não só às faces.
    """

    def __init__(self):
        self.faces_desenhadas = 0
        self.faces_descartadas = 0
        self.marcadores = 0
        self.pontos_desenhados = 0
        self.glow = GlowSprites()
        self._stars_key = None
        self._stars_proj = []
        self.show_orbits = True
        self.backdrop_mode = "estrelas"
        self.backdrops = {}                  # fonte -> (Surface, informações da imagem)
        self.backdrop_status = {}            # fonte -> texto enquanto não há imagem
        self._backdrop_ready = (None, None)
        self.schedule = None                 # visitas da agenda do James Webb
        self.schedule_status = ""

    # -- imagem de fundo dos telescópios -------------------------------------
    def set_backdrop(self, fonte, superficie, info):
        self.backdrops[fonte] = (superficie, info)
        self._backdrop_ready = (None, None)

    def cycle_backdrop(self):
        """Tecla V: estrelas reais -> James Webb -> Hubble."""
        i = BACKDROP_MODES.index(self.backdrop_mode)
        self.backdrop_mode = BACKDROP_MODES[(i + 1) % len(BACKDROP_MODES)]
        return self.backdrop_mode

    def backdrop_info(self):
        par = self.backdrops.get(self.backdrop_mode)
        return par[1] if par else None

    def _backdrop_surface(self):
        """
        A imagem do telescópio ampliada ou reduzida para cobrir a tela inteira,
        com corte central — sem faixas pretas e sem distorcer — e escurecida
        para a cena continuar legível. Só a versão pronta para o tamanho atual
        fica guardada: uma imagem 4K em memória ocupa 33 MB.
        """
        if self.backdrop_mode == "estrelas" or self.backdrop_mode not in self.backdrops:
            return None
        chave = (self.backdrop_mode, WIDTH, HEIGHT)
        if self._backdrop_ready[0] == chave:
            return self._backdrop_ready[1]
        original = self.backdrops[self.backdrop_mode][0]
        w, h = original.get_size()
        k = max(WIDTH / w, HEIGHT / h)
        tamanho = (max(WIDTH, int(math.ceil(w * k))), max(HEIGHT, int(math.ceil(h * k))))
        if original.get_bitsize() in (24, 32):
            escalada = pygame.transform.smoothscale(original, tamanho)
        else:
            escalada = pygame.transform.scale(original, tamanho)
        x, y = (tamanho[0] - WIDTH) // 2, (tamanho[1] - HEIGHT) // 2
        pronta = pygame.Surface((WIDTH, HEIGHT))
        pronta.blit(escalada, (-x, -y))
        veu = pygame.Surface((WIDTH, HEIGHT))
        veu.fill((0, 0, 0))
        veu.set_alpha(BACKDROP_VEIL)
        pronta.blit(veu, (0, 0))
        self._backdrop_ready = (chave, pronta)
        return pronta

    # -- quadro --------------------------------------------------------------
    def draw(self, surface, scene):
        configurar_viewport(*surface.get_size())
        cam = scene.camera
        fundo = self._backdrop_surface()
        if fundo is not None:
            surface.blit(fundo, (0, 0))
        else:
            surface.fill(BG_COLOR)
            self._draw_stars(surface, scene, cam)
        self._draw_atmosphere(surface, scene, cam)
        if self.show_orbits:
            self._draw_orbits(surface, scene, cam)
        self._draw_clouds(surface, scene, cam)

        itens = []
        descartadas = 0
        marcadores = 0
        sol = scene.sun
        ex, ey, ez = cam.eye
        fx, fy, fz = cam.forward
        for mesh in scene.meshes:
            if not mesh.visible:
                continue
            px, py, pz = mesh.pos
            profundidade = (px - ex) * fx + (py - ey) * fy + (pz - ez) * fz
            r = mesh.bounding_radius
            if profundidade + r < NEAR:
                descartadas += len(mesh.faces)
                continue
            raio_px = r * FOV / profundidade if profundidade > NEAR else 1e9
            if raio_px < MARKER_THRESHOLD_PX:
                # menor que um pixel e meio: em escala real, é quase tudo
                descartadas += len(mesh.faces)
                if mesh.marker_color is not None and profundidade > NEAR:
                    tela = project_view(cam.to_view(mesh.pos))
                    if 0 <= tela[0] < WIDTH and 0 <= tela[1] < HEIGHT:
                        itens.append((profundidade, 4, tela, (mesh.marker_color, mesh.marker_size)))
                        marcadores += 1
                continue
            if mesh.lods:
                mesh.use_lod(raio_px)
            visiveis, fora = mesh.collect(cam, emissivo=(mesh is sol))
            descartadas += fora
            tipo = 0 if mesh.edges else 5
            for prof, pts, cor in visiveis:
                itens.append((prof, tipo, pts, cor))

        for p in scene.particles.particles:
            mundo = scene.to_world(p["pos"])
            v = cam.to_view(mundo)
            if v[2] < NEAR:
                continue
            raio = max(1, int(p["size"] * p["life"] * FOV / v[2]))
            cor = ExhaustParticles.color_of(p)
            tela = project_view(v)
            cauda = cam.to_view(scene.to_world((p["pos"][0] - p["vel"][0] * 0.045,
                                                p["pos"][1] - p["vel"][1] * 0.045,
                                                p["pos"][2] - p["vel"][2] * 0.045)))
            if cauda[2] >= NEAR:
                itens.append((v[2], 3, (tela, project_view(cauda)), (cor, max(1, raio))))
            else:
                itens.append((v[2], 1, tela, (cor, raio)))
            if p["life"] > 0.78:
                itens.append((v[2] + 0.5, 2, tela, (cor, raio * 4)))

        for k, local in enumerate(scene.beacons.local):
            v = cam.to_view(scene.to_world(local))
            if v[2] < NEAR or v[2] > 60000.0:
                continue
            aceso = (k == scene.beacons.active)
            cor = scene.beacons.color if aceso else tuple(c // 4 for c in scene.beacons.color)
            raio = 6 if aceso else 3
            tela = project_view(v)
            itens.append((v[2], 1, tela, (cor, raio)))
            if aceso:
                itens.append((v[2] + 0.5, 2, tela, (scene.beacons.color, 22)))

        itens.sort(key=lambda it: it[0], reverse=True)
        for _, tipo, a, b in itens:
            if tipo == 0:
                pygame.draw.polygon(surface, b, a)
                # a aresta clara define o facetado, mas em faces de poucos pixels
                # ela só dobraria o custo de rasterização
                p0 = a[0]
                p1 = a[len(a) // 2]
                if abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) > 9:
                    pygame.draw.polygon(surface, (min(255, b[0] + 26),
                                                  min(255, b[1] + 26),
                                                  min(255, b[2] + 26)), a, 1)
            elif tipo == 1:
                pygame.draw.circle(surface, b[0], a, b[1])
            elif tipo == 2:
                self.glow.blit(surface, a, b[1], b[0])
            elif tipo == 5:
                pygame.draw.polygon(surface, b, a)
            elif tipo == 3:
                pygame.draw.line(surface, b[0], a[0], a[1], b[1])
            elif b[1] <= 1:
                surface.set_at(a, b[0])
            else:
                pygame.draw.circle(surface, b[0], a, b[1])

        self.faces_desenhadas = sum(1 for it in itens if it[1] in (0, 5))
        self.faces_descartadas = descartadas
        self.marcadores = marcadores
        self._draw_docking_flash(surface, scene, cam)
        self._draw_sight(surface, scene, cam)

    def _draw_docking_flash(self, surface, scene, cam):
        """Clarão da trava de acoplamento, somado por cima do anel de doca."""
        pulso = docking_pulse(scene.sim_time)
        if pulso <= 0.0:
            return
        v = cam.to_view(scene.to_world((92.0, 0.0, 0.0)))
        if v[2] < NEAR:
            return
        # a intensidade entra na chave do cache de halos: em 8 degraus, a janela
        # de 0,7 s reaproveita sprites em vez de criar um por quadro
        degrau = math.ceil(pulso * 8.0) / 8.0
        self.glow.blit(surface, project_view(v), int(150.0 * FOV / v[2]), (255, 226, 170),
                       intensidade=0.9 * degrau, queda=1.8)

    def _draw_stars(self, surface, scene, cam):
        """
        Campo estelar. As estrelas ficam no infinito: só a orientação da câmera
        as move, e a projeção fica em cache até ela girar. A cintilação continua
        por conta do brilho, recalculado a cada quadro, que custa quase nada.
        """
        chave = (tuple(round(c, 4) for c in cam.forward + cam.up), WIDTH, HEIGHT)
        if chave != self._stars_key:
            self._stars_key = chave
            projetadas = []
            rx, ry, rz = cam.right
            ux, uy, uz = cam.up
            fx, fy, fz = cam.forward
            cx, cy, foco = VIEW_CENTER_X, VIEW_CENTER_Y, FOV
            for star in scene.starfield.stars:
                dx, dy, dz = star["dir"]
                vz = dx * fx + dy * fy + dz * fz
                if vz < 0.05:
                    continue
                x = int((dx * rx + dy * ry + dz * rz) * foco / vz + cx)
                y = int(-(dx * ux + dy * uy + dz * uz) * foco / vz + cy)
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    projetadas.append(((x, y), star))
            self._stars_proj = projetadas

        t = scene.wall_time
        brilho_de = scene.starfield.brightness
        for p, star in self._stars_proj:
            k = brilho_de(star, t)
            cor = (int(star["tom"][0] * k), int(star["tom"][1] * k), int(star["tom"][2] * k))
            tamanho = star["size"]
            if tamanho <= 1:
                surface.set_at(p, cor)
            else:
                pygame.draw.circle(surface, cor, p, tamanho - 1 if tamanho == 2 else tamanho)
                if tamanho >= 3 and k > 0.8:          # cruz de difração nas mais brilhantes
                    braco = tamanho * 3
                    fraco = (cor[0] // 2, cor[1] // 2, cor[2] // 2)
                    pygame.draw.line(surface, fraco, (p[0] - braco, p[1]), (p[0] + braco, p[1]))
                    pygame.draw.line(surface, fraco, (p[0], p[1] - braco), (p[0], p[1] + braco))

    def _draw_atmosphere(self, surface, scene, cam):
        """
        Atmosfera da Terra e coroa do Sol, desenhadas antes das malhas. O brilho
        do Sol só aparece se a linha de visão até ele não atravessa a Terra — o
        mesmo teste raio-esfera do sensor, agora como iluminação binária.
        """
        terra = scene.earth
        v = cam.to_view(terra.pos)
        # de perto (calota do horizonte) o halo centrado no planeta não coincide com o limbo
        if v[2] >= NEAR and length(vec_sub(cam.eye, terra.pos)) > 3.0 * terra.bounding_radius:
            raio = int(terra.bounding_radius * FOV / v[2])
            if raio >= 8:
                centro = project_view(v)
                self.glow.blit(surface, centro, int(raio * 1.5), (46, 96, 172),
                               intensidade=0.34, queda=2.6)
                self.glow.blit(surface, centro, int(raio * 1.14), (104, 158, 228),
                               intensidade=0.5, queda=2.0)
        v = cam.to_view(scene.sun.pos)
        if v[2] >= NEAR and self.sun_visible(scene, cam):
            raio = int(scene.sun.bounding_radius * FOV / v[2])
            centro = project_view(v)
            self.glow.blit(surface, centro, max(int(raio * 3.4), 26), (255, 214, 128),
                           intensidade=0.42, queda=2.2)
            self.glow.blit(surface, centro, max(int(raio * 1.5), 9), (255, 242, 198),
                           intensidade=0.8, queda=2.4)

    @staticmethod
    def sun_visible(scene, cam):
        """Linha de visão do olho ao Sol livre da Terra?"""
        para_o_sol = vec_sub(scene.sun.pos, cam.eye)
        dist = length(para_o_sol)
        if dist < 1e-6:
            return True
        t = ray_sphere(cam.eye, vec_scale(para_o_sol, 1.0 / dist), scene.earth.pos,
                       scene.earth.bounding_radius)
        return t is None or t > dist

    def _draw_orbits(self, surface, scene, cam):
        """
        Traçado das órbitas. Cada anel é uma sequência de pontos projetados; os
        trechos que passam atrás do plano próximo são simplesmente interrompidos.
        Ficam de fora as órbitas pequenas demais na tela e a do próprio corpo
        que a câmera acompanha, que passaria por dentro dela.
        """
        ex, ey, ez = cam.eye
        rx, ry, rz = cam.right
        ux, uy, uz = cam.up
        fx, fy, fz = cam.forward
        cx0, cy0, foco = VIEW_CENTER_X, VIEW_CENTER_Y, FOV
        for _nome, pontos, centro, cor, raio in scene.orbit_rings():
            ox, oy, oz = centro
            dist = math.sqrt((ox - ex) ** 2 + (oy - ey) ** 2 + (oz - ez) ** 2)
            if raio * foco < 3.0 * dist or dist < raio * 0.35 or abs(dist - raio) < raio * 0.03:
                continue
            passo = 3 if raio * foco < 60.0 * dist else 1
            trecho = []
            # a mesma conta de project_point, desenrolada: são milhares de pontos
            # por quadro, e as chamadas de função pesavam mais que a projeção
            for px, py, pz in pontos[::passo] + pontos[:1]:
                dx, dy, dz = ox + px - ex, oy + py - ey, oz + pz - ez
                vz = dx * fx + dy * fy + dz * fz
                if vz < NEAR:
                    if len(trecho) > 1:
                        pygame.draw.lines(surface, cor, False, trecho)
                    trecho = []
                    continue
                x = (dx * rx + dy * ry + dz * rz) * foco / vz + cx0
                y = -(dx * ux + dy * uy + dz * uz) * foco / vz + cy0
                if abs(x) > 1e5 or abs(y) > 1e5:        # quase no plano do olho
                    if len(trecho) > 1:
                        pygame.draw.lines(surface, cor, False, trecho)
                    trecho = []
                    continue
                trecho.append((int(x), int(y)))
            if len(trecho) > 1:
                pygame.draw.lines(surface, cor, False, trecho)

    def _draw_clouds(self, surface, scene, cam):
        """
        Asteroides, cometas e satélites como pontos. As nuvens heliocêntricas só
        aparecem com a câmera longe da Terra, e as de satélites só fora da
        órbita baixa; o que não aparece nem é propagado (`visible`). Pontos atrás
        do disco da Terra não são desenhados.
        """
        terra = scene.earth.pos
        d_terra = length(vec_sub(cam.eye, terra))
        helio = d_terra > 4.0e6 * KM
        satelites = 9000.0 * KM < d_terra < 2.0e6 * KM
        ex, ey, ez = cam.eye
        rx, ry, rz = cam.right
        ux, uy, uz = cam.up
        fx, fy, fz = cam.forward
        cx0, cy0, foco = VIEW_CENTER_X, VIEW_CENTER_Y, FOV
        largura, altura = WIDTH, HEIGHT
        vt = cam.to_view(terra)
        disco = None
        if vt[2] > NEAR:
            et = project_view(vt)
            disco = (et[0], et[1], (scene.earth.bounding_radius * foco / vt[2]) ** 2, vt[2])
        desenhados = 0
        for grupo, visivel, base in ((scene.clouds, helio, SUN_POS),
                                     (scene.satellite_clouds, satelites, terra)):
            for nuvem in grupo:
                nuvem.visible = visivel
                if not visivel:
                    continue
                bx, by, bz = base
                cor = nuvem.color
                for rel in nuvem.positions:
                    if rel is None:
                        continue
                    # km relativos -> mundo, com a reflexão y <-> z desenrolada
                    dx = bx + rel[0] * KM - ex
                    dy = by + rel[2] * KM - ey
                    dz = bz + rel[1] * KM - ez
                    vz = dx * fx + dy * fy + dz * fz
                    if vz < NEAR:
                        continue
                    x = int((dx * rx + dy * ry + dz * rz) * foco / vz + cx0)
                    y = int(-(dx * ux + dy * uy + dz * uz) * foco / vz + cy0)
                    if not (0 <= x < largura and 0 <= y < altura):
                        continue
                    if (disco is not None and vz > disco[3]
                            and (x - disco[0]) ** 2 + (y - disco[1]) ** 2 < disco[2]):
                        continue
                    surface.set_at((x, y), cor)
                    desenhados += 1
        self.pontos_desenhados = desenhados

    @staticmethod
    def _draw_sight(surface, scene, cam):
        """Desenha cada raio: verde quando a linha está livre, vermelho quando bloqueada."""
        for linha in scene.sight:
            a = project_point(linha["origem"], cam)
            b = project_point(linha["ponto"], cam)
            if a is None or b is None:
                continue
            if max(abs(a[0]), abs(a[1]), abs(b[0]), abs(b[1])) > 20000:
                continue
            cor = (58, 226, 150) if linha["livre"] else (242, 74, 74)
            pygame.draw.line(surface, cor, a, b, 2)
            pygame.draw.circle(surface, cor, a, 4)
            if linha["livre"]:
                pygame.draw.circle(surface, (235, 255, 245), b, 3, 1)
            else:
                pygame.draw.circle(surface, (255, 228, 228), b, 5, 2)


# ============================================================
# 11. INTERFACE SOBREPOSTA (HUD) E CRÉDITOS
# ============================================================
TEAM = (
    ("Fellipe Augusto", "2401525", "Coordenação e integração"),
    ("Gabriel Muchon", "2401895", "Modelagem e composição da cena"),
    ("Paloma Eduarda", "2401660", "Animação e máquinas de estado"),
    ("Victor Wenzel", "2401698", "Câmera, interface e testes"),
)

REFERENCES = (
    "Slides da disciplina, Aulas 01 a 08 - Computação Gráfica e RA/RV",
    "Exercícios de aula 01 a 09 (pipeline, transformações, câmera)",
    "Enunciado Atividade-AP_1.pdf - variação Equipe 2, Estação Espacial",
    "Documentação do Pygame - draw, display, image, time e font",
)

DATA_SOURCES = (
    "JPL: posições aproximadas dos planetas, Horizons e SBDB",
    "CelesTrak: elementos orbitais (GP/OMM) dos satélites",
    "Yale Bright Star Catalogue, 5a ed. (VizieR V/50)",
    "Solar System Scope: mapas de cor dos planetas (CC BY 4.0)",
    "ESA/Webb e ESA/Hubble: imagens de fundo (CC BY 4.0)",
    "STScI: agenda de observação do James Webb",
    "Astronomical Almanac (Lua) e IAU WGCCRE (rotação)",
)

CONCEPTS = (
    "Câmera look-at com base ortonormal e transição interpolada",
    "Projeção em perspectiva e recorte no plano próximo",
    "Back-face culling e algoritmo do pintor por profundidade",
    "Sombreamento plano: Lambert, preenchimento e Blinn-Phong",
    "Hierarquia por matrizes: robôs e juntas solares seguindo o Sol",
    "Instanciação: robôs MR-1 a MR-4, satélites GPS e detritos",
    "Traçado de raio: linha de visão e eclipse do Sol pela Terra",
    "Máquinas de estado aninhadas: sequência e comporta de doca",
    "Equação de Kepler: o Sistema Solar na posição de hoje",
    "Níveis de detalhe e calota do horizonte em escala real",
)

HUD_BG = (10, 14, 22)
HUD_TXT = (226, 232, 240)
HUD_DIM = (138, 148, 164)
HUD_ACCENT = (86, 226, 198)
HUD_WARN = (255, 202, 84)


def _cortar(texto, limite):
    return texto if len(texto) <= limite else texto[:limite - 1] + "…"


class Hud:
    """Interface sobreposta: título, estado, tempo, progresso, telescópios e comandos."""

    FOOTER_HEIGHT = 86

    def __init__(self):
        self.font = pygame.font.SysFont("Consolas", 14)
        self.font_small = pygame.font.SysFont("Consolas", 12)
        self.font_bold = pygame.font.SysFont("Consolas", 15, bold=True)
        self.font_title = pygame.font.SysFont("Consolas", 19, bold=True)
        self.show_credits = False
        self.show_debug = False
        self.show_labels = False
        self.rotulos_desenhados = 0
        self._aviso = ""
        self._aviso_restante = 0          # quadros que o aviso ainda fica na tela
        self._texto_cache = {}
        self._camadas = {}
        self._fase_vista = None
        self._flash = 0.0
        self._agenda_segundo = None
        self._agenda_atual = (None, "")

    def txt(self, fonte, texto, antialias, cor):
        """
        Superfície de texto memorizada, com a mesma assinatura de `Font.render`.
        O HUD redesenha as mesmas frases dezenas de vezes por segundo, e
        rasterizar a fonte a cada quadro custava mais que todo o resto da
        interface junta.
        """
        chave = (id(fonte), texto, antialias, cor)
        pronto = self._texto_cache.get(chave)
        if pronto is None:
            if len(self._texto_cache) > 400:      # trava simples de crescimento
                self._texto_cache.clear()
            pronto = fonte.render(texto, antialias, cor)
            self._texto_cache[chave] = pronto
        return pronto

    def _camada(self, largura, altura, cor, alpha):
        """
        Retângulo translúcido reaproveitado. Criar uma Surface do tamanho da
        janela a cada quadro só para escurecê-la gerava megabytes de lixo por
        segundo; cada tamanho é alocado uma vez e a opacidade vira `set_alpha`.
        """
        chave = (largura, altura, cor)
        camada = self._camadas.get(chave)
        if camada is None:
            if len(self._camadas) > 64:
                self._camadas.clear()
            camada = pygame.Surface((largura, altura))
            camada.fill(cor)
            self._camadas[chave] = camada
        camada.set_alpha(alpha)
        return camada

    def _panel(self, surface, rect, alpha=205):
        surface.blit(self._camada(rect[2], rect[3], HUD_BG, alpha), (rect[0], rect[1]))
        pygame.draw.rect(surface, (46, 58, 76), rect, 1, border_radius=4)

    def draw(self, surface, scene, renderer, desempenho=None):
        """`desempenho` é (FPS medido, ms de CPU por quadro), publicado pela App."""
        if self.show_credits:
            self._draw_credits(surface, renderer)
        else:
            self._draw_body_labels(surface, scene)
            if self.show_labels:
                self._draw_labels(surface, scene)
            self._draw_main(surface, scene)
            self._draw_telescope(surface, scene, renderer)
            if self.show_debug:
                self._draw_debug(surface, scene, renderer, desempenho)
        self._draw_notice(surface)

    AVISO_QUADROS = 120                  # cerca de 2 s a 60 FPS

    def notify(self, texto):
        """Aviso curto acima do rodapé; some sozinho, contado por quadro como o clarão."""
        self._aviso = texto
        self._aviso_restante = self.AVISO_QUADROS

    def _draw_notice(self, surface):
        if self._aviso_restante <= 0:
            return
        self._aviso_restante -= 1
        rotulo = self.txt(self.font_bold, self._aviso, True, HUD_ACCENT)
        x = (WIDTH - rotulo.get_width()) // 2
        y = HEIGHT - self.FOOTER_HEIGHT - 52
        self._panel(surface, (x - 12, y - 6, rotulo.get_width() + 24, rotulo.get_height() + 12))
        surface.blit(rotulo, (x, y))

    def _draw_labels(self, surface, scene):
        """
        Tecla N: nome e papel de cada objeto, presos à projeção da sua posição.
        Vêm antes dos painéis, para a interface continuar legível por cima.
        """
        cam = scene.camera
        desenhados = 0
        for texto, pos in scene.label_targets():
            p = project_point(pos, cam)
            if p is None or not (0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT):
                continue
            rotulo = self.txt(self.font, texto, True, HUD_TXT)
            x, y = p[0] + 16, p[1] - 28
            pygame.draw.line(surface, HUD_DIM, p, (x - 4, y + rotulo.get_height() // 2), 1)
            pygame.draw.circle(surface, HUD_ACCENT, p, 3)
            surface.blit(self._camada(rotulo.get_width() + 8, rotulo.get_height() + 2,
                                      HUD_BG, 170), (x - 4, y - 1))
            surface.blit(rotulo, (x, y))
            desenhados += 1
        self.rotulos_desenhados = desenhados

    def _draw_body_labels(self, surface, scene):
        """
        Nomes dos corpos celestes e das naves. Em escala real quase tudo é um
        ponto, e sem nome ninguém sabe qual ponto é Júpiter. Nos enquadramentos
        orbitais aparecem planetas, anões e naves notáveis; com N, todos. Rótulos
        que cairiam em cima de outro são pulados.
        """
        cam = scene.camera
        orbital = cam.presets is ORBITAL_PRESETS
        if not orbital and not self.show_labels:
            return
        limite = 4 if self.show_labels else 1
        ocupado = set()
        for nome, malha, prioridade in sorted(scene.body_labels(), key=lambda r: r[2]):
            if prioridade > limite or not malha.visible:
                continue
            v = cam.to_view(malha.pos)
            if v[2] < NEAR:
                continue
            x, y = project_view(v)
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                continue
            raio = min(int(malha.bounding_radius * FOV / v[2]), 400)
            cor = HUD_TXT if prioridade <= 1 else HUD_DIM
            fonte = self.font if prioridade == 0 else self.font_small
            rotulo = self.txt(fonte, nome, True, cor)
            x0 = x + raio + 6
            # o rótulo ocupa todas as células que a largura dele cobre
            celulas = {(c, (y - 8) // 14) for c in range(x0 // 24, (x0 + rotulo.get_width()) // 24 + 1)}
            if celulas & ocupado:
                continue
            ocupado |= celulas
            surface.blit(rotulo, (x0, y - 8))

    FLASH_DECAIMENTO = 1.0 / 30.0        # cerca de meio segundo a 60 FPS

    def _draw_phase_flash(self, surface, scene):
        """
        Clarão curto a cada troca de fase. Marca o ritmo da sequência sem
        depender de o espectador estar lendo o texto do painel.

        O decaimento é contado por quadro, e não pelo tempo de simulação: com a
        sequência pausada ou concluída o relógio da cena para, e um clarão preso
        a ele ficaria aceso para sempre.
        """
        if scene.phase_index != self._fase_vista:
            self._fase_vista = scene.phase_index
            self._flash = 1.0
        if self._flash <= 0.02:
            return
        surface.blit(self._camada(WIDTH, HEIGHT, (96, 200, 214),
                                  int(26 * self._flash * self._flash)), (0, 0))
        self._flash -= self.FLASH_DECAIMENTO

    def _draw_main(self, surface, scene):
        self._draw_phase_flash(surface, scene)
        self._panel(surface, (18, 14, 650, 168))
        surface.blit(self.txt(self.font_title,
            "ESTAÇÃO ÓRBITA-2  |  Acoplamento e Inspeção Orbital", True, HUD_TXT), (30, 22))
        surface.blit(self.txt(self.font_bold,
            "[%s]  %s" % (scene.state, scene.phase_label), True, HUD_ACCENT), (30, 47))
        surface.blit(self.txt(self.font,
            "Comporta: %-9s Balizas: %-6s Câmera: %s" % (
                scene.door.state,
                "VERDE" if scene.beacons.color == AlertBeacons.GREEN else "ÂMBAR",
                scene.camera.name), True, HUD_TXT), (30, 68))
        texto, cor = self._sensor_text(scene)
        surface.blit(self.txt(self.font, texto, True, cor), (30, 88))
        surface.blit(self.txt(self.font, self._modo_text(scene), True, HUD_DIM), (30, 106))
        foco = scene.focus_name
        enquadramento = ("Foco: %s [P]" % foco) if foco else scene.zoom_level["name"]
        surface.blit(self.txt(self.font, "Enquadramento: %s   (escala real)" % enquadramento,
                              True, HUD_DIM), (30, 124))
        surface.blit(self.txt(self.font, "UTC %s   Relógio orbital: %s" % (
            scene.utc.strftime("%d/%m/%Y %H:%M:%S"), scene.time_scale_label), True,
            HUD_TXT if scene.time_scale == 1.0 else HUD_WARN), (30, 142))
        self._draw_footer(surface, scene)

    @staticmethod
    def _modo_text(scene):
        """Estado dos controles de observação: repetição, órbita e velocidade."""
        partes = ["Velocidade: %gx" % scene.speed]
        if scene.loop:
            partes.append("Repetição: LIGADA (ciclo %d)" % (scene.cycles + 1))
        else:
            partes.append("Repetição: desligada")
        if scene.extended_orbit:
            partes.append("Órbita estendida: ~%g voltas" % ORBIT_TURNS)
        if scene.tour:
            partes.append("Tour: LIGADO")
        return "   ".join(partes)

    @staticmethod
    def _sensor_text(scene):
        """Resumo do teste de linha de visão para o HUD."""
        if not scene.sight:
            return "Sensor da antena: sem alvo", HUD_DIM
        bloqueada = next((s for s in scene.sight if not s["livre"]), None)
        if bloqueada is not None:
            return ("Sensor: linha até %s BLOQUEADA por %s" % (
                bloqueada["alvo"], bloqueada["bloqueador"]), (242, 96, 96))
        livres = len(scene.sight)
        return ("Sensor: %d de %d linha(s) de visão LIVRE(S)" % (livres, livres),
                (58, 226, 150))

    def _draw_telescope(self, surface, scene, renderer):
        """
        Painel dos telescópios: o que o James Webb observa agora pela agenda
        oficial e, com a imagem de fundo ligada, de onde ela veio — o crédito é
        exigido pela licença CC BY 4.0 e fica sempre visível junto da imagem.
        """
        linhas = []
        if renderer.schedule:
            agora = datetime.now(timezone.utc)
            segundo = int(agora.timestamp()) // 5
            if segundo != self._agenda_segundo:
                self._agenda_segundo = segundo
                self._agenda_atual = fontes_online.observacao_em(renderer.schedule, agora)
            visita, situacao = self._agenda_atual
            if visita is not None:
                linhas.append(("JAMES WEBB %s: %s" % (situacao.upper(), _cortar(visita["alvo"], 34)),
                               HUD_ACCENT, self.font_bold))
                linhas.append(("%s  %s-%s UTC  %s" % (
                    _cortar(visita["instrumento"], 34), visita["inicio"].strftime("%d/%m %H:%M"),
                    visita["fim"].strftime("%H:%M"), _cortar(visita["categoria"], 18)),
                    HUD_DIM, self.font_small))
            else:
                linhas.append(("James Webb: %s" % situacao, HUD_DIM, self.font_small))
        elif renderer.schedule_status:
            linhas.append(("Agenda do James Webb: " + renderer.schedule_status, HUD_DIM,
                           self.font_small))
        modo = renderer.backdrop_mode
        info = renderer.backdrop_info()
        if modo == "estrelas":
            origem = ("estrelas reais (Yale Bright Star Catalogue)" if scene.starfield.reais
                      else "estrelas")
            linhas.append(("Fundo: %s  [V]" % origem, HUD_DIM, self.font_small))
        elif info is not None:
            data = info["data"].strftime("%d/%m/%Y") if info.get("data") else "?"
            linhas.append(("Fundo: %s — %s (%s)  [V]" % (
                BACKDROP_NAMES[modo], _cortar(info["titulo"], 52), data), HUD_TXT, self.font_small))
            linhas.append(("Crédito: " + _cortar(info["credito"], 86), HUD_DIM, self.font_small))
        else:
            linhas.append(("Fundo %s: %s  [V]" % (
                BACKDROP_NAMES[modo], renderer.backdrop_status.get(modo, "sem imagem")),
                HUD_WARN, self.font_small))
        rotulos = [self.txt(fonte, texto, True, cor) for texto, cor, fonte in linhas]
        largura = max(r.get_width() for r in rotulos) + 24
        altura = 10 + sum(r.get_height() + 3 for r in rotulos)
        x = WIDTH - 18 - largura
        y = HEIGHT - self.FOOTER_HEIGHT - 14 - 10 - altura
        self._panel(surface, (x, y, largura, altura), alpha=190)
        y += 6
        for r in rotulos:
            surface.blit(r, (x + 12, y))
            y += r.get_height() + 3

    def _draw_footer(self, surface, scene):
        """Rodapé: comandos e indicador de progresso com as marcas das fases."""
        alt = self.FOOTER_HEIGHT
        topo = HEIGHT - alt - 14
        self._panel(surface, (18, topo, WIDTH - 36, alt))
        linhas = (
            "[ESPAÇO] iniciar/pausar  [R] reiniciar  [1-4] fases  [C W S A D] câmeras  "
            "[F] foco  [T] tour  [L] repetir  [O] inspeção",
            "[Z/X] zoom  [P] corpo celeste  [,/.] relógio  [+/-] velocidade  [B] órbitas  "
            "[N] rótulos  [V] fundo",
            "[H] dados  [F11] tela cheia  [F12] captura  [TAB] créditos  [ESC] sair",
        )
        for i, texto in enumerate(linhas):
            surface.blit(self.txt(self.font, texto, True, HUD_DIM), (32, topo + 6 + i * 17))

        x, y, larg, esp = 32, topo + 64, WIDTH - 276, 11
        pygame.draw.rect(surface, (26, 34, 46), (x, y, larg, esp), border_radius=3)
        pygame.draw.rect(surface, HUD_ACCENT,
                         (x, y, int(larg * scene.progress), esp), border_radius=3)
        for i, limite in enumerate(PHASE_BOUNDS[:-1]):
            mx = x + int(larg * limite / TOTAL_SEQUENCE_TIME)
            pygame.draw.line(surface, (132, 146, 166), (mx, y - 1), (mx, y + esp + 1), 1)
            surface.blit(self.txt(self.font, str(i + 2), True, HUD_DIM), (mx + 3, y - 1))
        surface.blit(self.txt(self.font,
            "Fase %d/%d  %05.2fs/%.0fs  %3d%%" % (
                scene.phase_index + 1, len(PHASE_BOUNDS), scene.sim_time,
                TOTAL_SEQUENCE_TIME, int(scene.progress * 100)),
            True, HUD_TXT), (x + larg + 14, y - 3))

    @staticmethod
    def _orbital_rows(scene):
        """Dados orbitais do instante, para o painel [H]: (texto, é título)."""
        terra = scene.bodies["Terra"]
        geo = vec_sub(scene.station_km, terra.pos_km)
        paineis = scene.station_arrays
        geracao = sum(p.incidence for p in paineis) / len(paineis) if paineis else 0.0
        linhas = [("SISTEMA SOLAR (escala real)", True),
                  ("Terra-Sol ......... %.4f UA" % (length(terra.pos_km) / ef.UA_KM), False),
                  ("Órbita-2 altitude . %.0f km" % (length(geo) - 6371.0), False),
                  ("Órbita-2 período .. %.1f min" % scene.station_orbit.periodo_min, False),
                  ("sombra da Terra ... %s" % ("ECLIPSE" if scene.station.shadow > 0.0
                                               else "sol pleno"), False),
                  ("painéis Órbita-2 .. %3.0f%% do Sol" % (geracao * 100.0), False)]
        for s in scene.satellites:
            if s.model == "iss":
                linhas.append(("ISS altitude ...... %.0f km" % (length(s.geo_km) - 6371.0), False))
            elif s.model == "jwst":
                linhas.append(("James Webb-Terra .. %.2f mi km" % (length(s.geo_km) / 1e6), False))
        pontos = sum(len(n) for n in scene.clouds) + sum(len(n) for n in scene.satellite_clouds)
        linhas.append(("corpos %d  naves %d  pontos %d" % (len(scene.bodies),
                                                         len(scene.satellites), pontos), False))
        if scene.satellite_data_date:
            linhas.append(("elementos CelesTrak  %s" % scene.satellite_data_date, False))
        return linhas

    def _draw_debug(self, surface, scene, renderer, desempenho=None):
        cam = scene.camera
        if desempenho is None:
            fps_txt = cpu_txt = "medindo..."
        else:
            fps, cpu_ms = desempenho
            fps_txt = "%.0f" % fps if fps > 0.0 else "-- (sem janela)"
            cpu_txt = "%.1f ms / %.1f" % (cpu_ms, 1000.0 / FPS)
        linhas = [
            ("PIPELINE", True),
            ("FPS medido ........ " + fps_txt, False),
            ("quadro (CPU) ...... " + cpu_txt, False),
            ("faces desenhadas .. %d" % renderer.faces_desenhadas, False),
            ("faces descartadas . %d" % renderer.faces_descartadas, False),
            ("marcadores ........ %d" % renderer.marcadores, False),
            ("pontos ............ %d" % renderer.pontos_desenhados, False),
            ("malhas na cena .... %d" % len(scene.meshes), False),
            ("partículas ........ %d" % len(scene.particles.particles), False),
            ("resolução / FOV ... %dx%d / %.0f" % (WIDTH, HEIGHT, FOV), False),
            ("", False),
        ] + self._orbital_rows(scene)
        alt = 18 + len(linhas) * 17
        self._panel(surface, (WIDTH - 316, 16, 298, alt))
        for i, (txt, titulo) in enumerate(linhas):
            cor = HUD_ACCENT if titulo else HUD_DIM
            surface.blit(self.txt(self.font, txt, True, cor), (WIDTH - 302, 26 + i * 17))

    def _draw_credits(self, surface, renderer=None):
        surface.blit(self._camada(WIDTH, HEIGHT, (5, 7, 12), 242), (0, 0))
        esquerda = max(40, WIDTH // 2 - 520)
        direita = esquerda + 510
        y = 40
        surface.blit(self.txt(self.font_title,
            "CRÉDITOS - AP1 Computação Gráfica e RA/RV", True, HUD_ACCENT), (esquerda, y))
        y += 32
        surface.blit(self.txt(self.font_bold,
            "Variação escolhida: Equipe 2 - Estação Espacial", True, HUD_TXT), (esquerda, y))
        y += 20
        surface.blit(self.txt(self.font,
            "Acoplamento de módulos, trajetória orbital de robôs, comporta com "
            "estados e alerta sequencial.", True, HUD_DIM), (esquerda, y))

        topo = y + 34

        def bloco(x, y, titulo, itens, cor):
            surface.blit(self.txt(self.font_bold, titulo, True, HUD_ACCENT), (x, y))
            y += 22
            for item in itens:
                surface.blit(self.txt(self.font, item, True, cor), (x + 12, y))
                y += 19
            return y + 14

        y = bloco(esquerda, topo, "Equipe e contribuições",
                  ["%-16s %-8s %s" % (nome, ra, papel) for nome, ra, papel in TEAM], HUD_TXT)
        y = bloco(esquerda, y, "Referências dos materiais utilizados",
                  ["- " + r for r in REFERENCES], HUD_TXT)
        bloco(esquerda, y, "Fontes dos dados reais", ["- " + r for r in DATA_SOURCES], HUD_DIM)
        y = bloco(direita, topo, "Conceitos de Computação Gráfica aplicados",
                  ["- " + c for c in CONCEPTS], HUD_DIM)
        info = renderer.backdrop_info() if renderer is not None else None
        if info is not None:
            bloco(direita, y, "Imagem de fundo atual",
                  [_cortar(info["titulo"], 58), _cortar("Crédito: " + info["credito"], 58),
                   _cortar(info["pagina"], 58)], HUD_TXT)

        surface.blit(self.txt(self.font_bold,
            "[TAB] volta para a cena", True, HUD_WARN), (esquerda, HEIGHT - 40))


# ============================================================
# 12. APLICAÇÃO
# ============================================================
CAMERA_KEYS = {
    pygame.K_c: "geral",
    pygame.K_w: "superior",
    pygame.K_s: "inferior",
    pygame.K_a: "esquerda",
    pygame.K_d: "direita",
}
PHASE_KEYS = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4}
SPEED_UP_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
SPEED_DOWN_KEYS = (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS)
TIME_UP_KEYS = (pygame.K_PERIOD, pygame.K_KP_PERIOD)
TIME_DOWN_KEYS = (pygame.K_COMMA,)


def load_backdrop(fonte, largura, altura):
    """
    Roda na thread de download: baixa a imagem mais recente e já a decodifica
    e reduz ao tamanho que cobre a maior tela disponível, para o laço principal
    só precisar de um blit.
    """
    info = fontes_online.imagem_mais_recente(fonte, largura)
    imagem = pygame.image.load(io.BytesIO(info.pop("bytes")), "fundo.jpg")
    w, h = imagem.get_size()
    k = max(largura / w, altura / h)
    if k < 1.0 and imagem.get_bitsize() in (24, 32):
        imagem = pygame.transform.smoothscale(imagem, (max(largura, int(w * k) + 1),
                                                       max(altura, int(h * k) + 1)))
    info["surface"] = imagem
    return info


class App:
    """Janela, laço principal, controle de FPS, eventos de teclado e downloads."""

    def __init__(self, surface=None, online=None, tela_cheia=False, inicio_utc=None):
        pygame.init()
        self.fullscreen = False
        if surface is None:
            self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT))
            pygame.display.set_caption(
                "AP1 - Computação Gráfica | Estação Órbita-2 no Sistema Solar")
        else:
            self.screen = surface
        self.clock = pygame.time.Clock()
        self.scene = Scene(inicio_utc)
        self.renderer = Renderer()
        self.hud = Hud()
        self.running = True
        # medição publicada no painel [H]: (FPS do relógio, ms de CPU por quadro)
        self.desempenho = None
        self._janela_s = 0.0
        self._soma_ms = 0.0
        self._quadros = 0
        self._fundo_escolhido = False
        self.tasks = fontes_online.Tarefas()
        self.online = (surface is None) if online is None else online
        if tela_cheia:
            self.toggle_fullscreen()
        if self.online:
            self.start_downloads()

    # -- dados online ---------------------------------------------------------
    def start_downloads(self):
        """Dispara os downloads em segundo plano; a cena já roda com os snapshots."""
        try:
            largura, altura = max(pygame.display.get_desktop_sizes())
        except (pygame.error, ValueError):
            largura, altura = WIDTH, HEIGHT
        for fonte in ("webb", "hubble"):
            self.renderer.backdrop_status[fonte] = "baixando a imagem mais recente..."
            self.tasks.iniciar("fundo-" + fonte, load_backdrop, fonte, largura, altura)
        self.renderer.schedule_status = "baixando..."
        self.tasks.iniciar("agenda", fontes_online.agenda_webb)
        self.tasks.iniciar("satelites", fontes_online.satelites_atualizados)
        self.tasks.iniciar("jwst", fontes_online.vetores_jwst)

    def poll_downloads(self):
        """Aplica, no laço principal, o que as threads terminaram."""
        for fonte in ("webb", "hubble"):
            situacao, valor = self.tasks.consumir("fundo-" + fonte)
            if situacao == "pronto":
                imagem = valor.pop("surface")
                if pygame.display.get_surface() is not None:
                    imagem = imagem.convert()
                self.renderer.set_backdrop(fonte, imagem, valor)
                self.renderer.backdrop_status.pop(fonte, None)
                if fonte == "webb" and not self._fundo_escolhido:
                    # a primeira imagem do Webb vira o fundo, como pedido
                    self.renderer.backdrop_mode = "webb"
                    self.hud.notify("Fundo: %s" % _cortar(valor["titulo"], 70))
            elif situacao == "falhou":
                self.renderer.backdrop_status[fonte] = "indisponível (sem rede?)"
        situacao, valor = self.tasks.consumir("agenda")
        if situacao == "pronto":
            self.renderer.schedule = valor
            self.renderer.schedule_status = ""
        elif situacao == "falhou":
            self.renderer.schedule_status = "indisponível (sem rede?)"
        situacao, valor = self.tasks.consumir("satelites")
        if situacao == "pronto":
            self.scene.update_satellite_elements(*valor)
        situacao, valor = self.tasks.consumir("jwst")
        if situacao == "pronto":
            self.scene.update_jwst(valor)

    # -- tela cheia -------------------------------------------------------------
    def toggle_fullscreen(self):
        """
        F11: tela cheia na resolução nativa do monitor. A projeção se ajusta ao
        novo tamanho no próximo quadro (configurar_viewport), sem ampliar pixels.
        """
        if pygame.display.get_surface() is None or self.screen is not pygame.display.get_surface():
            return self.fullscreen                   # superfície fora da tela (testes)
        if self.fullscreen:
            self.screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT))
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.fullscreen = not self.fullscreen
        self.hud.notify("%s %dx%d  [F11]" % ("Tela cheia" if self.fullscreen else "Janela",
                                              *self.screen.get_size()))
        return self.fullscreen

    def handle_event(self, event):
        """Comandos discretos de teclado; nenhuma navegação contínua."""
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in CAMERA_KEYS or event.key == pygame.K_f:
            self.scene.tour = False            # o comando manual de câmera vence o tour
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_F11:
            self.toggle_fullscreen()
        elif event.key == pygame.K_t:
            self.scene.toggle_tour()
        elif event.key == pygame.K_SPACE:
            self.scene.toggle()
        elif event.key == pygame.K_r:
            self.scene.reset()
        elif event.key == pygame.K_f:
            self.scene.camera.follow(self.scene.cargo)
        elif event.key == pygame.K_h:
            self.hud.show_debug = not self.hud.show_debug
        elif event.key == pygame.K_n:
            self.hud.show_labels = not self.hud.show_labels
        elif event.key == pygame.K_F12:
            self.save_screenshot()
        elif event.key == pygame.K_l:
            self.scene.toggle_loop()
        elif event.key == pygame.K_z:
            self.scene.change_zoom(-1)
        elif event.key == pygame.K_x:
            self.scene.change_zoom(1)
        elif event.key == pygame.K_p:
            passo = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
            nome = self.scene.cycle_focus(passo)
            if nome:
                self.hud.notify("Foco: %s  [P / Shift+P]  [Z/X] volta ao zoom" % nome)
        elif event.key in TIME_UP_KEYS:
            self.scene.change_time_scale(1)
            self.hud.notify("Relógio orbital: %s" % self.scene.time_scale_label)
        elif event.key in TIME_DOWN_KEYS:
            self.scene.change_time_scale(-1)
            self.hud.notify("Relógio orbital: %s" % self.scene.time_scale_label)
        elif event.key == pygame.K_v:
            self._fundo_escolhido = True
            modo = self.renderer.cycle_backdrop()
            self.hud.notify("Fundo: %s" % BACKDROP_NAMES[modo])
        elif event.key == pygame.K_b:
            self.renderer.show_orbits = not self.renderer.show_orbits
        elif event.key == pygame.K_o:
            self.scene.toggle_extended_orbit()
        elif event.key in SPEED_UP_KEYS:
            self.scene.change_speed(1)
        elif event.key in SPEED_DOWN_KEYS:
            self.scene.change_speed(-1)
        elif event.key == pygame.K_TAB:
            self.hud.show_credits = not self.hud.show_credits
        elif event.key in CAMERA_KEYS:
            self.scene.camera.go_to(CAMERA_KEYS[event.key])
        elif event.key in PHASE_KEYS:
            self.scene.goto_phase(PHASE_KEYS[event.key])

    def step(self, dt):
        t0 = time.perf_counter()
        self.poll_downloads()
        self.scene.update(dt)
        self.renderer.draw(self.screen, self.scene)
        self.hud.draw(self.screen, self.scene, self.renderer, self.desempenho)
        self._medir((time.perf_counter() - t0) * 1000.0, dt)

    def _medir(self, trabalho_ms, dt):
        """
        Média do custo de CPU por quadro, publicada a cada meio segundo: um
        número novo por quadro criaria uma superfície de texto nova por quadro
        no cache do HUD, e ainda ficaria ilegível de tanto piscar.
        """
        self._soma_ms += trabalho_ms
        self._quadros += 1
        self._janela_s += dt
        if self._janela_s >= 0.5:
            self.desempenho = (self.clock.get_fps(), self._soma_ms / self._quadros)
            self._janela_s = self._soma_ms = 0.0
            self._quadros = 0

    def save_screenshot(self, pasta=None):
        """
        Tecla F12: grava a tela atual, com o HUD, em docs/img. Duas capturas no
        mesmo segundo ganham sufixo em vez de se sobrescreverem. Devolve o caminho.
        """
        if pasta is None:
            pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 os.pardir, "docs", "img")
        pasta = os.path.normpath(pasta)
        os.makedirs(pasta, exist_ok=True)
        base = time.strftime("captura-%Y%m%d-%H%M%S")
        caminho = os.path.join(pasta, base + ".png")
        n = 2
        while os.path.exists(caminho):
            caminho = os.path.join(pasta, "%s-%d.png" % (base, n))
            n += 1
        pygame.image.save(self.screen, caminho)
        self.hud.notify("Captura salva: %s" % os.path.basename(caminho))
        return caminho

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)          # protege a simulação de engasgos
            for event in pygame.event.get():
                self.handle_event(event)
            self.step(dt)
            pygame.display.flip()
        pygame.quit()


def enable_native_dpi():
    """
    No Windows com escala de tela (125%, 150%), um processo que não declara
    DPI enxerga uma resolução menor e o sistema amplia a janela: a tela cheia
    sairia borrada e a imagem do telescópio perderia a nitidez. Declarar o
    processo ciente de DPI faz o Pygame trabalhar com os pixels reais.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
        return True
    except (AttributeError, OSError):
        return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    enable_native_dpi()
    App(tela_cheia="--tela-cheia" in argv or "-f" in argv,
        online="--offline" not in argv).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
