"""
Efemérides do AP1 — onde cada corpo real está num instante UTC.

Sem pygame, sem rede e sem numpy: só `math` e `datetime`, para que a suíte de
testes exercite tudo sem janela. As contas trabalham em quilômetros, no
referencial eclíptico J2000 (x para o ponto vernal, z para o polo norte da
eclíptica), que é o referencial em que o JPL publica os elementos orbitais.
`para_mundo` e `base_para_mundo` fazem a única ponte com o motor gráfico.

Modelos usados, do mais preciso ao mais aproximado:
- planetas: elementos keplerianos médios do JPL com taxas seculares
  ("Approximate Positions of the Planets", válidos de 1800 a 2050);
- Lua: fórmula de baixa precisão do Astronomical Almanac (~0,3°);
- luas, planetas anões, asteroides e cometas: elementos osculadores do JPL
  propagados como problema de dois corpos;
- satélites artificiais: elementos médios do CelesTrak (formato OMM) com o
  efeito secular do achatamento da Terra (J2).
"""

import bisect
import math
from datetime import datetime, timedelta, timezone

# ============================================================
# 1. ESCALA, TEMPO E REFERENCIAIS
# ============================================================
KM = 5000.0                      # unidades de mundo por km: 1 u = 0,2 m
UA_KM = 149597870.7
SEGUNDOS_DIA = 86400.0
JD_J2000 = 2451545.0
JD_UNIX = 2440587.5              # 1970-01-01T00:00:00Z
OBLIQUIDADE = math.radians(23.43928)
_COS_EPS = math.cos(OBLIQUIDADE)
_SIN_EPS = math.sin(OBLIQUIDADE)

GM_SOL = 1.32712440018e11        # km³/s²
GM_TERRA = 398600.4418
RAIO_TERRA_EQ = 6378.137
J2_TERRA = 1.08262668e-3
MASSA_TERRA_LUA = 81.30057       # razão de massas Terra/Lua

_EPOCA_UNIX = datetime(1970, 1, 1, tzinfo=timezone.utc)
DUAS_PI = 2.0 * math.pi


