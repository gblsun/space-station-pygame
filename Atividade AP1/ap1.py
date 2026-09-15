"""
AP1 - Computação Gráfica e RA/RV
Mundo Virtual Animado: Estação Orbital Órbita-2 (Equipe 2 - Estação Espacial)

Renderizador 3D escrito do zero sobre Pygame, sem OpenGL, sem numpy e sem
bibliotecas de modelagem. Todo o pipeline é calculado neste arquivo:
transformações de modelo, câmera look-at, recorte no plano próximo, projeção
em perspectiva, back-face culling, ordenação por profundidade (algoritmo do
pintor) e sombreamento Lambertiano plano.

Execução:  python "Atividade AP1/ap1.py"
Testes:    python -m unittest discover -s "Atividade AP1" -p "test_*.py"

Importar este módulo NÃO abre janela nem inicializa o Pygame: a inicialização
acontece apenas dentro de main().
"""

import math
import os
import random
import sys
import time

import pygame

# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================
WIDTH, HEIGHT = 1080, 720
FPS = 60
FOV = 620.0          # distância focal, em pixels
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

PHASE_NAMES = (
    "Fase 1: Aproximação do Cargueiro",
    "Fase 2: Abertura da Comporta de Doca",
    "Fase 3: Acoplamento do Módulo",
    "Fase 4: Órbita de Inspeção dos Robôs",
)

# Origem da estação no mundo
STATION_ORIGIN = (0.0, 0.0, 560.0)   # posição de referência; a cena a substitui pela órbita


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


LIGHT_DIR = normalize((0.44, 0.70, -0.56))   # sol: luz principal, fixa no mundo
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
# 3. SISTEMA ORBITAL
# ============================================================
# As distâncias e os raios são comprimidos: em escala real a Terra teria menos
# de um pixel ao lado do Sol, e a estação seria invisível. Os valores abaixo
# preservam a *ordem* das grandezas (a Lua orbita mais longe que a estação, o
# Sol está muito além da Lua) e mantêm tudo enquadrável pelos níveis de zoom.
# O HUD deixa explícito que a escala não é real.

SUN_POS = (0.0, 0.0, 0.0)              # o Sol é a origem do mundo
SUN_RADIUS = 2600.0

EARTH_RADIUS = 520.0
EARTH_ORBIT = 26000.0
EARTH_YEAR = 300.0                     # segundos para uma volta completa
EARTH_DAY = 24.0                       # segundos para um giro sobre o eixo
EARTH_TILT = 23.4                      # inclinação do eixo, em graus

MOON_RADIUS = 150.0
MOON_ORBIT = 4200.0
MOON_MONTH = 72.0
MOON_INCLINATION = 18.0

STATION_ORBIT = 1400.0
STATION_PERIOD = 96.0
STATION_INCLINATION = 34.0
STATION_ATTITUDE = 26.0                # inclinação inercial do casco

STARFIELD_DISTANCE = 1.0e5             # casca de estrelas, praticamente no infinito


def orbit_point(centro, raio, angulo, inclinacao):
    """
    Ponto de uma órbita circular em torno de `centro`. A órbita nasce no plano
    XZ e é inclinada em torno do eixo X, o que dá aos planos orbitais ângulos
    distintos sem precisar de uma base completa por corpo.
    """
    local = (raio * math.cos(angulo), 0.0, raio * math.sin(angulo))
    return vec_add(centro, rotate_xyz(local, (inclinacao, 0.0, 0.0)))


def earth_position(t):
    return orbit_point(SUN_POS, EARTH_ORBIT, 2.0 * math.pi * t / EARTH_YEAR, 0.0)


def moon_position(t):
    return orbit_point(earth_position(t), MOON_ORBIT,
                       2.0 * math.pi * t / MOON_MONTH, MOON_INCLINATION)


def station_position(t):
    return orbit_point(earth_position(t), STATION_ORBIT,
                       2.0 * math.pi * t / STATION_PERIOD, STATION_INCLINATION)


def orbit_ring(centro, raio, inclinacao, passos=96):
    """Pontos de uma órbita fechada, para desenhar o traçado."""
    return [orbit_point(centro, raio, 2.0 * math.pi * k / passos, inclinacao)
            for k in range(passos)]


def in_earth_shadow(ponto, t):
    """
    Teste de eclipse: o ponto está no cone de sombra da Terra? A sombra é o
    cilindro de raio terrestre que parte da Terra na direção oposta ao Sol —
    uma aproximação de sombra cilíndrica, suficiente para a escala da cena.
    Reaproveita a mesma álgebra do teste de linha de visão.
    """
    terra = earth_position(t)
    para_o_sol = normalize(vec_sub(SUN_POS, terra))
    rel = vec_sub(ponto, terra)
    atras = -dot_product(rel, para_o_sol)          # distância no lado escuro
    if atras <= 0.0:
        return False, 0.0
    eixo = vec_scale(para_o_sol, -atras)
    desvio = length(vec_sub(rel, eixo))
    if desvio >= EARTH_RADIUS:
        return False, 0.0
    # penumbra suave junto à borda do cone
    return True, clamp(1.0 - desvio / EARTH_RADIUS, 0.0, 1.0)


# ============================================================
# 4. CÂMERA (look-at)
# ============================================================
# Os presets são deslocamentos em relação ao ponto ancorado, não posições
# absolutas: a estação orbita a Terra, então a câmera precisa acompanhá-la.
CAMERA_PRESETS = {
    "geral":    {"name": "Plano Geral [C]",     "eye": (20.0, 60.0, -700.0),   "target": (20.0, 0.0, 0.0)},
    "superior": {"name": "Visão Superior [W]",  "eye": (30.0, 540.0, -300.0),  "target": (20.0, 0.0, 0.0)},
    "inferior": {"name": "Visão Inferior [S]",  "eye": (10.0, -430.0, -330.0), "target": (20.0, 10.0, 0.0)},
    "esquerda": {"name": "Flanco Esquerdo [A]", "eye": (-560.0, 170.0, -420.0), "target": (30.0, 0.0, 30.0)},
    "direita":  {"name": "Flanco Direito [D]",  "eye": (600.0, 180.0, -360.0),  "target": (20.0, 0.0, 30.0)},
}
DEFAULT_CAMERA = "geral"
FOLLOW_CAMERA = "foco"
FOLLOW_NAME = "Foco Animado no Cargueiro [F]"
FOLLOW_OFFSET = (250.0, 130.0, -430.0)  # deslocamento do olho em relação ao alvo
# Tour de câmera (tecla T): um enquadramento por fase da sequência
TOUR_CAMERAS = ("direita", FOLLOW_CAMERA, "geral", "superior")

