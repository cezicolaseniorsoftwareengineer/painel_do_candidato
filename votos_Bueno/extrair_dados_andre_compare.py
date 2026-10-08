import csv
import glob
import io
import os
import time
import unicodedata
import zipfile
from collections import defaultdict

NOME_RELATORIO = "ANDRÉ BUENO"
ANO_ANTERIOR = 2022
ANO_ATUAL = 2026
NUMERO_ANTERIOR = "22010"
NUMERO_ATUAL = "15777"
PARTIDO_ANTERIOR = "PL"
PARTIDO_ATUAL = "MDB"
CARGO_ANTERIOR = "DEPUTADO ESTADUAL"
CARGO_ATUAL = "DEPUTADO ESTADUAL"
NOME_TOKENS = ['ANDRE','BUENO']
ANO_ANTERIOR_MUNICIPAL_CAPITAL = False

CAPITAL_REGIOES = {
    1:"Centro",3:"Centro",
    2:"Oeste",5:"Oeste",250:"Oeste",251:"Oeste",346:"Oeste",374:"Oeste",
    249:"Norte",254:"Norte",255:"Norte",256:"Norte",325:"Norte",327:"Norte",
    349:"Norte",376:"Norte",389:"Norte",403:"Norte",420:"Norte",422:"Norte",
    6:"Sul",20:"Sul",246:"Sul",258:"Sul",259:"Sul",260:"Sul",280:"Sul",
    320:"Sul",328:"Sul",351:"Sul",371:"Sul",372:"Sul",373:"Sul",381:"Sul",
    408:"Sul",413:"Sul",418:"Sul",
    4:"Leste",247:"Leste",248:"Leste",252:"Leste",253:"Leste",257:"Leste",
    326:"Leste",347:"Leste",348:"Leste",350:"Leste",352:"Leste",353:"Leste",
    375:"Leste",390:"Leste",392:"Leste",397:"Leste",398:"Leste",404:"Leste",
    405:"Leste",417:"Leste",421:"Leste"
}

CAPITAL_NOMES = {
    1:"Bela Vista",2:"Perdizes",3:"Santa Ifigênia",4:"Mooca",5:"Jardim Paulista",
    6:"Vila Mariana",20:"Valo Velho",246:"Santo Amaro",247:"São Miguel Paulista",
    248:"Itaquera",249:"Santana",250:"Lapa",251:"Pinheiros",252:"Penha de França",
    253:"Tatuapé",254:"Vila Maria",255:"Casa Verde",256:"Tucuruvi",
    257:"Vila Prudente",258:"Indianópolis",259:"Saúde",260:"Ipiranga",
    280:"Capela do Socorro",320:"Jabaquara",325:"Pirituba",326:"Ermelino Matarazzo",
    327:"Nossa Senhora do Ó",328:"Campo Limpo",346:"Morumbi",347:"Vila Matilde",
    348:"Vila Formosa",349:"Jaçanã",350:"Sapopemba",351:"Cidade Ademar",
    352:"Itaim Paulista",353:"Guaianases",371:"Grajaú",372:"Piraporinha",
    373:"Capão Redondo",374:"Rio Pequeno",375:"São Mateus",376:"Brasilândia",
    381:"Parelheiros",389:"Perus",390:"Cangaíba",392:"Ponte Rasa",
    397:"Jardim Helena",398:"Vila Jacuí",403:"Jaraguá",404:"Cidade Tiradentes",
    405:"Conjunto José Bonifácio",408:"Jardim São Luís",413:"Cursino",
    417:"Parque do Carmo",418:"Pedreira",420:"Vila Sabrina",
    421:"Teotônio Vilela",422:"Lauzane Paulista"
}

GRANDE_SP = {
    "ARUJA","BARUERI","BIRITIBA MIRIM","CAIEIRAS","CAJAMAR","CARAPICUIBA","COTIA",
    "DIADEMA","EMBU DAS ARTES","EMBU GUACU","FERRAZ DE VASCONCELOS",
    "FRANCISCO MORATO","FRANCO DA ROCHA","GUARAREMA","GUARULHOS",
    "ITAPECERICA DA SERRA","ITAPEVI","ITAQUAQUECETUBA","JANDIRA","JUQUITIBA",
    "MAIRIPORA","MAUA","MOGI DAS CRUZES","OSASCO","PIRAPORA DO BOM JESUS","POA",
    "RIBEIRAO PIRES","RIO GRANDE DA SERRA","SALESOPOLIS","SANTA ISABEL",
    "SANTANA DE PARNAIBA","SANTO ANDRE","SAO BERNARDO DO CAMPO",
    "SAO CAETANO DO SUL","SAO LOURENCO DA SERRA","SUZANO","TABOAO DA SERRA",
    "VARGEM GRANDE PAULISTA"
}

