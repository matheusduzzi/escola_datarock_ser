"""As previsões mais simples da venda da loja física: naive e naive sazonal, por horizonte e por frequência.

Rode de dentro da pasta dessa aula:  python3 naive.py
A previsão de um mês, num arquivo:   python3 naive.py --origem 2025-12-01 --saida previsoes.csv
Com a sua regra, do exercício:       python3 naive.py --origem 2025-12-01 --regra minha_baseline.py --saida minhas.csv
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

Sem opções, o programa mostra:
1. Uma noite, os próximos dias: o que cada previsão diz a partir da noite de 01/09/2025.
2. O erro por horizonte, de 01/09 a 26/10/2025: a previsão feita 1, 2, ... 63 dias antes de cada dia.
3. Os dias que ficam sem previsão quando o dia copiado não serve.
4. A mesma ideia com o total da semana: o período da repetição passa de 7 dias para 52 semanas.
5. A previsão de janeiro de 2026, feita na noite de 01/12/2025, e o que ela copia.

Com --origem, o programa prevê cada dia do mês seguinte à origem, grava o arquivo (se tiver --saida), mostra o
sha256 dele e refaz a previsão com a venda cortada na origem para ver se dá igual. Quando a venda real do mês
existe no arquivo, mostra também o erro.

Dia usável: dia completo (último pedido às 21h30 ou depois) com a loja aberta, como na aula 03.
"""
import argparse
import hashlib
import importlib.util
import io
import math
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
LOJA = AQUI.parent / "dados" / "loja"
INICIO, FIM = "2024-01-01", "2025-12-31"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
UM_DIA = pd.Timedelta(days=1)
UMA_SEMANA = pd.Timedelta(weeks=1)


