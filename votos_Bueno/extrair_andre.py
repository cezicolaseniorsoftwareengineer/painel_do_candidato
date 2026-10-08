import csv
import glob
import os
import time
import unicodedata
from collections import defaultdict

# ============================================================
# CONFIGURAÇÃO
# ============================================================

CANDIDATO = "15777"
NOME_CANDIDATO = "ANDRE BUENO"
PARTIDO = "MDB"


# ============================================================
# REGIÕES DA CAPITAL DE SÃO PAULO
#
# 57 zonas eleitorais da capital.
# Classificação territorial analítica:
# Leste / Norte / Sul / Oeste / Centro
# ============================================================

CAPITAL_REGIOES = {

    # -------------------------
    # CENTRO
    # -------------------------
    1: "Centro",    # Bela Vista
    3: "Centro",    # Santa Ifigênia

    # -------------------------
    # OESTE
    # -------------------------
    2: "Oeste",     # Perdizes
    5: "Oeste",     # Jardim Paulista
    250: "Oeste",   # Lapa
    251: "Oeste",   # Pinheiros
    346: "Oeste",   # Morumbi
    374: "Oeste",   # Rio Pequeno

    # -------------------------
    # NORTE
    # -------------------------
    249: "Norte",   # Santana
    254: "Norte",   # Vila Maria
    255: "Norte",   # Casa Verde
    256: "Norte",   # Tucuruvi
    325: "Norte",   # Pirituba
    327: "Norte",   # Nossa Senhora do Ó
    349: "Norte",   # Jaçanã
    376: "Norte",   # Brasilândia
    389: "Norte",   # Perus
    403: "Norte",   # Jaraguá
    420: "Norte",   # Vila Sabrina
    422: "Norte",   # Lauzane Paulista

    # -------------------------
    # SUL
    # -------------------------
    6: "Sul",       # Vila Mariana
    20: "Sul",      # Valo Velho
    246: "Sul",     # Santo Amaro
    258: "Sul",     # Indianópolis
    259: "Sul",     # Saúde
    260: "Sul",     # Ipiranga
    280: "Sul",     # Capela do Socorro
    320: "Sul",     # Jabaquara
    328: "Sul",     # Campo Limpo
    351: "Sul",     # Cidade Ademar
    371: "Sul",     # Grajaú
    372: "Sul",     # Piraporinha
    373: "Sul",     # Capão Redondo
    381: "Sul",     # Parelheiros
    408: "Sul",     # Jardim São Luís
    413: "Sul",     # Cursino
    418: "Sul",     # Pedreira

    # -------------------------
    # LESTE
    # -------------------------
    4: "Leste",     # Mooca
    247: "Leste",   # São Miguel Paulista
    248: "Leste",   # Itaquera
    252: "Leste",   # Penha de França
    253: "Leste",   # Tatuapé
    257: "Leste",   # Vila Prudente
    326: "Leste",   # Ermelino Matarazzo
    347: "Leste",   # Vila Matilde
    348: "Leste",   # Vila Formosa
    350: "Leste",   # Sapopemba
    352: "Leste",   # Itaim Paulista
    353: "Leste",   # Guaianases
    375: "Leste",   # São Mateus
    390: "Leste",   # Cangaíba
    392: "Leste",   # Ponte Rasa
    397: "Leste",   # Jardim Helena
    404: "Leste",   # Cidade Tiradentes
    405: "Leste",   # Conjunto José Bonifácio
    417: "Leste",   # Parque do Carmo
    421: "Leste",   # Teotônio Vilela
}


# ============================================================
# NOMES DAS 57 ZONAS DA CAPITAL
# ============================================================