LITORAL = {
    "UBATUBA","CARAGUATATUBA","SAO SEBASTIAO","ILHABELA","BERTIOGA","GUARUJA",
    "SANTOS","SAO VICENTE","CUBATAO","PRAIA GRANDE","MONGAGUA","ITANHAEM",
    "PERUIBE","IGUAPE","ILHA COMPRIDA","CANANEIA"
}

def normalizar(texto):
    if texto is None:
        return ""
    texto = unicodedata.normalize("NFD", str(texto).strip().upper())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("-", " ")
    while "  " in texto:
        texto = texto.replace("  ", " ")
    return texto.strip()

def classificar_regiao(zona, municipio):
    m = normalizar(municipio)
    if m == "SAO PAULO":
        return CAPITAL_REGIOES.get(zona, "Capital - não classificada")
    if m in GRANDE_SP:
        return "Grande SP"
    if m in LITORAL:
        return "Litoral"
    return "Interior"

def nome_referencia(zona, municipio):
    if normalizar(municipio) == "SAO PAULO":
        return CAPITAL_NOMES.get(zona, f"ZE {zona}")
    return municipio

def encontrar_bweb(ano):
    candidatos = []
    for padrao in (
        f"bweb_1t_SP_*{ano}*.csv", f"bweb_1t_SP_*{ano}*.zip",
        f"BWEB_1T_SP_*{ano}*.CSV", f"BWEB_1T_SP_*{ano}*.ZIP"
    ):
        candidatos.extend(glob.glob(padrao))
    candidatos = list(set(candidatos))
    if not candidatos:
        return None
    csvs = [x for x in candidatos if x.lower().endswith(".csv")]
    return max(csvs if csvs else candidatos, key=os.path.getsize)

def abrir_bweb(arquivo):
    if arquivo.lower().endswith(".zip"):
        z = zipfile.ZipFile(arquivo, "r")
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            z.close()
            raise RuntimeError(f"Nenhum CSV dentro de {arquivo}")
        interno = max(csvs, key=lambda n: z.getinfo(n).file_size)
        f = io.TextIOWrapper(z.open(interno, "r"), encoding="latin1",
                             errors="replace", newline="")
        return f, z, interno
    return open(arquivo, "r", encoding="latin1", errors="replace", newline=""), None, os.path.basename(arquivo)

def calcular_rank(dic):
    itens = sorted(((k,v) for k,v in dic.items() if v > 0), key=lambda x:(-x[1], str(x[0])))
    return {k:i for i,(k,_) in enumerate(itens, 1)}

def status_variacao(a, b):
    if a == 0 and b == 0: return "SEM VOTOS"
    if a == 0 and b > 0: return "NOVOS VOTOS"
    if a > 0 and b == 0: return "PERDEU TODA A BASE"
    if b > a: return "CRESCIMENTO"
    if b < a: return "REDUCAO"
    return "MANTEVE"

def variacao_pct(a, b):
    return None if a == 0 else ((b-a)/a)*100.0

