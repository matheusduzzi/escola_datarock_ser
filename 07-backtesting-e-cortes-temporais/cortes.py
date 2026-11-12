"""Backtesting da venda da loja física: cortes no tempo, origens, distância e o teste do plano.

Rode de dentro da pasta dessa aula:      python3 cortes.py
Testar um plano, com o contrato dele:    python3 cortes.py --plano plano_rafael.py --contrato semana
O plano do exercício:                    python3 cortes.py --plano meu_plano.py --contrato mes
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

Sem opções, o programa mostra:
1. Uma noite só: a escala do mês, prevista em duas noites diferentes, e quem erra menos em cada uma.
2. O plano do ajuste da semana (7 dias antes de cada dia) e o teste do plano.
3. O que o plano mede no período de escolha: o erro das três previsões, mês a mês.
4. A distância: os mesmos dias, previstos 1, 7, 14 e 28 dias antes e na noite da escala do mês.
5. O atraso: o que muda se a venda do dia só chegar na manhã seguinte.

Um plano é uma lista de cortes. Cada corte diz a parte (escolha ou teste), a noite da origem, a janela de
treino (o primeiro e o último dia de venda que a previsão pode ler) e os dias previstos. O programa testa o
plano contra o contrato da decisão e, se passar, roda as três previsões em cada corte. Cada previsão recebe
só a venda da janela de treino: ela não tem como ler um dia depois do corte.

Dia usável: dia completo (último pedido às 21h30 ou depois) com a loja aberta, como na aula 03.
Venda real para medir: dia completo ou loja fechada (venda zero). Dia sem registro ou incompleto fica fora.
"""
import argparse
import hashlib
import importlib.util
import math
import statistics
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
LOJA = AQUI.parent / "dados" / "loja"
INICIO, FIM = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
FIM_ESCOLHA = pd.Timestamp("2025-08-31")  # a venda que o curso usa para escolher modelos termina aqui
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
UM_DIA = pd.Timedelta(days=1)
SEMANA = pd.Timedelta(days=7)
JANELA_MINIMA = 28  # a média de 4 semanas e o mesmo dia de 4 semanas leem 28 dias
CAMPOS = ["parte", "origem", "treino_de", "treino_ate", "de", "ate"]

# O contrato vem da decisão, não do plano: quem escreve o plano não escolhe a distância.
CONTRATOS = {
    "semana": {"nome": "ajuste da semana: cada dia previsto 7 dias antes, na noite em que a loja fecha",
               "h_min": 7, "h_max": 7, "atraso": 0, "mes_seguinte": False},
    "mes": {"nome": "escala do mês: na noite do dia 1, o mês seguinte inteiro",
            "h_min": 28, "h_max": 61, "atraso": 0, "mes_seguinte": True},
}


