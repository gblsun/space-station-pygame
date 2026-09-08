"""Exemplo didático: leitura de faces OBJ e câmera perspectiva simplificada."""
import math
import pygame

LARGURA, ALTURA = 900, 650


def carregar_obj(nome):
    vertices, faces = [], []
    with open(nome, encoding="utf-8") as arquivo:
        for linha in arquivo:
            p = linha.split()
            if not p or p[0].startswith("#"):
                continue
            if p[0] == "v":
                vertices.append(tuple(map(float, p[1:4])))
            elif p[0] == "f":
                ids = [int(item.split("/")[0]) - 1 for item in p[1:]]
                faces.extend((ids[0], ids[i], ids[i + 1]) for i in range(1, len(ids) - 1))
    return vertices, faces


def camera_y(ponto, angulo, distancia):
    x, y, z = ponto
    x -= 0.0
    z -= distancia
    c, s = math.cos(angulo), math.sin(angulo)
    return (c * x - s * z, y, s * x + c * z)


def projetar(ponto, foco, centro):
    x, y, z = ponto
    if z <= 0.2:
        return None
    fator = foco / z
    return (int(centro[0] + x * fator), int(centro[1] - y * fator))


def main():
    pygame.init()
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Exemplo OBJ — Robô")
    fonte = pygame.font.Font(None, 26)
    vertices, faces = carregar_obj("modelo_robo.obj")
    relogio = pygame.time.Clock()
    angulo, distancia = 0.0, 6.0
    executando = True
    while executando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_LEFT:
                    angulo -= 0.12
                elif evento.key == pygame.K_RIGHT:
                    angulo += 0.12
                elif evento.key == pygame.K_w:
                    distancia = max(2.5, distancia - 0.3)
                elif evento.key == pygame.K_s:
                    distancia += 0.3
        pontos = [projetar(camera_y(v, angulo, distancia), 360, (LARGURA // 2, ALTURA // 2 + 50)) for v in vertices]
        tela.fill((30, 24, 35))
        for a, b, c in faces:
            if all(pontos[i] is not None for i in (a, b, c)):
                pygame.draw.polygon(tela, (220, 145, 80), (pontos[a], pontos[b], pontos[c]), 0)
                pygame.draw.line(tela, (255, 230, 190), pontos[a], pontos[b], 1)
                pygame.draw.line(tela, (255, 230, 190), pontos[b], pontos[c], 1)
                pygame.draw.line(tela, (255, 230, 190), pontos[c], pontos[a], 1)
        texto = f"OBJ: modelo_robo.obj | Setas: órbita | W/S: distância {distancia:.1f}"
        tela.blit(fonte.render(texto, True, "white"), (20, 20))
        pygame.display.flip()
        relogio.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