def extrair_eleicao(arquivo, ano, numero, partido, cargo):
    print("\n" + "="*110)
    print(f"PROCESSANDO {NOME_RELATORIO} - {ano}")
    print("="*110)
    print("Arquivo:", arquivo)

    f, z, interno = abrir_bweb(arquivo)
    print("CSV utilizado:", interno)

    total = registros = linhas = 0
    votos_regiao = defaultdict(int)
    votos_municipio = defaultdict(int)
    votos_zona = defaultdict(int)
    todas_zonas = set()
    todos_municipios = set()
    inicio = time.time()

    try:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        cab = [c.strip().replace("\ufeff","") for c in next(reader)]

        for campo in ("NR_ZONA","NR_VOTAVEL","QT_VOTOS","NM_MUNICIPIO"):
            if campo not in cab:
                raise RuntimeError(f"{ano}: coluna {campo} não encontrada.")

        iz = cab.index("NR_ZONA")
        inu = cab.index("NR_VOTAVEL")
        iv = cab.index("QT_VOTOS")
        im = cab.index("NM_MUNICIPIO")
        ic = cab.index("DS_CARGO_PERGUNTA") if "DS_CARGO_PERGUNTA" in cab else None
        inn = cab.index("NM_VOTAVEL") if "NM_VOTAVEL" in cab else None
        ip = cab.index("SG_PARTIDO") if "SG_PARTIDO" in cab else None

        for row in reader:
            linhas += 1
            try:
                municipio = normalizar(row[im])
                ztxt = row[iz].strip()
                if not ztxt:
                    continue
                zona = int(ztxt)
                chave = (municipio, zona)

                # Descobre TODAS as zonas existentes no BU, mesmo com zero voto.
                todas_zonas.add(chave)
                todos_municipios.add(municipio)

                if row[inu].strip() != numero:
                    if linhas % 2_000_000 == 0:
                        t = time.time()-inicio
                        print(f"{linhas:,} linhas | {registros:,} registros | {total:,} votos | {t/60:.1f} min")
                    continue

                if ic is not None and normalizar(cargo) not in normalizar(row[ic]):
                    continue

                if inn is not None:
                    nome = normalizar(row[inn])
                    if not all(tok in nome for tok in NOME_TOKENS):
                        continue

                if ip is not None and partido:
                    p = normalizar(row[ip])
                    if p and p != normalizar(partido):
                        continue

                votos = int(row[iv].strip())
                regiao = classificar_regiao(zona, municipio)

                total += votos
                registros += 1
                votos_regiao[regiao] += votos
                votos_municipio[municipio] += votos
                votos_zona[chave] += votos

            except (ValueError, IndexError):
                continue

            if linhas % 2_000_000 == 0:
                t = time.time()-inicio
                print(f"{linhas:,} linhas | {registros:,} registros | {total:,} votos | {t/60:.1f} min")

    finally:
        f.close()
        if z is not None:
            z.close()

    # Injeta todas as zonas conhecidas da capital para exibir também zero/zero.
    for zona in set(CAPITAL_NOMES) | set(CAPITAL_REGIOES):
        todas_zonas.add(("SAO PAULO", zona))
        todos_municipios.add("SAO PAULO")

    print(f"\n{NOME_RELATORIO} {ano}: {total:,} votos")
    print(f"Registros encontrados: {registros:,}")
    print(f"Zonas existentes mapeadas: {len(todas_zonas):,}")

    return {
        "ano":ano, "total":total, "registros":registros,
        "regioes":votos_regiao, "municipios":votos_municipio,
        "zonas":votos_zona, "todas_zonas":todas_zonas,
        "todos_municipios":todos_municipios
    }

arq_ant = encontrar_bweb(ANO_ANTERIOR)
arq_atu = encontrar_bweb(ANO_ATUAL)

if not arq_ant:
    print(f"ERRO: não encontrei bweb_1t_SP_*{ANO_ANTERIOR}*.csv/.zip")
    input("ENTER...")
    raise SystemExit
if not arq_atu:
    print(f"ERRO: não encontrei bweb_1t_SP_*{ANO_ATUAL}*.csv/.zip")
    input("ENTER...")
    raise SystemExit

ant = extrair_eleicao(arq_ant, ANO_ANTERIOR, NUMERO_ANTERIOR, PARTIDO_ANTERIOR, CARGO_ANTERIOR)
atu = extrair_eleicao(arq_atu, ANO_ATUAL, NUMERO_ATUAL, PARTIDO_ATUAL, CARGO_ATUAL)

# REGIÕES
regioes = set(ant["regioes"]) | set(atu["regioes"]) | {
    "Interior","Grande SP","Norte","Leste","Litoral","Sul","Oeste","Centro","Capital - não classificada"
}
rr_ant = calcular_rank(ant["regioes"]); rr_atu = calcular_rank(atu["regioes"])
comp_reg = []
for r in regioes:
    a = ant["regioes"].get(r,0); b = atu["regioes"].get(r,0)
    comp_reg.append((r, rr_ant.get(r,""), a, rr_atu.get(r,""), b, b-a, variacao_pct(a,b), status_variacao(a,b)))
comp_reg.sort(key=lambda x:(-x[4],-x[2],x[0]))

