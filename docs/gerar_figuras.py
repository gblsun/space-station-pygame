"""
Gera as figuras do esboco da cena a partir do proprio motor, para que o
material de apoio nunca divirja do que o programa desenha.

    python docs/gerar_figuras.py

Produz em docs/img/:
    esboco-planta.png  planta esquematica com objetos, trajetorias e cameras
    fases.png          folha de contato com as quatro fases da sequencia
"""

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "Atividade AP1"))

import pygame
import ap1

SAIDA = os.path.join(RAIZ, "docs", "img")
FUNDO = (15, 18, 26)
GRADE = (34, 42, 56)
TEXTO = (222, 228, 238)
FRACO = (140, 150, 168)
DESTAQUE = (86, 226, 198)
QUENTE = (255, 176, 72)
CAMERA = (232, 128, 200)


def planta(largura=1240, altura=860, escala=0.52):
    """Vista de cima (plano XZ) com os objetos, as trajetorias e as cameras."""
    tela = pygame.Surface((largura, altura))
    tela.fill(FUNDO)
    fonte = pygame.font.SysFont("Consolas", 14)
    pequena = pygame.font.SysFont("Consolas", 12)
    titulo = pygame.font.SysFont("Consolas", 20, bold=True)
    ox, oy = largura * 0.44, altura * 0.46

    def para_tela(x, z):
        return (int(ox + x * escala), int(oy - (z - ap1.SZ) * escala))

    for passo in range(-2400, 2401, 100):
        cor = GRADE if passo % 500 else (46, 56, 74)
        pygame.draw.line(tela, cor, para_tela(passo, ap1.SZ - 2400),
                         para_tela(passo, ap1.SZ + 2400))
        pygame.draw.line(tela, cor, para_tela(-2400, ap1.SZ + passo),
                         para_tela(2400, ap1.SZ + passo))
    pygame.draw.line(tela, (70, 84, 108), para_tela(-2400, ap1.SZ),
                     para_tela(2400, ap1.SZ), 2)
    pygame.draw.line(tela, (70, 84, 108), para_tela(0, ap1.SZ - 2400),
                     para_tela(0, ap1.SZ + 2400), 2)
    tela.blit(pequena.render("+X", True, FRACO), (largura - 34, oy - 20))
    tela.blit(pequena.render("+Z", True, FRACO), (ox + 8, 76))

    cena = ap1.Scene()

    # orbitas dos robos na fase 4
    for robo in cena.robots:
        raio, offset_x, _veloc, _fase, incl = robo.params
        traco = []
        for k in range(73):
            ang = k * (2.0 * math.pi / 72.0)
            local = ap1.rotate_xyz((offset_x, raio * math.cos(ang),
                                    raio * math.sin(ang)), (0.0, 0.0, incl))
            mundo = cena.to_world(local, 0.0)
            traco.append(para_tela(mundo[0], mundo[2]))
        pygame.draw.lines(tela, (104, 124, 178), True, traco, 1)

    # cinturao de detritos: nuvem sem rotulo individual
    for d in cena.debris:
        p = para_tela(d.pos[0], d.pos[2])
        pygame.draw.circle(tela, (128, 118, 110), p, max(3, int(d.bounding_radius * escala)), 1)

    # trajetoria de aproximacao do cargueiro, com marcas de fase
    pontos = [para_tela(ap1.SX + cena.cargo_x(k * 0.1), ap1.SZ)
              for k in range(int(ap1.TOTAL_SEQUENCE_TIME * 10) + 1)]
    pygame.draw.lines(tela, QUENTE, False, pontos, 3)
    for i, limite in enumerate(ap1.PHASE_BOUNDS):
        p = para_tela(ap1.SX + cena.cargo_x(limite - 0.01), ap1.SZ)
        alvo_y = p[1] + 22 + i * 17          # rotulos empilhados, com guia
        pygame.draw.circle(tela, QUENTE, p, 5)
        pygame.draw.line(tela, (150, 106, 48), p, (p[0], alvo_y))
        tela.blit(pequena.render("fim da fase %d" % (i + 1), True, QUENTE),
                  (p[0] + 5, alvo_y - 7))

    # objetos principais, com rotulo em leque para nao colidir
    principais = [
        (cena.station, "Nucleo Orbita-2 (composto)", (14, -30), DESTAQUE),
        (cena.lab, "Modulo Laboratorio", (-150, -52), TEXTO),
        (cena.cargo, "Cargueiro Vega-7 (composto)", (16, 26), TEXTO),
        (cena.satellite, "Satelite Farol-3", (14, 0), TEXTO),
    ]
    for mesh, rotulo, desloc, cor in principais:
        p = para_tela(mesh.pos[0], mesh.pos[2])
        r = max(4, int(mesh.bounding_radius * escala))
        pygame.draw.circle(tela, cor, p, r, 1)
        pygame.draw.circle(tela, cor, p, 3)
        tela.blit(fonte.render(rotulo, True, cor), (p[0] + desloc[0], p[1] + desloc[1]))

    for i, robo in enumerate(cena.robots):
        p = para_tela(robo.pos[0], robo.pos[2])
        pygame.draw.circle(tela, robo.cor, p, 4)
        tela.blit(pequena.render("MR-%d" % (i + 1), True, robo.cor),
                  (p[0] - 16, p[1] - 26 - i * 13))

    # cameras
    for preset in ap1.CAMERA_PRESETS.values():
        olho, alvo = preset["eye"], preset["target"]
        a, b = para_tela(olho[0], olho[2]), para_tela(alvo[0], alvo[2])
        pygame.draw.line(tela, CAMERA, a, b, 1)
        pygame.draw.circle(tela, CAMERA, a, 6)
        tela.blit(pequena.render(preset["name"], True, CAMERA), (a[0] + 9, a[1] + 7))

    tela.blit(titulo.render("Estacao Orbita-2 - planta do plano XZ (vista de cima)",
                            True, TEXTO), (24, 18))
    legenda = [
        ("grade fina 100 u / grossa 500 u", FRACO),
        ("laranja: trajetoria de aproximacao do cargueiro", QUENTE),
        ("azul: orbitas dos quatro robos na fase 4", (104, 124, 178)),
        ("rosa: posicao e mira das cameras", CAMERA),
        ("circulos marrons: cinturao de 9 detritos", (128, 118, 110)),
        ("Planeta Kaltus fica em (-1180, -470, +1750) relativo a estacao, fora da area", FRACO),
    ]
    for i, (txt, cor) in enumerate(legenda):
        tela.blit(pequena.render(txt, True, cor), (24, 46 + i * 16))

    pygame.image.save(tela, os.path.join(SAIDA, "esboco-planta.png"))
    print("docs/img/esboco-planta.png")