# Níveis de zoom: cada um escolhe o que fica no centro do quadro e quanto a
# câmera se afasta. É assim que a mesma cena mostra tanto a comporta de doca
# quanto a órbita da Terra em torno do Sol.
ZOOM_LEVELS = (
    {"name": "Doca",          "anchor": "station", "scale": 0.30},
    {"name": "Estação",       "anchor": "station", "scale": 1.00},
    {"name": "Órbita baixa",  "anchor": "station", "scale": 4.50},
    {"name": "Terra e Lua",   "anchor": "earth",   "scale": 15.0},
    {"name": "Sistema",       "anchor": "sun",     "scale": 100.0},
)
DEFAULT_ZOOM = 1


class Camera:
    """
    Câmera look-at ancorada num ponto móvel. Mantém olho e alvo, ambos
    interpolados, e reconstrói a base ortonormal a cada quadro. O preset define
    o deslocamento em relação à âncora; o nível de zoom multiplica esse
    deslocamento e escolhe quem é a âncora.
    """

    def __init__(self, preset=DEFAULT_CAMERA, anchor=None):
        p = CAMERA_PRESETS[preset]
        self.key = preset
        self.name = p["name"]
        self.eye_offset = p["eye"]
        self.target_offset = p["target"]
        self.anchor = list(anchor if anchor is not None else STATION_ORIGIN)
        self.anchor_source = None
        self.zoom = 1.0
        self.follow_mesh = None
        # tremor somado por cima da pose (efeito de acoplamento); fica fora da
        # interpolação, então não acumula deriva
        self.shake = (0.0, 0.0, 0.0)
        self._assentar()
        self._rebuild_basis()

    def _goal(self, offset):
        return (self.anchor[0] + offset[0] * self.zoom,
                self.anchor[1] + offset[1] * self.zoom,
                self.anchor[2] + offset[2] * self.zoom)

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
        self.eye = list(self._goal(self.eye_offset))
        self.target = list(self._goal(self.target_offset))
        self.eye_goal = list(self.eye)
        self.target_goal = list(self.target)

    def go_to(self, preset):
        """Agenda a transição suave para um preset."""
        p = CAMERA_PRESETS[preset]
        self.key = preset
        self.name = p["name"]
        self.eye_offset = p["eye"]
        self.target_offset = p["target"]
        self.follow_mesh = None

    def follow(self, mesh):
        """Entra no modo de foco animado: a âncora passa a ser um objeto móvel."""
        self.key = FOLLOW_CAMERA
        self.name = FOLLOW_NAME
        self.eye_offset = FOLLOW_OFFSET
        self.target_offset = (0.0, 0.0, 0.0)
        self.follow_mesh = mesh

    def set_anchor(self, pos, zoom=None, fonte=None):
        """
        Ponto que a câmera acompanha, atualizado pela cena a cada quadro.
        `fonte` diz quem é a âncora ("station", "earth", "sun"); quando ela
        troca, `update` recalcula o deslocamento para não saltar.
        """
        self.anchor = list(pos)
        if zoom is not None:
            self.zoom = zoom
        if fonte is not None:
            self.anchor_source = fonte

    def snap_to(self, preset):
        """Salta instantaneamente para um preset (usado no reset)."""
        self.go_to(preset)
        self._assentar()
        self._rebuild_basis()

    def update(self, dt):
        """
        Interpola o deslocamento em relação à âncora, e não a posição absoluta.
        A estação orbita a Terra, que orbita o Sol a ~545 unidades/s: com o lerp
        em coordenadas de mundo a câmera ficava ~115 unidades para trás e o foco
        animado nunca centralizava o cargueiro.
        """
        if self.follow_mesh is not None:
            self.anchor = list(self.follow_mesh.pos)
        ax, ay, az = self.anchor
        fonte = self._fonte()
        if fonte != self._fonte_vista:
            # a âncora trocou de dono: o deslocamento parte da pose atual, então a
            # troca continua sendo uma transição suave, e não um corte
            sx, sy, sz = self._shake_aplicado
            self._eye_rel = [self.eye[0] - sx - ax, self.eye[1] - sy - ay,
                             self.eye[2] - sz - az]
            self._target_rel = [self.target[0] - sx - ax, self.target[1] - sy - ay,
                                self.target[2] - sz - az]
            self._fonte_vista = fonte
        self.eye_goal = list(self._goal(self.eye_offset))
        self.target_goal = list(self._goal(self.target_offset))
        k = min(1.0, 5.0 * dt)
        z = self.zoom
        for i in range(3):
            self._eye_rel[i] = lerp(self._eye_rel[i], self.eye_offset[i] * z, k)
            self._target_rel[i] = lerp(self._target_rel[i], self.target_offset[i] * z, k)
            self.eye[i] = self.anchor[i] + self._eye_rel[i] + self.shake[i]
            self.target[i] = self.anchor[i] + self._target_rel[i] + self.shake[i]
        self._shake_aplicado = tuple(self.shake)
        self._rebuild_basis()

    def _rebuild_basis(self):
        """Base ortonormal (right, up, forward) do espaço de câmera."""
        fwd = normalize(vec_sub(self.target, self.eye))
        if length(fwd) < 0.5:                       # alvo coincide com o olho
            fwd = (0.0, 0.0, 1.0)
        up_ref = WORLD_UP
        if abs(dot_product(fwd, up_ref)) > 0.999:   # olhando reto para cima/baixo
            up_ref = (0.0, 0.0, 1.0)
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
        self.fill_view = (dot_product(FILL_DIR, right),
                          dot_product(FILL_DIR, up),
                          dot_product(FILL_DIR, fwd))
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
    Malha de polígonos com transformação própria (escala -> rotação XYZ ->
    translação). Guarda uma cor por face, o que permite detalhar um objeto
    composto sem multiplicar o número de malhas.

    Duas otimizações sustentam a densidade de malha da cena:
    o resultado da transformação de modelo é reaproveitado enquanto a pose não
    muda, e `collect` leva cada vértice para o espaço de câmera uma única vez,
    em vez de uma vez por face que o utiliza.
    """

    def __init__(self, vertices, faces, face_colors, position=(0, 0, 0),
                 rotation=(0, 0, 0), scale=1.0, name="", gloss=0.30):
        self.base_vertices = list(vertices)
        self.faces = list(faces)
        self.face_colors = list(face_colors)
        self.pos = list(position)
        self.rotation = list(rotation)
        self.scale = scale
        self.name = name
        self.gloss = gloss          # 0 para superfícies foscas (rocha, painel)
        self.shadow = 0.0           # 0 em pleno sol, 1 no centro do eclipse
        self.visible = True
        # raio da esfera envolvente em espaço local (multiplicado pela escala
        # no acesso), usado pelo teste de linha de visão
        self.local_radius = max((length(v) for v in self.base_vertices), default=0.0)
        self._pose_cache = None
        self._world_cache = None

    @property
    def bounding_radius(self):
        return self.local_radius * self.scale

    def update(self, pos=None, rot=None, scale=None):
        if pos is not None:
            self.pos = list(pos)
        if rot is not None:
            self.rotation = list(rot)
        if scale is not None:
            self.scale = scale

    def pose(self):
        """Assinatura da transformação atual; controla o cache de vértices."""
        return (self.pos[0], self.pos[1], self.pos[2],
                self.rotation[0], self.rotation[1], self.rotation[2], self.scale)

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
                k = FOV / (vz if vz > NEAR else NEAR)
                pontos.append((int(vx * k + VIEW_CENTER_X),
                               int(-vy * k + VIEW_CENTER_Y)))
            if testar_tela:
                xs = [p[0] for p in pontos]
                ys = [p[1] for p in pontos]
                x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
                if x1 < 0 or y1 < 0 or x0 >= WIDTH or y0 >= HEIGHT:
                    descartadas += 1          # nenhum pixel da face cai na janela
                    continue
                if (x0 < -SCREEN_GUARD or y0 < -SCREEN_GUARD
                        or x1 > WIDTH + SCREEN_GUARD or y1 > HEIGHT + SCREEN_GUARD):
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
                 pole_color=None, lumps=None):
    """
    Esfera com polos únicos (a versão anterior repetia vértices no polo e
    gerava faces degeneradas). `lumps` é uma lista de harmônicos que deforma
    o raio de acordo com a direção, produzindo detritos irregulares.
    """
    pole_color = pole_color or color
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


C_OCEANO = (28, 74, 148)
C_OCEANO_RASO = (46, 108, 184)
C_TERRA = (74, 126, 66)
C_TERRA_SECA = (146, 130, 82)
C_GELO = (238, 244, 250)


def build_earth(radius, rings=16, sectors=28, seed=77):
    """
    Terra: uma esfera cuja cor por face vem de um ruído de direção, separando
    oceano, continente e calotas. Não é textura — é a mesma malha colorida
    face a face, dentro do que o enunciado permite.
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