# MUNICÍPIOS
municipios = ant["todos_municipios"] | atu["todos_municipios"]
rm_ant = calcular_rank(ant["municipios"]); rm_atu = calcular_rank(atu["municipios"])
comp_mun = []
for m in municipios:
    a = ant["municipios"].get(m,0); b = atu["municipios"].get(m,0)
    comp_mun.append((m,rm_ant.get(m,""),a,rm_atu.get(m,""),b,b-a,variacao_pct(a,b),status_variacao(a,b)))
comp_mun.sort(key=lambda x:(-x[4],-x[2],x[0]))

# TODAS AS ZONAS
zonas = ant["todas_zonas"] | atu["todas_zonas"]
rz_ant = calcular_rank(ant["zonas"]); rz_atu = calcular_rank(atu["zonas"])
comp_zonas = []
for m,zona in zonas:
    chave=(m,zona)
    a=ant["zonas"].get(chave,0); b=atu["zonas"].get(chave,0)
    reg=classificar_regiao(zona,m)
    ref=nome_referencia(zona,m)
    comparabilidade = "COMPARAVEL"
    if ANO_ANTERIOR_MUNICIPAL_CAPITAL and m != "SAO PAULO":
        comparabilidade = f"NAO DIRETAMENTE COMPARAVEL: {ANO_ANTERIOR} ERA MUNICIPAL"
    comp_zonas.append((m,zona,ref,reg,rz_ant.get(chave,""),a,rz_atu.get(chave,""),b,b-a,variacao_pct(a,b),status_variacao(a,b),comparabilidade))
comp_zonas.sort(key=lambda x:(-x[7],-x[5],x[0],x[1]))

print("\n"+"="*110)
print(f"{NOME_RELATORIO} - COMPARAÇÃO {ANO_ANTERIOR} x {ANO_ATUAL}")
print("="*110)
print(f"{ANO_ANTERIOR}: {ant['total']:,} votos | {ant['registros']:,} registros")
print(f"{ANO_ATUAL}: {atu['total']:,} votos | {atu['registros']:,} registros")
print(f"DIFERENÇA TOTAL: {atu['total']-ant['total']:+,} votos")

print("\n"+"="*110)
print("RANKING POR REGIÃO - LADO A LADO")
print("="*110)
for r,ra,a,rb,b,d,p,s in comp_reg:
    print(f"{r:<24} | RANK {ANO_ANTERIOR} {str(ra):>3} | {a:>8,} | RANK {ANO_ATUAL} {str(rb):>3} | {b:>8,} | DIF {d:>+8,} | {s}")

print("\n"+"="*110)
print("TOP 30 MUNICÍPIOS - LADO A LADO")
print("="*110)
for i,(m,ra,a,rb,b,d,p,s) in enumerate(comp_mun[:30],1):
    print(f"{i:>2}º | {m:<30} | {ANO_ANTERIOR} {a:>7,} | {ANO_ATUAL} {b:>7,} | DIF {d:>+7,} | {s}")

print("\n"+"="*110)
print("TOP 50 ZONAS - LADO A LADO")
print("="*110)
for i,(m,z,ref,reg,ra,a,rb,b,d,p,s,c) in enumerate(comp_zonas[:50],1):
    print(f"{i:>2}º | ZE {z:>3} | {ref:<28} | {reg:<12} | {ANO_ANTERIOR} {a:>6,} | {ANO_ATUAL} {b:>6,} | DIF {d:>+6,} | {s}")

prefixo="comparacao_andre_2022_2026"
arq_reg=f"{prefixo}_regioes.csv"
arq_mun=f"{prefixo}_municipios.csv"
arq_zon=f"{prefixo}_todas_zonas.csv"
arq_res=f"{prefixo}_resumo.csv"

def pt(p): return "" if p is None else f"{p:.2f}%"

with open(arq_reg,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f,delimiter=";")
    w.writerow(["REGIAO",f"RANK_{ANO_ANTERIOR}",f"VOTOS_{ANO_ANTERIOR}",f"RANK_{ANO_ATUAL}",f"VOTOS_{ANO_ATUAL}","DIFERENCA","VARIACAO_PERCENTUAL","STATUS"])
    for r,ra,a,rb,b,d,p,s in comp_reg:
        w.writerow([r,ra,a,rb,b,d,pt(p),s])