def jd_de_datetime(dt):
    """Data juliana (escala UTC) de um datetime; sem fuso, assume UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return JD_UNIX + (dt - _EPOCA_UNIX).total_seconds() / SEGUNDOS_DIA


def datetime_de_jd(jd):
    # timedelta em vez de fromtimestamp: no Windows, instantes anteriores a
    # 1970 fazem fromtimestamp levantar OSError
    return _EPOCA_UNIX + timedelta(days=jd - JD_UNIX)


def jd_de_iso(texto):
    """'2026-09-14T05:49:25.902624' (formato do CelesTrak) -> data juliana."""
    texto = texto.strip().replace("Z", "")
    formato = "%Y-%m-%dT%H:%M:%S.%f" if "." in texto else "%Y-%m-%dT%H:%M:%S"
    return jd_de_datetime(datetime.strptime(texto, formato))


def seculos_j2000(jd):
    return (jd - JD_J2000) / 36525.0


def equatorial_para_ecliptica(v):
    """Rotação pela obliquidade: equador J2000 -> eclíptica J2000."""
    x, y, z = v
    return (x, y * _COS_EPS + z * _SIN_EPS, -y * _SIN_EPS + z * _COS_EPS)


def para_mundo(v_km):
    """
    Eclíptica J2000 em km -> coordenadas do motor.

    A câmera do motor tem right × up = forward, a convenção de mão esquerda na
    tela: uma cena destra sairia espelhada, com as constelações invertidas e os
    planetas girando no sentido errado. Trocar y com z é uma reflexão que
    compensa isso, e o eixo "para cima" do motor passa a ser o polo norte da
    eclíptica.
    """
    return (v_km[0] * KM, v_km[2] * KM, v_km[1] * KM)


def direcao_para_mundo(v):
    """A mesma reflexão, sem escala, para direções."""
    return (v[0], v[2], v[1])


def _norm(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n < 1e-15:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def base_para_mundo(eixo_x, eixo_y, eixo_z):
    """
    Base destra de um corpo, em eclíptica (x na longitude 0, y na longitude
    90° leste, z no polo norte), -> base para `PolyMesh`.

    As malhas do motor são construídas com o polo em +Y e a longitude medida de
    +X para +Z, então as colunas são as imagens de x, z e y, nessa ordem. Com a
    reflexão aplicada nos dois lados, o determinante continua +1: a malha não
    se espelha e o winding das faces se preserva.
    """
    return (direcao_para_mundo(eixo_x), direcao_para_mundo(eixo_z),
            direcao_para_mundo(eixo_y))


# ============================================================
# 2. EQUAÇÃO DE KEPLER E ÓRBITAS DE DOIS CORPOS
# ============================================================
def resolver_kepler(M, e):
    """Anomalia excêntrica E tal que M = E - e·sen E (Newton-Raphson)."""
    M = math.fmod(M, DUAS_PI)
    if M < 0.0:
        M += DUAS_PI
    # para excentricidade alta o chute E = M diverge perto do periélio
    E = M if e < 0.8 else math.pi
    for _ in range(50):
        passo = (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        E -= passo
        if abs(passo) < 1e-12:
            break
    return E


def vetores_pq(i, om, w):
    """
    Vetores unitários do plano orbital: P aponta para o periapsis e Q está 90°
    adiante no sentido do movimento. Ângulos em graus.
    """
    ci, si = math.cos(math.radians(i)), math.sin(math.radians(i))
    co, so = math.cos(math.radians(om)), math.sin(math.radians(om))
    cw, sw = math.cos(math.radians(w)), math.sin(math.radians(w))
    P = (cw * co - sw * so * ci, cw * so + sw * co * ci, sw * si)
    Q = (-sw * co - cw * so * ci, -sw * so + cw * co * ci, cw * si)
    return P, Q


class Orbita:
    """
    Órbita kepleriana fixa. P e Q são calculados uma única vez: cada posição
    custa uma equação de Kepler e duas combinações lineares, o que permite
    propagar milhares de asteroides.

    `n` é o movimento médio em rad/dia; sem ele, sai de `mu` pela 3ª lei.
    """

    __slots__ = ("a", "e", "b", "n", "m0", "epoca", "P", "Q", "i", "om", "w")

    def __init__(self, a, e, i, om, w, ma, epoca_jd, mu=GM_SOL, n=None):
        if not (0.0 <= e < 1.0) or a <= 0.0:
            raise ValueError("só órbitas fechadas: a=%r e=%r" % (a, e))
        self.a = a
        self.e = e
        self.b = a * math.sqrt(1.0 - e * e)
        self.n = n if n is not None else math.sqrt(mu / (a * a * a)) * SEGUNDOS_DIA
        self.m0 = math.radians(ma)
        self.epoca = epoca_jd
        self.i, self.om, self.w = i, om, w
        self.P, self.Q = vetores_pq(i, om, w)

    @property
    def periodo_dias(self):
        return DUAS_PI / self.n

    @property
    def normal(self):
        """Normal do plano orbital (momento angular), no referencial dos elementos."""
        return _cross(self.P, self.Q)

    def posicao(self, jd):
        E = resolver_kepler(self.m0 + self.n * (jd - self.epoca), self.e)
        x = self.a * (math.cos(E) - self.e)
        y = self.b * math.sin(E)
        P, Q = self.P, self.Q
        return (x * P[0] + y * Q[0], x * P[1] + y * Q[1], x * P[2] + y * Q[2])

    def pontos(self, passos=128):
        """Traçado fechado da órbita, com passos uniformes em anomalia excêntrica."""
        P, Q = self.P, self.Q
        saida = []
        for k in range(passos):
            E = DUAS_PI * k / passos
            x = self.a * (math.cos(E) - self.e)
            y = self.b * math.sin(E)
            saida.append((x * P[0] + y * Q[0], x * P[1] + y * Q[1], x * P[2] + y * Q[2]))
        return saida


# ============================================================
# 3. PLANETAS (JPL, Approximate Positions of the Planets, tabela 1)
# ============================================================
# (a [UA], e, I [°], L [°], ϖ [°], Ω [°]) em J2000 e as taxas por século juliano.
ELEMENTOS_PLANETAS = {
    "Mercúrio": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                 (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "Vênus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "Terra-Lua": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
                  (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "Marte": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
              (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "Júpiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "Saturno": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
                (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
    "Urano": ((19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
              (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589)),
    "Netuno": ((30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
               (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664)),
}


def elementos_planeta(nome, jd):
    """(a [km], e, i, Ω, ω, M) do planeta no instante, ângulos em graus."""
    base, taxa = ELEMENTOS_PLANETAS[nome]
    T = seculos_j2000(jd)
    a, e, i, L, peri, no = (b + r * T for b, r in zip(base, taxa))
    return a * UA_KM, e, i, no, peri - no, L - peri


def posicao_planeta(nome, jd):
    """Posição heliocêntrica eclíptica J2000, em km."""
    a, e, i, om, w, M = elementos_planeta(nome, jd)
    E = resolver_kepler(math.radians(M), e)
    x = a * (math.cos(E) - e)
    y = a * math.sqrt(1.0 - e * e) * math.sin(E)
    P, Q = vetores_pq(i, om, w)
    return (x * P[0] + y * Q[0], x * P[1] + y * Q[1], x * P[2] + y * Q[2])


def orbita_planeta(nome, jd):
    """Órbita instantânea do planeta, para desenhar o traçado."""
    a, e, i, om, w, M = elementos_planeta(nome, jd)
    return Orbita(a, e, i, om, w, M, jd)


# ============================================================
# 4. TERRA E LUA
# ============================================================
def _sen(graus):
    return math.sin(math.radians(graus))


def _cos(graus):
    return math.cos(math.radians(graus))


def posicao_lua_geocentrica(jd):
    """
    Lua geocêntrica, eclíptica J2000, em km. Fórmula de baixa precisão do
    Astronomical Almanac: longitude a ~0,3°, latitude a ~0,2°. Os elementos
    osculadores da Lua variam demais ao longo do mês para dois corpos servirem.
    """
    T = seculos_j2000(jd)
    lon = (218.32 + 481267.881 * T
           + 6.29 * _sen(135.0 + 477198.87 * T) - 1.27 * _sen(259.3 - 413335.36 * T)
           + 0.66 * _sen(235.7 + 890534.22 * T) + 0.21 * _sen(269.9 + 954397.74 * T)
           - 0.19 * _sen(357.5 + 35999.05 * T) - 0.11 * _sen(186.5 + 966404.03 * T))
    lat = (5.13 * _sen(93.3 + 483202.02 * T) + 0.28 * _sen(228.2 + 960400.89 * T)
           - 0.28 * _sen(318.3 + 6003.15 * T) - 0.17 * _sen(217.6 - 407332.21 * T))
    paralaxe = (0.9508 + 0.0518 * _cos(135.0 + 477198.87 * T)
                + 0.0095 * _cos(259.3 - 413335.36 * T) + 0.0078 * _cos(235.7 + 890534.22 * T)
                + 0.0028 * _cos(269.9 + 954397.74 * T))
    # a fórmula dá o equinócio da data; a precessão geral leva de volta a J2000
    lon -= 1.396971 * T
    r = 6378.14 / _sen(paralaxe)
    cl = _cos(lat)
    return (r * cl * _cos(lon), r * cl * _sen(lon), r * _sen(lat))


def posicao_terra(jd):
    """Terra heliocêntrica: o JPL tabela o baricentro Terra-Lua, a Terra fica 4.700 km ao lado."""
    bari = posicao_planeta("Terra-Lua", jd)
    lua = posicao_lua_geocentrica(jd)
    k = 1.0 / (1.0 + MASSA_TERRA_LUA)
    return (bari[0] - lua[0] * k, bari[1] - lua[1] * k, bari[2] - lua[2] * k)


def posicao_corpo_principal(nome, jd):
    """Planetas e Terra por um único nome, heliocêntricos em km."""
    if nome == "Terra":
        return posicao_terra(jd)
    return posicao_planeta(nome, jd)


# ============================================================
# 5. ORIENTAÇÃO DOS CORPOS (IAU WGCCRE, valores aproximados)
# ============================================================
# (α0 [°], δ0 [°], W0 [°], Ẇ [°/dia]) do polo norte e do meridiano principal,
# no equador J2000. Os termos periódicos pequenos foram omitidos.
ROTACAO_IAU = {
    "Sol": (286.13, 63.87, 84.176, 14.1844000),
    "Mercúrio": (281.0103, 61.4155, 329.5988, 6.1385108),
    "Vênus": (272.76, 67.16, 160.20, -1.4813688),
    "Terra": (0.0, 90.0, 190.147, 360.9856235),
    "Lua": (269.9949, 66.5392, 38.3213, 13.17635815),
    "Marte": (317.269202, 54.432516, 176.049863, 350.891982443297),
    "Júpiter": (268.056595, 64.495303, 284.95, 870.5360000),
    "Saturno": (40.589, 83.537, 38.90, 810.7939024),
    "Urano": (257.311, -15.175, 203.81, -501.1600928),
    "Netuno": (299.36, 43.46, 249.978, 541.1397757),
    "Plutão": (132.993, -6.163, 302.695, 56.3625225),
    "Ceres": (291.418, 66.764, 170.650, 952.1532),
}


def polo_ecliptico(alpha0, delta0):
    """Polo norte de rotação (α0, δ0 em graus) como vetor eclíptico unitário."""
    cd = _cos(delta0)
    return equatorial_para_ecliptica((cd * _cos(alpha0), cd * _sen(alpha0), _sen(delta0)))


def eixos_iau(alpha0, delta0, W):
    """
    Eixos destros do corpo em eclíptica J2000: x no meridiano principal, z no
    polo norte. O meridiano parte do nó do equador do corpo sobre o equador
    J2000 e avança W graus.
    """
    cd = _cos(delta0)
    polo = (cd * _cos(alpha0), cd * _sen(alpha0), _sen(delta0))
    no = (-_sen(alpha0), _cos(alpha0), 0.0)
    perp = _cross(polo, no)
    cw, sw = _cos(W), _sen(W)
    x = (cw * no[0] + sw * perp[0], cw * no[1] + sw * perp[1], cw * no[2] + sw * perp[2])
    y = _cross(polo, x)
    return (equatorial_para_ecliptica(x), equatorial_para_ecliptica(y),
            equatorial_para_ecliptica(polo))


def base_rotacao(nome, jd):
    """Base do motor para um corpo com elementos IAU; None se não houver."""
    dados = ROTACAO_IAU.get(nome)
    if dados is None:
        return None
    alpha0, delta0, w0, taxa = dados
    return base_para_mundo(*eixos_iau(alpha0, delta0, w0 + taxa * (jd - JD_J2000)))


def base_sincrona(para_o_pai, normal):
    """
    Rotação síncrona (luas em travamento de maré): o meridiano principal olha
    para o planeta e o polo acompanha a normal da órbita. Vetores em eclíptica.
    """
    x = _norm(para_o_pai)
    z = _norm(normal)
    y = _norm(_cross(z, x))
    z = _cross(x, y)
    return base_para_mundo(x, y, z)


# ============================================================
# 6. SATÉLITES ARTIFICIAIS (elementos médios OMM + J2 secular)
# ============================================================
class OrbitaTerrestre:
    """
    Satélite em órbita da Terra a partir dos elementos médios do CelesTrak.

    Não é o SGP4: é Kepler com as derivas seculares do J2 no nó, no perigeu e
    na anomalia média, mais o termo de arrasto do próprio conjunto de elementos.
    Para alguns dias em torno da época o erro fica em dezenas de km — invisível
    na escala da cena — e o código cabe em uma tela.

    O CelesTrak publica os elementos no equador verdadeiro da data (TEME). A
    precessão desde J2000 (~0,37° em longitude) deslocaria a ISS em ~45 km;
    ela é desfeita com uma rotação em torno do polo da eclíptica, e o erro cai
    para poucos km.
    """

    __slots__ = ("nome", "norad", "epoca", "a", "e", "b", "n", "ndot", "m0",
                 "om0", "w0", "i", "dom", "dw", "dm", "grupo", "_cp", "_sp")

    def __init__(self, omm, grupo=""):
        self.nome = omm["OBJECT_NAME"]
        self.norad = int(omm["NORAD_CAT_ID"])
        self.grupo = grupo
        self.epoca = jd_de_iso(omm["EPOCH"])
        n_rev_dia = float(omm["MEAN_MOTION"])
        self.n = n_rev_dia * DUAS_PI                          # rad/dia
        # MEAN_MOTION_DOT vem como ṅ/2 em rev/dia², como no TLE
        self.ndot = float(omm.get("MEAN_MOTION_DOT", 0.0) or 0.0) * DUAS_PI
        self.e = float(omm["ECCENTRICITY"])
        self.i = math.radians(float(omm["INCLINATION"]))
        self.om0 = math.radians(float(omm["RA_OF_ASC_NODE"]))
        self.w0 = math.radians(float(omm["ARG_OF_PERICENTER"]))
        self.m0 = math.radians(float(omm["MEAN_ANOMALY"]))
        n_rad_s = self.n / SEGUNDOS_DIA
        self.a = (GM_TERRA / (n_rad_s * n_rad_s)) ** (1.0 / 3.0)
        self.b = self.a * math.sqrt(1.0 - self.e * self.e)
        p = self.a * (1.0 - self.e * self.e)
        fator = 1.5 * J2_TERRA * (RAIO_TERRA_EQ / p) ** 2 * self.n
        si2 = math.sin(self.i) ** 2
        self.dom = -fator * math.cos(self.i)
        self.dw = fator * (2.0 - 2.5 * si2)
        self.dm = fator * math.sqrt(1.0 - self.e * self.e) * (1.0 - 1.5 * si2)
        precessao = math.radians(1.396971 * seculos_j2000(self.epoca))
        self._cp, self._sp = math.cos(precessao), math.sin(precessao)

    @property
    def periodo_min(self):
        return 1440.0 * DUAS_PI / (self.n + self.dm)

    @property
    def altitude_media_km(self):
        return self.a - RAIO_TERRA_EQ

    def elementos(self, jd):
        """(Ω, ω, M) em radianos no instante."""
        dt = jd - self.epoca
        return (self.om0 + self.dom * dt, self.w0 + self.dw * dt,
                self.m0 + (self.n + self.dm) * dt + self.ndot * dt * dt)

    def _para_j2000(self, v):
        """Equador da data -> eclíptica J2000: obliquidade e depois a precessão em longitude."""
        x, y, z = equatorial_para_ecliptica(v)
        return (x * self._cp + y * self._sp, -x * self._sp + y * self._cp, z)

    def posicao(self, jd):
        """Posição geocêntrica, eclíptica J2000, em km."""
        om, w, M = self.elementos(jd)
        E = resolver_kepler(M, self.e)
        x = self.a * (math.cos(E) - self.e)
        y = self.b * math.sin(E)
        co, so = math.cos(om), math.sin(om)
        cw, sw = math.cos(w), math.sin(w)
        ci, si = math.cos(self.i), math.sin(self.i)
        px, py, pz = cw * co - sw * so * ci, cw * so + sw * co * ci, sw * si
        qx, qy, qz = -sw * co - cw * so * ci, -sw * so + cw * co * ci, cw * si
        return self._para_j2000((x * px + y * qx, x * py + y * qy, x * pz + y * qz))

    def normal_orbita(self, jd):
        """Normal do plano orbital no instante, em eclíptica."""
        om = self.om0 + self.dom * (jd - self.epoca)
        si = math.sin(self.i)
        return self._para_j2000((si * math.sin(om), -si * math.cos(om), math.cos(self.i)))


def orbita_circular_leo(altitude_km, inclinacao, no, fase, epoca_jd):
    """
    Órbita circular fictícia no mesmo formato OMM dos satélites reais: é como a
    estação Órbita-2, que não existe, ganha uma órbita tão física quanto a da ISS.
    """
    a = RAIO_TERRA_EQ + altitude_km
    n_rev_dia = math.sqrt(GM_TERRA / a ** 3) * SEGUNDOS_DIA / DUAS_PI
    epoca = datetime_de_jd(epoca_jd).strftime("%Y-%m-%dT%H:%M:%S.%f")
    return {"OBJECT_NAME": "ORBITA-2", "NORAD_CAT_ID": 0, "EPOCH": epoca,
            "MEAN_MOTION": n_rev_dia, "ECCENTRICITY": 0.0, "INCLINATION": inclinacao,
            "RA_OF_ASC_NODE": no, "ARG_OF_PERICENTER": 0.0, "MEAN_ANOMALY": fase,
            "MEAN_MOTION_DOT": 0.0}


def na_sombra_da_terra(ponto_km, terra_km, raio=6371.0):
    """
    Eclipse por sombra cilíndrica: o ponto está atrás da Terra em relação ao Sol
    e a menos de um raio terrestre do eixo da sombra? Devolve de 0 (pleno Sol)
    a 1 (centro da sombra). A umbra real tem 1,4 milhão de km de comprimento;
    o cilindro para ali, senão eclipsaria Marte em oposição.
    """
    rel = (ponto_km[0] - terra_km[0], ponto_km[1] - terra_km[1], ponto_km[2] - terra_km[2])
    para_o_sol = _norm((-terra_km[0], -terra_km[1], -terra_km[2]))
    atras = -_dot(rel, para_o_sol)
    if atras <= 0.0 or atras > 1.4e6:
        return 0.0
    ex = (rel[0] + para_o_sol[0] * atras, rel[1] + para_o_sol[1] * atras,
          rel[2] + para_o_sol[2] * atras)
    desvio = math.sqrt(_dot(ex, ex))
    if desvio >= raio:
        return 0.0
    return min(1.0, (raio - desvio) / (raio * 0.08))    # penumbra na borda


# ============================================================
# 7. POSIÇÕES TABELADAS (Horizons) E O PONTO L2
# ============================================================
class TabelaVetores:
    """
    Posições tabeladas, interpoladas linearmente. É como o James Webb entra:
    ele não tem elementos simples — a órbita de halo em torno de L2 é mantida
    por manobras —, então a cena usa os vetores diários do Horizons.
    """

    def __init__(self, linhas):
        linhas = sorted(linhas)
        self.jds = [l[0] for l in linhas]
        self.vetores = [tuple(l[1:4]) for l in linhas]

    def cobre(self, jd):
        return bool(self.jds) and self.jds[0] <= jd <= self.jds[-1]

    def posicao(self, jd):
        """Vetor interpolado; None fora do intervalo tabelado."""
        if not self.cobre(jd):
            return None
        k = bisect.bisect_right(self.jds, jd)
        if k >= len(self.jds):
            return self.vetores[-1]
        j0, j1 = self.jds[k - 1], self.jds[k]
        u = (jd - j0) / (j1 - j0) if j1 > j0 else 0.0
        a, b = self.vetores[k - 1], self.vetores[k]
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u)


DISTANCIA_L2_KM = 1.5e6


def posicao_l2_aproximada(terra_km):
    """Ponto L2 Sol-Terra: 1,5 milhão de km além da Terra, na direção oposta ao Sol."""
    d = _norm(terra_km)
    return (d[0] * DISTANCIA_L2_KM, d[1] * DISTANCIA_L2_KM, d[2] * DISTANCIA_L2_KM)