def build_station_core():
    """
    Objeto COMPOSTO (requisito 3). Reúne estruturas de tipos diferentes: casco
    cilíndrico, colares de reforço, anel de doca, mastros, treliça da antena,
    painéis solares em grade, radiadores térmicos, escotilhas, propulsores de
    atitude e a antena parabólica.
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

    # mastros e painéis solares, abertos ao longo de Z
    for sinal in (1.0, -1.0):
        b.add_bar((-20.0, 0.0, 38.0 * sinal), (-20.0, 0.0, 126.0 * sinal),
                  14.0, C_CASCO_ESC)
        b.add_solar_panel((-20.0, 0.0, 188.0 * sinal), 152.0, 116.0, 6, 4,
                          C_PAINEL, C_PAINEL_ALT, C_PAINEL_BORDA)
        b.add_bar((-20.0, 0.0, 126.0 * sinal), (-20.0, 0.0, 250.0 * sinal),
                  7.0, C_PAINEL_BORDA)

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


def build_lab_module():
    """
    Módulo-laboratório acoplado ao núcleo: o "acoplamento de módulos" do tema
    da Equipe 2. É construído ao longo do eixo X, o mesmo do núcleo, para que
    herde a inclinação do pai sem precisar compor rotações fora de ordem.
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


def build_satellite():
    """Satélite de comunicação em órbita alta: objeto de fundo, malha simples."""
    b = MeshBuilder()
    b.add_box((-16.0, -16.0, -22.0), (16.0, 16.0, 22.0), C_CASCO, C_CASCO_ESC)
    for sinal in (1.0, -1.0):
        b.add_bar((16.0 * sinal, 0.0, 0.0), (34.0 * sinal, 0.0, 0.0), 5.0, C_CASCO_ESC)
        b.add_box((34.0 * sinal - (0.0 if sinal > 0 else 46.0), -2.0, -26.0),
                  (34.0 * sinal + (46.0 if sinal > 0 else 0.0), 2.0, 26.0),
                  C_PAINEL, C_PAINEL_BORDA)
    b.add_bar((0.0, 16.0, 0.0), (0.0, 34.0, 8.0), 4.0, C_CASCO_ESC)
    b.add_dish((0.0, 38.0, 10.0), "y", 18.0, -8.0, 9, C_PRATO, C_CASCO_ESC)
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
        i = len(b.verts)
        b.verts.extend([(52.0, 26.0 * c, 26.0 * s),
                        (18.0, 26.0 * c, 26.0 * s),
                        (58.0, 38.0 * c, 38.0 * s)])
        b.faces.append((i, i + 1, i + 2))
        b.colors.append(C_CARGA_DET)
        b.faces.append((i + 2, i + 1, i))
        b.colors.append(C_CARGA_DET)
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
    o que contaminava as partículas e o campo estelar.
    """
    rng = random.Random(seed)
    lumps = [(rng.uniform(1.2, 3.4), rng.uniform(1.2, 3.4), rng.uniform(1.2, 3.4),
              rng.uniform(0.07, 0.17), rng.uniform(0.0, 6.28)) for _ in range(4)]
    tom = rng.randint(-24, 24)
    cor = tuple(clamp(c + tom, 0, 255) for c in C_DETRITO)
    return build_sphere(radius, rings=rings, sectors=sectors, color=cor,
                        pole_color=tuple(clamp(c - 18, 0, 255) for c in cor),
                        lumps=lumps)


# ============================================================
# 8. SISTEMAS DE APOIO
# ============================================================
class ExhaustParticles:
    """Partículas dos retrofoguetes: vida decrescente e cor esfriando."""

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
    Campo estelar fixo numa casca distante. Estrelas ancoradas no mundo
    funcionam corretamente com a câmera look-at; a versão anterior deslocava
    as estrelas em -Z, o que só fazia sentido na vista frontal.
    """

    def __init__(self, count=420, seed=7):
        rng = random.Random(seed)
        self.stars = []
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
            })

    def brightness(self, star, t):
        pulso = 0.82 + 0.18 * math.sin(t * star["vel"] + star["fase"])
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