with open(arq_mun,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f,delimiter=";")
    w.writerow(["MUNICIPIO",f"RANK_{ANO_ANTERIOR}",f"VOTOS_{ANO_ANTERIOR}",f"RANK_{ANO_ATUAL}",f"VOTOS_{ANO_ATUAL}","DIFERENCA","VARIACAO_PERCENTUAL","STATUS"])
    for m,ra,a,rb,b,d,p,s in comp_mun:
        w.writerow([m,ra,a,rb,b,d,pt(p),s])

with open(arq_zon,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f,delimiter=";")
    w.writerow(["MUNICIPIO","ZONA","ZONA_BAIRRO_REFERENCIA","REGIAO",f"RANK_{ANO_ANTERIOR}",f"VOTOS_{ANO_ANTERIOR}",f"RANK_{ANO_ATUAL}",f"VOTOS_{ANO_ATUAL}","DIFERENCA","VARIACAO_PERCENTUAL","STATUS","COMPARABILIDADE"])
    for linha in comp_zonas:
        m,z,ref,reg,ra,a,rb,b,d,p,s,c=linha
        w.writerow([m,z,ref,reg,ra,a,rb,b,d,pt(p),s,c])

cres=[x for x in comp_zonas if x[8]>0]
perd=[x for x in comp_zonas if x[8]<0]
mant=[x for x in comp_zonas if x[5]>0 and x[5]==x[7]]
sem=[x for x in comp_zonas if x[5]==0 and x[7]==0]
cres.sort(key=lambda x:-x[8]); perd.sort(key=lambda x:x[8])

with open(arq_res,"w",encoding="utf-8-sig",newline="") as f:
    w=csv.writer(f,delimiter=";")
    w.writerow(["METRICA",str(ANO_ANTERIOR),str(ANO_ATUAL),"DIFERENCA"])
    w.writerow(["TOTAL_ESTADUAL",ant["total"],atu["total"],atu["total"]-ant["total"]])
    w.writerow(["REGISTROS",ant["registros"],atu["registros"],atu["registros"]-ant["registros"]])
    w.writerow(["ZONAS_EXISTENTES",len(ant["todas_zonas"]),len(atu["todas_zonas"]),len(atu["todas_zonas"])-len(ant["todas_zonas"])])
    w.writerow(["ZONAS_MANTIVERAM_EXATAMENTE",len(mant),"",""])
    w.writerow(["ZONAS_SEM_VOTOS_NOS_DOIS_ANOS",len(sem),"",""])

print("\n"+"="*110)
print("MAIORES AUMENTOS DE VOTOS POR ZONA")
print("="*110)
for x in cres[:15]:
    print(f"ZE {x[1]:>3} | {x[2]:<28} | {x[5]:>6,} -> {x[7]:>6,} | {x[8]:>+6,}")

print("\n"+"="*110)
print("MAIORES REDUÇÕES DE VOTOS POR ZONA")
print("="*110)
for x in perd[:15]:
    print(f"ZE {x[1]:>3} | {x[2]:<28} | {x[5]:>6,} -> {x[7]:>6,} | {x[8]:>+6,}")

print(f"\nZonas com mesma quantidade de votos: {len(mant):,}")
print(f"Zonas sem votos nos dois anos: {len(sem):,}")

print("\n"+"="*110)
print("AUDITORIA FINAL")
print("="*110)
for d in (ant,atu):
    sz=sum(d["zonas"].values())
    sm=sum(d["municipios"].values())
    sr=sum(d["regioes"].values())
    print(f"{d['ano']}: total={d['total']:,} | zonas={sz:,} | municipios={sm:,} | regioes={sr:,} | dif={d['total']-sz:,}")
    print("OK - 100% classificados." if d["total"]==sz==sm==sr else "ATENÇÃO - auditoria não fechou.")

print("\nCHECAGEM EXPLÍCITA GUAIANASES / ZE 353")
print(f"{ANO_ANTERIOR}: {ant['zonas'].get(('SAO PAULO',353),0):,} votos")
print(f"{ANO_ATUAL}: {atu['zonas'].get(('SAO PAULO',353),0):,} votos")

print("\nArquivos gerados:")
for x in (arq_reg,arq_mun,arq_zon,arq_res):
    print(os.path.abspath(x))

input("\nPressione ENTER para fechar...")
