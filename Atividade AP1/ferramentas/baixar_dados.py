"""
Gera os snapshots de dados/ que a cena usa quando não há rede (e nos testes).

    python "Atividade AP1/ferramentas/baixar_dados.py"                 # tudo
    python "Atividade AP1/ferramentas/baixar_dados.py" luas satelites  # só alguns

Conjuntos: estrelas, luas, pequenos, nuvens, satelites, jwst, mapas.

Cada JSON guarda a fonte, a data de geração e a época dos elementos, para a
própria aplicação poder dizer de quando são os dados que está mostrando.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_AP1 = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ_AP1)

import fontes_online as fo  # noqa: E402

DADOS = os.path.join(RAIZ_AP1, "dados")
HOJE = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def gravar(nome, conteudo):
    os.makedirs(DADOS, exist_ok=True)
    caminho = os.path.join(DADOS, nome)
    with open(caminho, "w", encoding="utf-8") as arq:
        json.dump(conteudo, arq, ensure_ascii=False, separators=(",", ":"))
    print("  -> dados/%s (%.0f KB)" % (nome, os.path.getsize(caminho) / 1024))


def cabecalho(fonte, **extra):
    base = {"fonte": fonte, "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    base.update(extra)
    return base


# ------------------------------------------------------------------ estrelas
def estrelas():
    """Yale Bright Star Catalogue (BSC5) pelo VizieR: posição, magnitude e cor."""
    consulta = ("/viz-bin/asu-tsv?-source=V/50/catalog&-out=RAJ2000&-out=DEJ2000"
                "&-out=Vmag&-out=B-V&-out=Name&Vmag=%3C6.0&-out.max=10000")
    texto = None
    for base in ("https://vizier.cfa.harvard.edu", "http://vizier.cds.unistra.fr"):
        try:
            texto = fo.baixar(base + consulta, timeout=90).decode("latin-1")
            break
        except fo.ErroDeFonte as erro:
            print("  falhou em %s: %s" % (base, erro))
    if texto is None:
        raise fo.ErroDeFonte("VizieR indisponível")
    linhas = []
    for bruta in texto.splitlines():
        if not bruta or bruta.startswith(("#", "RAJ", '"h', "--")):
            continue
        partes = bruta.split("\t")
        if len(partes) < 3 or not partes[2].strip():
            continue
        try:
            h, m, s = (float(x) for x in partes[0].split())
            dg, dm, ds = partes[1].split()
            sinal = -1.0 if dg.startswith("-") else 1.0
            dec = sinal * (abs(float(dg)) + float(dm) / 60.0 + float(ds) / 3600.0)
            ra = 15.0 * (h + m / 60.0 + s / 3600.0)
            vmag = float(partes[2])
            bv = float(partes[3]) if len(partes) > 3 and partes[3].strip() else 0.6
        except ValueError:
            continue
        nome = partes[4].strip() if len(partes) > 4 and vmag < 2.0 else ""
        linhas.append([round(ra, 4), round(dec, 4), round(vmag, 2), round(bv, 2), nome])
    linhas.sort(key=lambda l: l[2])
    gravar("estrelas.json", dict(cabecalho("VizieR V/50 (Yale Bright Star Catalogue, 5a ed.)"),
                                 campos=["ra", "dec", "vmag", "bv", "nome"], dados=linhas))


# ---------------------------------------------------------------------- luas
LUAS = (
    ("Fobos", "401", "Marte"), ("Deimos", "402", "Marte"),
    ("Io", "501", "Júpiter"), ("Europa", "502", "Júpiter"), ("Ganimedes", "503", "Júpiter"),
    ("Calisto", "504", "Júpiter"), ("Amalteia", "505", "Júpiter"),
    ("Mimas", "601", "Saturno"), ("Encélado", "602", "Saturno"), ("Tétis", "603", "Saturno"),
    ("Dione", "604", "Saturno"), ("Reia", "605", "Saturno"), ("Titã", "606", "Saturno"),
    ("Hipérion", "607", "Saturno"), ("Jápeto", "608", "Saturno"), ("Febe", "609", "Saturno"),
    ("Ariel", "701", "Urano"), ("Umbriel", "702", "Urano"), ("Titânia", "703", "Urano"),
    ("Oberon", "704", "Urano"), ("Miranda", "705", "Urano"),
    ("Tritão", "801", "Netuno"), ("Nereida", "802", "Netuno"), ("Proteu", "808", "Netuno"),
    ("Caronte", "901", "Plutão"),
)
CENTRO = {"Marte": "500@499", "Júpiter": "500@599", "Saturno": "500@699",
          "Urano": "500@799", "Netuno": "500@899", "Plutão": "500@999"}


def luas():
    saida = {}
    for nome, codigo, pai in LUAS:
        try:
            el = fo.elementos_horizons(codigo, CENTRO[pai], HOJE)
        except fo.ErroDeFonte as erro:
            print("  %s: %s" % (nome, erro))
            continue
        el["pai"] = pai
        saida[nome] = el
        print("  %-10s a=%10.0f km  e=%.4f  i=%6.2f" % (nome, el["a"], el["e"], el["i"]))
        time.sleep(0.4)
    gravar("luas.json", dict(cabecalho("JPL Horizons, elementos osculadores eclípticos J2000 "
                                       "relativos ao planeta", epoca=HOJE.strftime("%Y-%m-%d")),
                             corpos=saida))


# -------------------------------------------------- planetas anões e notáveis
PEQUENOS = (
    ("Plutão", "999", "anão"), ("Ceres", "1;", "anão"), ("Éris", "136199;", "anão"),
    ("Haumea", "136108;", "anão"), ("Makemake", "136472;", "anão"),
    ("Vesta", "4;", "asteroide"), ("Palas", "2;", "asteroide"), ("Juno", "3;", "asteroide"),
    ("Hígia", "10;", "asteroide"), ("Psiquê", "16;", "asteroide"), ("Eros", "433;", "asteroide"),
    ("Bennu", "101955;", "asteroide"), ("Apófis", "99942;", "asteroide"),
    ("Ryugu", "162173;", "asteroide"), ("Arrokoth", "486958;", "transnetuniano"),
    ("Sedna", "90377;", "transnetuniano"), ("Gonggong", "225088;", "transnetuniano"),
    ("Quaoar", "50000;", "transnetuniano"), ("Orco", "90482;", "transnetuniano"),
    ("Halley", "DES=1P;CAP;NOFRAG;", "cometa"), ("Encke", "DES=2P;CAP;NOFRAG;", "cometa"),
    ("Churyumov-Gerasimenko", "DES=67P;CAP;NOFRAG;", "cometa"),
    ("Swift-Tuttle", "DES=109P;CAP;NOFRAG;", "cometa"),
    ("Tempel-Tuttle", "DES=55P;CAP;NOFRAG;", "cometa"),
    ("Pons-Brooks", "DES=12P;CAP;NOFRAG;", "cometa"),
    ("Tempel 1", "DES=9P;CAP;NOFRAG;", "cometa"),
    ("Hale-Bopp", "DES=C/1995 O1;CAP;", "cometa"),
)


def pequenos():
    saida = {}
    for nome, comando, tipo in PEQUENOS:
        try:
            el = fo.elementos_horizons(comando, "500@10", HOJE)
        except fo.ErroDeFonte as erro:
            print("  %s: %s" % (nome, erro))
            continue
        if not (0.0 <= el["e"] < 1.0) or el["a"] <= 0.0:
            print("  %s: órbita aberta, ignorada" % nome)
            continue
        el["tipo"] = tipo
        saida[nome] = el
        print("  %-22s a=%6.2f UA  e=%.3f" % (nome, el["a"] / fo_ua(), el["e"]))
        time.sleep(0.4)
    gravar("pequenos_corpos.json",
           dict(cabecalho("JPL Horizons, elementos osculadores heliocêntricos eclípticos J2000",
                          epoca=HOJE.strftime("%Y-%m-%d")), corpos=saida))


def fo_ua():
    return 149597870.7


# -------------------------------------------------------------------- nuvens
NUVENS = (
    ("cinturao", {"sb_class": "MBA", "sort": "-diameter"}, 2000),
    ("troianos", {"sb_class": "TJN", "sort": "-diameter"}, 400),
    ("neo", {"sb_group": "neo", "sort": "-diameter"}, 250),
    ("kuiper", {"sb_class": "TNO"}, 900),
    ("centauros", {"sb_class": "CEN"}, 120),
    ("cometas", {"sb_kind": "c", "sb_class": "JFc"}, 350),
    ("cometas_halley", {"sb_kind": "c", "sb_class": "HTC"}, 80),
)


def nuvens():
    """Milhares de pequenos corpos reais do SBDB, em arrays compactos."""
    campos = ["a", "e", "i", "om", "w", "ma", "tp", "epoch"]
    saida = {}
    for nome, filtros, limite in NUVENS:
        try:
            linhas = fo.consulta_sbdb(campos, limite, **filtros)
        except fo.ErroDeFonte as erro:
            print("  %s: %s" % (nome, erro))
            continue
        compactas = []
        for l in linhas:
            try:
                a, e, i = float(l["a"]), float(l["e"]), float(l["i"])
                om, w, epoca = float(l["om"]), float(l["w"]), float(l["epoch"])
            except (TypeError, ValueError):
                continue
            if not (0.0 <= e < 1.0) or a <= 0.0:
                continue
            if l.get("ma") not in (None, ""):
                ma = float(l["ma"])
            elif l.get("tp") not in (None, ""):
                # cometas trazem o instante do periélio em vez da anomalia média
                n = 0.9856076686 / a ** 1.5
                ma = math.fmod(n * (epoca - float(l["tp"])), 360.0)
            else:
                continue
            compactas.append([round(a, 5), round(e, 5), round(i, 3), round(om, 3),
                              round(w, 3), round(ma, 3), round(epoca, 1)])
        saida[nome] = compactas
        print("  %-15s %5d objetos" % (nome, len(compactas)))
        time.sleep(3.0)                   # o SBDB rejeita rajadas de consultas
    gravar("nuvens.json", dict(cabecalho("JPL Small-Body Database (SBDB Query API)"),
                               campos=["a_ua", "e", "i", "om", "w", "ma", "epoca_jd"],
                               grupos=saida))


# ----------------------------------------------------------------- satélites
def satelites():
    """Mesma seleção que a aplicação usa ao atualizar online (fontes_online.satelites_por_grupo)."""
    def obter(grupo):
        try:
            itens = fo.grupo_celestrak(grupo)
        except fo.ErroDeFonte as erro:
            print("  %s: %s" % (grupo, erro))
            raise
        time.sleep(1.0)
        return itens

    saida = fo.satelites_por_grupo(obter)
    for nome, lista in saida.items():
        print("  %-9s %5d" % (nome, len(lista)))
    gravar("satelites.json", dict(cabecalho("CelesTrak GP (elementos médios, formato OMM)",
                                            amostragem={"starlink": 12}), grupos=saida))


# ---------------------------------------------------------------------- jwst
def jwst():
    """Vetores diários do James Webb relativos à Terra; o Horizons limita o futuro."""
    for dias in (540, 365, 180, 90):
        try:
            linhas = fo.vetores_horizons("-170", "500@399", HOJE - timedelta(days=30),
                                         HOJE + timedelta(days=dias), "1 d")
            break
        except fo.ErroDeFonte as erro:
            print("  +%d dias: %s" % (dias, str(erro)[:160]))
    else:
        raise fo.ErroDeFonte("Horizons sem efeméride do JWST")
    gravar("jwst.json", dict(cabecalho("JPL Horizons, JWST (-170) geocêntrico eclíptico J2000, km"),
                             vetores=[[round(v, 3) if k == 0 else round(v, 1)
                                       for k, v in enumerate(l)] for l in linhas]))


# --------------------------------------------------------------------- mapas
MAPAS = (
    ("sol", "2k_sun.jpg", (512, 256)), ("mercurio", "2k_mercury.jpg", (512, 256)),
    ("venus", "2k_venus_atmosphere.jpg", (512, 256)),
    ("terra", "2k_earth_daymap.jpg", (1024, 512)), ("nuvens", "2k_earth_clouds.jpg", (512, 256)),
    ("lua", "2k_moon.jpg", (512, 256)), ("marte", "2k_mars.jpg", (512, 256)),
    ("jupiter", "2k_jupiter.jpg", (512, 256)), ("saturno", "2k_saturn.jpg", (512, 256)),
    ("aneis_saturno", "2k_saturn_ring_alpha.png", (512, 16)),
    ("urano", "2k_uranus.jpg", (256, 128)), ("netuno", "2k_neptune.jpg", (256, 128)),
)
SSS = "https://www.solarsystemscope.com/textures/download/"


def _baixar_arquivo(url, destino):
    """urllib primeiro; o curl do sistema usa o repositório de certificados do Windows."""
    try:
        with open(destino, "wb") as arq:
            arq.write(fo.baixar(url, timeout=90))
        return
    except fo.ErroDeFonte:
        pass
    curl = shutil.which("curl")
    if curl is None:
        raise fo.ErroDeFonte("sem curl para " + url)
    subprocess.run([curl, "-sSfL", "-o", destino, url], check=True, timeout=180)


def mapas():
    """Mapas de cor Solar System Scope (CC BY 4.0), reduzidos: a cena amostra uma cor por face."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pasta = os.path.join(DADOS, "mapas")
    os.makedirs(pasta, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for nome, arquivo, tamanho in MAPAS:
            origem = os.path.join(tmp, arquivo)
            try:
                _baixar_arquivo(SSS + arquivo, origem)
            except (fo.ErroDeFonte, subprocess.SubprocessError) as erro:
                print("  %s: %s" % (nome, erro))
                continue
            imagem = pygame.image.load(origem)
            if imagem.get_bitsize() not in (24, 32):
                imagem = imagem.convert(32) if hasattr(imagem, "convert") else imagem
            reduzida = pygame.transform.smoothscale(imagem, tamanho)
            extensao = ".png" if arquivo.endswith(".png") else ".jpg"
            destino = os.path.join(pasta, nome + extensao)
            pygame.image.save(reduzida, destino)
            print("  %-14s %4dx%-4d %.0f KB" % (nome, tamanho[0], tamanho[1],
                                              os.path.getsize(destino) / 1024))
    with open(os.path.join(pasta, "LEIA-ME.txt"), "w", encoding="utf-8") as arq:
        arq.write("Mapas reduzidos a partir de Solar System Scope (solarsystemscope.com),\n"
                  "distribuidos sob a licenca Creative Commons Attribution 4.0 International.\n")


CONJUNTOS = {"estrelas": estrelas, "luas": luas, "pequenos": pequenos, "nuvens": nuvens,
             "satelites": satelites, "jwst": jwst, "mapas": mapas}


def main(argv):
    pedidos = argv or list(CONJUNTOS)
    falhas = []
    for nome in pedidos:
        print("== %s" % nome)
        try:
            CONJUNTOS[nome]()
        except Exception as erro:          # um conjunto falho não impede os outros
            print("  FALHOU: %s" % erro)
            falhas.append(nome)
    if falhas:
        print("Conjuntos com falha: %s" % ", ".join(falhas))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