# ============================================================
# 9. CENA E SEQUÊNCIA DE ANIMAÇÃO
# ============================================================
STATE_PARADO = "PARADO"
STATE_EXECUTANDO = "EXECUTANDO"
STATE_PAUSADO = "PAUSADO"
STATE_CONCLUIDO = "CONCLUIDO"

CARGO_X = (470.0, 300.0, 222.0, 178.0)

# Cinturão de detritos em órbita da Terra:
# (semente, raio da rocha, raio orbital, fase, inclinação, velocidade, malha cheia)
DEBRIS_BELT = (
    (101, 46.0, 1750.0, 0.4, 22.0, 0.055, True),
    (202, 30.0, 1980.0, 2.1, -16.0, 0.048, True),
    (303, 58.0, 2240.0, 4.0, 40.0, 0.041, True),
    (404, 62.0, 2600.0, 1.2, -34.0, 0.034, False),
    (505, 44.0, 2950.0, 3.4, 12.0, 0.030, False),
    (606, 80.0, 3300.0, 5.6, 54.0, 0.026, False),
    (707, 38.0, 3650.0, 0.9, -48.0, 0.023, False),
    (808, 54.0, 3980.0, 2.7, 28.0, 0.021, False),
    (909, 68.0, 4500.0, 4.8, -8.0, 0.018, False),
)

# Satélites: (escala, raio orbital, fase, inclinação, velocidade)
SATELLITES = (
    (1.4, 1650.0, 1.0, -52.0, 0.072),
    (1.0, 2300.0, 3.9, 68.0, 0.051),
    (1.8, 3100.0, 5.2, -24.0, 0.038),
)       # trajetória do cargueiro por fase
SENSOR_LOCAL = (-77.0, 208.0, 0.0)           # topo do mastro da antena
ROBOT_DOCK_LOCAL = ((-58.0, 56.0, 12.0), (-8.0, -58.0, 20.0),
                    (34.0, 54.0, -30.0), (-104.0, -50.0, -18.0))
MAST_X, MAST_Z = -77.0, 0.0                  # eixo do mastro, em coords locais
MAST_SAFE_RADIUS = 56.0


