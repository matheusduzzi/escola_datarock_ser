"""O teste de Dickey-Fuller na venda da loja e em séries sorteadas, antes e depois de cada transformação.

Rode de dentro da pasta dessa aula:  python3 estacionariedade.py
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)
Leva alguns segundos: a parte 5 roda o teste 3.500 vezes.

1. A série do teste: a venda até a noite de 01/12/2025 e os dias que precisaram de troca.
2. Uma série sorteada de cada tipo, com o mecanismo escrito, e o que o teste diz de cada uma.
3. O que o Rafael rodou: o teste nas linhas do arquivo, como elas vêm.
4. A venda da loja em sete versões: unidades, log, log com reta, sem o dia da semana e as diferenças.
5. Quantas vezes o teste rejeita, em 500 séries sorteadas de cada tipo.
6. Depois de tirar o calendário do log: o que sobra tem memória?

As séries sorteadas usam numpy.random.default_rng com número fixo: a saída é a mesma toda vez.
"""
import argparse
import math

import numpy as np
import pandas as pd

from dickey_fuller import adf
from testar import CORTE, LOJA, br, carregar_loja, d, p_br, preencher, sem_dia_da_semana, sinais

N = 701  # dias de 01/01/2024 a 01/12/2025, o tamanho da série da loja
REPETICOES = 500
PESO_DIA = np.log([0.92, 0.90, 0.95, 1.00, 1.12, 1.45, 0.70])  # os pesos do gerar.py, segunda a domingo


def ar1(phi, e):
    y = np.zeros(len(e))
    for i in range(1, len(e)):
        y[i] = phi * y[i - 1] + e[i]
    return y


def loja_sorteada(rng, n=N, onda=True):
    """O log de uma venda com o mecanismo do gerar.py, sem eventos e sem falhas do sistema."""
    t = np.arange(n)
    y = np.log(120 * (1 + 0.15 * t / 365)) + PESO_DIA[t % 7] + rng.normal(0, 0.08, n)
    if onda:
        y = y + np.log(1 + 0.12 * np.cos(2 * np.pi * (t + 1 - 350) / 365.25))
    return y


TIPOS = [
    ("passeio aleatório", "c", "hoje = ontem + sorteio; tem raiz unitária",
     lambda rng: np.cumsum(rng.normal(0, 0.08, N))),
    ("volta rápido ao nível", "c", "hoje = 0,5 x ontem + sorteio",
     lambda rng: ar1(0.5, rng.normal(0, 0.08, N))),
    ("volta devagar ao nível", "c", "hoje = 0,98 x ontem + sorteio",
     lambda rng: ar1(0.98, rng.normal(0, 0.08, N))),
    ("nível com degrau", "c", "sorteio em torno de um nível que sobe 0,2 no dia 351",
     lambda rng: rng.normal(0, 0.08, N) + np.where(np.arange(N) >= 350, 0.2, 0.0)),
]
TIPOS_LOJA = [
    ("loja pelo gerar.py", "ct", "log: reta + dia da semana + onda do ano + sorteio", lambda rng: loja_sorteada(rng)),
    ("a mesma loja, 4 anos", "ct", "o mesmo mecanismo com 1.461 dias", lambda rng: loja_sorteada(rng, 1461)),
    ("a mesma loja sem a onda", "ct", "log: reta + dia da semana + sorteio", lambda rng: loja_sorteada(rng, onda=False)),
]


def linha_teste(rotulo, x, regressao, largura=40):
    r = adf(np.asarray(x, dtype=float), regressao)
    return r, (f"   {rotulo:<{largura}} {br(r['estatistica'], 3):>7}  {p_br(r['p_valor']):>16}  "
               f"{r['lags']:>3}  {br(r['criticos']['5%'], 3):>6}")


