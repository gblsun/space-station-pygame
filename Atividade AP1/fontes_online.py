"""
Fontes de dados reais, baixadas pela rede só com a biblioteca padrão.

- ESA/Webb e ESA/Hubble: RSS das imagens publicadas (CC BY 4.0), em resolução
  de papel de parede para cobrir o fundo da tela.
- STScI: agenda oficial de observação do James Webb (o alvo de agora).
- CelesTrak: elementos médios dos satélites artificiais.
- JPL Horizons e SBDB: elementos de luas, planetas anões, asteroides e cometas,
  e os vetores do James Webb em torno de L2.

Nada aqui importa pygame, e a aplicação nunca espera a rede: tudo roda em
thread (`Tarefas`), com cache em disco, e a cena começa com os snapshots de
`dados/`. Os testes exercitam só os leitores, com textos de exemplo.
"""

import email.utils
import html
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

AGENTE = "AP1-Orbita2/1.0 (projeto academico de Computacao Grafica; Python urllib)"
TIMEOUT = 25


class ErroDeFonte(RuntimeError):
    """Falha ao obter ou interpretar uma fonte externa."""


# ============================================================
# 1. DOWNLOAD E CACHE
# ============================================================
def baixar(url, timeout=TIMEOUT, tentativas=3, espera=2.0, metodo="GET"):
    """Bytes da URL, com novas tentativas em erro de servidor ou de rede."""
    ultimo = None
    for k in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE}, method=metodo)
            with urllib.request.urlopen(req, timeout=timeout) as resposta:
                return resposta.read()
        except urllib.error.HTTPError as erro:
            ultimo = erro
            if erro.code < 500 and erro.code != 429:
                break                     # 404 não melhora tentando de novo
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            ultimo = erro
        if k + 1 < tentativas:
            time.sleep(espera * (k + 1))
    raise ErroDeFonte("%s -> %s" % (url, ultimo))


def existe(url, timeout=15):
    """HEAD: a URL responde 200? Usado para escolher o tamanho da imagem."""
    try:
        baixar(url, timeout=timeout, tentativas=1, metodo="HEAD")
        return True
    except ErroDeFonte:
        return False


