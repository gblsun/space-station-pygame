import sys
import math
import random
import pygame

# --- CONFIGURAÇÕES DO MOTOR ---
WIDTH, HEIGHT = 1080, 720
FPS = 60
FOV = 460

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AP1 - Computação Gráfica | Base Espacial e Asteroides")
clock = pygame.time.Clock()

font_hud = pygame.font.SysFont("Consolas", 14)
font_title = pygame.font.SysFont("Consolas", 18, bold=True)

# --- MATEMÁTICA VETORIAL ---
def vec_sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vec_add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def vec_scale(v, s): return (v[0]*s, v[1]*s, v[2]*s)

def cross_product(u, v):
    return (
        u[1]*v[2] - u[2]*v[1],
        u[2]*v[0] - u[0]*v[2],
        u[0]*v[1] - u[1]*v[0]
    )

def dot_product(u, v): return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]

def normalize(v):
    norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm == 0: return (0, 1, 0)
    return (v[0]/norm, v[1]/norm, v[2]/norm)

def lerp(a, b, t): return a + (b - a) * t

LIGHT_DIR = normalize((0.45, 0.75, -0.5))

def project(point, cam_pos):
    x = point[0] - cam_pos[0]
    y = point[1] - cam_pos[1]
    z = point[2] - cam_pos[2]
    if z <= 20: z = 20
    px = int((x * FOV) / z + WIDTH / 2)
    py = int((-y * FOV) / z + HEIGHT / 2)
    return px, py

def rotate_y(point, angle_deg):
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    x, y, z = point
    return (x * c + z * s, y, -x * s + z * c)

# --- MALHA POLIGONAL ---
class PolyMesh:
    def __init__(self, vertices, faces, base_color, position=(0, 0, 0), double_sided=False):
        self.base_vertices = vertices
        self.faces = faces
        self.base_color = base_color
        self.pos = list(position)
        self.rotation_y = 0.0
        self.scale = 1.0
        self.double_sided = double_sided

    def update(self, pos=None, rot_y=None, scale=None):
        if pos is not None: self.pos = list(pos)
        if rot_y is not None: self.rotation_y = rot_y
        if scale is not None: self.scale = scale

    def get_world_data(self, cam_pos):
        world_v = []
        for vx, vy, vz in self.base_vertices:
            sx, sy, sz = vx * self.scale, vy * self.scale, vz * self.scale
            rx, ry, rz = rotate_y((sx, sy, sz), self.rotation_y)
            world_v.append((rx + self.pos[0], ry + self.pos[1], rz + self.pos[2]))

        render_faces = []
        for face in self.faces:
            pts = [world_v[idx] for idx in face]
            u = vec_sub(pts[1], pts[0])
            v = vec_sub(pts[2], pts[0])
            normal = normalize(cross_product(u, v))

            if not self.double_sided:
                cam_dir = normalize(vec_sub(pts[0], cam_pos))
                if dot_product(normal, cam_dir) >= 0:
                    continue

            avg_z = sum(p[2] for p in pts) / len(pts)
            intensity = max(0.30, min(1.0, abs(dot_product(normal, LIGHT_DIR))))
            col = (
                int(self.base_color[0] * intensity),
                int(self.base_color[1] * intensity),
                int(self.base_color[2] * intensity)
            )
            render_faces.append((avg_z, pts, col))

        return render_faces

