"""
Testes do modelo do Sistema Solar — efemérides, catálogo e leitores das fontes
online. Rodam sem rede e sem janela.

    python -m unittest discover -s "Atividade AP1" -p "test_*.py" -v

Os valores de referência dos planetas e da Lua vieram do JPL Horizons para
2026-09-15 00:00 TDB (JD 2461298,5), em km, eclíptica J2000.
"""

import math
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import catalogo
import efemerides as ef
import fontes_online as fo

JD_REFERENCIA = 2461298.5
HORIZONS = {                                   # heliocêntricos
    "Terra": (1.4893e+08, -2.1421e+07, 8.0080e+02),
    "Marte": (5.0850e+07, 2.2438e+08, 3.4553e+06),
    "Júpiter": (-5.0821e+08, 6.0885e+08, 8.8412e+06),
    "Netuno": (4.4640e+09, 1.9892e+08, -1.0697e+08),
}
LUA_HORIZONS = (-306416.2, -245655.4, -33670.7)  # geocêntrica

ISS_OMM = {"OBJECT_NAME": "ISS (ZARYA)", "NORAD_CAT_ID": 25544,
           "EPOCH": "2026-09-15T08:51:14.158368", "MEAN_MOTION": 15.49122235,
           "ECCENTRICITY": 0.0004926, "INCLINATION": 51.6311, "RA_OF_ASC_NODE": 213.7631,
           "ARG_OF_PERICENTER": 142.7188, "MEAN_ANOMALY": 217.4143, "MEAN_MOTION_DOT": 5.779e-5}


def comprimento(v):
    return math.sqrt(sum(c * c for c in v))


def angulo(a, b):
    d = sum(x * y for x, y in zip(a, b)) / (comprimento(a) * comprimento(b))
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def determinante(colunas):
    (a, b, c), (d, e, f), (g, h, i) = colunas
    # colunas (a,b,c), (d,e,f), (g,h,i): det da matriz com essas colunas
    return a * (e * i - f * h) - d * (b * i - c * h) + g * (b * f - c * e)


class TestTempo(unittest.TestCase):

    def test_j2000(self):
        jd = ef.jd_de_datetime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
        self.assertAlmostEqual(jd, ef.JD_J2000, places=9)

    def test_ida_e_volta(self):
        dt = datetime(2026, 9, 15, 19, 5, 20, tzinfo=timezone.utc)
        volta = ef.datetime_de_jd(ef.jd_de_datetime(dt))
        self.assertLess(abs((volta - dt).total_seconds()), 1e-3)

    def test_datas_antes_de_1970_nao_quebram(self):
        """Regressão prevista: fromtimestamp negativo levanta OSError no Windows."""
        dt = ef.datetime_de_jd(ef.jd_de_datetime(datetime(1910, 4, 20, tzinfo=timezone.utc)))
        self.assertEqual(dt.year, 1910)

    def test_formato_do_celestrak(self):
        jd = ef.jd_de_iso("2026-09-15T08:51:14.158368")
        self.assertAlmostEqual(jd, ef.jd_de_datetime(
            datetime(2026, 9, 15, 8, 51, 14, 158368, tzinfo=timezone.utc)), places=9)