def br(x, casas=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d(t):
    return f"{t:%d/%m/%Y}"


def dm(t):
    return f"{t:%d/%m} {DIAS[t.dayofweek]}"


def carregar(loja=LOJA):
    """A venda no calendário. usavel: unidades do dia completo com a loja aberta (vazio nos outros).
    semana_bruta: unidades com o dia fechado valendo 0 e vazio no dia sem registro ou incompleto.
    calendario: o calendário inteiro, até 31/01/2026, que a loja conhece antes."""
    venda = pd.read_csv(loja / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
    cal = pd.read_csv(loja / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, FIM, freq="D")
    serie = venda.reindex(dias)
    fechada = cal["loja_fechada"].reindex(dias) == 1
    hora = pd.to_datetime(serie["ultimo_registro"], format="%H:%M", errors="coerce")
    completo = (hora.dt.hour * 60 + hora.dt.minute >= 21 * 60 + 30) & (serie["unidades"] > 0) & ~fechada
    usavel = serie["unidades"].where(completo).astype(float)
    semana_bruta = serie["unidades"].where(completo | fechada).astype(float)
    return usavel, semana_bruta, cal


def ate(serie, origem):
    """A série como ela estava na noite da origem: o que vem depois some."""
    return serie[:origem]


def horizonte(origem, dia, passo=UM_DIA):
    """Quantos passos (dias ou semanas) separam a noite da origem do dia previsto."""
    return int((dia - origem) / passo)


# As previsões. Todas recebem a série já cortada na origem e devolvem (valor, dia copiado).

def naive(serie, origem, dia, passo=UM_DIA):
    """Repete o último valor: o da própria origem. Vazio se a origem não é usável."""
    return serie.get(origem, math.nan), origem


def naive_sazonal(serie, origem, dia, m=7, passo=UM_DIA):
    """Repete o valor de m passos antes, no mesmo ponto da repetição, o mais recente que já existe na origem.
    Com horizonte h, volta (k + 1) vezes m passos a partir do dia previsto, com k = (h - 1) // m."""
    h = horizonte(origem, dia, passo)
    k = (h - 1) // m
    fonte = dia - m * (k + 1) * passo
    return serie.get(fonte, math.nan), fonte


def media_28(serie, origem, dia, passo=UM_DIA):
    """A média dos dias usáveis nos 28 dias até a origem (a da apresentação do curso)."""
    janela = serie[origem - 27 * UM_DIA: origem].dropna()
    return (janela.mean() if len(janela) else math.nan), None


METODOS = {"naive": naive, "naive sazonal": naive_sazonal, "média dos 28 dias": media_28}


def prever(funcao, serie, origem, dia, **kw):
    """Chama a previsão sempre com a série cortada na origem."""
    return funcao(ate(serie, origem), origem, dia, **kw)


def erros_por_horizonte(usavel, metodos, h, dias):
    """Para cada dia de `dias`, faz a previsão na noite de h dias antes. Mantém só os dias em que o real e todas
    as previsões têm número, para comparar os métodos nos mesmos dias. Devolve (n, {método: erro médio})."""
    linhas = []
    for dia in dias:
        real = usavel.get(dia, math.nan)
        origem = dia - h * UM_DIA
        prev = [prever(f, usavel, origem, dia)[0] for f in metodos.values()]
        if not math.isnan(real) and not any(math.isnan(p) for p in prev):
            linhas.append([abs(real - p) for p in prev])
    n = len(linhas)
    return n, {nome: sum(l[i] for l in linhas) / n for i, nome in enumerate(metodos)}


def semanas(semana_bruta):
    """Total de cada semana, de segunda a domingo. Só a semana com os 7 dias completos ou fechados tem total."""
    s = semana_bruta.to_frame("u")
    s["ok"] = s["u"].notna()
    g = s.resample("W-SUN").agg({"u": "sum", "ok": "sum"})
    return g["u"].where(g["ok"] == 7)


def carregar_regra(arquivo):
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        caminho = (Path.cwd() / caminho) if (Path.cwd() / caminho).exists() else AQUI / caminho
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.prever


def mes_seguinte(origem):
    inicio = (origem + pd.offsets.MonthBegin(1)).normalize()
    return pd.date_range(inicio, inicio + pd.offsets.MonthEnd(0), freq="D")


def tabela(previsoes):
    """O arquivo de previsões: uma linha por dia, sempre na mesma ordem e no mesmo formato."""
    buf = io.StringIO()
    buf.write("dia,dia_semana,origem,horizonte,metodo,previsao,copiado_de\n")
    for p in previsoes:
        valor = "" if p["previsao"] is None or math.isnan(p["previsao"]) else f"{p['previsao']:.1f}"
        copiado = "" if p["copiado_de"] is None else f"{p['copiado_de']:%Y-%m-%d}"
        buf.write(f"{p['dia']:%Y-%m-%d},{DIAS[p['dia'].dayofweek]},{p['origem']:%Y-%m-%d},{p['horizonte']},"
                  f"{p['metodo']},{valor},{copiado}\n")
    return buf.getvalue()


def previsoes_do_mes(usavel, cal, origem, regra=None):
    """Prevê cada dia do mês seguinte à origem. Sem regra, usa o naive sazonal puro."""
    linhas = []
    for dia in mes_seguinte(origem):
        if regra is None:
            valor, fonte = prever(naive_sazonal, usavel, origem, dia)
            metodo = "naive sazonal"
        else:
            valor, fonte = regra(ate(usavel, origem), cal, origem, dia)
            metodo = "regra"
        valor = math.nan if valor is None else float(valor)
        linhas.append({"dia": dia, "origem": origem, "horizonte": horizonte(origem, dia), "metodo": metodo,
                       "previsao": valor, "copiado_de": fonte})
    return linhas


def relatorio():
    usavel, semana_bruta, cal = carregar()
    sha_venda = hashlib.sha256((LOJA / "venda_diaria.csv").read_bytes()).hexdigest()

    print("1. Uma noite, os próximos dias: previsões feitas na noite de 01/09/2025 seg")
    origem = pd.Timestamp("2025-09-01")
    print(f"   venda do dia da origem, 01/09 seg: {br(usavel[origem], 0)}")
    print("   dia          real   naive   naive sazonal (copia)")
    for dia in pd.date_range("2025-09-02", "2025-09-10"):
        vn, _ = prever(naive, usavel, origem, dia)
        vs, fonte = prever(naive_sazonal, usavel, origem, dia)
        print(f"   {dm(dia):<11} {br(usavel.get(dia), 0):>5} {br(vn, 0):>7} {br(vs, 0):>8}  ({dm(fonte)})")

    print("2. O erro por horizonte: cada dia de 01/09 a 26/10/2025, previsto h dias antes")
    print("   só os dias em que o real e as três previsões têm número; erro médio em unidades por dia")
    print("   h    dias   naive   naive sazonal   média dos 28 dias")
    alvo = pd.date_range("2025-09-01", "2025-10-26", freq="D")
    for h in [1, 2, 3, 4, 5, 6, 7, 14, 28, 35, 63]:
        n, e = erros_por_horizonte(usavel, METODOS, h, alvo)
        print(f"   {h:<4} {n:>4} {br(e['naive']):>7} {br(e['naive sazonal']):>15} {br(e['média dos 28 dias']):>19}")

    print("3. Os dias sem previsão: naive sazonal feito 7 dias antes, de 01/09 a 26/10/2025")
    reais = [dia for dia in alvo if not math.isnan(usavel.get(dia, math.nan))]
    buracos = []
    for dia in reais:
        v, fonte = prever(naive_sazonal, usavel, dia - 7 * UM_DIA, dia)
        if math.isnan(v):
            buracos.append((dia, fonte))
    print(f"   dias usáveis: {len(reais)}; com previsão: {len(reais) - len(buracos)}; sem previsão: {len(buracos)}")
    for dia, fonte in buracos:
        print(f"   {dm(dia)}: copiaria {dm(fonte)}, que não é usável")

    print("4. A frequência semanal: total de segunda a domingo, semanas de 12/01 a 26/10/2025")
    tot = semanas(semana_bruta)
    fim_semanas = pd.date_range("2025-01-12", "2025-10-26", freq="W-SUN")
    print(f"   semanas no período: {len(fim_semanas)}; com os 7 dias completos ou fechados: "
          f"{int(tot[fim_semanas].notna().sum())}")
    print("   previsão feita    semanas   naive (semana anterior)   naive sazonal (52 semanas antes)")
    abaixo = []
    for h in (1, 4):
        linhas = []
        for w in fim_semanas:
            real = tot.get(w, math.nan)
            origem_w = w - h * UMA_SEMANA
            pn, _ = naive(ate(tot, origem_w), origem_w, w, passo=UMA_SEMANA)
            ps, _ = naive_sazonal(ate(tot, origem_w), origem_w, w, m=52, passo=UMA_SEMANA)
            if not any(math.isnan(x) for x in (real, pn, ps)):
                linhas.append((abs(real - pn), abs(real - ps), real, ps < real))
        n = len(linhas)
        abaixo.append((h, sum(l[3] for l in linhas), n))
        en = sum(l[0] for l in linhas) / n
        es = sum(l[1] for l in linhas) / n
        pn_ = 100 * sum(l[0] / l[2] for l in linhas) / n
        ps_ = 100 * sum(l[1] / l[2] for l in linhas) / n
        rot = f"{h} semana antes" if h == 1 else f"{h} semanas antes"
        print(f"   {rot:<17} {n:>4}   {br(en):>8} unidades ({br(pn_)}%)   {br(es):>8} unidades ({br(ps_)}%)")
    print("   semanas em que o naive sazonal ficou abaixo do real: "
          + "; ".join(f"{a} de {n} feito {h} semana{'s' if h > 1 else ''} antes" for h, a, n in abaixo))
    cresc = tot["2025-01-12":"2025-10-26"].mean() / tot["2024-01-14":"2024-10-27"].mean() - 1
    print(f"   média da semana completa, jan a out: 2024 {br(tot['2024-01-14':'2024-10-27'].mean())}, "
          f"2025 {br(tot['2025-01-12':'2025-10-26'].mean())} ({br(100 * cresc)}% a mais)")

    print("5. A escala de janeiro de 2026: naive sazonal feito na noite de 01/12/2025 seg")
    origem = pd.Timestamp("2025-12-01")
    linhas = previsoes_do_mes(usavel, cal, origem)
    print(f"   horizonte: {linhas[0]['horizonte']} a {linhas[-1]['horizonte']} dias")
    print("   o que cada dia da semana copia:")
    vistos = set()
    for p in linhas:
        fonte = p["copiado_de"]
        if fonte in vistos:
            continue
        vistos.add(fonte)
        marca = cal.loc[fonte, "feriado"] or cal.loc[fonte, "promocao"]
        print(f"      {DIAS[p['dia'].dayofweek]}: copia {dm(fonte)}, {br(p['previsao'], 0)} unidades"
              + (f"  ({marca})" if marca else ""))
    jan = [p for p in linhas]
    media = sum(p["previsao"] for p in jan) / len(jan)
    fechados = [p["dia"] for p in jan if cal.loc[p["dia"], "loja_fechada"] == 1]
    print(f"   média dos 31 dias previstos: {br(media)}; janeiro de 2025 vendeu "
          f"{br(usavel['2025-01-01':'2025-01-31'].mean())} por dia usável")
    print("   dias em que o calendário já diz loja fechada: "
          + ", ".join(f"{dm(x)} (previsto {br(next(p['previsao'] for p in jan if p['dia'] == x), 0)})" for x in fechados))
    texto = tabela(linhas)
    print(f"   arquivo de 31 linhas: sha256 {hashlib.sha256(texto.encode()).hexdigest()[:16]}")
    print(f"   venda usada: venda_diaria.csv sha256 {sha_venda[:16]}")


def por_origem(origem, saida=None, regra_arquivo=None):
    usavel, _, cal = carregar()
    regra = carregar_regra(regra_arquivo) if regra_arquivo else None
    if origem > pd.Timestamp(FIM):
        sys.exit(f"A origem {d(origem)} vem depois do último dia da venda ({d(pd.Timestamp(FIM))}).")
    linhas = previsoes_do_mes(usavel, cal, origem, regra)
    texto = tabela(linhas)
    nome = f"a regra de {Path(regra_arquivo).name}" if regra_arquivo else "o naive sazonal"
    print(f"Previsões com {nome}, feitas na noite de {d(origem)} {DIAS[origem.dayofweek]}")
    print(f"   dias previstos: {d(linhas[0]['dia'])} a {d(linhas[-1]['dia'])}, horizonte "
          f"{linhas[0]['horizonte']} a {linhas[-1]['horizonte']} dias")
    vazios = [p["dia"] for p in linhas if math.isnan(p["previsao"])]
    print(f"   dias sem número: {len(vazios)}" + (f" ({', '.join(dm(x) for x in vazios)})" if vazios else ""))
    print(f"   sha256 das previsões: {hashlib.sha256(texto.encode()).hexdigest()}")
    print(f"   venda usada: venda_diaria.csv sha256 "
          f"{hashlib.sha256((LOJA / 'venda_diaria.csv').read_bytes()).hexdigest()[:16]}")
    # A mesma previsão, com o arquivo cortado na origem: é o que existia na noite.
    cortada = previsoes_do_mes(usavel[:origem], cal, origem, regra)
    igual = tabela(cortada) == texto
    print(f"   com a venda cortada na origem: {'igual' if igual else 'DIFERENTE'}")
    if saida:
        Path(saida).write_text(texto, encoding="utf-8")
        print(f"   gravado em {saida}")
    reais = [(p, usavel.get(p["dia"], math.nan)) for p in linhas]
    reais = [(p, r) for p, r in reais if not math.isnan(r)]
    if reais:
        com_num = [(p, r) for p, r in reais if not math.isnan(p["previsao"])]
        erro = sum(abs(r - p["previsao"]) for p, r in com_num) / len(com_num) if com_num else math.nan
        print(f"   venda real no arquivo: {len(reais)} dias usáveis; com previsão: {len(com_num)}; "
              f"erro médio {br(erro)} unidades por dia")
    if not igual:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origem", help="noite da previsão, AAAA-MM-DD; prevê cada dia do mês seguinte")
    ap.add_argument("--saida", help="arquivo CSV onde gravar as previsões")
    ap.add_argument("--regra", help="arquivo com a função prever(usavel, calendario, origem, dia)")
    a = ap.parse_args()
    if a.origem:
        por_origem(pd.Timestamp(a.origem), a.saida, a.regra)
    else:
        relatorio()


if __name__ == "__main__":
    main()