def calendario_do_log(log, cal):
    """Mínimos quadrados do log contra reta, onda do ano (seno e cosseno), dia da semana e eventos."""
    t = np.arange(len(log), dtype=float) / 365.0
    dia_ano = log.index.dayofyear.to_numpy()
    colunas = {"constante": np.ones(len(log)), "reta": t,
               "seno do ano": np.sin(2 * np.pi * dia_ano / 365.25),
               "cosseno do ano": np.cos(2 * np.pi * dia_ano / 365.25)}
    for k, nome in enumerate(["ter", "qua", "qui", "sex", "sáb", "dom"], start=1):
        colunas[nome] = (log.index.dayofweek == k).astype(float)
    promo = cal["promocao"].reindex(log.index)
    feriado = cal["feriado"].reindex(log.index) != ""
    for nome in ["Black Friday", "fim de semana da Black Friday", "Natal"]:
        colunas[nome] = (promo == nome).astype(float).to_numpy()
    colunas["feriado aberto"] = feriado.astype(float).to_numpy()
    X = np.column_stack(list(colunas.values()))
    with np.errstate(all="ignore"):
        beta, *_ = np.linalg.lstsq(X, log.to_numpy(), rcond=None)
        sobra = log.to_numpy() - X @ beta
    return dict(zip(colunas, beta)), pd.Series(sobra, index=log.index)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repeticoes", type=int, default=REPETICOES, help="séries sorteadas por tipo na parte 5")
    a = ap.parse_args()

    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    usavel, evento = carregar_loja(CORTE)
    dias = usavel.index
    sem_linha = int((~dias.isin(venda.index)).sum())
    fechado = int((cal["loja_fechada"].reindex(dias) == 1).sum())
    incompleto = int(usavel.isna().sum()) - sem_linha - fechado
    cheia = preencher(usavel)
    log = np.log(cheia)

    print(f"1. A série do teste: a venda da loja física até a noite de {d(pd.Timestamp(CORTE))}")
    print(f"   {len(dias)} dias, de {d(dias[0])} a {d(dias[-1])}")
    print(f"   dias que não servem: {usavel.isna().sum()} ({sem_linha} sem linha, {fechado} com a loja fechada, "
          f"{incompleto} incompletos)")
    print("   cada um foi trocado pela média do mesmo dia da semana, 7 dias antes e 7 dias depois")
    print("   o teste usa o log da venda: o sábado multiplica o nível, e o log troca multiplicar por somar")

    print(f"2. Uma série sorteada de cada tipo, {N} dias, sorteio com desvio 0,08")
    print(f"   {'série':<40} {'estat.':>7}  {'p-valor':>16}  {'dif':>3}  {'5%':>6}")
    rng = np.random.default_rng(2025)
    for nome, reg, mecanismo, gerar in TIPOS:
        _, txt = linha_teste(nome, gerar(rng), reg)
        print(txt)
        print(f"      {mecanismo}")
    print("   estat.: a estatística do teste; dif: diferenças anteriores escolhidas pelo AIC; 5%: o valor crítico")
    print("   regressão com constante; rejeita a raiz unitária a 5% quando a estatística fica abaixo do valor crítico")

    print("3. O que o Rafael rodou: as linhas do arquivo até 01/12/2025, como vêm, sem calendário")
    linhas = venda.loc[:CORTE, "unidades"].astype(float)
    print(f"   {len(linhas)} linhas para {len(dias)} dias: os dias sem linha somem e os vizinhos ficam colados")
    print(f"   dias com 0 unidades: {(linhas == 0).sum()}; o log de 0 não existe")
    for rotulo, x in [("unidades", linhas), ("diferença de 1 dia", linhas.diff().dropna())]:
        _, txt = linha_teste(rotulo, x, "c")
        print(txt)

    print("4. A venda da loja em sete versões (a série da parte 1)")
    print(f"   {'versão':<40} {'estat.':>7}  {'p-valor':>16}  {'dif':>3}  {'5%':>6}   desvio  ac1    ac7")
    log_sem_dia, peso = sem_dia_da_semana(log, evento)
    versoes = [
        ("unidades, constante", cheia, "c"),
        ("log, constante", log, "c"),
        ("log, constante e reta", log, "ct"),
        ("log sem o dia da semana, constante e reta", log_sem_dia, "ct"),
        ("diferença de 1 dia do log", log.diff().dropna(), "c"),
        ("diferença de 7 dias do log", log.diff(7).dropna(), "c"),
        ("diferença de 1 dia, log sem o dia", log_sem_dia.diff().dropna(), "c"),
    ]
    for rotulo, x, reg in versoes:
        _, txt = linha_teste(rotulo, x, reg, 41)
        s = sinais(x)
        casas = 1 if rotulo.startswith("unidades") else 3
        print(f"{txt}  {br(s['desvio'], casas):>6}  {br(s['ac1']):>5}  {br(s['ac7']):>5}")
    print("   desvio: desvio-padrão da versão; ac1 e ac7: correlação com o valor de 1 e de 7 dias antes")
    print("   peso do dia da semana no log, sem feriados e promoções: "
          + "  ".join(f"{dia} {br(peso[k], 3)}" for k, dia in enumerate(["seg", "ter", "qua", "qui", "sex", "sáb", "dom"])))

    print(f"5. Quantas vezes o teste rejeita a raiz unitária a 5%, em {a.repeticoes} séries sorteadas de cada tipo")
    rng = np.random.default_rng(505)
    for nome, reg, mecanismo, gerar in TIPOS + TIPOS_LOJA:
        rejeita = sum(adf(gerar(rng), reg)["p_valor"] < 0.05 for _ in range(a.repeticoes))
        raiz = "sim" if nome == "passeio aleatório" else "não"
        print(f"   {nome:<26} raiz unitária: {raiz:<3}  rejeita em {rejeita:>3} de {a.repeticoes} "
              f"({br(100 * rejeita / a.repeticoes, 1)}%)   regressão {reg}")
    print("   só o passeio aleatório tem raiz unitária; nas outras seis, a resposta certa é rejeitar")

    print("6. Depois de tirar o calendário do log (mínimos quadrados com reta, onda do ano, dia da semana e eventos)")
    coef, sobra = calendario_do_log(log, cal)
    onda = math.hypot(coef["seno do ano"], coef["cosseno do ano"])
    print(f"   a reta sobe {br(100 * (math.exp(coef['reta']) - 1), 1)}% por ano; a onda do ano vai "
          f"{br(100 * (math.exp(onda) - 1), 1)}% acima e abaixo")
    s = sinais(sobra)
    print(f"   o que sobra: desvio {br(s['desvio'], 3)}  ac1 {br(s['ac1'])}  ac7 {br(s['ac7'])}")
    _, txt = linha_teste("o que sobra, constante", sobra, "c")
    print(f"   {'':<40} {'estat.':>7}  {'p-valor':>16}  {'dif':>3}  {'5%':>6}")
    print(txt)
    print("   os valores críticos do teste foram feitos para uma série crua; numa sobra de regressão, use a estatística")
    print("   só como ordem de grandeza")


if __name__ == "__main__":
    main()
