"""Exemplo didático: carregar e projetar um OBJ usando somente Pygame."""
import math
import pygame

LARGURA, ALTURA = 900, 650


def carregar_obj(nome):
    vertices, faces = [], []
    with open(nome, encoding="utf-8") as arquivo:
        for linha in arquivo:
            partes = linha.split()
            if not partes or partes[0].startswith("#"):
                continue
            if partes[0] == "v":
                vertices.append(tuple(float(valor) for valor in partes[1:4]))
            elif partes[0] == "f":
                indices = [int(item.split("/")[0]) - 1 for item in partes[1:]]
                for i in range(1, len(indices) - 1):
                    faces.append((indices[0], indices[i], indices[i + 1]))
    return vertices, faces


def girar_y(ponto, angulo):
    x, y, z = ponto
    c, s = math.cos(angulo), math.sin(angulo)
    return (c * x + s * z, y, -s * x + c * z)


def projetar(ponto, escala, centro):
    x, y, z = ponto
    fator = escala / max(1.0, z + 7.0)
    return (int(centro[0] + x * fator), int(centro[1] - y * fator))


def main():
    pygame.init()
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Exemplo OBJ — Torre")
    fonte = pygame.font.Font(None, 26)
    vertices, faces = carregar_obj("modelo_torre.obj")
    relogio, angulo = pygame.time.Clock(), 0.0
    executando = True
    while executando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                executando = False
        angulo += 0.01
        transformados = [girar_y(v, angulo) for v in vertices]
        pontos = [projetar(v, 230, (LARGURA // 2, ALTURA // 2 + 90)) for v in transformados]
        tela.fill((22, 27, 38))
        for a, b, c in faces:
            pygame.draw.polygon(tela, (90, 170, 220), (pontos[a], pontos[b], pontos[c]), 0)
            pygame.draw.line(tela, (220, 235, 245), pontos[a], pontos[b], 1)
            pygame.draw.line(tela, (220, 235, 245), pontos[b], pontos[c], 1)
            pygame.draw.line(tela, (220, 235, 245), pontos[c], pontos[a], 1)
        tela.blit(fonte.render("OBJ: modelo_torre.obj | ESC ou fechar para sair", True, "white"), (20, 20))
        pygame.display.flip()
        relogio.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