# --- MODELAGEM GEOMÉTRICA ---
def build_stable_rocket():
    verts = []
    faces = []
    r_body = 24
    h_bot = -60
    h_top = 45
    
    for y in [h_bot, h_top]:
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            verts.append((r_body * math.cos(ang), y, r_body * math.sin(ang)))
            
    verts.append((0, h_top + 55, 0))
    verts.append((0, h_bot, 0))

    for i in range(8):
        nxt = (i + 1) % 8
        faces.append((i, nxt, nxt + 8, i + 8))
        faces.append((i + 8, nxt + 8, 16))
        faces.append((nxt, i, 17))

    for ang_deg in [0, 90, 180, 270]:
        rad = math.radians(ang_deg)
        c, s = math.cos(rad), math.sin(rad)
        idx = len(verts)
        p_root_top = (r_body * c, h_bot + 40, r_body * s)
        p_root_bot = (r_body * c, h_bot, r_body * s)
        p_tip = ((r_body + 30) * c, h_bot - 10, (r_body + 30) * s)
        verts.extend([p_root_top, p_root_bot, p_tip])
        faces.append((idx, idx + 1, idx + 2))
        faces.append((idx + 2, idx + 1, idx))

    return verts, faces

def build_launch_tower():
    verts = [
        (-18, -120, -18), (18, -120, -18), (18, -120, 18), (-18, -120, 18),
        (-12, 130, -12), (12, 130, -12), (12, 130, 12), (-12, 130, 12),
        (-60, 45, -6), (-12, 45, -6), (-12, 45, 6), (-60, 45, 6),
        (-60, 58, -6), (-12, 58, -6), (-12, 58, 6), (-60, 58, 6)
    ]
    faces = [
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7),
        (8, 9, 13, 12), (9, 10, 14, 13), (10, 11, 15, 14), (11, 8, 12, 15), (12, 13, 14, 15)
    ]
    return verts, faces

def build_asteroid(radius=28):
    random.seed(42)
    verts, faces = [], []
    rings, sectors = 6, 9
    for r in range(rings + 1):
        lat = (math.pi * r) / rings - (math.pi / 2)
        for s in range(sectors):
            lon = (2 * math.pi * s) / sectors
            noise = random.uniform(0.75, 1.25)
            rad = radius * noise
            verts.append((rad * math.cos(lat) * math.cos(lon), rad * math.sin(lat), rad * math.cos(lat) * math.sin(lon)))

    for r in range(rings):
        for s in range(sectors):
            faces.append((r * sectors + s, r * sectors + ((s + 1) % sectors), (r + 1) * sectors + ((s + 1) % sectors), (r + 1) * sectors + s))
    return verts, faces

def build_sphere(radius=125, rings=8, sectors=14):
    verts, faces = [], []
    for r in range(rings + 1):
        lat = (math.pi * r) / rings - (math.pi / 2)
        for s in range(sectors):
            lon = (2 * math.pi * s) / sectors
            verts.append((radius * math.cos(lat) * math.cos(lon), radius * math.sin(lat), radius * math.cos(lat) * math.sin(lon)))
    for r in range(rings):
        for s in range(sectors):
            faces.append((r * sectors + s, r * sectors + ((s + 1) % sectors), (r + 1) * sectors + ((s + 1) % sectors), (r + 1) * sectors + s))
    return verts, faces

# --- INSTANCIAÇÃO DOS ELEMENTOS ---
ROCKET_V, ROCKET_F = build_stable_rocket()
TOWER_V, TOWER_F = build_launch_tower()
ASTEROID_V, ASTEROID_F = build_asteroid()
MOON_V, MOON_F = build_sphere()

rocket = PolyMesh(ROCKET_V, ROCKET_F, (245, 105, 30), position=(0, -45, 520), double_sided=True)
launch_tower = PolyMesh(TOWER_V, TOWER_F, (0, 180, 220), position=(130, 0, 520))
moon = PolyMesh(MOON_V, MOON_F, (215, 220, 230), position=(-420, 230, 860))

asteroids = [
    PolyMesh(ASTEROID_V, ASTEROID_F, (140, 130, 125), position=(-160, 110, 430)),
    PolyMesh(ASTEROID_V, ASTEROID_F, (160, 150, 140), position=(0, 190, 510)),
    PolyMesh(ASTEROID_V, ASTEROID_F, (120, 110, 110), position=(160, 120, 460))
]
asteroids[0].scale = 0.85
asteroids[1].scale = 1.35
asteroids[2].scale = 0.65

all_meshes = [rocket, launch_tower, moon] + asteroids