class TestKepler(unittest.TestCase):

    def test_equacao_satisfeita_ate_excentricidade_de_cometa(self):
        for e in (0.0, 0.1, 0.5, 0.9, 0.995):
            for M in (0.001, 0.5, 2.0, 3.1, 5.9):
                E = ef.resolver_kepler(M, e)
                self.assertAlmostEqual(E - e * math.sin(E), M, places=9, msg=(e, M))

    def test_periapsis_e_apoapsis(self):
        orbita = ef.Orbita(1.0e8, 0.3, 10.0, 40.0, 70.0, 0.0, ef.JD_J2000)
        self.assertAlmostEqual(comprimento(orbita.posicao(ef.JD_J2000)), 0.7e8, delta=1.0)
        meio = ef.JD_J2000 + orbita.periodo_dias / 2.0
        self.assertAlmostEqual(comprimento(orbita.posicao(meio)), 1.3e8, delta=1.0)

    def test_terceira_lei_um_ano_a_uma_ua(self):
        orbita = ef.Orbita(ef.UA_KM, 0.0, 0.0, 0.0, 0.0, 0.0, ef.JD_J2000)
        self.assertAlmostEqual(orbita.periodo_dias, 365.25, delta=0.1)

    def test_orbita_aberta_e_recusada(self):
        with self.assertRaises(ValueError):
            ef.Orbita(1.0e8, 1.2, 0.0, 0.0, 0.0, 0.0, ef.JD_J2000)


class TestPlanetasContraHorizons(unittest.TestCase):

    def test_posicoes(self):
        tolerancias = {"Terra": (0.02, 2e-4), "Marte": (0.05, 1e-3),
                       "Júpiter": (0.1, 2e-3), "Netuno": (0.05, 1e-3)}
        for nome, referencia in HORIZONS.items():
            meu = ef.posicao_corpo_principal(nome, JD_REFERENCIA)
            max_ang, max_dist = tolerancias[nome]
            self.assertLess(angulo(meu, referencia), max_ang, msg=nome)
            self.assertLess(abs(comprimento(meu) / comprimento(referencia) - 1.0), max_dist, msg=nome)

    def test_lua(self):
        lua = ef.posicao_lua_geocentrica(JD_REFERENCIA)
        self.assertLess(angulo(lua, LUA_HORIZONS), 0.3)
        self.assertLess(abs(comprimento(lua) - comprimento(LUA_HORIZONS)), 1500.0)

    def test_distancia_da_lua_fica_entre_perigeu_e_apogeu(self):
        for dia in range(0, 30):
            d = comprimento(ef.posicao_lua_geocentrica(JD_REFERENCIA + dia))
            self.assertTrue(356000.0 < d < 407500.0, (dia, d))


class TestSatelites(unittest.TestCase):

    def setUp(self):
        self.iss = ef.OrbitaTerrestre(ISS_OMM)

    def test_periodo_e_altitude_da_iss(self):
        self.assertAlmostEqual(self.iss.periodo_min, 92.9, delta=0.2)
        for minuto in range(0, 1440, 37):
            r = comprimento(self.iss.posicao(self.iss.epoca + minuto / 1440.0))
            self.assertTrue(6700.0 < r < 6850.0, (minuto, r))

    def test_j2_faz_o_no_regredir(self):
        """Com 51,6° de inclinação o plano orbital da ISS gira cerca de 5° por dia para oeste."""
        self.assertTrue(-5.5 < math.degrees(self.iss.dom) < -4.5)

    def test_orbita_circular_ficticia(self):
        omm = ef.orbita_circular_leo(420.0, 51.6, 30.0, 45.0, JD_REFERENCIA)
        orbita = ef.OrbitaTerrestre(omm)
        r = comprimento(orbita.posicao(JD_REFERENCIA + 0.3))
        self.assertAlmostEqual(r, ef.RAIO_TERRA_EQ + 420.0, delta=0.01)


