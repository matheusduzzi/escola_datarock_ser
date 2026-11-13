"""O modelo das entregas da aula «Exógenas conhecidas e previstas» do curso Séries temporais.

Este arquivo não imprime nada: comparar.py, cenarios.py e minha_chuva.py importam daqui. Deixe os
quatro na mesma pasta.

O modelo é a regressão do calendário da aula 10, no log das entregas, com uma coluna a mais: a chuva
forte (5 mm ou mais). O ajuste usa a chuva que caiu em cada dia do treino. Para prever, a chuva do dia
previsto entra como uma chance, de 0 a 1, e cada versão do modelo diz de onde essa chance vem.
"""
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
LOJA = AQUI.parent / "dados" / "loja"
ANO = 365.25
INICIO = pd.Timestamp("2024-01-01")
FIM = pd.Timestamp("2025-12-31")
CHUVA_FORTE_MM = 5.0
EVENTOS = ["Black Friday", "fim de semana da Black Friday", "Natal", "feriado com a loja aberta"]


# ---------- os dados ----------

def carregar(ate=FIM):
    """Um dia por linha, de 01/01/2024 até `ate`, com o calendário, as entregas e a chuva.

    `entregas` e `chuva` ficam vazias depois de 31/12/2025: esses dias ainda não aconteceram.
    `chuva` é 1 no dia de chuva forte, 0 no resto. O calendário vai até 31/01/2026.
    """
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    ent = pd.read_csv(DADOS / "entregas.csv", parse_dates=["data"]).set_index("data")
    mm = pd.read_csv(DADOS / "chuva.csv", parse_dates=["data"]).set_index("data")
    dias = pd.date_range(INICIO, ate)
    c = cal.reindex(dias)
    d = pd.DataFrame(index=dias)
    d["entregas"] = ent["entregas"].reindex(dias).astype(float)
    d["chuva_mm"] = mm["chuva_mm"].reindex(dias)
    d["chuva"] = (d["chuva_mm"] >= CHUVA_FORTE_MM).astype(float).where(d["chuva_mm"].notna())
    d["fechada"] = c["loja_fechada"] == 1
    for nome in EVENTOS[:3]:
        d[nome] = c["promocao"] == nome
    d[EVENTOS[3]] = (c["feriado"] != "") & ~d["fechada"]
    return d


def carregar_previsao():
    """A previsão do tempo: uma linha por (dia em que foi publicada, dia previsto), chance de 0 a 1."""
    p = pd.read_csv(DADOS / "previsao_chuva.csv", parse_dates=["publicada_em", "para_o_dia"])
    p["chance"] = p["chance_chuva_forte"] / 100
    return p.set_index(["publicada_em", "para_o_dia"])["chance"].sort_index()


def previsao_da_noite(prev, origem, dia):
    """A chance de chuva forte em `dia` na previsão publicada no dia da `origem`. Vazio se ela não chega lá."""
    return float(prev.get((origem, dia), np.nan))


# ---------- a regressão do calendário, com ou sem a chuva ----------

def colunas(d, datas):
    """Constante, tendência, onda do ano (seno e cosseno), dia da semana e eventos do calendário."""
    ang = 2 * np.pi * datas.dayofyear.to_numpy() / ANO
    x = {"constante": np.ones(len(datas)), "tendência": (datas - INICIO).days.to_numpy() / ANO,
         "sen1": np.sin(ang), "cos1": np.cos(ang), "sen2": np.sin(2 * ang), "cos2": np.cos(2 * ang)}
    for k in range(1, 7):
        x[f"dia {k}"] = (datas.dayofweek == k).astype(float)
    for nome in EVENTOS:
        x[nome] = d.loc[datas, nome].to_numpy(dtype=float)
    return pd.DataFrame(x, index=datas)


def ajustar(d, ate, com_chuva):
    """Mínimos quadrados no log das entregas, com os dias de loja aberta até `ate`.

    Com `com_chuva`, a coluna da chuva forte entra no ajuste com a chuva que caiu em cada dia do treino:
    esses dias já passaram. Coluna sem nenhum dia no treino fica de fora.
    """
    treino = d.loc[:ate]
    treino = treino[treino["entregas"].notna() & ~treino["fechada"]]
    X = colunas(d, treino.index)
    if com_chuva:
        X["chuva"] = treino["chuva"].to_numpy()
    X = X.loc[:, X.abs().sum() > 0]
    y = np.log(treino["entregas"].to_numpy())
    with np.errstate(all="ignore"):              # o NumPy do macOS avisa à toa no produto de matrizes
        coef, *_ = np.linalg.lstsq(X.to_numpy(), y, rcond=None)
    return {"nomes": list(X.columns), "coef": coef}


def efeito_chuva(ajuste):
    """Quanto a chuva forte multiplica as entregas, menos 1: +0,40 quer dizer 40% a mais."""
    return float(np.exp(ajuste["coef"][ajuste["nomes"].index("chuva")]) - 1)


def prever(ajuste, d, dia, chance=None):
    """Entregas previstas para `dia`. Zero se a loja fecha: o calendário já sabe.

    Sem a coluna da chuva, é o calendário. Com ela, `chance` diz quanto vale a chuva do dia previsto:
    1 é o cenário com chuva forte, 0 é o cenário seco, e uma chance entre os dois dá a média dos
    dois cenários pesada por ela.
    """
    if d.at[dia, "fechada"]:
        return 0.0
    nomes = [n for n in ajuste["nomes"] if n != "chuva"]
    x = colunas(d, pd.DatetimeIndex([dia]))[nomes].to_numpy()[0]
    b = dict(zip(ajuste["nomes"], ajuste["coef"]))
    with np.errstate(all="ignore"):
        seco = float(np.exp(x @ np.array([b[n] for n in nomes])))
    if "chuva" not in b:
        return seco
    return seco * (1 + chance * (np.exp(b["chuva"]) - 1))


# ---------- as contas do erro ----------

def wmape(real, prev):
    return float(np.abs(real - prev).sum() / real.sum() * 100)


def vies(real, prev):
    return float((prev - real).sum() / real.sum() * 100)


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def sinal(x, casas=1):
    """Com o sinal na frente: +0,4, −2,6. O que arredonda para zero sai 0,0."""
    v = round(x, casas)
    if v == 0:
        return br(0.0, casas)
    return ("+" if v > 0 else "") + br(v, casas)
