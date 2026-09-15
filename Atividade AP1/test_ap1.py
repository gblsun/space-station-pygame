"""
Suíte de testes do AP1 — roda sem abrir janela.

    python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v

Cobre a matemática vetorial, o winding das malhas, a câmera look-at, o recorte
no plano próximo e o teste de interseção raio-esfera.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import ap1


def centroide(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n,
            sum(p[1] for p in pts) / n,
            sum(p[2] for p in pts) / n)


class TestMatematica(unittest.TestCase):

    def test_normalize_vetor_nulo(self):
        self.assertEqual(ap1.normalize((0, 0, 0)), (0.0, 0.0, 0.0))

    def test_normalize_unitario(self):
        self.assertAlmostEqual(ap1.length(ap1.normalize((3, -4, 12))), 1.0)

    def test_cross_ortogonal_aos_operandos(self):
        u, v = (1.0, 2.0, 3.0), (-4.0, 5.0, 6.0)
        n = ap1.cross_product(u, v)
        self.assertAlmostEqual(ap1.dot_product(n, u), 0.0)
        self.assertAlmostEqual(ap1.dot_product(n, v), 0.0)

    def test_rotacao_completa_e_identidade(self):
        p = (11.0, -3.0, 7.0)
        for eixo in ((360, 0, 0), (0, 360, 0), (0, 0, 360)):
            r = ap1.rotate_xyz(p, eixo)
            for a, b in zip(p, r):
                self.assertAlmostEqual(a, b, places=6)

    def test_rotacao_y_leva_x_para_menos_z(self):
        x, y, z = ap1.rotate_xyz((1.0, 0.0, 0.0), (0, 90, 0))
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 0.0, places=6)
        self.assertAlmostEqual(z, -1.0, places=6)

    def test_face_normal_degenerada(self):
        self.assertIsNone(ap1.face_normal([(0, 0, 0), (1, 1, 1), (2, 2, 2)]))

    def test_smoothstep_nos_extremos(self):
        self.assertAlmostEqual(ap1.smoothstep(-5.0), 0.0)
        self.assertAlmostEqual(ap1.smoothstep(0.5), 0.5)
        self.assertAlmostEqual(ap1.smoothstep(9.0), 1.0)


class TestRaioEsfera(unittest.TestCase):

    def test_acerto_frontal(self):
        t = ap1.ray_sphere((0, 0, 0), (0, 0, 1), (0, 0, 50), 10.0)
        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, 40.0, places=5)

    def test_erro_por_desvio_lateral(self):
        self.assertIsNone(ap1.ray_sphere((0, 0, 0), (0, 0, 1), (60, 0, 50), 10.0))

    def test_esfera_atras_da_origem(self):
        self.assertIsNone(ap1.ray_sphere((0, 0, 0), (0, 0, 1), (0, 0, -50), 10.0))

    def test_origem_dentro_da_esfera(self):
        t = ap1.ray_sphere((0, 0, 0), (1, 0, 0), (0, 0, 0), 25.0)
        self.assertAlmostEqual(t, 25.0, places=5)


class TestCamera(unittest.TestCase):

    def test_base_ortonormal_em_todos_os_presets(self):
        for chave in ap1.CAMERA_PRESETS:
            cam = ap1.Camera(chave)
            for eixo in (cam.right, cam.up, cam.forward):
                self.assertAlmostEqual(ap1.length(eixo), 1.0, places=6, msg=chave)
            self.assertAlmostEqual(ap1.dot_product(cam.right, cam.up), 0.0, places=6)
            self.assertAlmostEqual(ap1.dot_product(cam.right, cam.forward), 0.0, places=6)
            self.assertAlmostEqual(ap1.dot_product(cam.up, cam.forward), 0.0, places=6)

    def test_base_valida_olhando_reto_para_baixo(self):
        """Caso degenerado: forward paralelo ao WORLD_UP."""
        cam = ap1.Camera()
        cam.eye = [0.0, 500.0, 0.0]
        cam.target = [0.0, 0.0, 0.0]
        cam._rebuild_basis()
        for eixo in (cam.right, cam.up, cam.forward):
            self.assertAlmostEqual(ap1.length(eixo), 1.0, places=6)
        self.assertAlmostEqual(ap1.dot_product(cam.right, cam.up), 0.0, places=6)

    def test_alvo_projeta_no_centro_de_projecao(self):
        """O alvo cai no centro óptico, que é deslocado para baixo do HUD."""
        for chave in ap1.CAMERA_PRESETS:
            cam = ap1.Camera(chave)
            px, py = ap1.project_point(tuple(cam.target), cam)
            self.assertAlmostEqual(px, ap1.VIEW_CENTER_X, delta=1, msg=chave)
            self.assertAlmostEqual(py, ap1.VIEW_CENTER_Y, delta=1, msg=chave)

    def test_ponto_atras_tem_profundidade_negativa(self):
        cam = ap1.Camera("geral")
        atras = ap1.vec_sub(cam.eye, ap1.vec_scale(cam.forward, 100.0))
        self.assertLess(cam.to_view(atras)[2], 0.0)
        self.assertIsNone(ap1.project_point(atras, cam))

    def test_transicao_suave_aproxima_do_alvo(self):
        cam = ap1.Camera("geral")
        inicio = list(cam.eye)
        cam.go_to("direita")
        for _ in range(180):
            cam.update(1.0 / 60.0)
        for atual, meta in zip(cam.eye, cam.eye_goal):
            self.assertAlmostEqual(atual, meta, delta=1.0)
        self.assertNotEqual(inicio, list(cam.eye))


class TestRecorteNear(unittest.TestCase):

    def test_poligono_totalmente_atras_some(self):
        poly = [(0, 0, -10), (10, 0, -10), (10, 10, -20)]
        self.assertEqual(ap1.clip_near(poly), [])

    def test_poligono_totalmente_a_frente_intacto(self):
        poly = [(0, 0, 100), (10, 0, 100), (10, 10, 120)]
        self.assertEqual(ap1.clip_near(poly), poly)

    def test_poligono_atravessando_fica_no_plano(self):
        poly = [(0, 0, -50), (100, 0, 200), (100, 100, 200)]
        recortado = ap1.clip_near(poly)
        self.assertGreaterEqual(len(recortado), 3)
        for p in recortado:
            self.assertGreaterEqual(p[2], ap1.NEAR - 1e-6)


class TestGeometria(unittest.TestCase):
    """As normais precisam apontar para fora, ou o culling descarta o lado errado."""

    def assert_normais_para_fora(self, verts, faces, centro=(0.0, 0.0, 0.0), rotulo=""):
        for i, face in enumerate(faces):
            pts = [verts[k] for k in face]
            n = ap1.face_normal(pts)
            self.assertIsNotNone(n, msg="face degenerada %d em %s" % (i, rotulo))
            fora = ap1.vec_sub(centroide(pts), centro)
            self.assertGreater(ap1.dot_product(n, fora), 0.0,
                               msg="normal invertida na face %d de %s" % (i, rotulo))

    def test_caixa_tem_seis_faces_para_fora(self):
        b = ap1.MeshBuilder()
        b.add_box((-10, -20, -30), (10, 20, 30), (100, 100, 100))
        verts, faces, colors = b.data()
        self.assertEqual(len(faces), 6)
        self.assertEqual(len(colors), 6)
        self.assert_normais_para_fora(verts, faces, rotulo="caixa")

    def test_caixa_fora_da_origem(self):
        b = ap1.MeshBuilder()
        b.add_box((40, 5, -8), (60, 25, 8), (1, 2, 3))
        verts, faces, _ = b.data()
        self.assert_normais_para_fora(verts, faces, centro=(50.0, 15.0, 0.0),
                                      rotulo="caixa deslocada")

    def test_prisma_em_cada_eixo(self):
        for eixo in ("x", "y", "z"):
            b = ap1.MeshBuilder()
            b.add_prism(eixo, (0.0, 0.0, 0.0), 20.0, 55.0, 8, (90, 90, 90))
            verts, faces, _ = b.data()
            self.assertEqual(len(faces), 8 + 2)
            self.assert_normais_para_fora(verts, faces, rotulo="prisma " + eixo)

    def test_prisma_deslocado_e_conico(self):
        for eixo in ("x", "y", "z"):
            b = ap1.MeshBuilder()
            centro = (12.0, -7.0, 33.0)
            b.add_prism(eixo, centro, 18.0, 30.0, 7, (90, 90, 90), taper=0.0)
            verts, faces, _ = b.data()
            self.assertEqual(len(faces), 7 + 1)   # cone: lados + uma tampa
            self.assert_normais_para_fora(verts, faces, centro=centro,
                                          rotulo="cone " + eixo)

    def test_esfera_sem_faces_degeneradas(self):
        verts, faces, colors = ap1.build_sphere(100.0, rings=9, sectors=14)
        self.assertEqual(len(faces), len(colors))
        self.assert_normais_para_fora(verts, faces, rotulo="esfera")

    def test_esfera_polos_unicos(self):
        verts, _, _ = ap1.build_sphere(50.0, rings=6, sectors=10)
        self.assertEqual(len(verts), 2 + (6 - 1) * 10)

    def test_detritos_sao_malhas_diferentes(self):
        a = ap1.build_debris(11, 30.0)[0]
        b = ap1.build_debris(22, 30.0)[0]
        self.assertEqual(len(a), len(b))
        self.assertNotEqual(a, b)

    def test_detrito_nao_mexe_no_random_global(self):
        """Regressão: build_asteroid chamava random.seed(42) global."""
        import random
        random.seed(123)
        esperado = [random.random() for _ in range(5)]
        random.seed(123)
        ap1.build_debris(7, 25.0)
        ap1.build_debris(8, 25.0)
        self.assertEqual([random.random() for _ in range(5)], esperado)

    def test_builders_com_indices_validos(self):
        construtores = {
            "estação": ap1.build_station_core(),
            "porta_inf": ap1.build_door_leaf(True),
            "porta_sup": ap1.build_door_leaf(False),
            "cargueiro": ap1.build_cargo_ship(),
            "laboratorio": ap1.build_lab_module(),
            "satelite": ap1.build_satellite(),
            "robo_corpo": ap1.build_robot_body((200, 120, 40)),
            "robo_braco": ap1.build_robot_arm((200, 120, 40), 34.0),
            "robo_garra": ap1.build_robot_arm((200, 120, 40), 26.0, garra=True),
            "detrito": ap1.build_debris(3, 40.0),
            "detrito_lod": ap1.build_debris(4, 40.0, rings=6, sectors=9),
            "planeta": ap1.build_sphere(200.0),
        }
        for nome, (verts, faces, colors) in construtores.items():
            self.assertGreater(len(verts), 3, msg=nome)
            self.assertEqual(len(faces), len(colors), msg=nome)
            for face in faces:
                self.assertGreaterEqual(len(face), 3, msg=nome)
                for i in face:
                    self.assertTrue(0 <= i < len(verts), msg=nome)

    def test_builders_sem_faces_degeneradas(self):
        for nome, (verts, faces, _) in (
            ("estação", ap1.build_station_core()),
            ("cargueiro", ap1.build_cargo_ship()),
            ("laboratorio", ap1.build_lab_module()),
            ("satelite", ap1.build_satellite()),
            ("robo_corpo", ap1.build_robot_body((200, 120, 40))),
            ("robo_braco", ap1.build_robot_arm((200, 120, 40), 30.0, garra=True)),
        ):
            for i, face in enumerate(faces):
                pts = [verts[k] for k in face]
                self.assertIsNotNone(ap1.face_normal(pts),
                                     msg="face %d degenerada em %s" % (i, nome))


class TestPolyMesh(unittest.TestCase):

    def malha_cubo(self):
        b = ap1.MeshBuilder()
        b.add_box((-10, -10, -10), (10, 10, 10), (200, 200, 200))
        return ap1.PolyMesh(*b.data(), position=(0, 0, 400))

    def test_raio_envolvente_acompanha_escala(self):
        m = self.malha_cubo()
        r0 = m.bounding_radius
        m.update(scale=2.0)
        self.assertAlmostEqual(m.bounding_radius, r0 * 2.0)

    def test_transformacao_aplica_escala_e_translacao(self):
        m = self.malha_cubo()
        m.update(scale=3.0)
        for v in m.world_vertices():
            self.assertAlmostEqual(abs(v[0]), 30.0)
            self.assertAlmostEqual(abs(v[1]), 30.0)
            self.assertAlmostEqual(abs(v[2] - 400.0), 30.0)

    def test_culling_descarta_metade_das_faces_de_um_cubo(self):
        """De um cubo convexo, no máximo 3 das 6 faces podem estar visíveis."""
        cam = ap1.Camera("geral")
        m = self.malha_cubo()
        m.update(pos=(cam.eye[0], cam.eye[1], cam.eye[2] + 300.0))
        visiveis, descartadas = m.collect(cam)
        self.assertLessEqual(len(visiveis), 3)
        self.assertEqual(len(visiveis) + descartadas, 6)

    def test_malha_invisivel_nao_gera_faces(self):
        m = self.malha_cubo()
        m.visible = False
        self.assertEqual(m.collect(ap1.Camera("geral")), ([], 0))


class TestMaquinaDeEstados(unittest.TestCase):

    def setUp(self):
        self.cena = ap1.Scene()

    def test_ciclo_iniciar_pausar_retomar(self):
        self.assertEqual(self.cena.state, ap1.STATE_PARADO)
        self.assertEqual(self.cena.toggle(), ap1.STATE_EXECUTANDO)
        self.assertEqual(self.cena.toggle(), ap1.STATE_PAUSADO)
        self.assertEqual(self.cena.toggle(), ap1.STATE_EXECUTANDO)

    def test_pausado_nao_avanca_o_tempo(self):
        self.cena.toggle()
        for _ in range(60):
            self.cena.update(1.0 / 60.0)
        marcado = self.cena.sim_time
        self.cena.toggle()                      # pausa
        for _ in range(60):
            self.cena.update(1.0 / 60.0)
        self.assertAlmostEqual(self.cena.sim_time, marcado, places=6)

    def test_conclui_e_nao_ultrapassa_o_total(self):
        self.cena.toggle()
        for _ in range(int(20 * 60)):
            self.cena.update(1.0 / 60.0)
        self.assertEqual(self.cena.state, ap1.STATE_CONCLUIDO)
        self.assertAlmostEqual(self.cena.sim_time, ap1.TOTAL_SEQUENCE_TIME)
        self.assertAlmostEqual(self.cena.progress, 1.0)

    def test_espaco_no_final_reinicia_a_sequencia(self):
        self.cena.state = ap1.STATE_CONCLUIDO
        self.cena.sim_time = ap1.TOTAL_SEQUENCE_TIME
        self.assertEqual(self.cena.toggle(), ap1.STATE_EXECUTANDO)
        self.assertEqual(self.cena.sim_time, 0.0)

    def test_reset_restaura_as_poses_iniciais(self):
        def instantaneo():
            return [(tuple(m.pos), tuple(m.rotation), m.scale) for m in self.cena.meshes]
        inicial = instantaneo()
        self.cena.toggle()
        for _ in range(300):
            self.cena.update(1.0 / 60.0)
        self.assertNotEqual(instantaneo(), inicial)
        self.cena.reset()
        self.assertEqual(self.cena.state, ap1.STATE_PARADO)
        self.assertEqual(self.cena.sim_time, 0.0)
        self.assertEqual(self.cena.particles.particles, [])
        for (pa, ra, sa), (pb, rb, sb) in zip(inicial, instantaneo()):
            for a, b in zip(pa + ra, pb + rb):
                self.assertAlmostEqual(a, b, places=9)
            self.assertAlmostEqual(sa, sb, places=9)

    def test_rotulo_de_fase_reflete_o_estado(self):
        self.assertIn("espera", self.cena.phase_label)
        self.cena.toggle()
        self.cena.update(0.5)
        self.assertEqual(self.cena.phase_label, ap1.PHASE_NAMES[0])
        self.cena.state = ap1.STATE_CONCLUIDO
        self.assertIn("concluída", self.cena.phase_label)


class TestFases(unittest.TestCase):

    def setUp(self):
        self.cena = ap1.Scene()

    def test_indice_de_fase_por_instante(self):
        esperado = [(0.0, 0), (3.9, 0), (4.1, 1), (6.9, 1),
                    (7.1, 2), (9.9, 2), (10.1, 3), (14.0, 3)]
        for t, indice in esperado:
            self.cena.sim_time = t
            self.assertEqual(self.cena.phase_index, indice, msg="t=%.1f" % t)

    def test_goto_phase_posiciona_o_tempo(self):
        for n, t in ((1, 0.0), (2, ap1.PHASE_BOUNDS[0]),
                     (3, ap1.PHASE_BOUNDS[1]), (4, ap1.PHASE_BOUNDS[2])):
            self.cena.goto_phase(n)
            self.assertAlmostEqual(self.cena.sim_time, t)
            self.assertEqual(self.cena.state, ap1.STATE_EXECUTANDO)
            self.assertEqual(self.cena.phase_index, n - 1)

    def test_goto_phase_fora_da_faixa_e_limitado(self):
        self.assertEqual(self.cena.goto_phase(0), 1)
        self.assertEqual(self.cena.goto_phase(99), len(ap1.PHASE_BOUNDS))

    def test_cargueiro_avanca_monotonicamente_ate_acoplar(self):
        anterior = self.cena.cargo_x(0.0)
        t = 0.0
        while t <= ap1.TOTAL_SEQUENCE_TIME:
            atual = self.cena.cargo_x(t)
            self.assertLessEqual(atual, anterior + 1e-9, msg="recuou em t=%.2f" % t)
            anterior = atual
            t += 0.05
        self.assertAlmostEqual(self.cena.cargo_x(ap1.TOTAL_SEQUENCE_TIME), ap1.CARGO_X[-1])


class TestComportaEBalizas(unittest.TestCase):

    def setUp(self):
        self.cena = ap1.Scene()

    def test_sequencia_dos_quatro_estados(self):
        esperado = [(1.0, ap1.DOOR_CLOSED), (5.0, ap1.DOOR_OPENING),
                    (7.0, ap1.DOOR_OPEN), (9.0, ap1.DOOR_CLOSING),
                    (12.0, ap1.DOOR_CLOSED)]
        for t, estado in esperado:
            self.assertEqual(self.cena.door.set_from_time(t), estado, msg="t=%.1f" % t)

    def test_abertura_e_monotonica_enquanto_abre(self):
        anterior = -1.0
        t = ap1.DOOR_OPEN_START
        while t <= ap1.DOOR_OPEN_END:
            self.cena.door.set_from_time(t)
            self.assertGreaterEqual(self.cena.door.opening, anterior)
            anterior = self.cena.door.opening
            t += 0.05
        self.assertAlmostEqual(anterior, 1.0, places=3)

    def test_folhas_se_afastam_ao_abrir(self):
        self.cena.apply_animation(1.0)
        fechada = abs(self.cena.door_hi.pos[1] - self.cena.door_lo.pos[1])
        self.cena.apply_animation(7.0)
        aberta = abs(self.cena.door_hi.pos[1] - self.cena.door_lo.pos[1])
        self.assertGreater(aberta, fechada + 40.0)

    def test_alerta_percorre_todas_as_balizas(self):
        vistos = set()
        for k in range(60):
            vistos.add(self.cena.beacons.set_from_time(k * 0.25, acoplado=False))
        self.assertEqual(vistos, set(range(ap1.AlertBeacons.COUNT)))

    def test_balizas_ficam_verdes_apos_o_acoplamento(self):
        self.cena.apply_animation(2.0)
        self.assertEqual(self.cena.beacons.color, ap1.AlertBeacons.AMBER)
        self.cena.apply_animation(ap1.PHASE_BOUNDS[1] + 0.1)
        self.assertEqual(self.cena.beacons.color, ap1.AlertBeacons.GREEN)


class TestLinhaDeVisao(unittest.TestCase):
    """Requisito 9: teste de interseção aplicado durante a animação."""

    def setUp(self):
        self.cena = ap1.Scene()

    def test_alvo_muda_de_cargueiro_para_robos(self):
        self.cena.sim_time = 2.0
        self.cena.apply_animation(2.0)
        self.assertEqual([s["alvo"] for s in self.cena.line_of_sight()],
                         [self.cena.cargo.name])
        self.cena.sim_time = 12.0
        self.cena.apply_animation(12.0)
        self.assertEqual([s["alvo"] for s in self.cena.line_of_sight()],
                         [r.name for r in self.cena.robots])

    def test_detrito_no_caminho_bloqueia_a_linha(self):
        self.cena.sim_time = 1.0
        self.cena.apply_animation(1.0)
        self.assertTrue(self.cena.line_of_sight()[0]["livre"])
        origem = self.cena.to_world(ap1.SENSOR_LOCAL, 1.0)
        meio = tuple((origem[k] + self.cena.cargo.pos[k]) * 0.5 for k in range(3))
        self.cena.debris[0].update(pos=meio)
        linha = self.cena.line_of_sight()[0]
        self.assertFalse(linha["livre"])
        self.assertEqual(linha["bloqueador"], "Detrito A")

    def test_ponto_de_impacto_fica_entre_origem_e_alvo(self):
        self.cena.sim_time = 1.0
        self.cena.apply_animation(1.0)
        origem = self.cena.to_world(ap1.SENSOR_LOCAL, 1.0)
        meio = tuple((origem[k] + self.cena.cargo.pos[k]) * 0.5 for k in range(3))
        self.cena.debris[0].update(pos=meio)
        linha = self.cena.line_of_sight()[0]
        percorrido = ap1.length(ap1.vec_sub(linha["ponto"], origem))
        self.assertGreater(percorrido, 0.0)
        self.assertLess(percorrido, linha["dist"])


class TestEvitacaoDeColisao(unittest.TestCase):

    def test_ponto_dentro_do_cilindro_e_empurrado(self):
        alvo, desviou = ap1.Scene._avoid_mast((ap1.MAST_X + 5.0, 90.0, ap1.MAST_Z))
        self.assertTrue(desviou)
        raio = math.hypot(alvo[0] - ap1.MAST_X, alvo[2] - ap1.MAST_Z)
        self.assertAlmostEqual(raio, ap1.MAST_SAFE_RADIUS, places=6)
        self.assertAlmostEqual(alvo[1], 90.0)

    def test_ponto_fora_do_cilindro_nao_muda(self):
        p = (ap1.MAST_X + 200.0, 90.0, ap1.MAST_Z)
        self.assertEqual(ap1.Scene._avoid_mast(p), (p, False))

    def test_ponto_abaixo_do_mastro_nao_muda(self):
        p = (ap1.MAST_X, -50.0, ap1.MAST_Z)
        self.assertEqual(ap1.Scene._avoid_mast(p), (p, False))

    def test_centro_exato_do_mastro_nao_divide_por_zero(self):
        alvo, desviou = ap1.Scene._avoid_mast((ap1.MAST_X, 90.0, ap1.MAST_Z))
        self.assertTrue(desviou)
        raio = math.hypot(alvo[0] - ap1.MAST_X, alvo[2] - ap1.MAST_Z)
        self.assertAlmostEqual(raio, ap1.MAST_SAFE_RADIUS, places=6)


class TestRenderizacao(unittest.TestCase):
    """Desenha fora da tela: confirma que cada câmera produz imagem."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.Surface((ap1.WIDTH, ap1.HEIGHT))

    def cena_em(self, t):
        cena = ap1.Scene()
        cena.state = ap1.STATE_EXECUTANDO
        for _ in range(int(round(t * 60))):
            cena.update(1.0 / 60.0)
        return cena

    def assert_desenhou_algo(self, rotulo):
        media = pygame.transform.average_color(self.surface)
        self.assertGreater(sum(media[:3]), sum(ap1.BG_COLOR),
                           msg="tela praticamente vazia em %s" % rotulo)

    def test_todas_as_cameras_produzem_imagem(self):
        cena = self.cena_em(12.0)
        renderer = ap1.Renderer()
        for chave in ap1.CAMERA_PRESETS:
            cena.camera.snap_to(chave)
            renderer.draw(self.surface, cena)
            self.assertGreater(renderer.faces_desenhadas, 40, msg=chave)
            self.assert_desenhou_algo(chave)

    def test_camera_de_foco_acompanha_o_cargueiro(self):
        cena = self.cena_em(2.0)
        cena.camera.follow(cena.cargo)
        for _ in range(120):
            cena.update(1.0 / 60.0)
        for eixo in range(3):
            self.assertAlmostEqual(cena.camera.target[eixo], cena.cargo.pos[eixo], delta=30.0)
        ap1.Renderer().draw(self.surface, cena)
        self.assert_desenhou_algo("foco")

    def test_culling_descarta_parte_relevante_das_faces(self):
        cena = self.cena_em(6.0)
        renderer = ap1.Renderer()
        renderer.draw(self.surface, cena)
        total = renderer.faces_desenhadas + renderer.faces_descartadas
        self.assertGreater(renderer.faces_descartadas, total * 0.3)

    def test_hud_desenha_nos_tres_modos(self):
        cena = self.cena_em(5.0)
        renderer = ap1.Renderer()
        renderer.draw(self.surface, cena)
        hud = ap1.Hud()
        for creditos, debug in ((False, False), (False, True), (True, False)):
            hud.show_credits, hud.show_debug = creditos, debug
            hud.draw(self.surface, cena, renderer)
        self.assert_desenhou_algo("hud")

    def test_hud_reporta_bloqueio_do_sensor(self):
        cena = self.cena_em(1.0)
        origem = cena.to_world(ap1.SENSOR_LOCAL, cena.sim_time)
        meio = tuple((origem[k] + cena.cargo.pos[k]) * 0.5 for k in range(3))
        cena.debris[0].update(pos=meio)
        cena.sight = cena.line_of_sight()
        texto, _ = ap1.Hud._sensor_text(cena)
        self.assertIn("BLOQUEADA", texto)


