"""O modelo e a faixa do dia, da aula «Intervalos e cenários», usados na aula «Demanda e equipe».

Este arquivo não imprime nada: o equipe.py importa daqui. Deixe os dois na mesma pasta.

O modelo é o calendário + AR(1) da aula «Modelo contra baseline»: a regressão do calendário no
log da venda, com o resíduo que passa de um dia para o seguinte. A régua é a média do mesmo dia
da semana nas 4 semanas anteriores. Tudo o que entra na previsão do dia D, feita na noite da
origem O = D − horizonte, sai da venda até O. O calendário entra inteiro, porque a loja já sabe
dele antes do dia.
"""
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
ANO = 365.25
INICIO = pd.Timestamp("2024-01-01")
FIM_VENDA = pd.Timestamp("2025-12-31")
FIM_CALENDARIO = pd.Timestamp("2026-01-31")
EVENTOS = ["Black Friday", "fim de semana da Black Friday", "Natal", "feriado com a loja aberta"]


# ---------- os dados ----------

def carregar():
    """Um dia por linha, de 01/01/2024 a 31/01/2026, com o calendário de cada dia.

    `real` é a venda do dia (vazio se não há registro, e vazio em 2026, que ainda não aconteceu).
    `usavel` é a venda que pode alimentar um modelo: dia com registro, completo e com a loja
    aberta (aula «Auditar a venda diária»).
    """
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, FIM_CALENDARIO)
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


# ---------- a régua: mesmo dia da semana, 4 semanas ----------