def pasta_cache():
    """Cache fora do repositório, para downloads nunca sujarem o git."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    pasta = os.path.join(base, "AP1-Orbita2")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def com_cache(nome, validade_s, obter):
    """
    Conteúdo em cache se ainda válido; senão chama `obter()` e grava. Se a rede
    falhar, devolve o cache vencido — dado velho é melhor que nenhum. Devolve
    (bytes, idade_em_segundos).
    """
    caminho = os.path.join(pasta_cache(), nome)
    idade = None
    if os.path.isfile(caminho):
        idade = time.time() - os.path.getmtime(caminho)
        if idade < validade_s:
            with open(caminho, "rb") as arq:
                return arq.read(), idade
    try:
        dados = obter()
    except ErroDeFonte:
        if idade is None:
            raise
        with open(caminho, "rb") as arq:
            return arq.read(), idade
    temporario = caminho + ".tmp"
    with open(temporario, "wb") as arq:
        arq.write(dados)
    os.replace(temporario, caminho)       # nunca deixa um arquivo pela metade
    return dados, 0.0


# ============================================================
# 2. JPL HORIZONS E SBDB
# ============================================================
HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
SBDB_CONSULTA = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"


def _url_horizons(**parametros):
    partes = ["format=text"]
    for chave, valor in parametros.items():
        # ';' e '=' precisam ir codificados: "COMMAND='1;'" cru volta 400 Bad Request
        partes.append("%s=%s" % (chave, urllib.parse.quote("'%s'" % valor, safe="'@")))
    return HORIZONS + "?" + "&".join(partes)


def linhas_horizons(texto):
    """Linhas CSV entre $$SOE e $$EOE, já divididas e sem campos vazios do fim."""
    ini = texto.find("$$SOE")
    fim = texto.find("$$EOE")
    if ini < 0 or fim < 0:
        trecho = texto.strip().splitlines()[-6:]
        raise ErroDeFonte("Horizons sem efeméride: " + " | ".join(trecho))
    linhas = []
    for bruta in texto[ini + 5:fim].strip().splitlines():
        campos = [c.strip() for c in bruta.split(",")]
        while campos and not campos[-1]:
            campos.pop()
        if campos:
            linhas.append(campos)
    return linhas


def elementos_horizons(comando, centro, data):
    """
    Elementos osculadores eclípticos J2000 (km, graus) no início de `data`.
    Colunas do CSV: JDTDB, data, EC, QR, IN, OM, W, Tp, N, MA, TA, A, AD, PR.
    """
    inicio = data.strftime("%Y-%m-%d")
    fim = (data + timedelta(days=1)).strftime("%Y-%m-%d")
    url = _url_horizons(COMMAND=comando, EPHEM_TYPE="ELEMENTS", CENTER=centro,
                        START_TIME=inicio, STOP_TIME=fim, STEP_SIZE="1 d",
                        REF_PLANE="ECLIPTIC", OUT_UNITS="KM-S", CSV_FORMAT="YES",
                        OBJ_DATA="NO")
    c = linhas_horizons(baixar(url).decode("utf-8", "replace"))[0]
    return {"epoca_jd": float(c[0]), "e": float(c[2]), "i": float(c[4]),
            "om": float(c[5]), "w": float(c[6]), "n_graus_s": float(c[8]),
            "ma": float(c[9]), "a": float(c[11])}


def vetores_horizons(comando, centro, inicio, fim, passo="1 d"):
    """Lista de (jd, x, y, z) em km, eclíptica J2000."""
    # com hora e minuto: janelas menores que um dia (a ISS) precisam deles
    url = _url_horizons(COMMAND=comando, EPHEM_TYPE="VECTORS", CENTER=centro,
                        START_TIME=inicio.strftime("%Y-%m-%d %H:%M"),
                        STOP_TIME=fim.strftime("%Y-%m-%d %H:%M"), STEP_SIZE=passo,
                        VEC_TABLE="1", REF_PLANE="ECLIPTIC", OUT_UNITS="KM-S",
                        CSV_FORMAT="YES", OBJ_DATA="NO")
    return [(float(c[0]), float(c[2]), float(c[3]), float(c[4]))
            for c in linhas_horizons(baixar(url).decode("utf-8", "replace"))]


def consulta_sbdb(campos, limite, **filtros):
    """Consulta em lote ao SBDB; devolve uma lista de dicts campo -> texto."""
    parametros = {"fields": ",".join(campos), "limit": str(limite)}
    parametros.update({k.replace("_", "-"): v for k, v in filtros.items()})
    url = SBDB_CONSULTA + "?" + urllib.parse.urlencode(parametros)
    # o SBDB responde 500 quando recebe consultas em sequência rápida
    resposta = json.loads(baixar(url, timeout=90, tentativas=4, espera=6.0))
    nomes = resposta["fields"]
    return [dict(zip(nomes, linha)) for linha in resposta.get("data", [])]


# ============================================================
# 3. CELESTRAK
# ============================================================
CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?GROUP=%s&FORMAT=json"
CAMPOS_OMM = ("OBJECT_NAME", "NORAD_CAT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY",
              "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY",
              "MEAN_MOTION_DOT")


CELESTRAK_SUPLEMENTAR = ("https://celestrak.org/NORAD/elements/supplemental/"
                         "sup-gp.php?FILE=%s&FORMAT=json")


def grupo_celestrak(grupo):
    """
    Elementos médios de um grupo do CelesTrak, só com os campos usados. O
    CelesTrak recusa (403) downloads repetidos do mesmo arquivo em pouco tempo;
    para o Starlink há o arquivo suplementar, publicado pelo próprio operador.
    """
    try:
        dados = json.loads(baixar(CELESTRAK % grupo, tentativas=2))
    except ErroDeFonte:
        if grupo != "starlink":
            raise
        dados = json.loads(baixar(CELESTRAK_SUPLEMENTAR % grupo, tentativas=2, timeout=90))
    return [{k: item.get(k) for k in CAMPOS_OMM} for item in dados]


# ============================================================
# 4. IMAGENS DO ESA/WEBB E DO ESA/HUBBLE
# ============================================================
FEEDS = {
    "webb": ("https://esawebb.org/images/feed/", "https://cdn.esawebb.org/archives/images/",
             "ESA/Webb"),
    "hubble": ("https://esahubble.org/images/feed/", "https://cdn.esahubble.org/archives/images/",
               "ESA/Hubble"),
}
# ids da imagem principal de cada divulgação: weic2619a, heic2612a, potm2608a
_ID_PRINCIPAL = re.compile(r"^(weic|heic|potm|potw)\d+a$")
# do maior para o menor; o ESA gera todos para as imagens de divulgação
TAMANHOS = (("wallpaper_uhd", 3840), ("wallpaper_qhd", 2560), ("wallpaper_fhd", 1920),
            ("publicationjpg", 0), ("screen", 0))


def ler_rss_imagens(xml_bytes, cdn):
    """Itens do RSS: título, página, id da imagem, data e a legenda em texto puro."""
    texto = xml_bytes.decode("utf-8", "replace")
    itens = []
    for bloco in re.findall(r"<item>(.*?)</item>", texto, re.S):
        def campo(nome):
            m = re.search(r"<%s>(.*?)</%s>" % (nome, nome), bloco, re.S)
            return html.unescape(m.group(1).strip()) if m else ""
        pagina = campo("link")
        ident = pagina.rstrip("/").rsplit("/", 1)[-1]
        data = None
        if campo("pubDate"):
            try:
                data = email.utils.parsedate_to_datetime(campo("pubDate"))
            except (TypeError, ValueError):
                data = None
        legenda = re.sub(r"<[^>]+>", " ", campo("description"))
        itens.append({"titulo": campo("title"), "pagina": pagina, "id": ident,
                      "data": data, "legenda": " ".join(legenda.split()), "cdn": cdn})
    return itens


def escolher_imagem(itens):
    """A divulgação mais recente com imagem principal; recortes e colagens ficam de fora."""
    for item in itens:
        if _ID_PRINCIPAL.match(item["id"]):
            return item
    return itens[0] if itens else None


def urls_da_imagem(item, largura_tela):
    """
    Candidatos em ordem de preferência: o menor papel de parede com folga de
    30% sobre a largura da tela — reduzido com filtro, fica mais nítido que um
    arquivo exatamente do tamanho da tela —, depois os maiores, depois os
    menores e, por fim, os formatos que nem toda imagem tem.
    """
    papeis = [nome for nome, largura in TAMANHOS if largura]
    cobrem = [nome for nome, largura in TAMANHOS if largura >= largura_tela * 1.3]
    inicio = papeis.index(cobrem[-1]) if cobrem else 0
    ordem = papeis[inicio::-1] + papeis[inicio + 1:] + [n for n, l in TAMANHOS if not l]
    return [item["cdn"] + nome + "/" + item["id"] + ".jpg" for nome in ordem]


def credito_da_pagina(html_bytes, padrao):
    """Linha de crédito exigida pela licença CC BY 4.0, lida da página da imagem."""
    texto = html_bytes.decode("utf-8", "replace")
    m = re.search(r'class="credit"[^>]*>(.*?)</div>', texto, re.S)
    if not m:
        return padrao
    credito = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).split())
    return credito or padrao


def imagem_mais_recente(fonte, largura_tela):
    """
    Baixa (com cache) a imagem mais recente de "webb" ou "hubble". Devolve um
    dict com os bytes do JPEG, título, data, crédito e a URL usada.
    """
    feed, cdn, credito_padrao = FEEDS[fonte]
    rss, _ = com_cache("feed-%s.xml" % fonte, 6 * 3600, lambda: baixar(feed))
    item = escolher_imagem(ler_rss_imagens(rss, cdn))
    if item is None:
        raise ErroDeFonte("feed de %s sem itens" % fonte)
    for url in urls_da_imagem(item, largura_tela):
        nome = "img-%s-%s" % (fonte, url.rsplit("/", 2)[-2] + "-" + item["id"] + ".jpg")
        try:
            dados, _ = com_cache(nome, 30 * 24 * 3600, lambda u=url: baixar(u, timeout=60))
            break
        except ErroDeFonte:
            continue
    else:
        raise ErroDeFonte("nenhum tamanho disponível para %s" % item["id"])
    try:
        pagina, _ = com_cache("pagina-%s.html" % item["id"], 30 * 24 * 3600,
                              lambda: baixar(item["pagina"]))
        credito = credito_da_pagina(pagina, credito_padrao)
    except ErroDeFonte:
        credito = credito_padrao
    return {"fonte": fonte, "bytes": dados, "titulo": item["titulo"], "data": item["data"],
            "credito": credito, "url": url, "pagina": item["pagina"]}


# ============================================================
# 5. AGENDA DO JAMES WEBB (STScI)
# ============================================================
STSCI_AGENDAS = "https://www.stsci.edu/jwst/science-execution/observing-schedules"
STSCI_ARQUIVO = ("https://www.stsci.edu/files/live/sites/www/files/home/jwst/"
                 "science-execution/observing-schedules/_documents/%s.txt")


def agendas_publicadas(html_bytes):
    """Nomes dos relatórios semanais citados na página, do mais novo ao mais velho."""
    nomes = set(re.findall(r"_documents/(\d{8}_report_\d{8})\.txt",
                           html_bytes.decode("utf-8", "replace")))
    return sorted(nomes, reverse=True)


def _duracao(texto):
    """'00/02:07:27' (dias/horas:min:s) -> timedelta."""
    m = re.match(r"(\d+)/(\d+):(\d+):(\d+)", texto.strip())
    if not m:
        return None
    d, h, mi, s = (int(g) for g in m.groups())
    return timedelta(days=d, hours=h, minutes=mi, seconds=s)


def ler_agenda_webb(texto):
    """
    Tabela de largura fixa da agenda. As colunas são deduzidas da linha de
    traços logo abaixo do cabeçalho, então a leitura não depende de posições
    fixas no código. Só entram as visitas com horário de início.
    """
    linhas = texto.splitlines()
    for k, linha in enumerate(linhas):
        if linha.startswith("-----") and k > 0:
            cabecalho, tracos, corpo = linhas[k - 1], linha, linhas[k + 1:]
            break
    else:
        raise ErroDeFonte("agenda sem cabeçalho reconhecível")
    faixas = [(m.start(), m.end()) for m in re.finditer(r"-+", tracos)]
    nomes = [cabecalho[a:b].strip() for a, b in faixas]
    visitas = []
    for linha in corpo:
        if not linha.strip():
            continue
        campos = {}
        for j, (a, _b) in enumerate(faixas):
            fim = faixas[j + 1][0] if j + 1 < len(faixas) else len(linha)
            campos[nomes[j]] = linha[a:fim].strip()
        try:
            inicio = datetime.strptime(campos.get("SCHEDULED START TIME", ""),
                                       "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue                     # paralelas "^ATTACHED TO PRIME^"
        duracao = _duracao(campos.get("DURATION", "")) or timedelta(0)
        visitas.append({"visita": campos.get("VISIT ID", ""), "inicio": inicio,
                        "fim": inicio + duracao,
                        "instrumento": campos.get("SCIENCE INSTRUMENT AND MODE", ""),
                        "alvo": campos.get("TARGET NAME", ""),
                        "categoria": campos.get("CATEGORY", ""),
                        "palavras": campos.get("KEYWORDS", ""),
                        "tipo": campos.get("VISIT TYPE", "")})
    return visitas


def observacao_em(visitas, agora):
    """
    (visita, situação): a visita em andamento, com situação "agora"; sem
    nenhuma em andamento (manobra, calibração sem alvo), a próxima.
    """
    em_curso = [v for v in visitas if v["inicio"] <= agora < v["fim"] and v["alvo"]]
    if em_curso:
        return em_curso[-1], "agora"
    proximas = [v for v in visitas if v["inicio"] > agora and v["alvo"]]
    if proximas:
        return min(proximas, key=lambda v: v["inicio"]), "próxima"
    return None, "sem agenda para este horário"


def agenda_webb():
    """Visitas das duas agendas mais recentes (a semana corrente costuma estar numa delas)."""
    pagina, _ = com_cache("stsci-agendas.html", 6 * 3600, lambda: baixar(STSCI_AGENDAS))
    visitas = []
    for nome in agendas_publicadas(pagina)[:2]:
        texto, _ = com_cache("agenda-%s.txt" % nome, 24 * 3600,
                             lambda n=nome: baixar(STSCI_ARQUIVO % n))
        visitas.extend(ler_agenda_webb(texto.decode("utf-8", "replace")))
    if not visitas:
        raise ErroDeFonte("nenhuma agenda publicada encontrada")
    return visitas


# ============================================================
# 6. TAREFAS EM SEGUNDO PLANO
# ============================================================
class Tarefas:
    """
    Executa funções numa thread e guarda o resultado para o laço principal
    buscar quando quiser. A App consulta `resultado(nome)` uma vez por quadro:
    nenhuma chamada de rede bloqueia a animação, e uma falha só vira aviso.
    """

    def __init__(self):
        self._trava = threading.Lock()
        self._estado = {}

    def iniciar(self, nome, funcao, *args):
        with self._trava:
            if self._estado.get(nome, ("",))[0] == "executando":
                return False
            self._estado[nome] = ("executando", None)

        def corpo():
            try:
                saida = ("pronto", funcao(*args))
            except Exception as erro:      # qualquer falha de fonte vira estado, não trava a App
                saida = ("falhou", "%s: %s" % (type(erro).__name__, erro))
            with self._trava:
                self._estado[nome] = saida

        threading.Thread(target=corpo, name="ap1-" + nome, daemon=True).start()
        return True

    def estado(self, nome):
        with self._trava:
            return self._estado.get(nome, ("parado", None))

    def retirar(self, nome):
        """Resultado pronto (e o esquece), ou None enquanto não houver."""
        with self._trava:
            situacao, valor = self._estado.get(nome, ("parado", None))
            if situacao != "pronto":
                return None
            self._estado[nome] = ("entregue", None)
            return valor

    def consumir(self, nome):
        """
        (situação, valor) de uma tarefa terminada — pronta ou com falha — e a
        marca como entregue; (situação, None) enquanto ainda roda.
        """
        with self._trava:
            situacao, valor = self._estado.get(nome, ("parado", None))
            if situacao in ("pronto", "falhou"):
                self._estado[nome] = ("entregue", None)
                return situacao, valor
            return situacao, None


# ============================================================
# 7. CONJUNTOS USADOS PELA APLICAÇÃO E PELO SCRIPT DE SNAPSHOT
# ============================================================
# (nome no snapshot, grupo do CelesTrak, amostragem). O Starlink tem mais de
# 11 mil satélites: um a cada 12 basta para mostrar a casca da constelação.
GRUPOS_SATELITES = (("estacoes", "stations", 1), ("ciencia", "science", 1),
                    ("clima", "weather", 1), ("gnss", "gnss", 1), ("geo", "geo", 1),
                    ("starlink", "starlink", 12))


def satelites_por_grupo(obter_grupo=grupo_celestrak):
    """
    Grupos de satélites sem repetição (um satélite pode estar em dois grupos;
    fica no primeiro). Grupo que falhar fica de fora, sem derrubar os outros.
    """
    vistos = set()
    saida = {}
    for nome, grupo, passo in GRUPOS_SATELITES:
        try:
            itens = obter_grupo(grupo)
        except ErroDeFonte:
            continue
        itens = sorted(itens, key=lambda o: int(o["NORAD_CAT_ID"]))
        escolhidos = []
        for k, item in enumerate(itens):
            if k % passo or item["NORAD_CAT_ID"] in vistos:
                continue
            vistos.add(item["NORAD_CAT_ID"])
            escolhidos.append(item)
        saida[nome] = escolhidos
    if not saida:
        raise ErroDeFonte("nenhum grupo do CelesTrak respondeu")
    return saida


def satelites_atualizados():
    """
    Elementos frescos com cache de 12 h por grupo — o CelesTrak pede que o
    mesmo arquivo não seja baixado mais que uma vez a cada duas horas.
    """
    def obter(grupo):
        dados, _ = com_cache("celestrak-%s.json" % grupo, 12 * 3600,
                             lambda: json.dumps(grupo_celestrak(grupo)).encode("utf-8"))
        return json.loads(dados)

    return satelites_por_grupo(obter), datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def vetores_jwst():
    """Vetores diários do James Webb relativos à Terra, de 30 dias atrás a um ano à frente."""
    def obter():
        hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        for dias in (365, 180, 90):
            try:
                linhas = vetores_horizons("-170", "500@399", hoje - timedelta(days=30),
                                          hoje + timedelta(days=dias))
                return json.dumps(linhas).encode("utf-8")
            except ErroDeFonte:
                continue
        raise ErroDeFonte("Horizons sem efeméride do James Webb")

    dados, _ = com_cache("jwst-vetores.json", 3 * 24 * 3600, obter)
    return [tuple(l) for l in json.loads(dados)]
