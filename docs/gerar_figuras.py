"""
Gera as figuras de apoio a partir do proprio motor, para que o material nunca
divirja do que o programa desenha.

    python docs/gerar_figuras.py

Produz em docs/img/:
    esboco-planta.png       planta do referencial da estacao (vista de cima)
    fases.png               folha de contato com as quatro fases da sequencia
    sistema-solar-hoje.png  o Sistema Solar em escala real, na data de execucao
"""

import math
import os
import sys
from datetime import datetime, timezone

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
# data fixa para as figuras de sequencia: a pose da estacao depende do instante
INSTANTE = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def planta(largura=1240, altura=860, escala=0.62):
    """
    Vista de cima do referencial local da estacao (plano XZ). E o referencial
    em que a sequencia e escrita: a estacao voa em LVLH, entao estas posicoes
    valem em qualquer ponto da orbita.
    """
    tela = pygame.Surface((largura, altura))
    tela.fill(FUNDO)
    fonte = pygame.font.SysFont("Consolas", 14)
    pequena = pygame.font.SysFont("Consolas", 12)
    titulo = pygame.font.SysFont("Consolas", 20, bold=True)
    ox, oy = largura * 0.47, altura * 0.52

    def para_tela(x, z):
        return (int(ox + x * escala), int(oy - z * escala))

    for passo in range(-1000, 1001, 50):
        cor = GRADE if passo % 250 else (46, 56, 74)
        pygame.draw.line(tela, cor, para_tela(passo, -1000), para_tela(passo, 1000))
        pygame.draw.line(tela, cor, para_tela(-1000, passo), para_tela(1000, passo))
    pygame.draw.line(tela, (70, 84, 108), para_tela(-1000, 0), para_tela(1000, 0), 2)
    pygame.draw.line(tela, (70, 84, 108), para_tela(0, -1000), para_tela(0, 1000), 2)
    tela.blit(pequena.render("+X (velocidade)", True, FRACO), (largura - 140, oy - 20))
    tela.blit(pequena.render("+Z", True, FRACO), (ox + 8, 76))

    cena = ap1.Scene(INSTANTE)

    # campo de detritos em orbita relativa lenta
    for (orbita, fase, incl, _veloc), detrito in zip(cena.debris_orbits, cena.debris):
        p = ap1.orbit_point((0.0, 0.0, 0.0), orbita, fase, incl)
        pygame.draw.circle(tela, (128, 118, 110), para_tela(p[0], p[2]),
                           max(3, int(detrito.bounding_radius * escala)), 1)

    # orbitas dos robos na fase 4
    for robo in cena.robots:
        raio, offset_x, _veloc, _fase, incl = robo.params
        traco = []
        for k in range(73):
            ang = k * (2.0 * math.pi / 72.0)
            local = ap1.rotate_xyz((offset_x, raio * math.cos(ang), raio * math.sin(ang)),
                                   (0.0, 0.0, incl))
            traco.append(para_tela(local[0], local[2]))
        pygame.draw.lines(tela, (104, 124, 178), True, traco, 1)

    # trajetoria de aproximacao do cargueiro, com marcas de fase
    pontos = [para_tela(cena.cargo_x(k * 0.1), 0.0)
              for k in range(int(ap1.TOTAL_SEQUENCE_TIME * 10) + 1)]
    pygame.draw.lines(tela, QUENTE, False, pontos, 3)
    for i, limite in enumerate(ap1.PHASE_BOUNDS):
        p = para_tela(cena.cargo_x(limite - 0.01), 0.0)
        alvo_y = p[1] + 22 + i * 17
        pygame.draw.circle(tela, QUENTE, p, 5)
        pygame.draw.line(tela, (150, 106, 48), p, (p[0], alvo_y))
        tela.blit(pequena.render("fim da fase %d" % (i + 1), True, QUENTE), (p[0] + 5, alvo_y - 7))

    principais = [
        ((-20.0, 0.0), 122, "Nucleo Orbita-2 (composto)", (-60, -150), DESTAQUE),
        ((-184.0, 0.0), 86, "Modulo Laboratorio", (-150, 60), TEXTO),
        ((92.0, 0.0), 30, "Comporta de doca", (20, -70), TEXTO),
        ((-20.0, 190.0), 80, "Painel articulado (segue o Sol)", (60, -10), TEXTO),
        ((-20.0, -190.0), 80, "Painel articulado", (60, -10), TEXTO),
    ]
    for (x, z), raio, rotulo, desloc, cor in principais:
        p = para_tela(x, z)
        pygame.draw.circle(tela, cor, p, max(4, int(raio * escala)), 1)
        pygame.draw.circle(tela, cor, p, 3)
        tela.blit(fonte.render(rotulo, True, cor), (p[0] + desloc[0], p[1] + desloc[1]))

    for i, ancora in enumerate(ap1.ROBOT_DOCK_LOCAL):
        p = para_tela(ancora[0], ancora[2])
        cor = cena.robots[i].cor
        pygame.draw.circle(tela, cor, p, 4)
        tela.blit(pequena.render("MR-%d" % (i + 1), True, cor), (p[0] - 16, p[1] - 26 - i * 13))

    for preset in ap1.CAMERA_PRESETS.values():
        olho, alvo = preset["eye"], preset["target"]
        a, b = para_tela(olho[0], olho[2]), para_tela(alvo[0], alvo[2])
        pygame.draw.line(tela, CAMERA, a, b, 1)
        pygame.draw.circle(tela, CAMERA, a, 6)
        tela.blit(pequena.render(preset["name"], True, CAMERA), (a[0] + 9, a[1] + 7))

    tela.blit(titulo.render("Estacao Orbita-2 - planta do referencial local (vista de cima)",
                            True, TEXTO), (24, 18))
    legenda = [
        ("grade fina 50 u (10 m) / grossa 250 u (50 m); 1 unidade = 0,2 m", FRACO),
        ("laranja: trajetoria de aproximacao do cargueiro (pelo eixo da velocidade)", QUENTE),
        ("azul: orbitas dos quatro robos na fase 4", (104, 124, 178)),
        ("rosa: posicao e mira das cameras", CAMERA),
        ("circulos marrons: campo de detritos em orbita relativa", (128, 118, 110)),
        ("a Terra fica abaixo e a frente: arfagem de %.0f graus sobre o LVLH" % ap1.STATION_PITCH,
         FRACO),
    ]
    for i, (txt, cor) in enumerate(legenda):
        tela.blit(pequena.render(txt, True, cor), (24, 46 + i * 16))

    pygame.image.save(tela, os.path.join(SAIDA, "esboco-planta.png"))
    print("docs/img/esboco-planta.png")


