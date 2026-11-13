"""Os modelos da aula «Modelo contra baseline» do curso Séries temporais.

Este arquivo não imprime nada: o comparar.py importa daqui. Deixe os dois na mesma pasta.

Tudo o que um modelo usa para prever o dia D, feito na noite da origem O = D − horizonte,
sai da venda até O. O calendário entra inteiro, porque a loja já sabe dele antes do dia.
"""
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
ANO = 365.25
INICIO = pd.Timestamp("2024-01-01")
EVENTOS = ["Black Friday", "fim de semana da Black Friday", "Natal", "feriado com a loja aberta"]


# ---------- os dados ----------

def carregar():
    """Um dia por linha, de 01/01/2024 a 31/12/2025, com o calendário de cada dia.

    `real` é a venda do dia (vazio se não há registro). `usavel` é a venda que pode alimentar
    um modelo: dia com registro, completo e com a loja aberta (aula 03).
    """
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, "2025-12-31")
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


# ---------- as duas previsões que a Bia já conhece (aulas 06 e 08) ----------

def mesmo_dia_4_semanas(d, dia, horizonte):
    """Média do mesmo dia da semana nas 4 semanas que terminam na origem."""
    k0 = -(-horizonte // 7)                      # a primeira semana que já existe na origem
    vals = [d["usavel"].get(dia - pd.Timedelta(days=7 * k)) for k in range(k0, k0 + 4)]
    vals = [x for x in vals if x is not None and not np.isnan(x)]
    return float(np.mean(vals)) if vals else np.nan


def semana_passada(d, dia, horizonte):
    """O mesmo dia da semana, na semana mais recente que já existe na origem."""
    k = -(-horizonte // 7)
    for _ in range(8):
        x = d["usavel"].get(dia - pd.Timedelta(days=7 * k))
        if x is not None and not np.isnan(x):
            return float(x)
        k += 1
    return np.nan


# ---------- Holt-Winters no log, com tendência amortecida e período 7 ----------

GRADE = [(a, b, g, f) for a in (0.05, 0.1, 0.2, 0.3, 0.5) for b in (0.0, 0.005, 0.02)
         for g in (0.05, 0.1, 0.2, 0.3) for f in (0.9, 0.98)]


def holt_winters_passada(d):
    """Uma passada pela venda inteira, com todas as combinações de parâmetros da GRADE juntas.

    Em cada dia t, o erro de um passo (o log da venda menos a previsão feita em t − 1) só usa a
    venda até t. Somando esses erros até a origem, eu escolho os parâmetros só com o treino:
    é o mesmo que reajustar o modelo em cada origem, sem rodar tudo de novo.
    Dia que não serve (sem registro, incompleto, fechado) não corrige nada: o modelo só anda.
    """
    y = np.log(d["usavel"].to_numpy())
    dow = d.index.dayofweek.to_numpy()
    p = np.array(GRADE)
    alfa, beta, gama, fi = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    n, m = len(y), len(p)
    ini = y[:28][~np.isnan(y[:28])]
    nivel = np.full(m, ini.mean())
    incl = np.zeros(m)
    sazon = np.zeros((m, 7))
    for k in range(7):
        sazon[:, k] = np.nanmean(y[:28][dow[:28] == k]) - ini.mean()
    estados = np.zeros((n, m, 9))                # nível, inclinação e os 7 ajustes, no fim de cada dia
    erro2 = np.zeros((n, m))
    for t in range(n):
        prev = nivel + fi * incl + sazon[:, dow[t]]
        if t >= 28 and not np.isnan(y[t]):
            e = y[t] - prev
            erro2[t] = e * e
            novo = nivel + fi * incl + alfa * e
            incl = fi * incl + beta * e
            sazon[:, dow[t]] += gama * e
            nivel = novo
        else:
            nivel = nivel + fi * incl
            incl = fi * incl
        estados[t, :, 0], estados[t, :, 1], estados[t, :, 2:] = nivel, incl, sazon
    return {"estados": estados, "sse": np.cumsum(erro2, axis=0), "fi": fi}


def holt_winters_prever(hw, d, origem, dia):
    """Previsão para `dia`, com o estado da noite da `origem`.

    Os parâmetros são os de menor soma de erros de 1 dia até a origem: só o treino escolhe.
    """
    io = d.index.get_loc(origem)
    j = int(np.argmin(hw["sse"][io]))
    nivel, incl, sazon = hw["estados"][io, j, 0], hw["estados"][io, j, 1], hw["estados"][io, j, 2:]
    h = (dia - origem).days
    fi = hw["fi"][j]
    soma_fi = sum(fi ** i for i in range(1, h + 1))
    return float(np.exp(nivel + soma_fi * incl + sazon[dia.dayofweek])), GRADE[j]


def holt_winters_erro_ajuste(hw, d, ate):
    """O erro do ajuste: a previsão de 1 dia dentro do próprio treino, com os parâmetros escolhidos nele.

    É o número que sai junto com o ajuste. Ele não é o erro de uma previsão feita 7 dias antes.
    """
    ia = d.index.get_loc(ate)
    j = int(np.argmin(hw["sse"][ia]))
    fi = hw["fi"][j]
    y, dow = d["usavel"].to_numpy(), d.index.dayofweek
    real, prev = [], []
    for t in range(29, ia + 1):
        if not np.isnan(y[t]):
            nivel, incl, sazon = hw["estados"][t - 1, j, 0], hw["estados"][t - 1, j, 1], hw["estados"][t - 1, j, 2:]
            real.append(y[t])
            prev.append(np.exp(nivel + fi * incl + sazon[dow[t]]))
    return np.array(real), np.array(prev)


# ---------- regressão do calendário com erro AR(1), no log ----------

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


def regressao_ajustar(d, ate):
    """Ajusta com os dias que servem até `ate`. Coluna sem nenhum dia no treino fica de fora.

    Primeiro a regressão por mínimos quadrados. Depois o AR(1) do resíduo: quanto o resíduo de
    um dia passa para o seguinte. O SARIMAX do statsmodels estima as duas partes juntas; aqui
    elas vão em duas etapas, para você ver cada uma.
    """
    treino = d.loc[:ate]
    treino = treino[treino["usavel"].notna()]
    X = colunas(d, treino.index)
    X = X.loc[:, X.abs().sum() > 0]
    y = np.log(treino["usavel"].to_numpy())
    with np.errstate(all="ignore"):              # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(X.to_numpy(), y, rcond=None)
        res = y - X.to_numpy() @ coef
    s = pd.Series(res, index=treino.index).reindex(pd.date_range(treino.index[0], ate))
    par = pd.concat([s, s.shift(1)], axis=1).dropna()
    fi = float(np.sum(par.iloc[:, 0] * par.iloc[:, 1]) / np.sum(par.iloc[:, 1] ** 2))
    return {"nomes": list(X.columns), "coef": coef, "fi": fi, "residuo": s.dropna()}


def regressao_prever(ajuste, d, origem, dia):
    """exp(calendário do dia + fi^h vezes o último resíduo conhecido na origem)."""
    x = colunas(d, pd.DatetimeIndex([dia]))[ajuste["nomes"]].to_numpy()[0]
    res = ajuste["residuo"].loc[:origem]
    h = (dia - res.index[-1]).days
    with np.errstate(all="ignore"):
        log = float(x @ ajuste["coef"]) + ajuste["fi"] ** h * float(res.iloc[-1])
    return float(np.exp(log))


def regressao_erro_ajuste(ajuste, d, ate):
    """O erro do ajuste da regressão: o calendário de cada dia do treino, com os pesos tirados dele."""
    treino = d.loc[:ate]
    treino = treino[treino["usavel"].notna()]
    X = colunas(d, treino.index)[ajuste["nomes"]].to_numpy()
    with np.errstate(all="ignore"):
        return treino["usavel"].to_numpy(), np.exp(X @ ajuste["coef"])


def efeito(ajuste, nome):
    """Quanto a coluna multiplica a venda: exp(peso) − 1. Vazio se ela ficou fora do ajuste."""
    if nome not in ajuste["nomes"]:
        return np.nan
    return float(np.exp(ajuste["coef"][ajuste["nomes"].index(nome)]) - 1)
