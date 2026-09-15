"""
Catálogo dos corpos reais da cena: tamanho, cor, quem orbita quem e como cada
um gira, mais a leitura dos snapshots de `dados/`.

Só dados e Python puro — nada de pygame. Os snapshots são lidos uma única vez
por processo e compartilhados entre cenas: a suíte de testes cria dezenas de
`Scene`, e reler milhares de órbitas a cada uma deixaria tudo lento.
"""

import json
import math
import os

import efemerides as ef

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
PASTA_MAPAS = os.path.join(PASTA_DADOS, "mapas")

# ------------------------------------------------------------------ corpos
# (nome, raio médio em km, cor do marcador, mapa de cor em dados/mapas)
SOL = ("Sol", 695700.0, (255, 226, 150), "sol")
PLANETAS = (
    ("Mercúrio", 2439.7, (176, 166, 156), "mercurio"),
    ("Vênus", 6051.8, (232, 206, 156), "venus"),
    ("Terra", 6371.0, (96, 146, 220), "terra"),
    ("Marte", 3389.5, (206, 112, 70), "marte"),
    ("Júpiter", 69911.0, (218, 186, 146), "jupiter"),
    ("Saturno", 58232.0, (226, 206, 152), "saturno"),
    ("Urano", 25362.0, (164, 214, 226), "urano"),
    ("Netuno", 24622.0, (92, 130, 226), "netuno"),
)
LUA = ("Lua", 1737.4, (190, 190, 186), "lua")

# nome: (planeta, raio médio em km, cor)
LUAS = {
    "Fobos": ("Marte", 11.1, (126, 116, 106)), "Deimos": ("Marte", 6.2, (146, 136, 122)),
    "Io": ("Júpiter", 1821.6, (226, 206, 104)), "Europa": ("Júpiter", 1560.8, (206, 190, 168)),
    "Ganimedes": ("Júpiter", 2634.1, (156, 146, 134)), "Calisto": ("Júpiter", 2410.3, (116, 106, 96)),
    "Amalteia": ("Júpiter", 83.5, (176, 96, 74)),
    "Mimas": ("Saturno", 198.2, (196, 196, 196)), "Encélado": ("Saturno", 252.1, (242, 246, 250)),
    "Tétis": ("Saturno", 531.1, (224, 224, 224)), "Dione": ("Saturno", 561.4, (206, 206, 206)),
    "Reia": ("Saturno", 763.8, (196, 196, 196)), "Titã": ("Saturno", 2574.7, (226, 166, 76)),
    "Hipérion": ("Saturno", 135.0, (176, 156, 136)), "Jápeto": ("Saturno", 734.5, (156, 136, 116)),
    "Febe": ("Saturno", 106.5, (96, 90, 84)),
    "Ariel": ("Urano", 578.9, (196, 196, 196)), "Umbriel": ("Urano", 584.7, (126, 126, 126)),
    "Titânia": ("Urano", 788.4, (186, 176, 170)), "Oberon": ("Urano", 761.4, (166, 156, 150)),
    "Miranda": ("Urano", 235.8, (176, 176, 176)),
    "Tritão": ("Netuno", 1353.4, (216, 206, 206)), "Nereida": ("Netuno", 170.0, (156, 156, 156)),
    "Proteu": ("Netuno", 210.0, (106, 106, 106)),
    "Caronte": ("Plutão", 606.0, (156, 146, 140)),
}

# nome: (raio médio em km, cor). Cometas: raio do núcleo.
PEQUENOS = {
    "Plutão": (1188.3, (216, 186, 156)), "Ceres": (469.7, (156, 150, 144)),
    "Éris": (1163.0, (236, 236, 236)), "Haumea": (780.0, (226, 226, 226)),
    "Makemake": (715.0, (206, 166, 136)),
    "Vesta": (262.7, (176, 170, 160)), "Palas": (256.0, (150, 150, 156)),
    "Juno": (123.3, (170, 160, 150)), "Hígia": (216.5, (110, 106, 102)),
    "Psiquê": (111.0, (170, 170, 176)), "Eros": (8.4, (176, 150, 120)),
    "Bennu": (0.245, (90, 86, 82)), "Apófis": (0.17, (150, 140, 130)),
    "Ryugu": (0.45, (80, 76, 72)), "Arrokoth": (9.0, (190, 120, 90)),
    "Sedna": (500.0, (196, 90, 70)), "Gonggong": (615.0, (190, 110, 90)),
    "Quaoar": (555.0, (176, 130, 110)), "Orco": (455.0, (160, 160, 166)),
    "Halley": (5.5, (180, 220, 255)), "Encke": (2.4, (180, 220, 255)),
    "Churyumov-Gerasimenko": (2.0, (180, 220, 255)), "Swift-Tuttle": (13.0, (180, 220, 255)),
    "Tempel-Tuttle": (1.8, (180, 220, 255)), "Pons-Brooks": (15.0, (180, 220, 255)),
    "Tempel 1": (3.0, (180, 220, 255)), "Hale-Bopp": (30.0, (180, 220, 255)),
}

# Anéis: (raio interno, raio externo) em km, no equador do planeta
ANEIS = {"Saturno": (66900.0, 136775.0), "Urano": (41800.0, 51150.0)}