class TestReferenciais(unittest.TestCase):

    def test_base_do_motor_nao_espelha(self):
        for nome in ef.ROTACAO_IAU:
            base = ef.base_rotacao(nome, JD_REFERENCIA)
            self.assertAlmostEqual(determinante(base), 1.0, places=9, msg=nome)

    def test_orbitas_giram_no_sentido_antihorario_vistas_do_norte(self):
        """
        Na vista superior do motor a tela mostra X para a direita e Z para cima.
        A reflexão y <-> z precisa manter o sentido real: anti-horário.
        """
        a = ef.para_mundo(ef.posicao_terra(JD_REFERENCIA))
        b = ef.para_mundo(ef.posicao_terra(JD_REFERENCIA + 10.0))
        self.assertGreater(a[0] * b[2] - a[2] * b[0], 0.0)

    def test_inclinacao_do_eixo_da_terra(self):
        _x, _y, polo = ef.eixos_iau(*ef.ROTACAO_IAU["Terra"][:2], 0.0)
        self.assertAlmostEqual(angulo(polo, (0.0, 0.0, 1.0)), 23.44, delta=0.05)

    def test_greenwich_olha_para_o_sol_ao_meio_dia_do_equinocio(self):
        jd = ef.jd_de_datetime(datetime(2026, 9, 23, 12, tzinfo=timezone.utc))
        alpha0, delta0, w0, taxa = ef.ROTACAO_IAU["Terra"]
        greenwich, _y, _z = ef.eixos_iau(alpha0, delta0, w0 + taxa * (jd - ef.JD_J2000))
        terra = ef.posicao_terra(jd)
        para_o_sol = tuple(-c / comprimento(terra) for c in terra)
        self.assertGreater(sum(g * s for g, s in zip(greenwich, para_o_sol)), 0.98)

    def test_rotacao_da_terra_e_para_leste(self):
        alpha0, delta0, w0, taxa = ef.ROTACAO_IAU["Terra"]
        x0, _y, polo = ef.eixos_iau(alpha0, delta0, w0)
        x1, _y, _z = ef.eixos_iau(alpha0, delta0, w0 + 10.0)
        giro = (x0[1] * x1[2] - x0[2] * x1[1], x0[2] * x1[0] - x0[0] * x1[2],
                x0[0] * x1[1] - x0[1] * x1[0])
        self.assertGreater(sum(g * p for g, p in zip(giro, polo)), 0.0)


class TestSombraETabela(unittest.TestCase):

    def test_sombra_cilindrica(self):
        terra = (ef.UA_KM, 0.0, 0.0)
        self.assertEqual(ef.na_sombra_da_terra((ef.UA_KM + 7000.0, 0.0, 0.0), terra), 1.0)
        self.assertEqual(ef.na_sombra_da_terra((ef.UA_KM - 7000.0, 0.0, 0.0), terra), 0.0)
        self.assertEqual(ef.na_sombra_da_terra((ef.UA_KM, 7000.0, 0.0), terra), 0.0)
        self.assertEqual(ef.na_sombra_da_terra((ef.UA_KM + 2.0e6, 0.0, 0.0), terra), 0.0)

    def test_interpolacao_e_limites(self):
        tabela = ef.TabelaVetores([(10.0, 0.0, 0.0, 0.0), (11.0, 100.0, 50.0, -20.0)])
        self.assertEqual(tabela.posicao(10.5), (50.0, 25.0, -10.0))
        self.assertIsNone(tabela.posicao(9.0))
        self.assertIsNone(tabela.posicao(12.0))

    def test_l2_fica_alem_da_terra(self):
        terra = ef.posicao_terra(JD_REFERENCIA)
        l2 = ef.posicao_l2_aproximada(terra)
        self.assertAlmostEqual(comprimento(l2), ef.DISTANCIA_L2_KM, delta=1.0)
        self.assertLess(angulo(l2, terra), 1e-6)


