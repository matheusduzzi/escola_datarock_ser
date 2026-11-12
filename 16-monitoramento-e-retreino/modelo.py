"""O modelo, a régua e as faixas da aula «Monitoramento e retreino» do curso Séries temporais.

Este arquivo não imprime nada: o monitor.py importa daqui. Deixe os dois na mesma pasta.

O modelo é o calendário + AR(1) da aula «Modelo contra baseline», com as faixas da aula
«Intervalos e cenários»: a regressão do calendário no log da venda, com o resíduo que passa de
um dia para o seguinte. A régua é a média do mesmo dia da semana nas 4 semanas anteriores.

O que muda nessa aula é o tempo. A venda de 2026 chega em duas leituras: o número da noite e o
número fechado, que só existe de 1 a 3 dias depois. Cada conta recebe a data em que ela é feita e
só usa a venda que já tinha fechado naquela data.
"""
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

AULA = Path(__file__).resolve().parent
LOJA = AULA.parent / "dados" / "loja"
DADOS = AULA / "dados"
ANO = 365.25
INICIO = pd.Timestamp("2024-01-01")
FIM_CALENDARIO = pd.Timestamp("2026-05-31")
EVENTOS = ["Black Friday", "fim de semana da Black Friday", "Natal", "feriado com a loja aberta"]
OBRA = ["obra, segunda a sexta", "obra, sábado e domingo"]


# ---------- os dados ----------

def carregar():
    """Um dia por linha, de 01/01/2024 a 31/05/2026.

    - `real`: a venda fechada (vazio se não há registro ou se ainda não fechou);
    - `noite`: o número lido às 22h do dia (em 2024 e 2025, igual ao fechado);
    - `fechada_em`: o dia em que a venda fechou (em 2024 e 2025, o próprio dia);
    - `usavel`: a venda fechada que pode alimentar um modelo: dia com registro, completo e com a
      loja aberta (aula «Auditar a venda diária»).
    """
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    nova = pd.read_csv(DADOS / "venda_2026.csv", parse_dates=["data", "fechada_em"])
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False)
    cal_nova = pd.read_csv(DADOS / "calendario_2026.csv", parse_dates=["data"], keep_default_na=False)
    cal = pd.concat([cal[cal["data"] < cal_nova["data"].min()], cal_nova]).set_index("data")
    dias = pd.date_range(INICIO, FIM_CALENDARIO)
    v = venda.set_index("data").reindex(dias)
    n = nova.set_index("data").reindex(dias)
    c = cal.reindex(dias)
    d = pd.DataFrame(index=dias)
    d["real"] = v["unidades"].astype(float).fillna(n["unidades"])
    d["noite"] = v["unidades"].astype(float).fillna(n["unidades_noite"])
    tem_venda_antiga = v["unidades"].notna()
    d["fechada_em"] = pd.Series(dias, index=dias).where(tem_venda_antiga, n["fechada_em"])
    incompleto = v["ultimo_registro"].notna() & (v["ultimo_registro"] < "21:30")
    d["fechada"] = c["loja_fechada"] == 1
    d["usavel"] = d["real"].where(~(d["real"].isna() | incompleto | d["fechada"]))
    for nome in EVENTOS[:3]:
        d[nome] = c["promocao"] == nome
    d[EVENTOS[3]] = (c["feriado"] != "") & ~d["fechada"]
    d["evento"] = d[EVENTOS].any(axis=1)
    d["util"] = d.index.dayofweek < 5
    return d


def fechado_ate(d, quando):
    """A venda fechada que já existia na manhã de `quando`: fechou até a véspera."""
    ok = d["fechada_em"].notna() & (d["fechada_em"] < quando) & (d.index < quando)
    return d["usavel"].where(ok)


# ---------- a régua: mesmo dia da semana, 4 semanas ----------