# --- PARTICULAS DE EXAUSTÃO ---
class ExhaustParticles:
    def __init__(self):
        self.particles = []

    def emit(self, base_pos, count=4):
        for _ in range(count):
            ox = random.uniform(-6, 6)
            oz = random.uniform(-6, 6)
            self.particles.append({
                'pos': [base_pos[0] + ox, base_pos[1] - 45, base_pos[2] + oz],
                'vel_y': random.uniform(-75, -45),
                'life': 1.0,
                'size': random.uniform(3, 7)
            })

    def update(self, dt):
        alive = []
        for p in self.particles:
            p['life'] -= dt * 2.3
            p['pos'][1] += p['vel_y'] * dt
            if p['life'] > 0: alive.append(p)
        self.particles = alive

    def draw(self, surface, cam_pos):
        for p in self.particles:
            px, py = project(p['pos'], cam_pos)
            color = (255, int(160 * p['life']), 20) if p['life'] > 0.35 else (100, 100, 100)
            pygame.draw.circle(surface, color, (px, py), max(1, int(p['size'] * p['life'])))

exhaust = ExhaustParticles()

# --- CAMPO ESTELAR ---
class Starfield:
    def __init__(self, count=120):
        self.stars = [[random.uniform(-650, 650), random.uniform(-450, 450), random.uniform(100, 950)] for _ in range(count)]
    def update(self, speed):
        for s in self.stars:
            s[2] -= speed
            if s[2] <= 40: s[2] = 950
    def draw(self, surface, cam_pos):
        for s in self.stars:
            px, py = project(s, cam_pos)
            pygame.draw.circle(surface, (180, 205, 235), (px, py), 1)

starfield = Starfield()

# --- CÂMERA ---
STATE_PARADO = "PARADO"
STATE_EXECUTANDO = "EXECUTANDO"
STATE_PAUSADO = "PAUSADO"
STATE_CONCLUIDO = "CONCLUIDO"

current_state = STATE_PARADO
sim_time = 0.0
TOTAL_SEQUENCE_TIME = 12.0

cam_target = [0.0, 15.0, 0.0]
cam_current = [0.0, 15.0, 0.0]
cam_name = "Visão Frontal (Default)"
show_credits = False