def regua(d, dia, horizonte):
    """Média do mesmo dia da semana nas 4 semanas mais recentes que já existem na origem."""
    k0 = -(-horizonte // 7)
    vals = [d["usavel"].get(dia - pd.Timedelta(days=7 * k)) for k in range(k0, k0 + 4)]
    vals = [x for x in vals if x is not None and not np.isnan(x)]
    return float(np.mean(vals)) if vals else np.nan


# ---------- o modelo: calendário + AR(1), no log ----------

def colunas(d, datas):
    """Constante, tendência, onda do ano (seno e cosseno), dia da semana e eventos."""
    ang = 2 * np.pi * datas.dayofyear.to_numpy() / ANO
    x = {"constante": np.ones(len(datas)), "tendência": (datas - INICIO).days.to_numpy() / ANO,
         "sen1": np.sin(ang), "cos1": np.cos(ang), "sen2": np.sin(2 * ang), "cos2": np.cos(2 * ang)}
    for k in range(1, 7):
        x[f"dia {k}"] = (datas.dayofweek == k).astype(float)
    for nome in EVENTOS:
        x[nome] = d.loc[datas, nome].to_numpy(dtype=float)
    return pd.DataFrame(x, index=datas)


def ajustar(d, ate):
    """Ajusta com os dias que servem até `ate`, a noite da origem.

    Guarda o que as duas faixas precisam:
    - `s2`: a variância do resíduo da regressão, e `xtx_inv`, que diz quanto os pesos do
      calendário podem estar errados (é daí que sai a incerteza da média prevista);
    - `fi` e `s2_choque`: quanto do resíduo passa para o dia seguinte e o tamanho da parte nova
      de cada dia, o choque que ninguém prevê.
    """
    treino = d.loc[:ate]
    treino = treino[treino["usavel"].notna()]
    X = colunas(d, treino.index)
    X = X.loc[:, X.abs().sum() > 0]
    A = X.to_numpy()
    y = np.log(treino["usavel"].to_numpy())
    with np.errstate(all="ignore"):              # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ coef
        xtx_inv = np.linalg.pinv(A.T @ A)
    n, k = A.shape
    s = pd.Series(res, index=treino.index).reindex(pd.date_range(treino.index[0], ate))
    par = pd.concat([s, s.shift(1)], axis=1).dropna()
    fi = float(np.sum(par.iloc[:, 0] * par.iloc[:, 1]) / np.sum(par.iloc[:, 1] ** 2))
    choque = par.iloc[:, 0] - fi * par.iloc[:, 1]
    return {"nomes": list(X.columns), "coef": coef, "fi": fi, "residuo": s.dropna(),
            "s2": float(np.sum(res ** 2) / (n - k)), "s2_choque": float(np.mean(choque ** 2)),
            "xtx_inv": xtx_inv}


def z_de(nivel):
    """Quantos desvios a faixa central de `nivel` (0,8 para 80%) tem para cada lado na normal."""
    return NormalDist().inv_cdf(0.5 + nivel / 2)


def prever(aj, d, origem, dia, nivel=0.8, mudar=None):
    """Previsão do modelo para `dia`, feita na `origem`, com as duas faixas de `nivel`.

    Retorna (previsão, faixa da média, faixa do dia), cada faixa como (piso, teto).
    - faixa da média: o intervalo de confiança da venda média esperada para um dia com esse
      calendário. Só leva em conta a dúvida sobre os pesos do calendário.
    - faixa do dia: o intervalo de previsão da venda daquele dia. Soma a dúvida dos pesos com o
      choque do próprio dia, que nenhum histórico elimina.
    `mudar` troca colunas do calendário daquele dia, para montar um cenário: {"Natal": 1}.
    """
    x = colunas(d, pd.DatetimeIndex([dia]))[aj["nomes"]]
    for nome, valor in (mudar or {}).items():
        if nome in x.columns:
            x[nome] = float(valor)
    x = x.to_numpy()[0]
    res = aj["residuo"].loc[:origem]
    h = (dia - res.index[-1]).days
    with np.errstate(all="ignore"):
        log = float(x @ aj["coef"]) + aj["fi"] ** h * float(res.iloc[-1])
        var_media = aj["s2"] * float(x @ aj["xtx_inv"] @ x)
    var_choques = aj["s2_choque"] * sum(aj["fi"] ** (2 * i) for i in range(h))
    z = z_de(nivel)
    se_media, se_dia = np.sqrt(var_media), np.sqrt(var_media + var_choques)
    faixa_media = (float(np.exp(log - z * se_media)), float(np.exp(log + z * se_media)))
    faixa_dia = (float(np.exp(log - z * se_dia)), float(np.exp(log + z * se_dia)))
    return float(np.exp(log)), faixa_media, faixa_dia


def distribuicao(aj, d, origem, dia, mudar=None):
    """A venda do dia como o modelo a vê: o centro e o desvio, no log.

    É a mesma conta da faixa do dia do `prever`, sem escolher um nível: com (mu, desvio), o
    quantil q da venda é exp(mu + z × desvio), em que z é o quantil q da normal. O `prever`
    com nível 80% dá o piso e o teto dos quantis 10% e 90% dessa distribuição.
    """
    x = colunas(d, pd.DatetimeIndex([dia]))[aj["nomes"]]
    for nome, valor in (mudar or {}).items():
        if nome in x.columns:
            x[nome] = float(valor)
    x = x.to_numpy()[0]
    res = aj["residuo"].loc[:origem]
    h = (dia - res.index[-1]).days
    with np.errstate(all="ignore"):
        mu = float(x @ aj["coef"]) + aj["fi"] ** h * float(res.iloc[-1])
        var_media = aj["s2"] * float(x @ aj["xtx_inv"] @ x)
    var_choques = aj["s2_choque"] * sum(aj["fi"] ** (2 * i) for i in range(h))
    return mu, float(np.sqrt(var_media + var_choques))


def efeito(aj, nome):
    """Quanto a coluna multiplica a venda: exp(peso) − 1. Vazio se ela ficou fora do ajuste."""
    if nome not in aj["nomes"]:
        return np.nan
    return float(np.exp(aj["coef"][aj["nomes"].index(nome)]) - 1)


# ---------- a faixa pelos erros do passado ----------

def faixa_pelos_erros(razoes, nivel=0.8):
    """Os quantis da razão real / previsão em previsões passadas, feitas com o mesmo horizonte.

    Com nivel 0,8, o piso multiplica a previsão pelo quantil 10% e o teto pelo quantil 90%.
    Não supõe distribuição normal: usa o tamanho dos erros que já aconteceram.
    """
    r = np.asarray(razoes, dtype=float)
    r = r[~np.isnan(r)]
    return float(np.quantile(r, 0.5 - nivel / 2)), float(np.quantile(r, 0.5 + nivel / 2))
