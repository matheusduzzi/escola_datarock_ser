"""As contas das três famílias feitas à mão, para ver a forma da previsão que cada uma consegue fazer.

Aula «ARIMA, SARIMAX e suavização» do curso Séries temporais.

Rode de dentro da pasta da aula:  python3 a_mao.py

Usa as 8 semanas de 07/07/2025 a 31/08/2025 (nenhum dia com falha, feriado ou promoção) e prevê a
semana de 01/09 a 07/09/2025. Os parâmetros são escolhidos por mim e ficam fixos: aqui ninguém ajusta
nada. O que interessa é a FORMA da previsão. Ajustar de verdade, com o statsmodels, é na aula 11.
A coluna "só calendário" é a regressão do hipoteses.py: essa sim é ajustada, por mínimos quadrados.
"""
from pathlib import Path

import numpy as np
import pandas as pd

import hipoteses as hp

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
INICIO, ORIGEM = pd.Timestamp("2025-07-07"), pd.Timestamp("2025-08-31")
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
H = 7


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def carregar():
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"]).set_index("data")["unidades"]
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, ORIGEM + pd.Timedelta(days=H))
    return venda.reindex(dias).astype(float), cal.reindex(dias)


def suavizacao_simples(y, alfa):
    """Nível novo = alfa × venda de hoje + (1 − alfa) × nível de ontem. A previsão é o último nível."""
    nivel = y[0]
    for v in y[1:]:
        nivel = alfa * v + (1 - alfa) * nivel
    return [nivel] * H, nivel


def holt_winters(y, alfa, beta, gama, m=7):
    """Holt-Winters aditivo: nível, inclinação e um ajuste para cada dia da semana."""
    nivel = float(np.mean(y[:m]))
    inclinacao = 0.0
    sazonal = [v - nivel for v in y[:m]]          # quanto cada dia da 1ª semana fica acima ou abaixo
    for t in range(m, len(y)):
        s = sazonal[t - m]
        anterior = nivel
        nivel = alfa * (y[t] - s) + (1 - alfa) * (nivel + inclinacao)
        inclinacao = beta * (nivel - anterior) + (1 - beta) * inclinacao
        sazonal.append(gama * (y[t] - anterior - inclinacao) + (1 - gama) * s)
    n = len(y)
    prev = [nivel + h * inclinacao + sazonal[n - m + (h - 1) % m] for h in range(1, H + 1)]
    return prev, nivel, inclinacao, sazonal[-m:]


def arima_111(y, phi, theta):
    """ARIMA(1,1,1) sem constante: a mudança de hoje = phi × mudança de ontem + erro + theta × erro de ontem."""
    dy = np.diff(y)
    erro = [0.0]
    for t in range(1, len(dy)):
        erro.append(dy[t] - phi * dy[t - 1] - theta * erro[t - 1])
    prev, ultimo, mudanca, e = [], y[-1], dy[-1], erro[-1]
    for h in range(H):
        mudanca = phi * mudanca + (theta * e if h == 0 else 0.0)  # o erro futuro vale zero
        ultimo += mudanca
        prev.append(ultimo)
    return prev


def so_calendario(dias):
    """A regressão do calendário do hipoteses.py, ajustada de 01/01/2024 a 31/08/2025, aplicada aos dias.

    É a parte X de um SARIMAX sozinha: tendência, onda do ano, dia da semana e eventos, sem memória.
    """
    hist = hp.carregar(ORIGEM)
    x = hist[hist["serve"]]
    efeito, _ = hp.regressao(np.log(x["unidades"].to_numpy()), x.index, hist.index[0], hp.extras_diarios(x))
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    f = pd.DataFrame({"promocao": cal.loc[dias, "promocao"],
                      "feriado_aberto": (cal.loc[dias, "feriado"] != "") & (cal.loc[dias, "loja_fechada"] == 0)},
                     index=dias)
    nomes, X = hp.matriz(dias, hist.index[0], hp.extras_diarios(f))
    with np.errstate(all="ignore"):
        return list(np.exp(X @ np.array([efeito[n] for n in nomes])))


def main():
    venda, cal = carregar()
    y = venda[:ORIGEM].to_numpy()
    futuro = venda[ORIGEM + pd.Timedelta(days=1):]
    print(f"Histórico: {INICIO:%d/%m/%Y} a {ORIGEM:%d/%m/%Y}, {len(y)} dias, {int(np.isnan(y).sum())} vazios")

    print("\n1. A diferença de 7 dias: a última semana do histórico contra a anterior")
    print("  dia            venda   venda 7 dias antes   diferença")
    for d in pd.date_range(ORIGEM - pd.Timedelta(days=6), ORIGEM):
        a, b = venda[d], venda[d - pd.Timedelta(days=7)]
        print(f"  {DIAS[d.dayofweek]} {d:%d/%m}    {a:>8.0f}   {b:>18.0f}   {a - b:>+9.0f}".replace("-", "−"))
    sem = venda[ORIGEM - pd.Timedelta(days=6):ORIGEM]
    dif = (venda - venda.shift(7))[ORIGEM - pd.Timedelta(days=6):ORIGEM]
    print(f"  maior − menor na semana: venda {sem.max() - sem.min():.0f}, diferença {dif.max() - dif.min():.0f}")

    ses, nivel_ses = suavizacao_simples(y, 0.3)
    hw, nivel, inclinacao, sazonal = holt_winters(y, 0.2, 0.05, 0.2)
    ar = arima_111(y, 0.3, -0.8)
    cx = so_calendario(futuro.index)
    print("\n2. O que sobra no fim do histórico")
    print(f"  suavização simples (alfa 0,3): nível {br(nivel_ses)}")
    print(f"  Holt-Winters (alfa 0,2, beta 0,05, gama 0,2): nível {br(nivel)}, inclinação {br(inclinacao, 2)} por dia")
    print("    ajuste de cada dia da semana: " + ", ".join(
        f"{DIAS[(ORIGEM - pd.Timedelta(days=6 - i)).dayofweek]} {br(s)}" for i, s in enumerate(sazonal)))

    print("\n3. A previsão da semana seguinte, feita na noite de 31/08/2025")
    print("  dia          calendário        simples   Holt-Winters   ARIMA(1,1,1)   só calendário   venda real")
    for h, d in enumerate(futuro.index):
        marca = cal.loc[d, "feriado"] or cal.loc[d, "promocao"] or ""
        print(f"  {DIAS[d.dayofweek]} {d:%d/%m}    {marca[:14]:<14} {br(ses[h]):>10} {br(hw[h]):>14} "
              f"{br(ar[h]):>14} {br(cx[h]):>15} {futuro[d]:>12.0f}")
    print(f"  maior − menor na semana: simples {br(max(ses) - min(ses))}, Holt-Winters {br(max(hw) - min(hw))}, "
          f"ARIMA(1,1,1) {br(max(ar) - min(ar))}, só calendário {br(max(cx) - min(cx))}, "
          f"venda real {futuro.max() - futuro.min():.0f}")


if __name__ == "__main__":
    main()