def regua(fechado, dia, horizonte):
    """Média do mesmo dia da semana nas 4 semanas mais recentes que já existem na origem."""
    k0 = -(-horizonte // 7)
    vals = [fechado.get(dia - pd.Timedelta(days=7 * k)) for k in range(k0, k0 + 4)]
    vals = [x for x in vals if x is not None and not np.isnan(x)]
    return float(np.mean(vals)) if vals else np.nan


# ---------- o modelo: calendário + AR(1), no log ----------

def colunas(d, datas, obra_desde=None):
    """Constante, tendência, onda do ano, dia da semana e eventos.

    Com `obra_desde`, mais duas colunas que valem 1 a partir dessa data: uma de segunda a sexta e
    outra no sábado e no domingo. É o modelo atualizado depois da investigação.
    """
    ang = 2 * np.pi * datas.dayofyear.to_numpy() / ANO
    x = {"constante": np.ones(len(datas)), "tendência": (datas - INICIO).days.to_numpy() / ANO,
         "sen1": np.sin(ang), "cos1": np.cos(ang), "sen2": np.sin(2 * ang), "cos2": np.cos(2 * ang)}
    for k in range(1, 7):
        x[f"dia {k}"] = (datas.dayofweek == k).astype(float)
    for nome in EVENTOS:
        x[nome] = d.loc[datas, nome].to_numpy(dtype=float)
    if obra_desde is not None:
        depois = datas >= obra_desde
        x[OBRA[0]] = (depois & (datas.dayofweek < 5)).astype(float)
        x[OBRA[1]] = (depois & (datas.dayofweek >= 5)).astype(float)
    return pd.DataFrame(x, index=datas)


def ajustar(d, quando, obra_desde=None):
    """Ajusta os pesos na manhã de `quando`, só com a venda que já tinha fechado.

    Guarda o que a previsão e a faixa do dia precisam: os pesos, o fi do AR(1), a variância do
    resíduo e do choque de cada dia e a matriz `xtx_inv` (a dúvida dos pesos).
    """
    y_ok = fechado_ate(d, quando).dropna()
    X = colunas(d, y_ok.index, obra_desde)
    X = X.loc[:, X.abs().sum() > 0]
    A = X.to_numpy()
    y = np.log(y_ok.to_numpy())
    with np.errstate(all="ignore"):              # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ coef
        xtx_inv = np.linalg.pinv(A.T @ A)
    n, k = A.shape
    s = pd.Series(res, index=y_ok.index).reindex(pd.date_range(y_ok.index[0], y_ok.index[-1]))
    par = pd.concat([s, s.shift(1)], axis=1).dropna()
    fi = float(np.sum(par.iloc[:, 0] * par.iloc[:, 1]) / np.sum(par.iloc[:, 1] ** 2))
    choque = par.iloc[:, 0] - fi * par.iloc[:, 1]
    return {"nomes": list(X.columns), "coef": coef, "fi": fi, "quando": quando, "obra_desde": obra_desde,
            "s2": float(np.sum(res ** 2) / (n - k)), "s2_choque": float(np.mean(choque ** 2)),
            "xtx_inv": xtx_inv, "dias": n}


def prever(aj, d, origem, dia, nivel=0.8):
    """Previsão de `dia`, feita na noite da `origem`, com a faixa do dia de `nivel`.

    O AR(1) parte do resíduo do último dia que já tinha fechado na origem, calculado com os pesos
    de `aj`. Retorna (previsão, piso, teto).
    """
    x = colunas(d, pd.DatetimeIndex([dia]), aj["obra_desde"]).reindex(columns=aj["nomes"], fill_value=0.0)
    x = x.to_numpy()[0]
    fech = fechado_ate(d, origem + pd.Timedelta(days=1)).loc[:origem].dropna()
    ult = fech.index[-1]
    xu = colunas(d, pd.DatetimeIndex([ult]), aj["obra_desde"]).reindex(columns=aj["nomes"], fill_value=0.0)
    with np.errstate(all="ignore"):
        res_ult = float(np.log(fech.iloc[-1]) - xu.to_numpy()[0] @ aj["coef"])
        h = (dia - ult).days
        log = float(x @ aj["coef"]) + aj["fi"] ** h * res_ult
        var_media = aj["s2"] * float(x @ aj["xtx_inv"] @ x)
    var_choques = aj["s2_choque"] * sum(aj["fi"] ** (2 * i) for i in range(h))
    z = NormalDist().inv_cdf(0.5 + nivel / 2)
    se = np.sqrt(var_media + var_choques)
    return float(np.exp(log)), float(np.exp(log - z * se)), float(np.exp(log + z * se))


def efeito(aj, nome):
    """Quanto a coluna multiplica a venda: exp(peso) − 1. Vazio se ela ficou fora do ajuste."""
    if nome not in aj["nomes"]:
        return np.nan
    return float(np.exp(aj["coef"][aj["nomes"].index(nome)]) - 1)


# ---------- as medidas do painel ----------

def wmape(real, prev):
    real, prev = np.asarray(real, float), np.asarray(prev, float)
    return float(np.sum(np.abs(real - prev)) / np.sum(real)) if len(real) else np.nan


def vies(real, prev):
    """Quanto a previsão passou da venda, em proporção da venda: positivo é previsão alta."""
    real, prev = np.asarray(real, float), np.asarray(prev, float)
    return float(np.sum(prev - real) / np.sum(real)) if len(real) else np.nan