def folha_de_fases(col=2, lin=2, larg=560):
    """Miniaturas das quatro fases, renderizadas pelo motor."""
    alt = int(larg * ap1.HEIGHT / ap1.WIDTH)
    folha = pygame.Surface((col * larg, lin * alt))
    folha.fill((8, 10, 16))
    quadro = pygame.Surface((ap1.WIDTH, ap1.HEIGHT))
    fonte = pygame.font.SysFont("Consolas", 17, bold=True)
    instantes = (2.0, 5.5, 8.8, 12.6)
    for i, t in enumerate(instantes):
        cena = ap1.Scene()
        cena.state = ap1.STATE_EXECUTANDO
        for _ in range(int(round(t * 60))):
            cena.update(1.0 / 60.0)
        r, h = ap1.Renderer(), ap1.Hud()
        r.draw(quadro, cena)
        h.draw(quadro, cena, r)
        mini = pygame.transform.smoothscale(quadro, (larg, alt))
        x, y = (i % col) * larg, (i // col) * alt
        folha.blit(mini, (x, y))
        pygame.draw.rect(folha, (52, 64, 84), (x, y, larg, alt), 1)
        rotulo = fonte.render(ap1.PHASE_NAMES[i], True, TEXTO)
        tarja = pygame.Surface((larg, 30))
        tarja.fill((10, 13, 20))
        folha.blit(tarja, (x, y + alt - 30))
        pygame.draw.line(folha, DESTAQUE, (x, y + alt - 30), (x + larg, y + alt - 30))
        folha.blit(rotulo, (x + 14, y + alt - 24))
    pygame.image.save(folha, os.path.join(SAIDA, "fases.png"))
    print("docs/img/fases.png")


def main():
    os.makedirs(SAIDA, exist_ok=True)
    pygame.init()
    planta()
    folha_de_fases()
    return 0


if __name__ == "__main__":
    sys.exit(main())