class MaintenanceRobot:
    """
    Robô de manutenção com braço de dois segmentos. Demonstra a cadeia
    hierárquica corpo -> braço -> antebraço: cada junta é posicionada pela
    transformação do elo anterior, e a estação é o avô de toda a cadeia.
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

    def place(self, pos, giro, incl, ombro, cotovelo):
        """
        Posiciona a cadeia inteira. A orientação do corpo não usa o canal X, de
        modo que somar o ângulo da junta nesse canal equivale a girar o elo no
        próprio eixo antes de aplicar a orientação do pai — a composição fica
        exata sem precisar de matrizes.
        """
        base = (0.0, giro, incl)
        self.body.update(pos=pos, rot=base)
        s = self.scale
        junta = vec_add(pos, rotate_xyz(vec_scale(self.SHOULDER_LOCAL, s), base))
        rot_sup = (ombro, giro, incl)
        self.upper.update(pos=junta, rot=rot_sup)
        cotov = vec_add(junta, rotate_xyz((0.0, 0.0, self.UPPER_LEN * s), rot_sup))
        self.fore.update(pos=cotov, rot=(ombro + cotovelo, giro, incl))


class Scene:
    """
    Todo o estado da simulação. Não importa nada de pygame: é esta classe que
    a suíte de testes exercita. A pose de cada objeto é função pura do tempo
    de simulação, então pausar, reiniciar e saltar de fase são consistentes.
    """

    def __init__(self):
        self.station = PolyMesh(*build_station_core(), position=STATION_ORIGIN,
                                name="Núcleo Órbita-2")
        self.lab = PolyMesh(*build_lab_module(), name="Módulo Laboratório")
        self.door_hi = PolyMesh(*build_door_leaf(False), name="Comporta superior")
        self.door_lo = PolyMesh(*build_door_leaf(True), name="Comporta inferior")
        self.cargo = PolyMesh(*build_cargo_ship(), name="Cargueiro Vega-7")

        # corpos celestes
        self.sun = PolyMesh(*build_sphere(SUN_RADIUS, rings=14, sectors=24,
                                          color=(255, 238, 190), pole_color=(255, 226, 150)),
                            position=SUN_POS, name="Sol", gloss=0.0)
        self.earth = PolyMesh(*build_earth(EARTH_RADIUS), name="Terra", gloss=0.06)
        self.moon = PolyMesh(*build_debris(4242, MOON_RADIUS, rings=12, sectors=20),
                             name="Lua", gloss=0.0)

        # quatro instâncias do mesmo tipo, com parâmetros diferentes (requisito 3)
        especificacao = (
            ((232, 128, 46), 0.95, (186.0, 62.0, 1.00, 0.00, 18.0)),
            ((86, 196, 224), 0.66, (238.0, -44.0, 1.38, 1.57, -26.0)),
            ((198, 108, 206), 1.25, (150.0, -132.0, 0.74, 3.14, 34.0)),
            ((236, 220, 96), 0.84, (272.0, 18.0, 1.12, 4.71, -12.0)),
        )
        self.robots = [MaintenanceRobot(i + 1, cor, escala, params)
                       for i, (cor, escala, params) in enumerate(especificacao)]

        # cinturão de detritos em órbita da Terra: os de dentro em malha cheia,
        # os de fora em LOD grosso
        self.debris = []
        self.debris_orbits = []
        for i, (seed, raio, orbita, fase, incl, veloc, fino) in enumerate(DEBRIS_BELT):
            if fino:
                dados = build_debris(seed, raio)
            else:
                dados = build_debris(seed, raio, rings=5, sectors=8)
            self.debris.append(PolyMesh(*dados, name="Detrito %s" % chr(65 + i), gloss=0.0))
            self.debris_orbits.append((orbita, fase, incl, veloc))

        # satélites em órbitas próprias
        self.satellites = []
        self.satellite_orbits = []
        for i, (escala, orbita, fase, incl, veloc) in enumerate(SATELLITES):
            self.satellites.append(PolyMesh(*build_satellite(), scale=escala,
                                            name="Satélite %s-%d" % ("Farol", i + 1)))
            self.satellite_orbits.append((orbita, fase, incl, veloc))

        self.meshes = ([self.sun, self.earth, self.moon] + self.debris + self.satellites
                       + [self.station, self.lab, self.door_hi, self.door_lo]
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
        self.cycles = 0
        self.anim_time = 0.0           # relógio contínuo do ambiente
        self.zoom_index = DEFAULT_ZOOM
        self.station_pos = station_position(0.0)
        self.reset()

    # -- sistema orbital ---------------------------------------------------
    def anchor_position(self, nome):
        """Ponto que a câmera acompanha em cada nível de zoom."""
        if nome == "earth":
            return earth_position(self.anim_time)
        if nome == "sun":
            return SUN_POS
        return self.station_pos

    @property
    def zoom_level(self):
        return ZOOM_LEVELS[self.zoom_index]

    def change_zoom(self, passo):
        """Teclas Z e X: aproxima ou afasta, trocando também o que fica centrado."""
        self.zoom_index = int(clamp(self.zoom_index + passo, 0, len(ZOOM_LEVELS) - 1))
        return self.zoom_level

    _aneis_locais = None

    def orbit_rings(self):
        """
        Traçados das órbitas, para o renderizador desenhar. A forma de cada anel
        não muda: ela é calculada uma única vez em torno da origem e, a cada
        quadro, apenas transladada até a Terra.
        """
        aneis = Scene._aneis_locais
        if aneis is None:
            origem = (0.0, 0.0, 0.0)
            aneis = Scene._aneis_locais = (
                orbit_ring(SUN_POS, EARTH_ORBIT, 0.0, 128),
                orbit_ring(origem, MOON_ORBIT, MOON_INCLINATION, 96),
                orbit_ring(origem, STATION_ORBIT, STATION_INCLINATION, 80),
            )
        tx, ty, tz = earth_position(self.anim_time)
        return (
            ("Terra", aneis[0], (120, 150, 210)),
            ("Lua", [(tx + x, ty + y, tz + z) for x, y, z in aneis[1]], (168, 172, 186)),
            ("Órbita-2", [(tx + x, ty + y, tz + z) for x, y, z in aneis[2]],
             (86, 226, 198)),
        )

    def label_targets(self):
        """
        Rótulos da tecla N: nome e papel de cada objeto no requisito 3 —
        instâncias de um mesmo tipo, objetos sem partes e objetos compostos.
        """
        rotulos = [("%s · instância" % r.name.replace("Robô ", ""), r.pos) for r in self.robots]
        rotulos += [("%s · composto" % m.name, m.pos) for m in (self.station, self.lab, self.cargo)]
        rotulos += [("%s · sem partes" % m.name, m.pos) for m in (self.earth, self.moon)]
        return rotulos

    def shadow_factor(self, ponto):
        """Quanto o ponto está eclipsado pela Terra, de 0 (pleno sol) a 1."""
        dentro, intensidade = in_earth_shadow(ponto, self.anim_time)
        return intensidade if dentro else 0.0

    # -- transformação hierárquica pai -> filho ---------------------------
    def station_roll(self, t=None):
        """
        Atitude da estação. É fixa: mantendo a orientação inercial, o anel de
        doca continua alinhado com a rota de aproximação do cargueiro durante
        toda a órbita. O movimento visual vem da órbita, não de um giro próprio.
        """
        return STATION_ATTITUDE

    def to_world(self, local, t=None):
        """
        Converte um ponto do referencial da estação para o mundo. A estação
        orbita a Terra, então a origem desse referencial se desloca a cada
        quadro e tudo que é filho dela acompanha.
        """
        return vec_add(self.station_pos,
                       rotate_xyz(local, (STATION_ATTITUDE, 0.0, 0.0)))

    # -- controle ---------------------------------------------------------
    def reset(self):
        self.state = STATE_PARADO
        self.sim_time = 0.0
        self.anim_time = 0.0
        self.cycles = 0
        self.particles.clear()
        self.station_pos = station_position(0.0)
        nivel = self.zoom_level
        self.camera.set_anchor(self.anchor_position(nivel["anchor"]), nivel["scale"],
                               fonte=nivel["anchor"])
        self.camera.snap_to(DEFAULT_CAMERA)
        self.apply_animation(0.0)
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
        if self.state == STATE_EXECUTANDO:
            passo = dt * self.speed
            self.anim_time += passo
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
            self.anim_time += dt          # o ambiente respira mesmo em pausa
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
        nivel = self.zoom_level
        self.camera.set_anchor(self.anchor_position(nivel["anchor"]), nivel["scale"],
                               fonte=nivel["anchor"])
        if antes < DOCKING_LATCH_TIME <= self.sim_time:
            self._emit_docking_sparks()
        pulso = docking_pulse(self.sim_time) if self.state == STATE_EXECUTANDO else 0.0
        if pulso > 0.0:
            # tremor curto da trava, somado por cima da pose da câmera
            a = 7.0 * nivel["scale"] * pulso
            tau = self.anim_time
            self.camera.shake = (a * math.sin(tau * 47.0), a * math.sin(tau * 61.0),
                                 a * math.sin(tau * 53.0))
        else:
            self.camera.shake = (0.0, 0.0, 0.0)
        self.camera.update(dt)
        self.sight = self.line_of_sight()

    def _emit_docking_sparks(self):
        """Faíscas da trava: quatro jatos radiais saindo do anel de doca."""
        anel = self.to_world((92.0, 0.0, 0.0))
        for direcao in ((0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)):
            self.particles.emit(anel, rotate_xyz(direcao, (STATION_ATTITUDE, 0.0, 0.0)),
                                count=6, speed=120.0)

    def apply_animation(self, t, emitir=False):
        # o ambiente segue o relógio contínuo; a sequência segue o tempo da fase
        ambiente = self.anim_time
        self.station_pos = station_position(ambiente)
        roll = STATION_ATTITUDE

        terra = earth_position(ambiente)
        self.earth.update(pos=terra, rot=(EARTH_TILT, ambiente * 360.0 / EARTH_DAY, 0.0))
        self.moon.update(pos=moon_position(ambiente),
                         rot=(0.0, ambiente * 360.0 / MOON_MONTH, 0.0))
        self.sun.update(pos=SUN_POS, rot=(0.0, ambiente * 1.5, 0.0))

        self.station.update(pos=self.station_pos, rot=(roll, 0.0, 0.0))
        self.lab.update(pos=self.to_world((-184.0, 0.0, 0.0)), rot=(roll, 0.0, 0.0))

        self._animate_door(t, roll)
        self._animate_cargo(t, emitir)
        self._animate_robots(t)
        self._animate_belt(ambiente, terra)
        self.beacons.set_from_time(t, acoplado=(t >= PHASE_BOUNDS[1]))
        self._update_shadows()

    def _animate_belt(self, t, terra):
        """Detritos e satélites em órbitas próprias ao redor da Terra."""
        for i, d in enumerate(self.debris):
            orbita, fase, incl, veloc = self.debris_orbits[i]
            d.update(pos=orbit_point(terra, orbita, t * veloc + fase, incl),
                     rot=(t * (9.0 + i * 5.0), t * (13.0 - i * 3.0), t * 4.0))
        for i, s in enumerate(self.satellites):
            orbita, fase, incl, veloc = self.satellite_orbits[i]
            s.update(pos=orbit_point(terra, orbita, t * veloc + fase, incl),
                     rot=(t * 4.0, 18.0 + t * 7.0, 0.0))

    def _update_shadows(self):
        """
        Eclipse: o que entra no cone de sombra da Terra escurece. A Terra e o
        Sol nunca se auto-eclipsam, então ficam de fora do teste.
        """
        for m in self.meshes:
            if m is self.earth or m is self.sun:
                continue
            m.shadow = self.shadow_factor(m.pos)

    def _animate_door(self, t, roll):
        self.door.set_from_time(t)
        desloc = 36.0 * self.door.opening
        self.door_hi.update(pos=self.to_world((92.0, desloc, 0.0)), rot=(roll, 0.0, 0.0))
        self.door_lo.update(pos=self.to_world((92.0, -desloc, 0.0)), rot=(roll, 0.0, 0.0))

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
        self.cargo.update(pos=self.to_world((x, y, z)),
                          rot=(STATION_ATTITUDE + roll, 0.0, pitch), scale=escala)
        if emitir and t < PHASE_BOUNDS[2]:
            bocal = vec_add(self.cargo.pos, rotate_xyz((80.0, 0.0, 0.0), self.cargo.rotation))
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
            robo.place(self.to_world(local), giro,
                       18.0 * math.sin(ang * 1.3), ombro, cotovelo)
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


class Renderer:
    """
    Desenha a cena numa Surface qualquer (funciona fora da tela, o que permite
    testar a renderização sem abrir janela). Poligonos, partículas e balizas
    entram num único buffer ordenado por profundidade: é o algoritmo do pintor
    aplicado a todos os elementos, não só as faces.
    """

    def __init__(self):
        self.faces_desenhadas = 0
        self.faces_descartadas = 0
        self.glow = GlowSprites()
        self._stars_key = None
        self._stars_proj = []
        self.show_orbits = True

    def draw(self, surface, scene):
        cam = scene.camera
        surface.fill(BG_COLOR)
        self._draw_stars(surface, scene, cam)
        self._draw_atmosphere(surface, scene, cam)
        if self.show_orbits:
            self._draw_orbits(surface, scene, cam)

        itens = []
        descartadas = 0
        sol = scene.sun
        for mesh in scene.meshes:
            visiveis, fora = mesh.collect(cam, emissivo=(mesh is sol))
            descartadas += fora
            for profundidade, pts, cor in visiveis:
                itens.append((profundidade, 0, pts, cor))

        for p in scene.particles.particles:
            v = cam.to_view(p["pos"])
            if v[2] < NEAR:
                continue
            raio = max(1, int(p["size"] * p["life"] * FOV / v[2]))
            cor = ExhaustParticles.color_of(p)
            tela = project_view(v)
            cauda = cam.to_view((p["pos"][0] - p["vel"][0] * 0.045,
                                 p["pos"][1] - p["vel"][1] * 0.045,
                                 p["pos"][2] - p["vel"][2] * 0.045))
            if cauda[2] >= NEAR:
                itens.append((v[2], 3, (tela, project_view(cauda)), (cor, max(1, raio))))
            else:
                itens.append((v[2], 1, tela, (cor, raio)))
            if p["life"] > 0.78:
                itens.append((v[2] + 0.5, 2, tela, (cor, raio * 4)))

        for k, local in enumerate(scene.beacons.local):
            mundo = scene.to_world(local)
            v = cam.to_view(mundo)
            if v[2] < NEAR:
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
            else:
                pygame.draw.line(surface, b[0], a[0], a[1], b[1])

        self.faces_desenhadas = sum(1 for it in itens if it[1] == 0)
        self.faces_descartadas = descartadas
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
        Campo estelar. A projeção fica em cache e só é refeita quando a câmera
        se move, de modo que a cintilação continua por conta do brilho, que é
        recalculado a cada quadro e custa quase nada.
        """
        chave = tuple(round(c, 4) for c in cam.forward + cam.up)
        if chave != self._stars_key:
            self._stars_key = chave
            projetadas = []
            # as estrelas ficam no infinito: a posição da câmera não as move,
            # só a orientação. Isso mantém o fundo estável enquanto a estação
            # percorre milhares de unidades de órbita.
            for star in scene.starfield.stars:
                p = project_point(vec_add(cam.eye,
                                          vec_scale(star["dir"], STARFIELD_DISTANCE)), cam)
                if p is None or not (0 <= p[0] < WIDTH and 0 <= p[1] < HEIGHT):
                    continue
                projetadas.append((p, star))
            self._stars_proj = projetadas

        t = scene.sim_time
        brilho_de = scene.starfield.brightness
        for p, star in self._stars_proj:
            k = brilho_de(star, t)
            cor = (int(star["tom"][0] * k), int(star["tom"][1] * k), int(star["tom"][2] * k))
            tamanho = star["size"]
            if tamanho <= 1:
                surface.set_at(p, cor)
            else:
                pygame.draw.circle(surface, cor, p, tamanho)
                if tamanho >= 2 and k > 0.8:          # cruz de difração
                    braco = tamanho * 3
                    fraco = (cor[0] // 2, cor[1] // 2, cor[2] // 2)
                    pygame.draw.line(surface, fraco, (p[0] - braco, p[1]), (p[0] + braco, p[1]))
                    pygame.draw.line(surface, fraco, (p[0], p[1] - braco), (p[0], p[1] + braco))

    def _draw_atmosphere(self, surface, scene, cam):
        """Atmosfera da Terra e coroa do Sol, desenhadas antes das malhas."""
        v = cam.to_view(scene.earth.pos)
        if v[2] >= NEAR:
            raio = int(scene.earth.bounding_radius * FOV / v[2])
            if raio >= 8:
                centro = project_view(v)
                self.glow.blit(surface, centro, int(raio * 1.5), (46, 96, 172),
                               intensidade=0.34, queda=2.6)
                self.glow.blit(surface, centro, int(raio * 1.14), (104, 158, 228),
                               intensidade=0.5, queda=2.0)
        v = cam.to_view(scene.sun.pos)
        if v[2] >= NEAR:
            raio = int(scene.sun.bounding_radius * FOV / v[2])
            if raio >= 3:
                centro = project_view(v)
                self.glow.blit(surface, centro, int(raio * 3.4), (255, 214, 128),
                               intensidade=0.42, queda=2.2)
                self.glow.blit(surface, centro, int(raio * 1.5), (255, 242, 198),
                               intensidade=0.8, queda=2.4)

    def _draw_orbits(self, surface, scene, cam):
        """
        Traçado das órbitas. Cada anel é uma sequência de pontos projetados; os
        trechos que passam atrás do plano próximo são simplesmente interrompidos,
        o que já basta para uma linha.
        """
        ex, ey, ez = cam.eye
        rx, ry, rz = cam.right
        ux, uy, uz = cam.up
        fx, fy, fz = cam.forward
        for _nome, pontos, cor in scene.orbit_rings():
            trecho = []
            # a mesma conta de project_point, desenrolada: são ~300 pontos por
            # quadro, e as duas chamadas de função por ponto pesavam mais que a
            # própria projeção
            for px, py, pz in pontos + pontos[:1]:
                dx, dy, dz = px - ex, py - ey, pz - ez
                vz = dx * fx + dy * fy + dz * fz
                if vz < NEAR:
                    if len(trecho) > 1:
                        pygame.draw.lines(surface, cor, False, trecho)
                    trecho = []
                    continue
                trecho.append((int((dx * rx + dy * ry + dz * rz) * FOV / vz + VIEW_CENTER_X),
                               int(-(dx * ux + dy * uy + dz * uz) * FOV / vz + VIEW_CENTER_Y)))
            if len(trecho) > 1:
                pygame.draw.lines(surface, cor, False, trecho)

    @staticmethod
    def _draw_sight(surface, scene, cam):
        """Desenha cada raio: verde quando a linha está livre, vermelho quando bloqueada."""
        for linha in scene.sight:
            a = project_point(linha["origem"], cam)
            b = project_point(linha["ponto"], cam)
            if a is None or b is None:
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
    "Exercícios de aula 01 a 09 (pipeline, transformações, câmera, galeria 3D)",
    "Enunciado Atividade-AP_1.pdf - variação Equipe 2, Estação Espacial",
    "Documentação oficial do Pygame - módulos draw, display, time e font",
)

