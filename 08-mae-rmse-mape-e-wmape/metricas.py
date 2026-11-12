"""As contas da aula «MAE, RMSE, MAPE e WMAPE» do curso Séries temporais.

Rode de dentro da pasta da aula:  python3 metricas.py
Lê a venda da loja física em dados/loja, na raiz do kit, e monta as previsões de 2025
feitas 7 dias antes de cada dia. Depois calcula as quatro métricas e os outros quadros da aula.
"""
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
HORIZONTE = 7


# ---------- as quatro métricas ----------
# erro = real - previsão. Erro positivo: a previsão ficou abaixo da venda (faltou).

def mae(real, prev):
    return np.mean(np.abs(real - prev))


def rmse(real, prev):
    return np.sqrt(np.mean((real - prev) ** 2))


def mape(real, prev):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.mean(np.abs(real - prev) / np.abs(real)) * 100


def wmape(real, prev):
    return np.sum(np.abs(real - prev)) / np.sum(np.abs(real)) * 100


METRICAS = {"MAE": mae, "RMSE": rmse, "MAPE": mape, "WMAPE": wmape}


# ---------- as previsões ----------

def carregar():
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range("2024-01-01", "2025-12-31")
    real = venda.set_index("data")["unidades"].reindex(dias)
    ultimo = venda.set_index("data")["ultimo_registro"].reindex(dias)
    incompleto = ultimo.notna() & (ultimo < "21:30")
    fechada = cal["loja_fechada"].reindex(dias) == 1
    # o que pode alimentar uma previsão: dia completo e com a loja aberta (aula 03)
    usavel = real.where(~(real.isna() | incompleto | fechada))
    return real, incompleto, fechada, usavel


def previsoes():
    real, incompleto, fechada, usavel = carregar()
    linhas = []
    for dia in pd.date_range("2025-01-01", "2025-12-31"):
        if np.isnan(real[dia]) or incompleto[dia]:
            continue  # sem registro ou incompleto: não há venda real para comparar
        semanas = [usavel[dia - pd.Timedelta(days=7 * k)] for k in (1, 2, 3, 4)]
        validas = [x for x in semanas if not np.isnan(x)]
        # semana passada: o mesmo dia 7 dias antes; se ele não serve, uma semana a mais
        semana = next(x for x in semanas if not np.isnan(x))
        media4 = usavel[dia - pd.Timedelta(days=HORIZONTE + 27): dia - pd.Timedelta(days=HORIZONTE)].mean()
        linhas.append({"data": dia, "real": real[dia], "fechada": bool(fechada[dia]),
                       "semana passada": semana, "média de 4 semanas": media4,
                       "mesmo dia, 4 semanas": np.mean(validas)})
    return pd.DataFrame(linhas)


NOMES = ["semana passada", "média de 4 semanas", "mesmo dia, 4 semanas"]


# ---------- saída ----------

def br(x, casas=2):
    if np.isinf(x):
        return "inf"
    if np.isnan(x):
        return "nan"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x):
    return br(x, 1) + ("%" if np.isfinite(x) else "")


def quadro(p, prevs, titulo):
    print(titulo)
    print(f"  {'':24}{'MAE':>8}{'RMSE':>8}{'MAPE':>9}{'WMAPE':>9}")
    for nome in NOMES:
        r, f = p["real"].to_numpy(float), prevs[nome].to_numpy(float)
        print(f"  {nome:24}{br(mae(r, f)):>8}{br(rmse(r, f)):>8}{pct(mape(r, f)):>9}{pct(wmape(r, f)):>9}")
    print()


def main():
    p = previsoes()
    fech = p[p["fechada"]]
    print(f"Previsões de 2025, feitas {HORIZONTE} dias antes de cada dia")
    print(f"  dias avaliados: {len(p)} (ficam fora 9 dias: 5 sem registro e 4 incompletos)")
    print(f"  loja fechada, venda zero: {len(fech)} dias ({', '.join(d.strftime('%d/%m') for d in fech['data'])})")
    print(f"  venda média por dia avaliado: {br(p['real'].mean())} unidades\n")

    quadro(p, p, "1. Todos os dias, com a previsão como saiu")

    com_cal = p.copy()
    for nome in NOMES:
        com_cal.loc[com_cal["fechada"], nome] = 0.0
    quadro(p, com_cal, "2. Dia de loja fechada previsto como zero (o calendário já sabe)")

    tem_venda = (p["real"] > 0).to_numpy()
    aberto = p[tem_venda]
    quadro(aberto, com_cal[tem_venda], f"3. Só os {len(aberto)} dias com venda (sem os {len(fech)} dias de venda zero)")

    print("4. Os maiores erros da semana passada (erro = real - previsão)")
    e = p["real"] - p["semana passada"]
    for i in e.abs().sort_values(ascending=False).index[:3]:
        print(f"  {p.loc[i, 'data']:%d/%m/%Y}  real {p.loc[i, 'real']:>4.0f}  previsão {p.loc[i, 'semana passada']:>4.0f}"
              f"  erro {e[i]:>5.0f}")
    r = aberto["real"].to_numpy(float)
    f = aberto["semana passada"].to_numpy(float)
    ea = r - f
    top2 = np.argsort(-np.abs(ea))[:2]
    resto = np.delete(np.arange(len(ea)), top2)
    datas = " e ".join(aberto["data"].iloc[i].strftime("%d/%m") for i in sorted(top2))
    print(f"  nos {len(aberto)} dias com venda, os dois maiores erros ({datas}) são "
          f"{br(100 * np.sum(ea[top2] ** 2) / np.sum(ea ** 2), 1)}% da soma dos erros ao quadrado")
    print(f"  sem esses dois dias: MAE {br(mae(r, f))} vai a {br(mae(r[resto], f[resto]))}; "
          f"RMSE {br(rmse(r, f))} vai a {br(rmse(r[resto], f[resto]))}\n")

    print(f"5. O número fixo (o mesmo todo dia) que cada métrica prefere, nos {len(aberto)} dias com venda")
    grade = np.arange(50, 301)
    for nome, fn in METRICAS.items():
        valores = [fn(r, np.full_like(r, c)) for c in grade]
        print(f"  {nome:6} prefere {grade[int(np.argmin(valores))]} unidades por dia")
    print(f"  para comparar: mediana {br(np.median(r), 0)}, média {br(r.mean())}\n")

    print("6. Quanto custa o erro, se faltar custa R$ 6 por unidade e sobrar custa R$ 2")
    print(f"  previsão 'mesmo dia, 4 semanas' com o calendário, {len(p)} dias, multiplicada por um fator")
    print(f"  {'fator':>7}{'MAE':>8}{'faltou':>9}{'sobrou':>9}{'custo (R$)':>13}")
    r = p["real"].to_numpy(float)
    base = com_cal["mesmo dia, 4 semanas"].to_numpy(float)
    for fator in (0.95, 1.00, 1.05, 1.10, 1.15, 1.20):
        f = base * fator
        falta = np.clip(r - f, 0, None).sum()
        sobra = np.clip(f - r, 0, None).sum()
        print(f"  {br(fator):>7}{br(mae(r, f)):>8}{br(falta, 0):>9}{br(sobra, 0):>9}{br(6 * falta + 2 * sobra, 0):>13}")
    print(f"  em quantos dias a previsão ficou acima da venda, fator 1,00: "
          f"{int((base > r).sum())} de {len(r)}; fator 1,10: {int((base * 1.10 > r).sum())} de {len(r)}")


if __name__ == "__main__":
    main()