CAPITAL_NOMES = {

    1: "Bela Vista",
    2: "Perdizes",
    3: "Santa Ifigênia",
    4: "Mooca",
    5: "Jardim Paulista",
    6: "Vila Mariana",

    20: "Valo Velho",

    246: "Santo Amaro",
    247: "São Miguel Paulista",
    248: "Itaquera",
    249: "Santana",
    250: "Lapa",
    251: "Pinheiros",
    252: "Penha de França",
    253: "Tatuapé",
    254: "Vila Maria",
    255: "Casa Verde",
    256: "Tucuruvi",
    257: "Vila Prudente",
    258: "Indianópolis",
    259: "Saúde",
    260: "Ipiranga",

    280: "Capela do Socorro",

    320: "Jabaquara",
    325: "Pirituba",
    326: "Ermelino Matarazzo",
    327: "Nossa Senhora do Ó",
    328: "Campo Limpo",

    346: "Morumbi",
    347: "Vila Matilde",
    348: "Vila Formosa",
    349: "Jaçanã",
    350: "Sapopemba",
    351: "Cidade Ademar",
    352: "Itaim Paulista",
    353: "Guaianases",

    371: "Grajaú",
    372: "Piraporinha",
    373: "Capão Redondo",
    374: "Rio Pequeno",
    375: "São Mateus",
    376: "Brasilândia",

    381: "Parelheiros",

    389: "Perus",
    390: "Cangaíba",
    392: "Ponte Rasa",
    397: "Jardim Helena",

    403: "Jaraguá",
    404: "Cidade Tiradentes",
    405: "Conjunto José Bonifácio",

    408: "Jardim São Luís",

    413: "Cursino",

    417: "Parque do Carmo",
    418: "Pedreira",

    420: "Vila Sabrina",
    421: "Teotônio Vilela",
    422: "Lauzane Paulista",
}


# ============================================================
# GRANDE SÃO PAULO
# Municípios da Região Metropolitana de São Paulo
# exceto a própria capital
# ============================================================

GRANDE_SP = {

    "ARUJA",
    "BARUERI",
    "BIRITIBA MIRIM",
    "CAIEIRAS",
    "CAJAMAR",
    "CARAPICUIBA",
    "COTIA",
    "DIADEMA",
    "EMBU DAS ARTES",
    "EMBU GUACU",
    "FERRAZ DE VASCONCELOS",
    "FRANCISCO MORATO",
    "FRANCO DA ROCHA",
    "GUARAREMA",
    "GUARULHOS",
    "ITAPECERICA DA SERRA",
    "ITAPEVI",
    "ITAQUAQUECETUBA",
    "JANDIRA",
    "JUQUITIBA",
    "MAIRIPORA",
    "MAUA",
    "MOGI DAS CRUZES",
    "OSASCO",
    "PIRAPORA DO BOM JESUS",
    "POA",
    "RIBEIRAO PIRES",
    "RIO GRANDE DA SERRA",
    "SALESOPOLIS",
    "SANTA ISABEL",
    "SANTANA DE PARNAIBA",
    "SANTO ANDRE",
    "SAO BERNARDO DO CAMPO",
    "SAO CAETANO DO SUL",
    "SAO LOURENCO DA SERRA",
    "SUZANO",
    "TABOAO DA SERRA",
    "VARGEM GRANDE PAULISTA",
}


# ============================================================
# LITORAL DO ESTADO DE SP
# ============================================================

LITORAL = {

    # Litoral Norte
    "UBATUBA",
    "CARAGUATATUBA",
    "SAO SEBASTIAO",
    "ILHABELA",

    # Baixada Santista
    "BERTIOGA",
    "GUARUJA",
    "SANTOS",
    "SAO VICENTE",
    "CUBATAO",
    "PRAIA GRANDE",
    "MONGAGUA",
    "ITANHAEM",
    "PERUIBE",

    # Litoral Sul
    "IGUAPE",
    "ILHA COMPRIDA",
    "CANANEIA",
}


# ============================================================
# FUNÇÕES
# ============================================================

def normalizar(texto):

    if texto is None:
        return ""

    texto = str(texto).strip().upper()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = texto.replace("-", " ")

    while "  " in texto:
        texto = texto.replace("  ", " ")

    return texto.strip()


def classificar_regiao(zona, municipio):

    municipio_norm = normalizar(municipio)

    # --------------------------------------------
    # CAPITAL
    # --------------------------------------------

    if municipio_norm == "SAO PAULO":

        return CAPITAL_REGIOES.get(
            zona,
            "Capital - não classificada"
        )

    # --------------------------------------------
    # GRANDE SP
    # --------------------------------------------

    if municipio_norm in GRANDE_SP:

        return "Grande SP"

    # --------------------------------------------
    # LITORAL
    # --------------------------------------------

    if municipio_norm in LITORAL:

        return "Litoral"

    # --------------------------------------------
    # RESTANTE DO ESTADO
    # --------------------------------------------

    return "Interior"