# Nuvens de pontos: cor por grupo do snapshot
CORES_NUVENS = {
    "cinturao": (150, 136, 116), "troianos": (176, 150, 96), "neo": (226, 120, 90),
    "kuiper": (126, 156, 196), "centauros": (156, 176, 146),
    "cometas": (156, 216, 255), "cometas_halley": (190, 230, 255),
}
CORES_SATELITES = {
    "estacoes": (255, 255, 255), "ciencia": (126, 236, 196), "clima": (126, 196, 255),
    "gnss": (255, 206, 96), "geo": (236, 150, 236), "starlink": (170, 176, 196),
}

# Ordem da tecla P: do Sol para fora, cada planeta seguido das suas luas e das
# naves que orbitam perto dele
ORDEM_FOCO = (
    "Sol", "Mercúrio", "Vênus", "Terra", "ISS", "Hubble", "Tiangong", "Lua", "James Webb",
    "Marte", "Fobos", "Deimos", "Ceres", "Vesta", "Palas", "Júpiter", "Io", "Europa",
    "Ganimedes", "Calisto", "Saturno", "Titã", "Encélado", "Reia", "Jápeto", "Urano",
    "Titânia", "Oberon", "Miranda", "Netuno", "Tritão", "Plutão", "Caronte", "Haumea",
    "Makemake", "Éris", "Arrokoth", "Sedna", "Halley", "Hale-Bopp",
)


# ------------------------------------------------------------------ leitura
_CACHE = {}


def ler_json(nome):
    """Snapshot de dados/, ou None se ausente ou corrompido (a cena degrada, não quebra)."""
    if nome in _CACHE:
        return _CACHE[nome]
    caminho = os.path.join(PASTA_DADOS, nome)
    try:
        with open(caminho, encoding="utf-8") as arq:
            conteudo = json.load(arq)
    except (OSError, ValueError):
        conteudo = None
    _CACHE[nome] = conteudo
    return conteudo


def caminho_mapa(nome):
    """Arquivo do mapa de cor, se foi baixado."""
    for extensao in (".jpg", ".png"):
        caminho = os.path.join(PASTA_MAPAS, nome + extensao)
        if os.path.isfile(caminho):
            return caminho
    return None


def cor_da_estrela(bv):
    """
    Cor aparente pelo índice B−V: temperatura pela fórmula de Ballesteros e
    temperatura em RGB pela aproximação de corpo negro de Tanner Helland.
    """
    bv = max(-0.4, min(2.0, bv))
    t = 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62)) / 100.0
    if t <= 66.0:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19.0 else 138.5177312231 * math.log(t - 10.0) - 305.0447927307
    else:
        r = 329.698727446 * (t - 60.0) ** -0.1332047592
        g = 288.1221695283 * (t - 60.0) ** -0.0755148492
        b = 255.0
    # dessatura um pouco: estrelas a olho nu parecem quase brancas
    return tuple(int(max(0.0, min(255.0, 0.55 * c + 0.45 * 235.0))) for c in (r, g, b))


def estrelas(vmag_max):
    """
    [(direção no mundo, vmag, cor, nome)] das estrelas do BSC5 até `vmag_max`,
    ou None sem snapshot. As estrelas ficam no infinito: basta a direção.
    """
    chave = ("estrelas", vmag_max)
    if chave in _CACHE:
        return _CACHE[chave]
    dados = ler_json("estrelas.json")
    saida = None
    if dados:
        saida = []
        for ra, dec, vmag, bv, nome in dados["dados"]:
            if vmag > vmag_max:
                continue
            cd = math.cos(math.radians(dec))
            eq = (cd * math.cos(math.radians(ra)), cd * math.sin(math.radians(ra)),
                  math.sin(math.radians(dec)))
            saida.append((ef.direcao_para_mundo(ef.equatorial_para_ecliptica(eq)), vmag,
                          cor_da_estrela(bv), nome))
    _CACHE[chave] = saida
    return saida


def elementos(nome_arquivo):
    """Dict nome -> elementos osculadores de luas.json ou pequenos_corpos.json."""
    dados = ler_json(nome_arquivo)
    return dados["corpos"] if dados else {}


def orbita_de_elementos(el, mu=None):
    """Órbita de dois corpos a partir de um registro do Horizons (km, graus, época TDB)."""
    n = math.radians(el["n_graus_s"]) * ef.SEGUNDOS_DIA if el.get("n_graus_s") else None
    return ef.Orbita(el["a"], el["e"], el["i"], el["om"], el["w"], el["ma"], el["epoca_jd"],
                     mu=mu or ef.GM_SOL, n=n)


def nuvens():
    """grupo -> lista de órbitas heliocêntricas dos pequenos corpos do SBDB."""
    if "nuvens" in _CACHE:
        return _CACHE["nuvens"]
    dados = ler_json("nuvens.json")
    saida = {}
    if dados:
        for grupo, linhas in dados["grupos"].items():
            orbitas = []
            for a_ua, e, i, om, w, ma, epoca in linhas:
                try:
                    orbitas.append(ef.Orbita(a_ua * ef.UA_KM, e, i, om, w, ma, epoca))
                except ValueError:
                    continue
            saida[grupo] = orbitas
    _CACHE["nuvens"] = saida
    return saida


def satelites():
    """grupo -> lista de OMM do snapshot do CelesTrak, e a data de geração."""
    dados = ler_json("satelites.json")
    if not dados:
        return {}, None
    return dados["grupos"], dados.get("gerado_em")


def tabela_jwst():
    """Vetores do James Webb relativos à Terra, ou None sem snapshot."""
    dados = ler_json("jwst.json")
    if not dados or not dados.get("vetores"):
        return None
    return ef.TabelaVetores([tuple(l) for l in dados["vetores"]])
