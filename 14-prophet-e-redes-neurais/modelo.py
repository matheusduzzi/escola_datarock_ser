"""O modelo do ajuste da semana, para a aula «Prophet e redes neurais» do curso Séries temporais.

Este arquivo não imprime nada: o criterio.py importa daqui. Deixe os dois na mesma pasta.

É o calendário + AR(1) da aula «Modelo contra baseline»: a regressão do calendário no log da
venda, com o resíduo que passa de um dia para o seguinte. Duas opções a mais servem para medir
o efeito do volume de dados:
- `ordem`: quantos pares de seno e cosseno desenham a onda do ano. O modelo do ajuste da semana usa 2.
  O Prophet usa 10 por padrão, segundo a documentação dele.
- `desde`: o primeiro dia de histórico que o ajuste usa. Vazio é o histórico inteiro.
Tudo o que entra na previsão do dia D, feita na noite da origem O = D − horizonte, sai da venda
até O. O calendário entra inteiro, porque a loja já sabe dele antes do dia.
"""
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
ANO = 365.25
INICIO = pd.Timestamp("2024-01-01")
FIM_VENDA = pd.Timestamp("2025-12-31")
EVENTOS = ["Black Friday", "fim de semana da Black Friday", "Natal", "feriado com a loja aberta"]
FALTA, SOBRA = 6.0, 2.0          # R$ por unidade, a estimativa da Bia na aula 08


def carregar():
    """Um dia por linha, de 01/01/2024 a 31/12/2025, com o calendário de cada dia.

    `real` é a venda do dia (vazio se não há registro). `usavel` é a venda que pode alimentar
    um modelo: dia com registro, completo e com a loja aberta (aula «Auditar a venda diária»).
    """
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, FIM_VENDA)
    v = venda.set_index("data").reindex(dias)
    c = cal.reindex(dias)
    d = pd.DataFrame(index=dias)
    d["real"] = v["unidades"].astype(float)
    d["incompleto"] = v["ultimo_registro"].notna() & (v["ultimo_registro"] < "21:30")
    d["fechada"] = c["loja_fechada"] == 1
    d["usavel"] = d["real"].where(~(d["real"].isna() | d["incompleto"] | d["fechada"]))
    for nome in EVENTOS[:3]:
        d[nome] = c["promocao"] == nome
    d[EVENTOS[3]] = (c["feriado"] != "") & ~d["fechada"]
    d["evento"] = d[EVENTOS].any(axis=1)
    return d


def colunas(d, datas, ordem=2):
    """Constante, tendência, onda do ano (`ordem` pares de seno e cosseno), dia da semana e eventos."""
    ang = 2 * np.pi * datas.dayofyear.to_numpy() / ANO
    x = {"constante": np.ones(len(datas)), "tendência": (datas - INICIO).days.to_numpy() / ANO}
    for k in range(1, ordem + 1):
        x[f"sen{k}"] = np.sin(k * ang)
        x[f"cos{k}"] = np.cos(k * ang)
    for k in range(1, 7):
        x[f"dia {k}"] = (datas.dayofweek == k).astype(float)
    for nome in EVENTOS:
        x[nome] = d.loc[datas, nome].to_numpy(dtype=float)
    return pd.DataFrame(x, index=datas)


def ajustar(d, ate, desde=None, ordem=2):
    """Ajusta com os dias que servem, de `desde` até `ate`, a noite da origem.

    Coluna que é zero em todo o treino sai do ajuste: um evento que ainda não aconteceu no
    histórico não tem peso para estimar. `numeros` conta o que o ajuste estimou: um peso por
    coluna e o fi do AR(1).
    """
    treino = d.loc[desde:ate]
    treino = treino[treino["usavel"].notna()]
    X = colunas(d, treino.index, ordem)
    X = X.loc[:, X.abs().sum() > 0]
    A = X.to_numpy()
    y = np.log(treino["usavel"].to_numpy())
    with np.errstate(all="ignore"):              # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ coef
    s = pd.Series(res, index=treino.index).reindex(pd.date_range(treino.index[0], ate))
    par = pd.concat([s, s.shift(1)], axis=1).dropna()
    fi = float(np.sum(par.iloc[:, 0] * par.iloc[:, 1]) / np.sum(par.iloc[:, 1] ** 2))
    choque = par.iloc[:, 0] - fi * par.iloc[:, 1]
    return {"nomes": list(X.columns), "coef": coef, "fi": fi, "ordem": ordem, "residuo": s.dropna(),
            "dias": len(treino), "numeros": A.shape[1] + 1,
            "desvio_choque": float(np.sqrt(np.mean(choque ** 2)))}


def prever(aj, d, origem, dia):
    """Previsão do modelo para `dia`, feita na noite da `origem`. Loja fechada: zero."""
    if d.at[dia, "fechada"]:
        return 0.0
    x = colunas(d, pd.DatetimeIndex([dia]), aj["ordem"])[aj["nomes"]].to_numpy()[0]
    res = aj["residuo"].loc[:origem]
    h = (dia - res.index[-1]).days
    with np.errstate(all="ignore"):
        return float(np.exp(x @ aj["coef"] + aj["fi"] ** h * float(res.iloc[-1])))


def wmape(real, prev):
    return float(np.sum(np.abs(real - prev)) / np.sum(real) * 100)


def custo(real, prev):
    """R$ do erro do ajuste da semana: faltar custa R$ 6 por unidade, sobrar custa R$ 2."""
    erro = np.asarray(real) - np.asarray(prev)
    return float(FALTA * erro.clip(min=0).sum() + SOBRA * (-erro).clip(min=0).sum())