# ============================================================
# LOCALIZA CSV
# ============================================================

arquivos = glob.glob(
    "bweb_1t_SP_*.csv"
)

if not arquivos:

    print(
        "ERRO: não encontrei "
        "bweb_1t_SP_*.csv"
    )

    input(
        "Pressione ENTER..."
    )

    raise SystemExit


ARQUIVO = max(
    arquivos,
    key=os.path.getsize
)


print()
print("=" * 100)
print("ANDRÉ BUENO - 15777 - MDB")
print("VARREDURA COMPLETA DO ESTADO DE SÃO PAULO")
print("=" * 100)

print(
    "\nArquivo:",
    ARQUIVO
)

print(
    f"Tamanho: "
    f"{os.path.getsize(ARQUIVO)/(1024**3):.2f} GB"
)

print()
print(
    "Procurando TODOS os votos do 15777..."
)

print(
    "Não feche esta janela."
)

print()


# ============================================================
# CONTADORES
# ============================================================

total_estado = 0

linhas = 0

registros = 0

totais_regiao = defaultdict(int)

totais_zona = defaultdict(int)

totais_municipio = defaultdict(int)

zona_municipios = defaultdict(
    lambda: defaultdict(int)
)

inicio = time.time()


# ============================================================
# LEITURA DO CSV
# ============================================================

with open(
    ARQUIVO,
    "r",
    encoding="latin1",
    errors="replace",
    newline=""
) as f:

    reader = csv.reader(
        f,
        delimiter=";",
        quotechar='"'
    )

    cabecalho = next(reader)

    cabecalho = [
        c.strip().replace(
            "\ufeff",
            ""
        )
        for c in cabecalho
    ]

    print(
        "Colunas:",
        len(cabecalho)
    )

    obrigatorias = [

        "NR_ZONA",
        "NR_VOTAVEL",
        "QT_VOTOS",
        "NM_MUNICIPIO",

    ]

    for campo in obrigatorias:

        if campo not in cabecalho:

            print()
            print(
                "ERRO:"
                f" coluna {campo}"
                " não encontrada."
            )

            print(cabecalho)

            input(
                "Pressione ENTER..."
            )

            raise SystemExit


    idx_zona = cabecalho.index(
        "NR_ZONA"
    )

    idx_votavel = cabecalho.index(
        "NR_VOTAVEL"
    )

    idx_votos = cabecalho.index(
        "QT_VOTOS"
    )

    idx_municipio = cabecalho.index(
        "NM_MUNICIPIO"
    )


    idx_cargo = (

        cabecalho.index(
            "DS_CARGO_PERGUNTA"
        )

        if "DS_CARGO_PERGUNTA"
        in cabecalho

        else None
    )


    idx_nome = (

        cabecalho.index(
            "NM_VOTAVEL"
        )

        if "NM_VOTAVEL"
        in cabecalho

        else None
    )


    idx_partido = (

        cabecalho.index(
            "SG_PARTIDO"
        )

        if "SG_PARTIDO"
        in cabecalho

        else None
    )


    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    for row in reader:

        linhas += 1


        # ----------------------------------------------------
        # PROGRESSO
        # ----------------------------------------------------

        if linhas % 2_000_000 == 0:

            tempo = (
                time.time()
                - inicio
            )

            print(
                f"{linhas:,} linhas | "
                f"{registros:,} registros 15777 | "
                f"{total_estado:,} votos encontrados | "
                f"{tempo/60:.1f} min"
            )


        try:

            # ------------------------------------------------
            # NÚMERO
            # ------------------------------------------------

            if (
                row[idx_votavel].strip()
                != CANDIDATO
            ):

                continue


            # ------------------------------------------------
            # CARGO
            # ------------------------------------------------

            if idx_cargo is not None:

                cargo = normalizar(
                    row[idx_cargo]
                )

                if (
                    "DEPUTADO ESTADUAL"
                    not in cargo
                ):

                    continue


            # ------------------------------------------------
            # NOME
            # ------------------------------------------------

            if idx_nome is not None:

                nome = normalizar(
                    row[idx_nome]
                )

                # segurança contra eventual colisão
                # do número em outro contexto

                if (
                    "ANDRE"
                    not in nome
                    or
                    "BUENO"
                    not in nome
                ):

                    continue


            # ------------------------------------------------
            # PARTIDO
            # ------------------------------------------------

            if idx_partido is not None:

                partido = normalizar(
                    row[idx_partido]
                )

                if (
                    partido
                    and
                    partido != "MDB"
                ):

                    continue


            # ------------------------------------------------
            # ZONA
            # ------------------------------------------------

            zona_txt = (
                row[idx_zona]
                .strip()
            )

            if not zona_txt:

                continue

            zona = int(
                zona_txt
            )


            # ------------------------------------------------
            # MUNICÍPIO
            # ------------------------------------------------

            municipio = (
                row[idx_municipio]
                .strip()
            )


            # ------------------------------------------------
            # VOTOS
            # ------------------------------------------------

            votos_txt = (
                row[idx_votos]
                .strip()
            )

            if not votos_txt:

                continue

            votos = int(
                votos_txt
            )


            # ------------------------------------------------
            # REGIÃO
            # ------------------------------------------------

            regiao = classificar_regiao(
                zona,
                municipio
            )


            # ------------------------------------------------
            # SOMAS
            # ------------------------------------------------

            total_estado += votos

            totais_regiao[
                regiao
            ] += votos

            totais_zona[
                zona
            ] += votos

            totais_municipio[
                municipio
            ] += votos

            zona_municipios[
                zona
            ][
                municipio
            ] += votos

            registros += 1


        except (
            ValueError,
            IndexError
        ):

            continue