class TestCatalogo(unittest.TestCase):
    """Os snapshots de dados/ fazem parte do repositório: a cena não depende da rede."""

    def test_estrelas_reais(self):
        estrelas = catalogo.estrelas(6.0)
        self.assertIsNotNone(estrelas)
        self.assertGreater(len(estrelas), 1500)
        mais_brilhante = min(estrelas, key=lambda e: e[1])
        self.assertAlmostEqual(mais_brilhante[1], -1.46, delta=0.01)    # Sírius
        self.assertIn("CMa", mais_brilhante[3])

    def test_cor_da_estrela_pelo_indice_de_cor(self):
        azul = catalogo.cor_da_estrela(-0.3)
        vermelha = catalogo.cor_da_estrela(1.8)
        self.assertGreater(azul[2], azul[0])
        self.assertGreater(vermelha[0], vermelha[2])

    def test_luas_com_periodos_reais(self):
        luas = catalogo.elementos("luas.json")
        for nome, periodo in (("Io", 1.769), ("Titã", 15.945), ("Caronte", 6.387)):
            orbita = catalogo.orbita_de_elementos(luas[nome])
            self.assertAlmostEqual(orbita.periodo_dias, periodo, delta=0.05, msg=nome)

    def test_pequenos_corpos_e_nuvens(self):
        pequenos = catalogo.elementos("pequenos_corpos.json")
        self.assertIn("Plutão", pequenos)
        self.assertAlmostEqual(pequenos["Plutão"]["a"] / ef.UA_KM, 39.5, delta=0.5)
        nuvens = catalogo.nuvens()
        self.assertGreater(len(nuvens.get("cinturao", [])), 1000)
        for orbita in nuvens["cinturao"][:50]:
            self.assertTrue(1.5 * ef.UA_KM < orbita.a < 5.5 * ef.UA_KM)

    def test_satelites_e_jwst(self):
        grupos, gerado = catalogo.satelites()
        self.assertIsNotNone(gerado)
        norads = {int(o["NORAD_CAT_ID"]) for lista in grupos.values() for o in lista}
        self.assertIn(25544, norads)                  # ISS
        tabela = catalogo.tabela_jwst()
        self.assertIsNotNone(tabela)
        meio = (tabela.jds[0] + tabela.jds[-1]) / 2.0
        self.assertTrue(0.8e6 < comprimento(tabela.posicao(meio)) < 2.0e6)

    def test_mapas_de_cor(self):
        for nome in ("terra", "lua", "jupiter", "aneis_saturno"):
            self.assertIsNotNone(catalogo.caminho_mapa(nome), msg=nome)


# ------------------------------------------------------------ leitores online
AMOSTRA_HORIZONS = """*******************************************************************************
            JDTDB,            Calendar Date (TDB),                     EC,                     QR,
$$SOE
2461298.500000000, A.D. 2026-Sep-15 00:00:00.0000,  4.728624017131290E-03,  4.200478904840078E+05,  2.226161467802171E+00,  3.384221140173485E+02,  5.965158980406337E+01,  2.461298354080496E+06,  2.352134382789048E-03,  2.965440525229155E+01,  2.992388297283616E+01,  4.220435758731577E+05,  4.240392612623076E+05,  1.530524797537840E+05,
$$EOE
*******************************************************************************
"""