class TestRoteiroDoChecklist(unittest.TestCase):
    """
    Roteiro exigido no checklist do enunciado: iniciar, pausar, retomar,
    reiniciar, alternar câmera, concluir a sequência e encerrar.
    """

    def setUp(self):
        self.app = ap1.App(surface=pygame.Surface((ap1.WIDTH, ap1.HEIGHT)))

    def tecla(self, key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_iniciar_pausar_retomar(self):
        self.tecla(pygame.K_SPACE)
        self.assertEqual(self.app.scene.state, ap1.STATE_EXECUTANDO)
        self.tecla(pygame.K_SPACE)
        self.assertEqual(self.app.scene.state, ap1.STATE_PAUSADO)
        self.tecla(pygame.K_SPACE)
        self.assertEqual(self.app.scene.state, ap1.STATE_EXECUTANDO)

    def test_reiniciar(self):
        self.tecla(pygame.K_SPACE)
        for _ in range(120):
            self.app.step(1.0 / 60.0)
        self.tecla(pygame.K_r)
        self.assertEqual(self.app.scene.state, ap1.STATE_PARADO)
        self.assertEqual(self.app.scene.sim_time, 0.0)

    def test_alternar_todas_as_cameras(self):
        for key, chave in ap1.CAMERA_KEYS.items():
            self.tecla(key)
            self.assertEqual(self.app.scene.camera.key, chave)
        self.tecla(pygame.K_f)
        self.assertEqual(self.app.scene.camera.key, ap1.FOLLOW_CAMERA)
        self.assertIs(self.app.scene.camera.follow_mesh, self.app.scene.cargo)

    def test_alternar_fases_pelas_teclas(self):
        for key, numero in ap1.PHASE_KEYS.items():
            self.tecla(key)
            self.assertEqual(self.app.scene.phase_index, numero - 1)

    def test_creditos_e_painel_de_dados(self):
        self.tecla(pygame.K_TAB)
        self.assertTrue(self.app.hud.show_credits)
        self.app.step(1.0 / 60.0)
        self.tecla(pygame.K_TAB)
        self.assertFalse(self.app.hud.show_credits)
        self.tecla(pygame.K_h)
        self.assertTrue(self.app.hud.show_debug)
        self.app.step(1.0 / 60.0)

    def test_concluir_a_sequencia_desenhando_todos_os_quadros(self):
        self.tecla(pygame.K_SPACE)
        for _ in range(int(ap1.TOTAL_SEQUENCE_TIME * 60) + 30):
            self.app.step(1.0 / 60.0)
        self.assertEqual(self.app.scene.state, ap1.STATE_CONCLUIDO)

    def test_encerrar_por_esc_e_por_quit(self):
        self.tecla(pygame.K_ESCAPE)
        self.assertFalse(self.app.running)
        outro = ap1.App(surface=pygame.Surface((ap1.WIDTH, ap1.HEIGHT)))
        outro.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(outro.running)


class TestCacheDeVertices(unittest.TestCase):
    """
    O cache de `world_vertices` é a otimização com maior risco de bug: se a
    invalidação falhar, a cena desenha a pose do quadro anterior.
    """

    def malha(self):
        b = ap1.MeshBuilder()
        b.add_box((-10, -10, -10), (10, 10, 10), (200, 200, 200))
        return ap1.PolyMesh(*b.data(), position=(0, 0, 400))

    def test_sem_mudanca_reutiliza_o_resultado(self):
        m = self.malha()
        self.assertIs(m.world_vertices(), m.world_vertices())

    def test_mudar_posicao_invalida(self):
        m = self.malha()
        antes = m.world_vertices()[0]
        m.update(pos=(50, 0, 400))
        self.assertAlmostEqual(m.world_vertices()[0][0], antes[0] + 50.0)

    def test_mudar_rotacao_invalida(self):
        m = self.malha()
        antes = list(m.world_vertices())
        m.update(rot=(0, 37, 0))
        self.assertNotEqual(list(m.world_vertices()), antes)

    def test_mudar_escala_invalida(self):
        m = self.malha()
        m.update(scale=2.0)
        for v in m.world_vertices():
            self.assertAlmostEqual(abs(v[0]), 20.0)

    def test_atribuicao_direta_tambem_invalida(self):
        """Mexer em `pos` sem passar por update() não pode furar o cache."""
        m = self.malha()
        m.world_vertices()
        m.pos[1] = 123.0
        self.assertAlmostEqual(m.world_vertices()[0][1], -10.0 + 123.0)

    def test_matriz_de_rotacao_bate_com_rotate_xyz(self):
        """A composição por vetores da base deve dar o mesmo que rotacionar ponto a ponto."""
        rot = (23.0, -47.0, 61.0)
        m = self.malha()
        m.update(pos=(0, 0, 0), rot=rot, scale=1.7)
        for base, mundo in zip(m.base_vertices, m.world_vertices()):
            esperado = ap1.rotate_xyz(tuple(c * 1.7 for c in base), rot)
            for a, b in zip(esperado, mundo):
                self.assertAlmostEqual(a, b, places=9)


class TestFrustumCulling(unittest.TestCase):

    def malha_em(self, pos, raio=30.0):
        b = ap1.MeshBuilder()
        b.add_box((-raio, -raio, -raio), (raio, raio, raio), (150, 150, 150))
        return ap1.PolyMesh(*b.data(), position=pos)

    def test_objeto_no_centro_do_quadro_e_mantido(self):
        cam = ap1.Camera("geral")
        m = self.malha_em(tuple(cam.target))
        self.assertTrue(m.in_frustum(cam))

    def test_objeto_atras_da_camera_e_descartado(self):
        cam = ap1.Camera("geral")
        atras = ap1.vec_sub(cam.eye, ap1.vec_scale(cam.forward, 500.0))
        m = self.malha_em(atras)
        self.assertFalse(m.in_frustum(cam))
        self.assertEqual(m.collect(cam), ([], len(m.faces)))

    def test_objeto_muito_a_esquerda_e_descartado(self):
        cam = ap1.Camera("geral")
        fora = ap1.vec_add(ap1.vec_add(cam.eye, ap1.vec_scale(cam.forward, 400.0)),
                           ap1.vec_scale(cam.right, -3000.0))
        self.assertFalse(self.malha_em(fora).in_frustum(cam))

    def test_objeto_grande_na_borda_nao_e_descartado(self):
        """A esfera envolvente precisa segurar objetos que só cruzam a borda."""
        cam = ap1.Camera("geral")
        borda = ap1.vec_add(ap1.vec_add(cam.eye, ap1.vec_scale(cam.forward, 400.0)),
                            ap1.vec_scale(cam.right, 360.0))
        self.assertTrue(self.malha_em(borda, raio=300.0).in_frustum(cam))

    def test_frustum_distingue_malha_inteira_dentro_de_malha_na_borda(self):
        cam = ap1.Camera("geral")
        frente = ap1.vec_add(cam.eye, ap1.vec_scale(cam.forward, 400.0))
        self.assertEqual(self.malha_em(frente, raio=20.0).frustum_test(cam), 2)
        borda = ap1.vec_add(frente, ap1.vec_scale(cam.right, 360.0))
        self.assertEqual(self.malha_em(borda, raio=300.0).frustum_test(cam), 1)

    def test_faces_projetadas_fora_da_janela_sao_descartadas(self):
        """Regressão: a esfera cruzava a borda e faces sem nenhum pixel na tela eram desenhadas."""
        cam = ap1.Camera("geral")
        pos = ap1.vec_add(ap1.vec_add(cam.eye, ap1.vec_scale(cam.forward, 400.0)),
                          ap1.vec_scale(cam.right, 560.0))
        m = self.malha_em(pos, raio=100.0)
        self.assertEqual(m.frustum_test(cam), 1)
        self.assertEqual(m.collect(cam), ([], len(m.faces)))

    def test_faces_gigantes_sao_recortadas_na_margem_da_janela(self):
        """Regressão: faces junto ao plano próximo projetavam para dezenas de milhares de pixels."""
        cam = ap1.Camera("geral")
        borda = ap1.vec_add(ap1.vec_add(cam.eye, ap1.vec_scale(cam.forward, 400.0)),
                            ap1.vec_scale(cam.right, 360.0))
        visiveis, _ = self.malha_em(borda, raio=300.0).collect(cam)
        self.assertTrue(visiveis)
        g = ap1.SCREEN_GUARD
        for _, pontos, _ in visiveis:
            for x, y in pontos:
                self.assertTrue(-g <= x <= ap1.WIDTH + g and -g <= y <= ap1.HEIGHT + g, (x, y))

    def test_recorte_de_tela_limita_poligono_gigante(self):
        g = ap1.SCREEN_GUARD
        recortado = ap1.clip_screen([(-30000, -20000), (30000, -20000),
                                     (30000, 20000), (-30000, 20000)])
        self.assertEqual(sorted(recortado), sorted([(-g, -g), (ap1.WIDTH + g, -g),
                                                    (ap1.WIDTH + g, ap1.HEIGHT + g),
                                                    (-g, ap1.HEIGHT + g)]))

    def test_recorte_de_tela_preserva_poligono_dentro_da_janela(self):
        poly = [(10, 10), (200, 10), (200, 150), (10, 150)]
        self.assertEqual(ap1.clip_screen(poly), poly)

    def test_toda_a_cena_fica_visivel_no_plano_geral(self):
        cena = ap1.Scene()
        cena.camera.snap_to("geral")
        for m in cena.meshes:
            self.assertTrue(m.in_frustum(cena.camera), msg=m.name)


class TestDetalheDasMalhas(unittest.TestCase):
    """DETAIL é a válvula de calibração: precisa gerar malha válida em qualquer nível."""

    def tearDown(self):
        ap1.DETAIL = 1.0

    def test_resolucao_respeita_o_minimo(self):
        ap1.DETAIL = 0.01
        self.assertEqual(ap1.resolucao(20), 3)
        self.assertEqual(ap1.resolucao(20, minimo=6), 6)

    def test_malhas_validas_em_varios_niveis(self):
        for nivel in (0.5, 1.0, 1.8):
            ap1.DETAIL = nivel
            b = ap1.MeshBuilder()
            b.add_prism("x", (0.0, 0.0, 0.0), 20.0, 40.0, 8, (90, 90, 90))
            verts, faces, cores = b.data()
            self.assertEqual(len(faces), len(cores))
            for i, face in enumerate(faces):
                pts = [verts[k] for k in face]
                n = ap1.face_normal(pts)
                self.assertIsNotNone(n, msg="nivel %.1f face %d" % (nivel, i))
                fora = centroide(pts)
                self.assertGreater(ap1.dot_product(n, fora), 0.0,
                                   msg="nivel %.1f face %d" % (nivel, i))

    def test_detalhe_maior_gera_mais_faces(self):
        ap1.DETAIL = 0.6
        poucas = len(ap1.build_sphere(50.0, rings=10, sectors=16)[1])
        ap1.DETAIL = 1.6
        muitas = len(ap1.build_sphere(50.0, rings=10, sectors=16)[1])
        self.assertGreater(muitas, poucas * 2)


class TestCacheDeTextoDoHud(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_texto_igual_reaproveita_a_superficie(self):
        hud = ap1.Hud()
        a = hud.txt(hud.font, "Órbita-2", True, (255, 255, 255))
        b = hud.txt(hud.font, "Órbita-2", True, (255, 255, 255))
        self.assertIs(a, b)

    def test_texto_ou_cor_diferente_gera_outra(self):
        hud = ap1.Hud()
        a = hud.txt(hud.font, "Fase 1", True, (255, 255, 255))
        self.assertIsNot(a, hud.txt(hud.font, "Fase 2", True, (255, 255, 255)))
        self.assertIsNot(a, hud.txt(hud.font, "Fase 1", True, (200, 0, 0)))

    def test_cache_nao_cresce_sem_limite(self):
        hud = ap1.Hud()
        for i in range(600):
            hud.txt(hud.font, "linha %d" % i, True, (255, 255, 255))
        self.assertLessEqual(len(hud._texto_cache), 401)


class TestModoDeObservacao(unittest.TestCase):
    """Repetição contínua, órbita estendida e controle de velocidade."""

    def setUp(self):
        self.cena = ap1.Scene()

    def test_repeticao_emenda_os_ciclos_sem_concluir(self):
        self.cena.toggle_loop()
        self.cena.state = ap1.STATE_EXECUTANDO
        for _ in range(int(40 * 60)):
            self.cena.update(1.0 / 60.0)
        self.assertEqual(self.cena.state, ap1.STATE_EXECUTANDO)
        self.assertGreaterEqual(self.cena.cycles, 2)
        self.assertLess(self.cena.sim_time, self.cena.total_time)

    def test_sem_repeticao_a_sequencia_conclui(self):
        self.cena.state = ap1.STATE_EXECUTANDO
        for _ in range(int(20 * 60)):
            self.cena.update(1.0 / 60.0)
        self.assertEqual(self.cena.state, ap1.STATE_CONCLUIDO)
        self.assertEqual(self.cena.cycles, 0)

    def test_ligar_repeticao_no_final_retoma(self):
        self.cena.state = ap1.STATE_CONCLUIDO
        self.cena.sim_time = self.cena.total_time
        self.cena.toggle_loop()
        self.assertEqual(self.cena.state, ap1.STATE_EXECUTANDO)
        self.assertEqual(self.cena.sim_time, 0.0)

    def test_orbita_estendida_alonga_apenas_a_ultima_fase(self):
        normal = self.cena.phase_bounds
        self.cena.toggle_extended_orbit()
        estendida = self.cena.phase_bounds
        self.assertEqual(normal[:-1], estendida[:-1])
        self.assertGreater(estendida[-1], normal[-1])
        self.assertAlmostEqual(estendida[-1] - estendida[-2], ap1.EXTENDED_ORBIT_TIME)

    def test_orbita_estendida_da_tres_voltas_ao_robo_de_referencia(self):
        self.cena.toggle_extended_orbit()
        duracao = self.cena.total_time - ap1.PHASE_BOUNDS[-2]
        veloc = self.cena.robots[0].params[2]          # 1 rad/s, o de referência
        voltas = duracao * veloc / (2.0 * math.pi)
        self.assertAlmostEqual(voltas, ap1.ORBIT_TURNS, places=6)

    def test_desligar_orbita_estendida_nao_deixa_o_tempo_fora_da_faixa(self):
        self.cena.toggle_extended_orbit()
        self.cena.sim_time = self.cena.total_time - 0.5
        self.cena.toggle_extended_orbit()
        self.assertLessEqual(self.cena.sim_time, self.cena.total_time)

    def test_velocidade_escala_o_avanco_e_respeita_os_limites(self):
        self.assertEqual(self.cena.speed, 1.0)
        self.cena.change_speed(-99)
        self.assertEqual(self.cena.speed, ap1.SPEED_STEPS[0])
        self.cena.change_speed(99)
        self.assertEqual(self.cena.speed, ap1.SPEED_STEPS[-1])
        self.cena.speed_index = ap1.DEFAULT_SPEED_INDEX
        self.cena.change_speed(1)
        self.cena.state = ap1.STATE_EXECUTANDO
        self.cena.update(1.0)
        self.assertAlmostEqual(self.cena.sim_time, self.cena.speed)

    def test_ambiente_avanca_mesmo_com_a_sequencia_parada(self):
        """O relógio do ambiente não para: senão a estação congela na pausa."""
        antes = self.cena.anim_time
        for _ in range(60):
            self.cena.update(1.0 / 60.0)
        self.assertGreater(self.cena.anim_time, antes)
        self.assertEqual(self.cena.sim_time, 0.0)

    def test_ciclo_nao_salta_a_pose_da_estacao(self):
        """O ambiente usa relógio contínuo, então o laço emenda sem pulo."""
        self.cena.toggle_loop()
        self.cena.state = ap1.STATE_EXECUTANDO
        self.cena.sim_time = self.cena.total_time - 1.0 / 60.0
        antes = tuple(self.cena.station.rotation)
        self.cena.update(1.0 / 60.0)
        self.cena.update(1.0 / 60.0)
        self.assertEqual(self.cena.cycles, 1)
        depois = tuple(self.cena.station.rotation)
        self.assertLess(abs(depois[0] - antes[0]), 1.0)

    def test_reset_zera_ciclos_e_relogio_do_ambiente(self):
        self.cena.toggle_loop()
        self.cena.state = ap1.STATE_EXECUTANDO
        for _ in range(int(35 * 60)):
            self.cena.update(1.0 / 60.0)
        self.assertGreater(self.cena.cycles, 0)
        self.cena.reset()
        self.assertEqual(self.cena.cycles, 0)
        self.assertEqual(self.cena.anim_time, 0.0)
        self.assertTrue(self.cena.loop)          # preferência de visualização permanece


class TestEfeitosVisuais(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.Surface((ap1.WIDTH, ap1.HEIGHT))

    def test_halo_reaproveita_sprite_do_cache(self):
        glow = ap1.GlowSprites()
        a, _ = glow.sprite(40, (255, 180, 40), 0.5, 2.0)
        b, _ = glow.sprite(40, (255, 180, 40), 0.5, 2.0)
        self.assertIs(a, b)

    def test_halo_quantiza_raios_proximos(self):
        glow = ap1.GlowSprites()
        a, ra = glow.sprite(40, (255, 180, 40), 0.5, 2.0)
        b, rb = glow.sprite(41, (255, 180, 40), 0.5, 2.0)
        self.assertEqual(ra, rb)
        self.assertIs(a, b)

    def test_halo_clareia_o_fundo_sem_saturar(self):
        """A soma aditiva precisa da cor pré-multiplicada, senão vira disco chapado."""
        fundo = pygame.Surface((80, 80))
        fundo.fill((0, 0, 0))
        ap1.GlowSprites().blit(fundo, (40, 40), 30, (200, 120, 40))
        centro = fundo.get_at((40, 40))
        meio = fundo.get_at((40, 22))
        borda = fundo.get_at((40, 6))
        self.assertGreater(sum(centro[:3]), sum(meio[:3]))
        self.assertGreater(sum(meio[:3]), sum(borda[:3]))

    def test_halo_gigante_tem_memoria_limitada(self):
        """Regressão: um astro colado ao plano próximo pedia um sprite de dezenas de GB."""
        glow = ap1.GlowSprites()
        fundo = pygame.Surface((ap1.WIDTH, ap1.HEIGHT))
        fundo.fill((0, 0, 0))
        centro = (ap1.WIDTH // 2, ap1.HEIGHT // 2)
        glow.blit(fundo, centro, 200000, (255, 214, 128))
        self.assertGreater(sum(fundo.get_at(centro)[:3]), 0)
        for sprite in glow._cache.values():
            self.assertLessEqual(sprite.get_width(), 2 * ap1.GlowSprites.RAIO_BASE)

    def test_halo_fora_da_tela_nao_cria_sprite(self):
        glow = ap1.GlowSprites()
        glow.blit(self.surface, (-5000, -5000), 300, (255, 180, 40))
        self.assertEqual(glow._cache, {})

    def test_cache_de_halos_respeita_orcamento(self):
        glow = ap1.GlowSprites()
        for i in range(40):                   # 40 sprites de ~1 MB contra teto de 32 MB
            glow.sprite(ap1.GlowSprites.RAIO_BASE, (255, 180, 40), 0.3 + i * 0.01, 2.0)
        self.assertLessEqual(glow._bytes, ap1.GlowSprites.ORCAMENTO)
        self.assertLess(len(glow._cache), 40)
        self.assertEqual(glow._bytes, sum(s.get_width() * s.get_height() * 4
                                          for s in glow._cache.values()))

    def test_cache_de_estrelas_invalida_ao_mover_a_camera(self):
        cena = ap1.Scene()
        r = ap1.Renderer()
        r.draw(self.surface, cena)
        primeira = r._stars_key
        self.assertIsNotNone(primeira)
        cena.camera.snap_to("direita")
        r.draw(self.surface, cena)
        self.assertNotEqual(r._stars_key, primeira)

    def test_flash_de_fase_dispara_na_troca(self):
        cena = ap1.Scene()
        hud = ap1.Hud()
        r = ap1.Renderer()
        r.draw(self.surface, cena)
        hud.draw(self.surface, cena, r)
        self.assertEqual(hud._fase_vista, 0)
        cena.goto_phase(3)
        hud.draw(self.surface, cena, r)
        self.assertEqual(hud._fase_vista, 2)
        self.assertGreater(hud._flash, 0.5)

    def test_flash_termina_mesmo_com_o_tempo_parado(self):
        """Regressão: preso ao tempo de simulação, o clarão nunca apagava."""
        cena = ap1.Scene()
        cena.state = ap1.STATE_CONCLUIDO
        cena.sim_time = ap1.TOTAL_SEQUENCE_TIME
        hud = ap1.Hud()
        r = ap1.Renderer()
        r.draw(self.surface, cena)
        for _ in range(120):
            hud.draw(self.surface, cena, r)
        self.assertLessEqual(hud._flash, 0.02)


def bench(quadros=240):
    """
    Mede o custo de um quadro completo, sem janela. O orçamento a 60 FPS é de
    16,7 ms; o painel [H] da aplicação mostra os mesmos contadores em execução.
    """
    import time
    pygame.init()
    surf = pygame.Surface((ap1.WIDTH, ap1.HEIGHT))
    cena = ap1.Scene()
    cena.state = ap1.STATE_EXECUTANDO
    renderer, hud = ap1.Renderer(), ap1.Hud()
    for _ in range(120):                       # aquece e chega à fase 3
        cena.update(1.0 / 60.0)

    def mede(rotulo, fn, n=200):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        print("  %-18s %6.2f ms" % (rotulo, (time.perf_counter() - t0) * 1000 / n))

    vertices = sum(len(m.base_vertices) for m in cena.meshes)
    faces = sum(len(m.faces) for m in cena.meshes)
    print("Cena: %d malhas | %d vértices | %d faces" % (len(cena.meshes), vertices, faces))
    print("Custo por etapa do quadro:")
    mede("scene.update", lambda: cena.update(1.0 / 60.0))
    mede("renderer.draw", lambda: renderer.draw(surf, cena))
    mede("hud.draw", lambda: hud.draw(surf, cena, renderer))

    amostras = []
    for _ in range(quadros):
        t0 = time.perf_counter()
        cena.update(1.0 / 60.0)
        renderer.draw(surf, cena)
        hud.draw(surf, cena, renderer)
        amostras.append((time.perf_counter() - t0) * 1000)
    amostras.sort()
    mediana = amostras[len(amostras) // 2]
    p95 = amostras[int(len(amostras) * 0.95)]
    print("Quadro completo (%d amostras):" % quadros)
    print("  mediana %.2f ms | p95 %.2f ms | max %.2f ms" % (mediana, p95, amostras[-1]))
    print("  orçamento 16,67 ms a 60 FPS -> %.0f%% usado | folga %.2f ms"
          % (mediana / 16.67 * 100, 16.67 - mediana))
    print("  faces desenhadas %d | descartadas %d"
          % (renderer.faces_desenhadas, renderer.faces_descartadas))
    return 0


def smoke():
    """
    Executa a aplicação inteira sem janela, percorrendo o roteiro do checklist,
    e imprime um relatório quadro a quadro dos marcos da sequência.
    """
    pygame.init()
    app = ap1.App(surface=pygame.Surface((ap1.WIDTH, ap1.HEIGHT)))
    dt = 1.0 / 60.0
    print("Roteiro do checklist - Estação Órbita-2")
    print("-" * 72)

    def marco(texto):
        cena = app.scene
        print("%-30s estado=%-11s t=%05.2f fase=%d comporta=%-9s sensor=%s"
              % (texto, cena.state, cena.sim_time, cena.phase_index + 1,
                 cena.door.state,
                 "".join("L" if s["livre"] else "B" for s in cena.sight) or "-"))

    marco("estado inicial")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    for _ in range(120):
        app.step(dt)
    marco("iniciado (2s)")

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    for _ in range(60):
        app.step(dt)
    marco("pausado (1s parado)")

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    for _ in range(120):
        app.step(dt)
    marco("retomado")

    for key, chave in ap1.CAMERA_KEYS.items():
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        for _ in range(30):
            app.step(dt)
        marco("câmera " + chave)

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
    for _ in range(30):
        app.step(dt)
    marco("câmera foco animado")

    for key in ap1.PHASE_KEYS:
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        for _ in range(20):
            app.step(dt)
        marco("salto para fase %d" % ap1.PHASE_KEYS[key])

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    app.step(dt)
    marco("tela de créditos")
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
    app.step(dt)
    marco("painel de dados")

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    app.step(dt)
    marco("reiniciado")

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    quadros = 0
    while app.scene.state != ap1.STATE_CONCLUIDO and quadros < 60 * 30:
        app.step(dt)
        quadros += 1
    marco("sequência concluída")

    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    print("-" * 72)
    print("encerrado por ESC: running=%s | quadros desenhados=%d"
          % (app.running, quadros))
    return 0 if not app.running else 1


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        sys.exit(smoke())
    if "--bench" in sys.argv:
        sys.exit(bench())
    unittest.main(verbosity=2)