# ============================================================
# RESULTADO ESTADUAL
# ============================================================

print()
print("=" * 100)
print("TOTAL ESTADUAL")
print("=" * 100)

print(
    f"ANDRÉ BUENO 15777: "
    f"{total_estado:,} votos"
)

print(
    f"Registros encontrados: "
    f"{registros:,}"
)


# ============================================================
# RANKING DE REGIÕES
# ============================================================

ranking_regioes = sorted(
    totais_regiao.items(),
    key=lambda x: x[1],
    reverse=True
)


print()
print("=" * 100)
print("RANKING POR REGIÃO")
print("=" * 100)


for posicao, (
    regiao,
    votos
) in enumerate(
    ranking_regioes,
    start=1
):

    percentual = (

        votos
        / total_estado
        * 100

        if total_estado
        else 0
    )

    print(
        f"{posicao:>2}º | "
        f"{regiao:<15} | "
        f"{votos:>7,} votos | "
        f"{percentual:>6.2f}%"
    )


# ============================================================
# RANKING DOS MUNICÍPIOS
# ============================================================

ranking_municipios = sorted(
    totais_municipio.items(),
    key=lambda x: x[1],
    reverse=True
)


print()
print("=" * 100)
print("TOP 30 MUNICÍPIOS")
print("=" * 100)


for posicao, (
    municipio,
    votos
) in enumerate(
    ranking_municipios[:30],
    start=1
):

    percentual = (

        votos
        / total_estado
        * 100

        if total_estado
        else 0
    )

    print(
        f"{posicao:>2}º | "
        f"{municipio:<30} | "
        f"{votos:>7,} | "
        f"{percentual:>6.2f}%"
    )


# ============================================================
# RANKING DAS ZONAS
# ============================================================

ranking_zonas = sorted(
    totais_zona.items(),
    key=lambda x: x[1],
    reverse=True
)


print()
print("=" * 100)
print("TOP 50 ZONAS ELEITORAIS")
print("=" * 100)


for posicao, (
    zona,
    votos
) in enumerate(
    ranking_zonas[:50],
    start=1
):

    # Município com mais votos
    # dentro daquela zona
    municipios_zona = (
        zona_municipios[zona]
    )

    principal_municipio = max(
        municipios_zona.items(),
        key=lambda x: x[1]
    )[0]


    if (
        normalizar(
            principal_municipio
        )
        == "SAO PAULO"
    ):

        nome_zona = (
            CAPITAL_NOMES.get(
                zona,
                principal_municipio
            )
        )

    else:

        nome_zona = (
            principal_municipio
        )


    regiao = classificar_regiao(
        zona,
        principal_municipio
    )


    print(
        f"{posicao:>2}º | "
        f"ZE {zona:>3} | "
        f"{nome_zona:<30} | "
        f"{regiao:<12} | "
        f"{votos:>6,} votos"
    )