# --- LOOP PRINCIPAL ---
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # 1. EVENTOS DISCRETOS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if current_state == STATE_PARADO: current_state = STATE_EXECUTANDO
                elif current_state == STATE_EXECUTANDO: current_state = STATE_PAUSADO
                elif current_state == STATE_PAUSADO: current_state = STATE_EXECUTANDO
                elif current_state == STATE_CONCLUIDO:
                    sim_time = 0.0
                    current_state = STATE_EXECUTANDO
            elif event.key == pygame.K_r:
                current_state = STATE_PARADO
                sim_time = 0.0
                cam_target = [0.0, 15.0, 0.0]
                cam_name = "Visão Frontal (Default)"
                rocket.update(pos=(0, -45, 520), rot_y=0, scale=1.0)
                moon.update(rot_y=0)
                asteroids[0].update(pos=(-160, 110, 430), rot_y=0)
                asteroids[1].update(pos=(0, 190, 510), rot_y=0)
                asteroids[2].update(pos=(160, 120, 460), rot_y=0)
            elif event.key == pygame.K_w:
                cam_target = [0.0, 240.0, 320.0]
                cam_name = "Visão Superior [W]"
            elif event.key == pygame.K_s:
                cam_target = [0.0, -80.0, 240.0]
                cam_name = "Visão Inferior [S]"
            elif event.key == pygame.K_a:
                cam_target = [-280.0, 30.0, 400.0]
                cam_name = "Flanco Esquerdo [A]"
            elif event.key == pygame.K_d:
                cam_target = [280.0, 30.0, 400.0]
                cam_name = "Flanco Direito [D]"
            elif event.key == pygame.K_c:
                cam_target = [0.0, 15.0, 0.0]
                cam_name = "Visão Frontal [C]"
            elif event.key == pygame.K_TAB:
                show_credits = not show_credits

    for i in range(3):
        cam_current[i] = lerp(cam_current[i], cam_target[i], min(1.0, 5.0 * dt))

    # 2. ANIMAÇÕES COM DETECÇÃO E DESVIO DE COLISÃO
    phase_label = "Em Espera (Pressione ESPAÇO)"
    exhaust.update(dt)

    if current_state == STATE_EXECUTANDO:
        sim_time += dt
        starfield.update(speed=60.0 * dt)
        moon.update(rot_y=(sim_time * 5.0) % 360)

        if sim_time < 3.5:
            phase_label = "Fase 1: Alinhamento e Desacoplamento da Torre"
            rocket.update(pos=(0, -45, 520), rot_y=(sim_time * 80.0) % 360, scale=1.0)
        elif sim_time < 7.5:
            phase_label = "Fase 2: Ignição Principal e Subida do Foguete"
            t_rel = sim_time - 3.5
            y_pos = -45 + (t_rel * 32.0)
            sc = 1.0 + 0.05 * math.sin(sim_time * 8.0)
            rocket.update(pos=(0, y_pos, 520), rot_y=(3.5 * 80.0) + (t_rel * 35.0), scale=sc)
            exhaust.emit(rocket.pos, count=4)
        elif sim_time < TOTAL_SEQUENCE_TIME:
            phase_label = "Fase 3: Órbita com Evitação de Colisão (AABB)"
            t_rel = sim_time - 7.5
            
            # Caixa envolvente de segurança da torre (AABB de Colisão)
            # Torre em X: 70 a 160 | Z: 480 a 560 | Y: -120 a 140
            for i, ast in enumerate(asteroids):
                ang = sim_time * 2.2 + i * (2 * math.pi / 3)
                rad = 145 + t_rel * 14.0
                
                # Trajetória teórica
                dx = math.cos(ang) * rad
                dy = 110 + i * 22
                dz = 520 + math.sin(ang) * 90

                # Teste de Intersecção de Caixa / Esfera com a Torre
                dist_to_tower_xz = math.sqrt((dx - launch_tower.pos[0])**2 + (dz - launch_tower.pos[2])**2)
                collision_radius = 65.0  # Zona de impacto da torre

                if dist_to_tower_xz < collision_radius:
                    # Desvio Vetorial de Colisão: empurra o asteroide para fora da zona do mastro
                    push_dir = normalize((dx - launch_tower.pos[0], 0, dz - launch_tower.pos[2]))
                    dx = launch_tower.pos[0] + push_dir[0] * collision_radius
                    dz = launch_tower.pos[2] + push_dir[2] * collision_radius
                    dy += 20.0 * math.sin(sim_time * 10.0)  # Leve perturbação no impacto

                ast.update(pos=(dx, dy, dz), rot_y=(sim_time * 90) % 360)
        else:
            current_state = STATE_CONCLUIDO
            phase_label = "Sequência Concluída"

    # 3. TRAÇADO DE RAIO (TORRE -> FOGUETE)
    tower_beam = (launch_tower.pos[0] - 50, launch_tower.pos[1] + 50, launch_tower.pos[2])
    target_center = (rocket.pos[0], rocket.pos[1], rocket.pos[2])
    dist_total = math.sqrt(sum((a - b)**2 for a, b in zip(tower_beam, target_center)))
    ray_hit = dist_total < 330.0
    ray_dir = normalize(vec_sub(target_center, tower_beam))
    hit_point = vec_sub(target_center, vec_scale(ray_dir, 40.0 * rocket.scale)) if ray_hit else target_center
    ray_color = (255, 60, 60) if ray_hit else (40, 240, 140)

    # 4. RENDERIZAÇÃO
    screen.fill((8, 10, 16))
    starfield.draw(screen, cam_current)

    # Z-Sort
    scene_faces = []
    for m in all_meshes:
        scene_faces.extend(m.get_world_data(cam_current))
    scene_faces.sort(key=lambda item: item[0], reverse=True)

    for avg_z, pts, color in scene_faces:
        poly_2d = [project(p, cam_current) for p in pts]
        pygame.draw.polygon(screen, color, poly_2d)
        edge_col = (min(255, color[0] + 25), min(255, color[1] + 25), min(255, color[2] + 25))
        pygame.draw.polygon(screen, edge_col, poly_2d, 1)

    exhaust.draw(screen, cam_current)

    # Raycast
    p_rad = project(tower_beam, cam_current)
    p_hit = project(hit_point, cam_current)
    pygame.draw.line(screen, ray_color, p_rad, p_hit, 2 if ray_hit else 1)
    pygame.draw.circle(screen, ray_color, p_rad, 4)
    if ray_hit:
        pygame.draw.circle(screen, (255, 255, 255), p_hit, 3)

    # 5. HUD
    if not show_credits:
        hud_lines = [
            ("AP1 - Computação Gráfica | Base de Lançamento e Campo de Asteroides", (255, 255, 255), font_title),
            (f"Estado FSM: [{current_state}]  |  {phase_label}", (0, 255, 200), font_hud),
            (f"Tempo: {sim_time:05.2f}s / {TOTAL_SEQUENCE_TIME:.1f}s  |  Raio Sensor: {'CONTATO/ALERTA' if ray_hit else 'LIVRE'}", ray_color, font_hud),
            (f"Perspectiva Ativa: {cam_name}", (220, 220, 220), font_hud),
            ("[ESPAÇO] Play/Pause | [R] Reset | [W,A,S,D,C] Câmeras | [TAB] Créditos", (140, 140, 140), font_hud)
        ]
        for idx, (txt, col, f) in enumerate(hud_lines):
            screen.blit(f.render(txt, True, col), (24, 20 + idx * 22))

        prog = min(sim_time / TOTAL_SEQUENCE_TIME, 1.0)
        pygame.draw.rect(screen, (30, 40, 55), (24, 140, 240, 10), border_radius=3)
        pygame.draw.rect(screen, (0, 255, 200), (24, 140, int(240 * prog), 10), border_radius=3)
        screen.blit(font_hud.render(f"{int(prog * 100)}%", True, (160, 160, 160)), (272, 137))
    else:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 12, 240))
        screen.blit(overlay, (0, 0))
        credits_text = [
            "TELA DE CRÉDITOS & ARQUITETURA GRÁFICA",
            "----------------------------------------------------------------",
            "Tema: Estação Espacial (Pipeline 3D)",
            "Equipe: Fellipe Augusto, Gabriel Muchon, Paloma Eduarda e Victor Wenzel",
            "",
            "Conceitos de Computação Gráfica Aplicados:",
            "- Detecção de Intersecção: Bounding Volume Obstacle Avoidance com a torre",
            "- Modelagem Composta: Foguete aeroespacial com base selada e aletas bilaterais",
            "- Superfícies Procedurais: Malhas deformadas para geração dos 3 Asteroides e da Lua",
            "- Oclusão e Visibilidade: Back-Face Culling vetorial + Algoritmo do Pintor (Z-Sort)",
            "- Iluminação Lambertiana: Flat Shading com vetor de luz direcional",
            "- Sistema de Partículas: Exaustão dos motores com decaimento temporal e cor dinâmica",
            "- Traçado de Raio: Teste de intersecção raio-esfera da torre de suporte ao foguete",
            "",
            "Pressione [TAB] para voltar ao cenário"
        ]
        for idx, line in enumerate(credits_text):
            c = (0, 255, 200) if idx == 0 else ((255, 200, 0) if idx == len(credits_text)-1 else (230, 230, 230))
            screen.blit(font_hud.render(line, True, c), (WIDTH // 2 - 290, 140 + idx * 24))

    pygame.display.flip()

pygame.quit()
sys.exit()