CONCEPTS = (
    "Câmera look-at com base ortonormal e transição interpolada",
    "Projeção em perspectiva com distância focal e recorte no plano próximo",
    "Back-face culling vetorial e algoritmo do pintor por profundidade de câmera",
    "Sombreamento plano: Lambert com a luz do Sol, preenchimento e realce Blinn-Phong",
    "Transformação hierárquica: comportas e robôs ancorados no núcleo",
    "Instanciação parametrizada: quatro robôs MR-1 a MR-4 e nove detritos",
    "Traçado de raio: interseção raio-esfera para teste de linha de visão",
    "Máquinas de estado aninhadas: sequência geral e comporta de doca",
)

HUD_BG = (10, 14, 22)
HUD_TXT = (226, 232, 240)
HUD_DIM = (138, 148, 164)
HUD_ACCENT = (86, 226, 198)


class Hud:
    """Interface sobreposta: título, estado, tempo, progresso e comandos."""

    def __init__(self):
        self.font = pygame.font.SysFont("Consolas", 14)
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
            self._draw_credits(surface)
        else:
            if self.show_labels:
                self._draw_labels(surface, scene)
            self._draw_main(surface, scene)
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
        y = HEIGHT - 120
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
        self._panel(surface, (18, 14, 612, 148))
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
        surface.blit(self.txt(self.font, "Enquadramento: %s   (escala comprimida)"
                              % scene.zoom_level["name"], True, HUD_DIM), (30, 124))
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

    def _draw_footer(self, surface, scene):
        """Rodapé: comandos e indicador de progresso com as marcas das fases."""
        alt = 68
        topo = HEIGHT - alt - 14
        self._panel(surface, (18, topo, WIDTH - 36, alt))
        surface.blit(self.txt(self.font, 
            "[ESPAÇO] iniciar/pausar  [R] reiniciar  [1-4] fases  [C W S A D] câmeras  "
            "[F] foco  [T] tour  [Z/X] zoom  [+/-] velocidade",
            True, HUD_DIM), (32, topo + 8))
        # em uma linha só os comandos passavam da largura do painel e [TAB] e
        # [ESC] ficavam cortados
        surface.blit(self.txt(self.font,
            "[B] órbitas  [L] repetir  [O] inspeção  [N] rótulos  [H] dados  "
            "[F12] captura  [TAB] créditos  [ESC] sair",
            True, HUD_DIM), (32, topo + 26))

        x, y, larg, esp = 32, topo + 48, WIDTH - 276, 11
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
        """Dados orbitais dos corpos, para o painel [H]."""
        t = scene.anim_time
        corpos = (("Terra", EARTH_ORBIT, EARTH_YEAR, scene.earth.pos),
                  ("Lua", MOON_ORBIT, MOON_MONTH, scene.moon.pos),
                  ("Órbita-2", STATION_ORBIT, STATION_PERIOD, scene.station_pos))
        linhas = ["ÓRBITAS  raio / período / voltas"]
        for nome, raio, periodo, _pos in corpos:
            linhas.append("%-9s %5.0f %5.0fs %6.2f" % (nome, raio, periodo, t / periodo))
        eclipsados = sum(1 for m in scene.meshes if m.shadow > 0.02)
        linhas.append("na sombra da Terra . %d" % eclipsados)
        linhas.append("tempo simulado ..... %.0fs" % t)
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
            "PIPELINE",
            "FPS medido ........ " + fps_txt,
            "quadro (CPU) ...... " + cpu_txt,
            "faces desenhadas .. %d" % renderer.faces_desenhadas,
            "faces descartadas . %d" % renderer.faces_descartadas,
            "malhas na cena .... %d" % len(scene.meshes),
            "partículas ........ %d" % len(scene.particles.particles),
            "olho .............. %.0f %.0f %.0f" % tuple(cam.eye),
            "alvo .............. %.0f %.0f %.0f" % tuple(cam.target),
            "FOV / near ........ %.0f / %.0f" % (FOV, NEAR),
            "",
        ] + self._orbital_rows(scene)
        alt = 18 + len(linhas) * 17
        self._panel(surface, (WIDTH - 306, 16, 288, alt))
        for i, txt in enumerate(linhas):
            cor = HUD_ACCENT if txt and not txt.startswith((" ", "f", "m", "p", "o", "a", "F", "n", "t", "q")) else HUD_DIM
            surface.blit(self.txt(self.font, txt, True, cor), (WIDTH - 292, 26 + i * 17))

    def _draw_credits(self, surface):
        surface.blit(self._camada(WIDTH, HEIGHT, (5, 7, 12), 242), (0, 0))
        x, y = 74, 56
        surface.blit(self.txt(self.font_title, 
            "CRÉDITOS - AP1 Computação Gráfica e RA/RV", True, HUD_ACCENT), (x, y))
        y += 34
        surface.blit(self.txt(self.font_bold, 
            "Variação escolhida: Equipe 2 - Estação Espacial", True, HUD_TXT), (x, y))
        y += 20
        surface.blit(self.txt(self.font, 
            "Acoplamento de módulos, trajetória orbital de robôs, comporta com "
            "estados e alerta sequencial.", True, HUD_DIM), (x, y))

        y += 34
        surface.blit(self.txt(self.font_bold, "Equipe e contribuições", True, HUD_ACCENT), (x, y))
        y += 22
        for nome, ra, papel in TEAM:
            surface.blit(self.txt(self.font, 
                "%-18s %-9s %s" % (nome, ra, papel), True, HUD_TXT), (x + 12, y))
            y += 19

        y += 16
        surface.blit(self.txt(self.font_bold, 
            "Referências dos materiais utilizados", True, HUD_ACCENT), (x, y))
        y += 22
        for ref in REFERENCES:
            surface.blit(self.txt(self.font, "- " + ref, True, HUD_TXT), (x + 12, y))
            y += 19

        y += 16
        surface.blit(self.txt(self.font_bold, 
            "Conceitos de Computação Gráfica aplicados", True, HUD_ACCENT), (x, y))
        y += 22
        for c in CONCEPTS:
            surface.blit(self.txt(self.font, "- " + c, True, HUD_DIM), (x + 12, y))
            y += 19

        surface.blit(self.txt(self.font_bold, 
            "[TAB] volta para a cena", True, (255, 202, 84)), (x, HEIGHT - 40))


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


class App:
    """Janela, laço principal, controle de FPS e tratamento de eventos."""

    def __init__(self, surface=None):
        pygame.init()
        if surface is None:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption(
                "AP1 - Computação Gráfica | Estação Órbita-2")
        else:
            self.screen = surface
        self.clock = pygame.time.Clock()
        self.scene = Scene()
        self.renderer = Renderer()
        self.hud = Hud()
        self.running = True
        # medição publicada no painel [H]: (FPS do relógio, ms de CPU por quadro)
        self.desempenho = None
        self._janela_s = 0.0
        self._soma_ms = 0.0
        self._quadros = 0

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


def main():
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