# ============================================================
# CSV 1 - REGIÕES
# ============================================================

arquivo_regioes = (
    "ranking_regioes_andre_bueno.csv"
)


with open(
    arquivo_regioes,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.writer(
        f,
        delimiter=";"
    )

    writer.writerow(
        [
            "POSICAO",
            "REGIAO",
            "VOTOS",
            "PERCENTUAL"
        ]
    )

    for posicao, (
        regiao,
        votos
    ) in enumerate(
        ranking_regioes,
        start=1
    ):

        percentual = (

            votos
            / total_estado
            * 100

            if total_estado
            else 0
        )

        writer.writerow(
            [
                posicao,
                regiao,
                votos,
                f"{percentual:.2f}%"
            ]
        )


# ============================================================
# CSV 2 - MUNICÍPIOS
# ============================================================

arquivo_municipios = (
    "ranking_municipios_andre_bueno.csv"
)


with open(
    arquivo_municipios,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.writer(
        f,
        delimiter=";"
    )

    writer.writerow(
        [
            "POSICAO",
            "MUNICIPIO",
            "VOTOS",
            "PERCENTUAL"
        ]
    )

    for posicao, (
        municipio,
        votos
    ) in enumerate(
        ranking_municipios,
        start=1
    ):

        percentual = (

            votos
            / total_estado
            * 100

            if total_estado
            else 0
        )

        writer.writerow(
            [
                posicao,
                municipio,
                votos,
                f"{percentual:.2f}%"
            ]
        )


# ============================================================
# CSV 3 - TODAS AS ZONAS
# ============================================================

arquivo_zonas = (
    "ranking_todas_zonas_andre_bueno.csv"
)


with open(
    arquivo_zonas,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.writer(
        f,
        delimiter=";"
    )

    writer.writerow(
        [
            "POSICAO",
            "ZONA",
            "NOME_REFERENCIA",
            "REGIAO",
            "VOTOS"
        ]
    )

    for posicao, (
        zona,
        votos
    ) in enumerate(
        ranking_zonas,
        start=1
    ):

        municipios_zona = (
            zona_municipios[zona]
        )

        principal_municipio = max(
            municipios_zona.items(),
            key=lambda x: x[1]
        )[0]

        if (
            normalizar(
                principal_municipio
            )
            == "SAO PAULO"
        ):

            nome_zona = (
                CAPITAL_NOMES.get(
                    zona,
                    principal_municipio
                )
            )

        else:

            nome_zona = (
                principal_municipio
            )


        regiao = classificar_regiao(
            zona,
            principal_municipio
        )


        writer.writerow(
            [
                posicao,
                zona,
                nome_zona,
                regiao,
                votos
            ]
        )


# ============================================================
# VALIDAÇÃO
# ============================================================

soma_regioes = sum(
    totais_regiao.values()
)

print()
print("=" * 100)
print("VALIDAÇÃO")
print("=" * 100)

print(
    f"Total estadual pelo BU: "
    f"{total_estado:,}"
)

print(
    f"Soma das regiões:       "
    f"{soma_regioes:,}"
)

print(
    f"Diferença:              "
    f"{total_estado - soma_regioes:,}"
)


if (
    total_estado
    == soma_regioes
):

    print(
        "OK - 100% DOS VOTOS "
        "FORAM CLASSIFICADOS."
    )

else:

    print(
        "ATENÇÃO - EXISTE "
        "DIFERENÇA NA CLASSIFICAÇÃO."
    )


# ============================================================
# ARQUIVOS
# ============================================================

tempo_total = (
    time.time()
    - inicio
)

print()
print("=" * 100)
print("PROCESSAMENTO CONCLUÍDO")
print("=" * 100)

print(
    f"Tempo: "
    f"{tempo_total/60:.1f} minutos"
)

print()

print(
    "Arquivos gerados:"
)

print(
    os.path.abspath(
        arquivo_regioes
    )
)

print(
    os.path.abspath(
        arquivo_municipios
    )
)

print(
    os.path.abspath(
        arquivo_zonas
    )
)

print()

input(
    "Pressione ENTER para fechar..."
)