AMOSTRA_RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Collage of cutouts of IC 348</title><link>https://esawebb.org/images/weic2619b/</link>
<description>&lt;img src="https://cdn.esawebb.org/archives/images/news/weic2619b.jpg" /&gt;&lt;p&gt;Recortes&lt;/p&gt;</description>
<pubDate>Tue, 15 Sep 2026 16:00:00 +0200</pubDate></item>
<item><title>Star-forming region IC 348 (NIRCam image)</title><link>https://esawebb.org/images/weic2619a/</link>
<description>Legenda &amp;amp; texto</description><pubDate>Tue, 15 Sep 2026 16:00:00 +0200</pubDate></item>
</channel></rss>"""

COLUNAS_AGENDA = (("VISIT ID", 13), ("PCS MODE", 10), ("VISIT TYPE", 29),
                  ("SCHEDULED START TIME", 20), ("DURATION", 11),
                  ("SCIENCE INSTRUMENT AND MODE", 50), ("TARGET NAME", 31),
                  ("CATEGORY", 30), ("KEYWORDS", 32))


def agenda_de_exemplo():
    def linha(valores):
        return "  ".join(v.ljust(w) for v, (_n, w) in zip(valores, COLUNAS_AGENDA)).rstrip()
    return "\n".join([
        "Visit Information for OP Package 2625607f01", "",
        linha([n for n, _w in COLUNAS_AGENDA]),
        "  ".join("-" * w for _n, w in COLUNAS_AGENDA),
        linha(["7648:3:1", "FINEGUIDE", "PRIME TARGETED FIXED", "2026-09-14T15:43:57Z",
               "00/02:07:27", "NIRCam Imaging", "NAME-N6946-BH1", "Star", "Black holes"]),
        linha(["1520:218:1", "NONE", "PARALLEL SLEW CALIBRATION", "^ATTACHED TO PRIME^", "",
               "MIRI Anneal"]),
        linha(["7648:4:1", "FINEGUIDE", "PRIME TARGETED FIXED", "2026-09-14T18:00:24Z",
               "00/07:40:16", "MIRI Medium Resolution Spectroscopy", "NAME-N6946-BH1", "Star",
               "Black holes, Circumstellar dust"]),
    ])


class TestLeitoresOnline(unittest.TestCase):

    def test_horizons_csv(self):
        linhas = fo.linhas_horizons(AMOSTRA_HORIZONS)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(len(linhas[0]), 14)
        n_graus_s = float(linhas[0][8])
        self.assertAlmostEqual(360.0 / n_graus_s / 86400.0, 1.771, delta=0.002)   # Io

    def test_horizons_sem_efemeride_vira_erro_de_fonte(self):
        with self.assertRaises(fo.ErroDeFonte):
            fo.linhas_horizons("API VERSION: 1.2\nBad dates -- start must be earlier than stop")

    def test_rss_e_escolha_da_imagem_principal(self):
        itens = fo.ler_rss_imagens(AMOSTRA_RSS, "https://cdn.esawebb.org/archives/images/")
        self.assertEqual([i["id"] for i in itens], ["weic2619b", "weic2619a"])
        self.assertEqual(itens[0]["data"].year, 2026)
        escolhida = fo.escolher_imagem(itens)
        self.assertEqual(escolhida["id"], "weic2619a")      # a colagem fica de fora

    def test_tamanho_da_imagem_com_folga_sobre_a_tela(self):
        item = {"cdn": "https://cdn.esawebb.org/archives/images/", "id": "weic2619a"}
        self.assertIn("/wallpaper_qhd/", fo.urls_da_imagem(item, 1920)[0])
        self.assertIn("/wallpaper_uhd/", fo.urls_da_imagem(item, 2560)[0])
        self.assertIn("/wallpaper_uhd/", fo.urls_da_imagem(item, 5120)[0])
        self.assertIn("/wallpaper_fhd/", fo.urls_da_imagem(item, 1280)[0])
        self.assertTrue(fo.urls_da_imagem(item, 1920)[-1].endswith("/screen/weic2619a.jpg"))

    def test_credito_da_pagina(self):
        pagina = b'<div class="credit"><p>ESA/Webb, NASA, CSA, <a href="#">K. Luhman</a></p></div>'
        self.assertEqual(fo.credito_da_pagina(pagina, "ESA/Webb"), "ESA/Webb, NASA, CSA, K. Luhman")
        self.assertEqual(fo.credito_da_pagina(b"<html></html>", "ESA/Webb"), "ESA/Webb")

    def test_agenda_do_webb(self):
        visitas = fo.ler_agenda_webb(agenda_de_exemplo())
        self.assertEqual(len(visitas), 2)                  # a paralela sem horário fica de fora
        self.assertEqual(visitas[0]["alvo"], "NAME-N6946-BH1")
        self.assertEqual(visitas[1]["instrumento"], "MIRI Medium Resolution Spectroscopy")
        self.assertEqual(visitas[0]["fim"] - visitas[0]["inicio"], timedelta(hours=2, minutes=7, seconds=27))

    def test_observacao_agora_e_proxima(self):
        visitas = fo.ler_agenda_webb(agenda_de_exemplo())
        visita, situacao = fo.observacao_em(visitas, datetime(2026, 9, 14, 16, 0, tzinfo=timezone.utc))
        self.assertEqual((visita["visita"], situacao), ("7648:3:1", "agora"))
        visita, situacao = fo.observacao_em(visitas, datetime(2026, 9, 14, 17, 55, tzinfo=timezone.utc))
        self.assertEqual((visita["visita"], situacao), ("7648:4:1", "próxima"))
        visita, _situacao = fo.observacao_em(visitas, datetime(2026, 12, 1, tzinfo=timezone.utc))
        self.assertIsNone(visita)

    def test_agendas_publicadas_da_mais_nova(self):
        pagina = (b'<a href="/files/_documents/20260907_report_20260908.txt">a</a>'
                  b'<a href="/files/_documents/20260914_report_20260910.txt">b</a>')
        self.assertEqual(fo.agendas_publicadas(pagina)[0], "20260914_report_20260910")

    def test_satelites_por_grupo_sem_repeticao(self):
        def falso(grupo):
            if grupo == "science":
                raise fo.ErroDeFonte("fora do ar")
            base = [{"NORAD_CAT_ID": 25544}] if grupo in ("stations", "weather") else []
            return base + [{"NORAD_CAT_ID": 1000 + k} for k in range(24)] if grupo == "starlink" else base
        grupos = fo.satelites_por_grupo(falso)
        self.assertNotIn("ciencia", grupos)
        self.assertEqual(len(grupos["estacoes"]), 1)
        self.assertEqual(len(grupos["clima"]), 0)          # a ISS já estava em estações
        self.assertEqual(len(grupos["starlink"]), 2)       # um a cada 12


class TestCacheETarefas(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.antigo = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.pasta.name

    def tearDown(self):
        if self.antigo is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.antigo
        self.pasta.cleanup()

    def test_cache_valido_nao_baixa_de_novo(self):
        chamadas = []

        def obter():
            chamadas.append(1)
            return b"dados"
        self.assertEqual(fo.com_cache("x.bin", 3600, obter)[0], b"dados")
        self.assertEqual(fo.com_cache("x.bin", 3600, obter)[0], b"dados")
        self.assertEqual(len(chamadas), 1)

    def test_rede_fora_do_ar_devolve_cache_vencido(self):
        fo.com_cache("y.bin", 3600, lambda: b"antigo")

        def falha():
            raise fo.ErroDeFonte("sem rede")
        self.assertEqual(fo.com_cache("y.bin", 0, falha)[0], b"antigo")
        with self.assertRaises(fo.ErroDeFonte):
            fo.com_cache("z.bin", 0, falha)

    def esperar(self, tarefas, nome):
        limite = time.time() + 5.0
        while time.time() < limite:
            situacao, valor = tarefas.consumir(nome)
            if situacao in ("pronto", "falhou"):
                return situacao, valor
            time.sleep(0.01)
        self.fail("tarefa %s não terminou" % nome)

    def test_tarefas_em_segundo_plano(self):
        tarefas = fo.Tarefas()
        self.assertTrue(tarefas.iniciar("soma", lambda a, b: a + b, 2, 3))
        self.assertEqual(self.esperar(tarefas, "soma"), ("pronto", 5))
        self.assertEqual(tarefas.estado("soma")[0], "entregue")

    def test_falha_vira_estado_e_nao_excecao(self):
        tarefas = fo.Tarefas()

        def quebra():
            raise fo.ErroDeFonte("sem rede")
        tarefas.iniciar("x", quebra)
        situacao, mensagem = self.esperar(tarefas, "x")
        self.assertEqual(situacao, "falhou")
        self.assertIn("sem rede", mensagem)


if __name__ == "__main__":
    unittest.main(verbosity=2)
