"""Roda o teste de Dickey-Fuller numa série da loja ou num CSV, antes e depois de uma transformação.

Na pasta dessa aula:
    python3 testar.py loja                          # a venda da loja até a noite de 01/12/2025
    python3 testar.py loja --log --regressao ct     # no log, com constante e reta
    python3 testar.py loja --log --dif 1            # a diferença de um dia do log
    python3 testar.py loja --log --dif 7            # a diferença contra 7 dias antes
    python3 testar.py loja --log --sem-dia-da-semana --regressao ct
    python3 testar.py dados/quiosque.csv --log --de 2025-07-01

O CSV precisa das colunas data e unidades; a coluna fechado (1 quando a loja fechou) é opcional.
Dia sem linha, dia fechado e dia incompleto não servem para o teste, que precisa de todos os dias em
sequência. Cada um é trocado pela média do mesmo dia da semana, 7 dias antes e 7 dias depois (se um
deles também não serve, o programa procura até 4 semanas para cada lado). A troca usa dias depois do
buraco: vale para olhar o passado como foto, não para prever.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dickey_fuller import adf

AQUI = Path(__file__).resolve().parent
LOJA = AQUI.parent / "dados" / "loja"
CORTE = "2025-12-01"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def br(x, casas=2):
    if isinstance(x, float) and math.isnan(x):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d(t):
    return f"{t:%d/%m/%Y}"


def p_br(p):
    if p < 0.0001:
        return "abaixo de 0,0001"
    return br(p, 4)


def carregar_loja(corte=CORTE, loja=LOJA):
    """A venda da loja física, dia a dia, até a noite do corte. Vazio onde o dia não serve."""
    venda = pd.read_csv(loja / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
    cal = pd.read_csv(loja / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(venda.index.min(), corte, freq="D")
    serie = venda.reindex(dias)
    fechada = cal["loja_fechada"].reindex(dias) == 1
    hora = pd.to_datetime(serie["ultimo_registro"], format="%H:%M", errors="coerce")
    completo = (hora.dt.hour * 60 + hora.dt.minute >= 21 * 60 + 30) & (serie["unidades"] > 0) & ~fechada
    evento = (cal["feriado"].reindex(dias) != "") | (cal["promocao"].reindex(dias) != "")
    return serie["unidades"].where(completo).astype(float), evento


def carregar_csv(caminho):
    """Um CSV com data e unidades. Dia sem linha e dia fechado ficam vazios."""
    tab = pd.read_csv(caminho, parse_dates=["data"]).set_index("data").sort_index()
    dias = pd.date_range(tab.index.min(), tab.index.max(), freq="D")
    tab = tab.reindex(dias)
    unidades = tab["unidades"].astype(float)
    if "fechado" in tab:
        unidades = unidades.where(tab["fechado"].fillna(0) != 1)
    return unidades


def preencher(serie):
    """Troca cada dia vazio pela média do mesmo dia da semana, uma semana antes e uma depois."""
    cheia = serie.copy()
    for dia in serie.index[serie.isna()]:
        antes = depois = None
        for k in range(1, 5):
            if antes is None and not np.isnan(serie.get(dia - pd.Timedelta(days=7 * k), np.nan)):
                antes = serie[dia - pd.Timedelta(days=7 * k)]
            if depois is None and not np.isnan(serie.get(dia + pd.Timedelta(days=7 * k), np.nan)):
                depois = serie[dia + pd.Timedelta(days=7 * k)]
        vizinhos = [v for v in (antes, depois) if v is not None]
        if not vizinhos:
            raise ValueError(f"{d(dia)} não tem o mesmo dia da semana para trocar em 4 semanas")
        cheia[dia] = sum(vizinhos) / len(vizinhos)
    return cheia


def sem_dia_da_semana(log, evento=None):
    """Tira do log o peso médio de cada dia da semana, medido só nos dias sem feriado e sem promoção."""
    base = log if evento is None else log[~evento.reindex(log.index, fill_value=False)]
    peso = base.groupby(base.index.dayofweek).mean()
    peso = peso - peso.mean()
    return log - log.index.dayofweek.map(peso).to_numpy(), peso


def transformar(serie, log=False, dif=0, sem_dia=False, evento=None):
    x = serie
    if log:
        if (x <= 0).any():
            raise ValueError("o log precisa de venda acima de zero em todo dia")
        x = np.log(x)
    if sem_dia:
        if not log:
            raise ValueError("--sem-dia-da-semana trabalha no log: use junto com --log")
        x, _ = sem_dia_da_semana(x, evento)
    if dif:
        x = x.diff(dif).dropna()
    return x


def sinais(x):
    return {"desvio": float(x.std()), "ac1": float(x.autocorr(1)), "ac7": float(x.autocorr(7))}


def leitura(r):
    if r["p_valor"] < 0.05:
        return ("rejeita a raiz unitária a 5%, com essa regressão e esse trecho. Não diz que a série "
                "vai continuar assim, nem qual transformação usar.")
    return ("não rejeita a raiz unitária a 5%. Isso não prova a raiz unitária: o teste pode não ter "
            "separado essa série de um passeio.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("serie", help='"loja" ou o caminho de um CSV com data e unidades')
    ap.add_argument("--corte", default=CORTE, help="só para a loja: a noite até onde a venda entra")
    ap.add_argument("--de", help="primeiro dia do trecho, AAAA-MM-DD")
    ap.add_argument("--ate", help="último dia do trecho, AAAA-MM-DD")
    ap.add_argument("--log", action="store_true", help="tira o log da venda")
    ap.add_argument("--sem-dia-da-semana", action="store_true", help="tira do log o peso de cada dia da semana")
    ap.add_argument("--dif", type=int, default=0, help="diferença: 1 (contra ontem) ou 7 (contra 7 dias antes)")
    ap.add_argument("--regressao", choices=("c", "ct"), default="c",
                    help='"c": constante (padrão do adfuller); "ct": constante e reta no tempo')
    a = ap.parse_args()

    evento = None
    try:
        if a.serie == "loja":
            bruta, evento = carregar_loja(a.corte)
        else:
            bruta = carregar_csv(a.serie)
        if a.de or a.ate:
            bruta = bruta[a.de:a.ate]
        if bruta.notna().sum() < 60:
            raise ValueError("o trecho tem menos de 60 dias que servem; o teste fica sem sentido")
        vazios = int(bruta.isna().sum())
        cheia = preencher(bruta)
        x = transformar(cheia, a.log, a.dif, a.sem_dia_da_semana, evento)
        r = adf(x.to_numpy(), a.regressao)
    except (ValueError, FileNotFoundError, KeyError) as erro:
        print(f"PAROU: {erro}")
        sys.exit(1)

    nome = "a venda da loja física" if a.serie == "loja" else Path(a.serie).name
    passos = (["log"] if a.log else []) + (["sem o dia da semana"] if a.sem_dia_da_semana else []) + \
             ([f"diferença de {a.dif} dia" + ("s" if a.dif > 1 else "")] if a.dif else [])
    print(f"Série: {nome}, de {d(cheia.index[0])} a {d(cheia.index[-1])}, {len(cheia)} dias")
    print(f"   dias trocados pela média do mesmo dia da semana: {vazios}")
    print(f"   transformação: {', '.join(passos) if passos else 'nenhuma (a venda em unidades)'}")
    print(f"   regressão do teste: {'constante e reta' if a.regressao == 'ct' else 'constante'}")
    print("Dickey-Fuller aumentado")
    print(f"   estatística {br(r['estatistica'])}   p-valor {p_br(r['p_valor'])}")
    print(f"   diferenças anteriores escolhidas pelo AIC: {r['lags']}   linhas na regressão: {r['n']}")
    c = r["criticos"]
    print(f"   valores críticos: 1% {br(c['1%'])}   5% {br(c['5%'])}   10% {br(c['10%'])}")
    print(f"   leitura: {leitura(r)}")
    s = sinais(x)
    print("Outros sinais da mesma série")
    print(f"   desvio-padrão {br(s['desvio'], 3)}   correlação com 1 dia antes {br(s['ac1'])}   "
          f"com 7 dias antes {br(s['ac7'])}")
    tri = x.groupby(x.index.to_period("Q")).mean()
    print("   média por trimestre: " + "  ".join(f"{p.year}T{p.quarter} {br(v, 3 if a.log else 1)}"
                                                for p, v in tri.items()))


if __name__ == "__main__":
    main()