def folha_de_fases(col=2, lin=2, larg=560):
    """Miniaturas das quatro fases, renderizadas pelo motor."""
    alt = int(larg * ap1.BASE_HEIGHT / ap1.BASE_WIDTH)
    folha = pygame.Surface((col * larg, lin * alt))
    folha.fill((8, 10, 16))
    quadro = pygame.Surface((ap1.BASE_WIDTH, ap1.BASE_HEIGHT))
    fonte = pygame.font.SysFont("Consolas", 17, bold=True)
    for i, t in enumerate((2.0, 5.5, 8.8, 12.6)):
        cena = ap1.Scene(INSTANTE)
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
        tarja = pygame.Surface((larg, 30))
        tarja.fill((10, 13, 20))
        folha.blit(tarja, (x, y + alt - 30))
        pygame.draw.line(folha, DESTAQUE, (x, y + alt - 30), (x + larg, y + alt - 30))
        folha.blit(fonte.render(ap1.PHASE_NAMES[i], True, TEXTO), (x + 14, y + alt - 24))
    pygame.image.save(folha, os.path.join(SAIDA, "fases.png"))
    print("docs/img/fases.png")


def sistema_solar(largura=1600, altura=900):
    """O Sistema Solar visto de cima, na posicao real de hoje, com os nomes dos corpos."""
    agora = datetime.now(timezone.utc)
    cena = ap1.Scene(agora)
    tela = pygame.Surface((largura, altura))
    renderer, hud = ap1.Renderer(), ap1.Hud()
    cena.zoom_index = 6                                    # Sistema interno
    cena.camera.go_to("superior")
    for _ in range(420):
        cena.update(1.0 / 60.0)
    renderer.draw(tela, cena)
    renderer.draw(tela, cena)                               # a nuvem de asteroides aparece no 2o quadro
    hud._draw_body_labels(tela, cena)
    titulo = pygame.font.SysFont("Consolas", 22, bold=True)
    fonte = pygame.font.SysFont("Consolas", 15)
    tela.blit(titulo.render("Sistema Solar interno em %s UTC (escala real, vista do norte)"
                            % agora.strftime("%d/%m/%Y %H:%M"), True, TEXTO), (24, 18))
    tela.blit(fonte.render("Posicoes pelos elementos do JPL; pontos: %d asteroides e cometas reais do SBDB"
                           % sum(len(n) for n in cena.clouds), True, FRACO), (24, 48))
    pygame.image.save(tela, os.path.join(SAIDA, "sistema-solar-hoje.png"))
    ap1.configurar_viewport(ap1.BASE_WIDTH, ap1.BASE_HEIGHT)
    print("docs/img/sistema-solar-hoje.png")


def main():
    os.makedirs(SAIDA, exist_ok=True)
    pygame.init()
    planta()
    folha_de_fases()
    sistema_solar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
