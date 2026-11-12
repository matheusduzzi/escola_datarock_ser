"""Mede os componentes da venda da loja física, para escolher as famílias de modelo.

Aula «ARIMA, SARIMAX e suavização» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 hipoteses.py                # a venda diária, com o histórico até 31/08/2025
    python3 hipoteses.py --semanal      # a venda somada por semana, até 28/12/2025 (exercício)

Lê a venda e o calendário em dados/loja, na raiz do kit. Só usa o histórico até a data de --ate.
Na diária, é o que existe antes das primeiras previsões que a aula 11 vai testar.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
ANO = 365.25


def br(x, casas=2):
    if pd.isna(x):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def pct(x, casas=0):
    return f"{'+' if x >= 0 else '−'}{br(abs(x) * 100, casas)}%"


def carregar(ate):
    """Um dia por linha, do primeiro dia da venda até `ate`, com o que o calendário diz de cada dia."""
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False)
    cal = cal[cal["data"] <= ate].set_index("data")
    v = venda.set_index("data").reindex(cal.index)
    d = pd.DataFrame(index=cal.index)
    d["unidades"] = v["unidades"].astype(float)
    d["sem_registro"] = v["unidades"].isna()
    d["incompleto"] = v["ultimo_registro"].notna() & (v["ultimo_registro"] < "21:30")
    d["fechada"] = cal["loja_fechada"] == 1
    d["feriado_aberto"] = (cal["feriado"] != "") & ~d["fechada"]
    d["promocao"] = cal["promocao"]
    # o dia que serve para medir: com registro, completo e com a loja aberta (aula 03)
    d["serve"] = ~(d["sem_registro"] | d["incompleto"] | d["fechada"])
    return d


def autocorrelacao(s, lag):
    """Correlação da série com ela mesma `lag` passos antes, só nos pares em que os dois têm valor."""
    par = pd.concat([s, s.shift(lag)], axis=1).dropna()
    return par.iloc[:, 0].corr(par.iloc[:, 1]), len(par)


def onda_anual(datas):
    """Dois pares de seno e cosseno com período de um ano: uma onda suave que se repete todo ano."""
    ang = 2 * np.pi * datas.dayofyear.to_numpy() / ANO
    return {"sen1": np.sin(ang), "cos1": np.cos(ang), "sen2": np.sin(2 * ang), "cos2": np.cos(2 * ang)}


def matriz(datas, inicio, extras):
    """As colunas da regressão: constante, tendência, onda do ano e `extras` (dia da semana, eventos)."""
    colunas = {"constante": np.ones(len(datas)),
               "tendência": (datas - inicio).days.to_numpy() / ANO, **onda_anual(datas), **extras}
    return list(colunas), np.column_stack([np.asarray(c, dtype=float) for c in colunas.values()])


def regressao(y_log, datas, inicio, extras):
    """log(venda) = constante + tendência + onda do ano + `extras`. Mínimos quadrados.

    É a parte de regressão de um SARIMAX: o que o calendário explica, sem memória de um passo
    para o outro. O que sobra (o resíduo) mostra se ainda há memória para a parte ARMA.
    """
    nomes, X = matriz(datas, inicio, extras)
    with np.errstate(all="ignore"):     # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(X, y_log, rcond=None)
        ajuste = X @ coef
    if not np.all(np.isfinite(ajuste)):
        raise SystemExit("a regressão não fechou: confira os dados em dados/loja")
    return dict(zip(nomes, coef)), y_log - ajuste


def extras_diarios(x):
    """Dia da semana e eventos do calendário de cada dia. A loja sabe tudo isso antes do dia."""
    extras = {f"dia {DIAS[k]}": x.index.dayofweek == k for k in range(1, 7)}
    extras.update({
        "Black Friday": x["promocao"] == "Black Friday",
        "fim de semana da Black Friday": x["promocao"] == "fim de semana da Black Friday",
        "Natal": x["promocao"] == "Natal",
        "feriado com a loja aberta": x["feriado_aberto"],
    })
    return extras


def imprimir_onda(efeito):
    """O multiplicador da onda do ano no dia 15 de cada mês, contra a média do ano."""
    meio = pd.DatetimeIndex([f"2025-{m:02d}-15" for m in range(1, 13)])
    o = onda_anual(meio)
    log = sum(efeito[k] * o[k] for k in o)
    return ", ".join(f"{MESES[i]} {br(np.exp(v), 2)}" for i, v in enumerate(log))


def imprimir_memoria(serie, lags, unidade):
    print(f"  defasagem   correlação   pares")
    for lag in lags:
        r, n = autocorrelacao(serie, lag)
        print(f"  {lag:>3} {unidade:<7}{br(r, 3):>10}   {n:>5}")


def diaria(ate):
    d = carregar(ate)
    serve = d["serve"]
    u = d["unidades"].where(serve)
    normal = serve & (d["promocao"] == "") & ~d["feriado_aberto"]
    print(f"Venda diária da loja física, de {d.index[0]:%d/%m/%Y} a {d.index[-1]:%d/%m/%Y}")
    print(f"  {len(d)} dias no calendário; {int(serve.sum())} servem para medir")
    print(f"  fora: {int(d['sem_registro'].sum())} sem registro, {int(d['incompleto'].sum())} incompletos, "
          f"{int(d['fechada'].sum())} de loja fechada")

    print("\n1. Memória: a venda parece com a de quantos dias antes?")
    imprimir_memoria(u, (1, 2, 3, 7, 14, 28), "dias")

    print("\n2. Semana: venda média de cada dia da semana, em dias sem promoção nem feriado")
    media = u[normal].mean()
    for k in range(7):
        m = u[normal & (d.index.dayofweek == k)].mean()
        print(f"  {DIAS[k]}   {br(m, 1):>6}   {br(m / media, 2)} vez a média")
    print(f"  média de todos os dias: {br(media, 1)}")

    print("\n3. Tendência e tamanho do vaivém da semana, de janeiro a agosto de cada ano")
    print("  ano    média   sábado   domingo   sábado − domingo")
    for ano in (2024, 2025):
        p = normal & (d.index.year == ano) & (d.index.month <= 8)
        sab = u[p & (d.index.dayofweek == 5)].mean()
        dom = u[p & (d.index.dayofweek == 6)].mean()
        print(f"  {ano}  {br(u[p].mean(), 1):>7}  {br(sab, 1):>7}  {br(dom, 1):>8}  {br(sab - dom, 1):>17}")

    x = d[serve]
    extras = extras_diarios(x)
    eventos = {k: v for k, v in extras.items() if not k.startswith("dia ")}
    efeito, res = regressao(np.log(x["unidades"].to_numpy()), x.index, d.index[0], extras)
    residuo = pd.Series(res, index=x.index).reindex(d.index)
    print("\n4. Regressão do calendário, no log da venda: quanto cada parte multiplica a venda")
    print(f"  tendência: {pct(np.exp(efeito['tendência']) - 1, 1)} por ano")
    print("  dia da semana, contra a segunda: " + ", ".join(
        f"{DIAS[k]} {pct(np.exp(efeito[f'dia {DIAS[k]}']) - 1)}" for k in range(1, 7)))
    print("  onda do ano, no dia 15 de cada mês: " + imprimir_onda(efeito))
    print("  eventos do calendário, e quantos dias de cada um há no histórico:")
    for nome, marca in eventos.items():
        print(f"    {nome:<30} {pct(np.exp(efeito[nome]) - 1):>6}   {int(marca.sum()):>3} dia(s)")

    print("\n5. O que a regressão do calendário não explica (o resíduo)")
    print(f"  desvio do resíduo: {br(residuo.std(), 3)} no log, cerca de {br((np.exp(residuo.std()) - 1) * 100, 1)}% da venda")
    imprimir_memoria(residuo, (1, 2, 3, 7, 14), "dias")
    print(f"  com {int(residuo.notna().sum())} dias, correlação entre −{br(2 / np.sqrt(residuo.notna().sum()), 2)} "
          f"e +{br(2 / np.sqrt(residuo.notna().sum()), 2)} é do tamanho do acaso")

    print(f"\n6. Histórico: {len(d)} dias, {br(len(d) / ANO, 1)} ciclo(s) de um ano e {len(d) // 7} de uma semana")


def semanal(ate):
    d = carregar(ate)
    seg = d.index[d.index.dayofweek == 0][0]
    dom = d.index[d.index.dayofweek == 6][-1]
    d = d.loc[seg:dom]
    g = d.groupby((d.index - seg).days // 7)
    s = pd.DataFrame({
        "unidades": g["unidades"].sum(min_count=1),
        "falha": g.apply(lambda x: int((x["sem_registro"] | x["incompleto"]).sum())),
        "fechada": g["fechada"].sum(),
        "feriado_aberto": g["feriado_aberto"].sum(),
        "bf": g["promocao"].apply(lambda x: int((x == "Black Friday").any())),
        "natal": g["promocao"].apply(lambda x: int((x == "Natal").sum())),
    })
    s.index = pd.DatetimeIndex([seg + pd.Timedelta(weeks=int(i)) for i in s.index])
    completa = s["falha"] == 0
    u = s["unidades"].where(completa)
    print(f"Venda semanal da loja física, de segunda a domingo, de {s.index[0]:%d/%m/%Y} a {dom:%d/%m/%Y}")
    print(f"  {len(s)} semanas; {int(completa.sum())} sem dia sem registro nem incompleto")
    print("  as outras ficam de fora das contas abaixo: a soma delas está incompleta")

    print("\n1. Memória: a semana parece com a de quantas semanas antes?")
    imprimir_memoria(u, (1, 2, 4, 52), "semanas")

    print("\n2. Dia da semana: toda semana tem uma segunda, uma terça... e um domingo")
    print("  o peso de cada dia da semana entra igual em toda soma semanal")

    print("\n3. Tendência: as mesmas semanas do ano, sem evento nem falha, nos dois anos")
    limpa = completa & (s["bf"] == 0) & (s["natal"] == 0) & (s["fechada"] == 0) & (s["feriado_aberto"] == 0)
    n = len(s) // 2
    pares = [i for i in range(n) if limpa.iloc[i] and i + n < len(s) and limpa.iloc[i + n]]
    m24, m25 = u.iloc[pares].mean(), u.iloc[[i + n for i in pares]].mean()
    print(f"  {len(pares)} pares de semanas: 2024 {br(m24, 0)}, 2025 {br(m25, 0)}, {pct(m25 / m24 - 1, 1)}")

    x = s[completa]
    meio = x.index + pd.Timedelta(days=3)          # a quinta-feira representa a semana
    eventos = {"semana da Black Friday": x["bf"], "dias de Natal na semana": x["natal"],
               "dias de loja fechada na semana": x["fechada"], "feriados abertos na semana": x["feriado_aberto"]}
    efeito, res = regressao(np.log(x["unidades"].to_numpy()), meio, s.index[0], eventos)
    residuo = pd.Series(res, index=x.index).reindex(s.index)
    print("\n4. Regressão do calendário, no log da venda semanal: quanto cada parte multiplica a semana")
    print(f"  tendência: {pct(np.exp(efeito['tendência']) - 1, 1)} por ano")
    print("  onda do ano, no dia 15 de cada mês: " + imprimir_onda(efeito))
    print("  eventos do calendário (por semana, ou por dia na semana), e quantas semanas têm cada um:")
    for nome, col in eventos.items():
        print(f"    {nome:<32} {pct(np.exp(efeito[nome]) - 1):>6}   {int((col > 0).sum()):>3} semana(s)")

    print("\n5. O que a regressão do calendário não explica (o resíduo)")
    print(f"  desvio do resíduo: {br(residuo.std(), 3)} no log, cerca de {br((np.exp(residuo.std()) - 1) * 100, 1)}% da semana")
    imprimir_memoria(residuo, (1, 2, 4), "semanas")
    k = int(residuo.notna().sum())
    print(f"  com {k} semanas, correlação entre −{br(2 / np.sqrt(k), 2)} e +{br(2 / np.sqrt(k), 2)} é do tamanho do acaso")

    print(f"\n6. Histórico: {len(s)} semanas, {br(len(s) / 52, 1)} ciclo(s) de 52 semanas")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ate", help="último dia do histórico (padrão: 31/08/2025 na diária, 28/12/2025 na semanal)")
    ap.add_argument("--semanal", action="store_true", help="soma a venda por semana, de segunda a domingo")
    a = ap.parse_args()
    ate = pd.Timestamp(a.ate or ("2025-12-28" if a.semanal else "2025-08-31"))
    semanal(ate) if a.semanal else diaria(ate)


if __name__ == "__main__":
    main()