def br(x, casas=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d(t):
    return f"{t:%d/%m/%Y}"


def carregar(loja=LOJA):
    """A venda no calendário. usavel: unidades do dia completo com a loja aberta (vazio nos outros).
    real: a venda para medir o erro, com o dia fechado valendo 0 (vazio no dia sem registro ou incompleto).
    fechada: os dias em que o calendário diz loja fechada, até 31/01/2026."""
    venda = pd.read_csv(loja / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    venda = venda.set_index("data")
    cal = pd.read_csv(loja / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, FIM, freq="D")
    serie = venda.reindex(dias)
    fechada_venda = cal["loja_fechada"].reindex(dias) == 1
    hora = pd.to_datetime(serie["ultimo_registro"], format="%H:%M", errors="coerce")
    completo = (hora.dt.hour * 60 + hora.dt.minute >= 21 * 60 + 30) & (serie["unidades"] > 0) & ~fechada_venda
    usavel = serie["unidades"].where(completo).astype(float)
    real = serie["unidades"].where(completo | fechada_venda).astype(float)
    fechada = cal["loja_fechada"] == 1
    return usavel, real, fechada


# As previsões. Todas recebem só a janela de treino, já cortada. O último dia que elas enxergam é o fim da janela.

def ultimo_mesmo_dia(janela, dia):
    """O dia da semana igual ao do dia previsto, o mais recente dentro da janela."""
    fonte = dia - SEMANA
    while fonte > janela.index[-1]:
        fonte -= SEMANA
    return fonte


def semana_passada(janela, dia):
    """A venda do mesmo dia da semana, a mais recente que é usável. Se ela não serve, uma semana a mais."""
    fonte = ultimo_mesmo_dia(janela, dia)
    while fonte >= janela.index[0]:
        valor = janela.get(fonte, math.nan)
        if not math.isnan(valor):
            return float(valor)
        fonte -= SEMANA
    return math.nan


def media_4_semanas(janela, dia):
    """A média dos dias usáveis nos 28 dias que terminam no fim da janela."""
    ultimos = janela[janela.index[-1] - 27 * UM_DIA:].dropna()
    return float(ultimos.mean()) if len(ultimos) else math.nan


def mesmo_dia_4_semanas(janela, dia):
    """A média do mesmo dia da semana nas 4 semanas mais recentes da janela, só com os dias usáveis."""
    fonte = ultimo_mesmo_dia(janela, dia)
    valores = [janela.get(fonte - k * SEMANA, math.nan) for k in range(4)]
    valores = [v for v in valores if not math.isnan(v)]
    return float(sum(valores) / len(valores)) if valores else math.nan


METODOS = {"semana passada": semana_passada, "média de 4 semanas": media_4_semanas,
           "mesmo dia, 4 semanas": mesmo_dia_4_semanas}


def prever(funcao, usavel, fechada, corte, dia):
    """Chama a previsão só com a janela de treino do corte. Dia que o calendário já diz fechado é 0."""
    if bool(fechada.get(dia, False)):
        return 0.0
    janela = usavel[corte["treino_de"]:corte["treino_ate"]]
    return funcao(janela, dia)


# Os planos.

def plano_semana():
    """O plano do ajuste da semana, o que o curso usa daqui em diante.
    Uma origem por noite. Escolha: origens de 01/02/2024 a 24/08/2025, que preveem até 31/08/2025.
    Teste: origens de 31/08/2025 a 24/12/2025, que preveem de 07/09 a 31/12/2025.
    Janela de treino expansiva: de 01/01/2024 até a noite da origem."""
    cortes = []
    for origem in pd.date_range("2024-02-01", "2025-12-24", freq="D"):
        if FIM_ESCOLHA - SEMANA < origem < FIM_ESCOLHA:
            continue  # essas noites preveem setembro, que é do teste, com a venda de agosto, que é da escolha
        dia = origem + SEMANA
        cortes.append({"parte": "escolha" if dia <= FIM_ESCOLHA else "teste", "origem": origem,
                       "treino_de": INICIO, "treino_ate": origem, "de": dia, "ate": dia})
    return cortes


def carregar_plano(arquivo):
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        caminho = (Path.cwd() / caminho) if (Path.cwd() / caminho).exists() else AQUI / caminho
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.plano()


def normalizar(plano):
    """Datas viram Timestamp; o que não é data vira erro de formato."""
    cortes, erros = [], []
    for i, c in enumerate(plano or []):
        try:
            novo = {"parte": c["parte"]}
            for campo in CAMPOS[1:]:
                novo[campo] = pd.Timestamp(c[campo]).normalize()
            cortes.append(novo)
        except (KeyError, TypeError, ValueError) as e:
            erros.append(f"corte {i + 1}: {type(e).__name__} {e}")
    return cortes, erros


def testar_plano(plano, contrato):
    """As seis regras do plano sem vazamento. Retorna (cortes, problemas); problemas é uma lista de
    (regra, quantos cortes falham, primeiro exemplo)."""
    cortes, erros = normalizar(plano)
    problemas = []

    def falha(regra, ruins, exemplo):
        if ruins:
            problemas.append((regra, len(ruins), exemplo(ruins[0])))

    if not plano:
        return [], [("1. o plano tem cortes", 0, "o plano está vazio")]
    falha("1. cada corte tem parte, origem, treino_de, treino_ate, de e ate, em datas", erros, lambda e: e)
    if erros:
        return cortes, problemas
    falha("1. a parte é escolha ou teste", [c for c in cortes if c["parte"] not in ("escolha", "teste")],
          lambda c: f"parte {c['parte']!r} na origem {d(c['origem'])}")
    falha("1. a janela e os dias previstos estão em ordem", [c for c in cortes if c["treino_de"] > c["treino_ate"]
                                                              or c["de"] > c["ate"]],
          lambda c: f"origem {d(c['origem'])}: treino {d(c['treino_de'])} a {d(c['treino_ate'])}, "
                    f"dias {d(c['de'])} a {d(c['ate'])}")
    atraso = contrato["atraso"] * UM_DIA
    falha("2. o treino termina na noite da origem", [c for c in cortes if c["treino_ate"] > c["origem"] - atraso],
          lambda c: f"origem {d(c['origem'])}, treino até {d(c['treino_ate'])}")

    def fora(c):
        h1, h2 = (c["de"] - c["origem"]).days, (c["ate"] - c["origem"]).days
        if h1 < contrato["h_min"] or h2 > contrato["h_max"]:
            return True
        if contrato["mes_seguinte"]:
            seguinte = c["origem"] + pd.offsets.MonthBegin(1)
            return c["origem"].day != 1 or c["de"] != seguinte or c["ate"] != seguinte + pd.offsets.MonthEnd(0)
        return False

    falha(f"3. a distância é a do contrato ({contrato['nome']})", [c for c in cortes if fora(c)],
          lambda c: f"origem {d(c['origem'])}, dias {d(c['de'])} a {d(c['ate'])}: "
                    f"{(c['de'] - c['origem']).days} a {(c['ate'] - c['origem']).days} dias depois")
    falha("4. a venda existe: treino desde 01/01/2024 e dias previstos até 31/12/2025",
          [c for c in cortes if c["treino_de"] < INICIO or c["ate"] > FIM],
          lambda c: f"origem {d(c['origem'])}: treino desde {d(c['treino_de'])}, dias até {d(c['ate'])}")
    falha(f"4. a janela de treino tem pelo menos {JANELA_MINIMA} dias, o que as previsões leem",
          [c for c in cortes if (c["treino_ate"] - c["treino_de"]).days + 1 < JANELA_MINIMA],
          lambda c: f"origem {d(c['origem'])}: {(c['treino_ate'] - c['treino_de']).days + 1} dias")
    esc = [c for c in cortes if c["parte"] == "escolha"]
    tst = [c for c in cortes if c["parte"] == "teste"]
    if not esc or not tst:
        problemas.append(("5. a escolha vem antes do teste", 0,
                          f"o plano precisa das duas partes: {len(esc)} cortes de escolha e {len(tst)} de teste"))
    else:
        primeira = min(c["origem"] for c in tst)
        falha("5. a escolha só prevê dias até 31/08/2025 e antes da primeira origem do teste",
              [c for c in esc if c["ate"] > FIM_ESCOLHA or c["ate"] > primeira],
              lambda c: f"escolha na origem {d(c['origem'])} prevê até {d(c['ate'])}; "
                        f"primeira origem do teste: {d(primeira)}")
        falha("5. o teste começa depois da venda da escolha", [c for c in tst if c["origem"] < FIM_ESCOLHA],
              lambda c: f"teste na origem {d(c['origem'])}, antes de 31/08/2025")
    for parte in ("escolha", "teste"):
        vistos, repetidos = set(), []
        for c in cortes:
            if c["parte"] != parte:
                continue
            for dia in pd.date_range(c["de"], c["ate"]):
                if dia in vistos:
                    repetidos.append((c, dia))
                vistos.add(dia)
        falha(f"6. nenhum dia previsto duas vezes na {parte}", repetidos,
              lambda r: f"{d(r[1])} de novo na origem {d(r[0]['origem'])}")
    return cortes, problemas


def tabela_plano(cortes):
    linhas = ["parte,origem,treino_de,treino_ate,de,ate"]
    for c in sorted(cortes, key=lambda c: (c["origem"], c["de"], c["parte"])):
        linhas.append(",".join([c["parte"]] + [f"{c[k]:%Y-%m-%d}" for k in CAMPOS[1:]]))
    return "\n".join(linhas) + "\n"


def avaliar(cortes, usavel, real, fechada, metodos=METODOS):
    """Roda as previsões em cada corte. Só entram os dias com venda real e com as três previsões em número:
    as três são medidas nos mesmos dias. Retorna uma linha por dia previsto."""
    linhas = []
    for c in cortes:
        for dia in pd.date_range(c["de"], c["ate"]):
            r = real.get(dia, math.nan)
            if math.isnan(r):
                continue
            p = {nome: prever(f, usavel, fechada, c, dia) for nome, f in metodos.items()}
            if any(math.isnan(v) for v in p.values()):
                continue
            linhas.append({"parte": c["parte"], "origem": c["origem"], "dia": dia, "real": r,
                           **{nome: abs(r - v) for nome, v in p.items()}})
    return pd.DataFrame(linhas)


def resumo(linhas, parte, nomes=tuple(METODOS)):
    """Erro médio da parte (todos os dias juntos), mediana do erro por origem e em quantas origens cada um ganha."""
    p = linhas[linhas["parte"] == parte]
    por_origem = p.groupby("origem")[list(nomes)].mean()
    vitorias = {n: 0 for n in nomes}
    for _, linha in por_origem.iterrows():
        menor = min(linha[n] for n in nomes)
        for n in nomes:
            if linha[n] == menor:
                vitorias[n] += 1
    return {"origens": len(por_origem), "dias": len(p),
            "erro": {n: float(p[n].mean()) for n in nomes},
            "mediana": {n: float(statistics.median(por_origem[n])) for n in nomes},
            "vitorias": vitorias, "por_origem": por_origem}


def tabela_resultado(linhas):
    texto = linhas.to_csv(index=False, float_format="%.4f", date_format="%Y-%m-%d", lineterminator="\n")
    return texto


def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def imprimir_resumo(r, recuo="   "):
    print(f"{recuo}{r['origens']} origens, {r['dias']} dias previstos com venda real")
    print(f"{recuo}{'':22}{'erro médio':>12}{'mediana por origem':>20}{'origens em que erra menos':>28}")
    for n in r["erro"]:
        print(f"{recuo}{n:22}{br(r['erro'][n]):>12}{br(r['mediana'][n]):>20}{r['vitorias'][n]:>28}")


def rodar_plano(arquivo, contrato_nome, usavel, real, fechada):
    contrato = CONTRATOS[contrato_nome]
    cortes, problemas = testar_plano(carregar_plano(arquivo), contrato)
    print(f"Plano {Path(arquivo).name}, contrato: {contrato['nome']}")
    print(f"   {len(cortes)} cortes: {sum(c['parte'] == 'escolha' for c in cortes)} de escolha e "
          f"{sum(c['parte'] == 'teste' for c in cortes)} de teste")
    if problemas:
        for regra, n, exemplo in problemas:
            quantos = "1 corte falha" if n == 1 else f"{n} cortes falham"
            print(f"   regra {regra}: {quantos}; o primeiro: {exemplo}" if n else f"   regra {regra}: {exemplo}")
        print(f"FALHOU: o plano tem vazamento ou não segue o contrato "
              f"({'1 problema' if len(problemas) == 1 else f'{len(problemas)} problemas'})")
        return 1
    print("   plano sem vazamento: as seis regras passam")
    print(f"   sha256 do plano: {sha(tabela_plano(cortes))}")
    linhas = avaliar(cortes, usavel, real, fechada)
    for parte in ("escolha", "teste"):
        r = resumo(linhas, parte)
        print(f"{parte.capitalize()}:")
        imprimir_resumo(r)
        if r["origens"] <= 24:
            print(f"   {'origem':12}" + "".join(f"{n:>22}" for n in METODOS))
            for origem, linha in r["por_origem"].iterrows():
                print(f"   {d(origem):12}" + "".join(f"{br(linha[n]):>22}" for n in METODOS))
    print(f"   sha256 dos erros por dia: {sha(tabela_resultado(linhas))}")
    return 0


def mes_da_escala(origem):
    seguinte = origem + pd.offsets.MonthBegin(1)
    return {"parte": "escolha", "origem": origem, "treino_de": INICIO, "treino_ate": origem,
            "de": seguinte, "ate": seguinte + pd.offsets.MonthEnd(0)}


def mostrar_aula(usavel, real, fechada):
    print("1. Uma noite só: a escala do mês, fechada na noite do dia 1, prevê o mês seguinte inteiro")
    for origem in (pd.Timestamp("2024-12-01"), pd.Timestamp("2025-03-01")):
        c = mes_da_escala(origem)
        linhas = avaliar([c], usavel, real, fechada)
        erros = {n: float(linhas[n].mean()) for n in METODOS}
        melhor = min(erros, key=erros.get)
        print(f"   noite de {d(origem)}, dias de {d(c['de'])} a {d(c['ate'])} ({len(linhas)} com venda real)")
        print("      " + "; ".join(f"{n} {br(e)}" for n, e in erros.items()) + f"  -> erra menos: {melhor}")

    print("2. O plano do ajuste da semana: cada dia previsto 7 dias antes, uma origem por noite")
    cortes, problemas = testar_plano(plano_semana(), CONTRATOS["semana"])
    for parte in ("escolha", "teste"):
        cs = [c for c in cortes if c["parte"] == parte]
        print(f"   {parte:8} origens de {d(cs[0]['origem'])} a {d(cs[-1]['origem'])} ({len(cs)} noites), "
              f"dias previstos de {d(cs[0]['de'])} a {d(cs[-1]['ate'])}")
    janelas = [(c["treino_ate"] - c["treino_de"]).days + 1 for c in cortes]
    print(f"   janela de treino: de 01/01/2024 até a noite da origem; de {janelas[0]} dias na primeira origem "
          f"a {janelas[-1]} na última")
    pulas = [c for c in pd.date_range(FIM_ESCOLHA - 6 * UM_DIA, FIM_ESCOLHA - UM_DIA)]
    print(f"   noites fora do plano: {d(pulas[0])} a {d(pulas[-1])} ({len(pulas)}), preveem setembro com a venda "
          f"de agosto")
    print("   teste do plano: " + ("sem vazamento, as seis regras passam" if not problemas else f"FALHOU {problemas}"))
    print(f"   sha256 do plano: {sha(tabela_plano(cortes))}")

    print("3. O período de escolha: o erro das três previsões, 7 dias antes, mês a mês do dia previsto")
    linhas = avaliar(cortes, usavel, real, fechada)
    r = resumo(linhas, "escolha")
    imprimir_resumo(r)
    esc = linhas[linhas["parte"] == "escolha"].copy()
    esc["mes"] = esc["dia"].dt.to_period("M")
    mensal = esc.groupby("mes")[list(METODOS)].mean()
    ganha = int((mensal["mesmo dia, 4 semanas"] < mensal["semana passada"]).sum())
    print(f"   meses em que o mesmo dia, 4 semanas erra menos que a semana passada: {ganha} de {len(mensal)}")
    for n in ("semana passada", "mesmo dia, 4 semanas"):
        lo, hi = mensal[n].idxmin(), mensal[n].idxmax()
        print(f"   {n}: o erro do mês vai de {br(mensal[n][lo])} ({lo.strftime('%m/%Y')}) "
              f"a {br(mensal[n][hi])} ({hi.strftime('%m/%Y')})")
    tst = linhas[linhas["parte"] == "teste"]
    print(f"   teste: {tst['origem'].nunique()} origens com venda real no dia previsto, guardadas para a comparação "
          f"de modelos")
    print(f"   sha256 dos erros por dia: {sha(tabela_resultado(linhas))}")

    print("4. A distância: os mesmos dias, de 01/04/2024 a 31/08/2025, previstos de noites diferentes")
    dias = pd.date_range("2024-04-01", FIM_ESCOLHA)  # a 56 dias, a primeira origem já tem 4 semanas de venda
    print(f"   {'previsto':26}{'semana passada':>16}{'mesmo dia, 4 semanas':>24}   dias")
    distancias = [("na véspera", 1), ("7 dias antes", 7), ("14 dias antes", 14), ("28 dias antes", 28),
                  ("35 dias antes", 35), ("56 dias antes", 56)]
    for rotulo, h in distancias:
        cs = []
        for dia in dias:
            origem = dia - h * UM_DIA
            cs.append({"parte": "escolha", "origem": origem, "treino_de": INICIO, "treino_ate": origem,
                       "de": dia, "ate": dia})
        linhas_h = avaliar(cs, usavel, real, fechada)
        print(f"   {rotulo:26}{br(linhas_h['semana passada'].mean()):>16}"
              f"{br(linhas_h['mesmo dia, 4 semanas'].mean()):>24}   {len(linhas_h)}")

    print("5. O atraso: se a venda do dia só chegasse na manhã seguinte, no período de escolha")
    atrasados = [dict(c, treino_ate=c["origem"] - UM_DIA) for c in cortes]
    _, prob = testar_plano(atrasados, dict(CONTRATOS["semana"], atraso=1))
    for rotulo, cs in (("venda do dia às 22h (corte na origem)", cortes),
                       ("venda do dia na manhã seguinte (corte na véspera)", atrasados)):
        cs = [c for c in cs if c["parte"] == "escolha"]
        lh = avaliar(cs, usavel, real, fechada)
        print(f"   {rotulo:50} semana passada {br(lh['semana passada'].mean())}; "
              f"mesmo dia, 4 semanas {br(lh['mesmo dia, 4 semanas'].mean())} ({len(lh)} dias)")
    print("   o plano com corte na véspera e atraso de 1 dia no contrato: "
          + ("sem vazamento" if not prob else f"FALHOU {prob}"))
    _, prob0 = testar_plano(cortes, dict(CONTRATOS["semana"], atraso=1))
    print("   o plano com corte na noite da origem e atraso de 1 dia no contrato: "
          + ("sem vazamento" if not prob0 else f"falha na regra 2 em {prob0[0][1]} cortes"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plano", help="arquivo .py com uma função plano() que retorna a lista de cortes")
    ap.add_argument("--contrato", choices=sorted(CONTRATOS), default="semana",
                    help="a decisão que o plano testa (padrão: semana)")
    a = ap.parse_args(argv)
    usavel, real, fechada = carregar()
    if a.plano:
        return rodar_plano(a.plano, a.contrato, usavel, real, fechada)
    mostrar_aula(usavel, real, fechada)
    venda = (LOJA / "venda_diaria.csv").read_bytes()
    print(f"venda usada: venda_diaria.csv sha256 {hashlib.sha256(venda).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
