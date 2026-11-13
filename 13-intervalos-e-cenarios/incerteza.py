"""Mede quantas vezes a faixa da previsão pegou a venda, em cada horizonte.

Aula «Intervalos e cenários» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 incerteza.py                     # faixas de 80%
    python3 incerteza.py --nivel 90          # faixas de 90% (exercício)
    python3 incerteza.py --salvar faixas.csv # grava cada previsão e as faixas, uma linha por dia e horizonte

Os dias medidos são de 28/09 a 31/12/2025, os mesmos em todos os horizontes. A origem é o dia
menos o horizonte: com 28 dias, a primeira origem é a noite de 31/08/2025. Em cada origem o
modelo se ajusta só com a venda até aquela noite.

A faixa pelos erros do passado usa as previsões dos dias de 01/03 a 31/08/2025, feitas do
mesmo jeito. Tudo o que ela usa já existia na noite de 31/08/2025.
"""
import argparse

import numpy as np
import pandas as pd

import modelo as M

HORIZONTES = [7, 14, 21, 28]
PRIMEIRO_DIA = pd.Timestamp("2025-09-28")
ULTIMO_DIA = pd.Timestamp("2025-12-31")
CALIBRA = (pd.Timestamp("2025-03-01"), pd.Timestamp("2025-08-31"))
SABADO, ORIGEM_SABADO = pd.Timestamp("2025-11-08"), pd.Timestamp("2025-11-01")
ORIGEM_CENARIO = pd.Timestamp("2025-12-31")
SEMANA = pd.date_range("2026-01-12", "2026-01-18")
OFERTA = [pd.Timestamp("2026-01-17"), pd.Timestamp("2026-01-18")]
OFERTA_COLUNA = "fim de semana da Black Friday"


def br(x, casas=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def pct(x):
    return f"{br(100 * x, 0)}%"


class Previsoes:
    """Guarda um ajuste por origem: o mesmo ajuste serve para todos os dias previstos dela."""

    def __init__(self, d, nivel):
        self.d, self.nivel, self.cache = d, nivel, {}

    def ajuste(self, origem):
        if origem not in self.cache:
            self.cache[origem] = M.ajustar(self.d, origem)
        return self.cache[origem]

    def linhas(self, inicio, fim, horizonte):
        d, out = self.d, []
        for dia in pd.date_range(inicio, fim):
            if d.at[dia, "fechada"] or np.isnan(d.at[dia, "real"]) or d.at[dia, "incompleto"]:
                continue                     # loja fechada: o calendário já sabe; sem venda completa: não dá para medir
            origem = dia - pd.Timedelta(days=horizonte)
            prev, media, faixa = M.prever(self.ajuste(origem), d, origem, dia, self.nivel)
            out.append({"dia": dia, "origem": origem, "horizonte": horizonte, "real": d.at[dia, "real"],
                        "evento": bool(d.at[dia, "evento"]), "modelo": prev,
                        "media_piso": media[0], "media_teto": media[1],
                        "dia_piso": faixa[0], "dia_teto": faixa[1],
                        "regua": M.regua(d, dia, horizonte)})
        return pd.DataFrame(out)


def dentro(real, piso, teto):
    return float(np.mean((real >= piso) & (real <= teto)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nivel", type=int, default=80, choices=[50, 80, 90, 95],
                    help="nível das faixas, em %% (padrão 80)")
    ap.add_argument("--salvar", help="grava as previsões e as faixas nesse CSV")
    a = ap.parse_args()
    nivel = a.nivel / 100
    d = M.carregar()
    P = Previsoes(d, nivel)

    teste = {h: P.linhas(PRIMEIRO_DIA, ULTIMO_DIA, h) for h in HORIZONTES}
    calib = {h: P.linhas(*CALIBRA, h) for h in HORIZONTES}
    n = len(teste[7])
    print(f"Faixas de {a.nivel}%. Dias previstos de {PRIMEIRO_DIA:%d/%m} a {ULTIMO_DIA:%d/%m/%Y}, "
          f"os mesmos em todos os horizontes")
    print(f"  {n} dias entram na conta; ficam fora os de loja fechada e os sem venda completa")
    print("  cada previsão usa só a venda até a noite da origem (o dia menos o horizonte)")

    # 1. Um sábado
    prev, media, faixa = M.prever(P.ajuste(ORIGEM_SABADO), d, ORIGEM_SABADO, SABADO, nivel)
    print(f"\n1. Um sábado: previsão feita na noite de {ORIGEM_SABADO:%d/%m} para {SABADO:%d/%m/%Y}")
    print(f"  previsão do modelo:                       {br(prev)}")
    print(f"  faixa da média (intervalo de confiança):  {br(media[0])} a {br(media[1])}")
    print(f"  faixa do dia (intervalo de previsão):     {br(faixa[0])} a {br(faixa[1])}")
    print(f"  venda que aconteceu:                      {br(d.at[SABADO, 'real'], 0)}")
    aj = P.ajuste(ORIGEM_SABADO)
    print(f"  quanto do resíduo passa de um dia para o seguinte (fi do AR(1)): {br(aj['fi'], 3)}")
    print(f"  desvio do choque de cada dia, no log: {br(np.sqrt(aj['s2_choque']), 3)}")

    # 2. As duas faixas do modelo, 7 dias
    t = teste[7]
    print(f"\n2. Quantas vezes cada faixa do modelo pegou a venda, 7 dias antes, nos {n} dias")
    print(f"  {'':34}{'dentro':>8}{'abaixo do piso':>16}{'acima do teto':>15}{'largura média':>15}")
    for nome, piso, teto in [("faixa da média (confiança)", "media_piso", "media_teto"),
                             ("faixa do dia (previsão)", "dia_piso", "dia_teto")]:
        r = t["real"]
        print(f"  {nome:34}{pct(dentro(r, t[piso], t[teto])):>8}{pct(np.mean(r < t[piso])):>16}"
              f"{pct(np.mean(r > t[teto])):>15}{br(np.mean(t[teto] - t[piso])):>15}")

    # faixas pelos erros do passado
    cal_mod = {h: M.faixa_pelos_erros(calib[h]["real"] / calib[h]["modelo"], nivel) for h in HORIZONTES}
    cal_reg = {h: M.faixa_pelos_erros(calib[h]["real"] / calib[h]["regua"], nivel) for h in HORIZONTES}
    for h in HORIZONTES:
        t = teste[h]
        t["passado_piso"], t["passado_teto"] = t["modelo"] * cal_mod[h][0], t["modelo"] * cal_mod[h][1]
        t["regua_piso"], t["regua_teto"] = t["regua"] * cal_reg[h][0], t["regua"] * cal_reg[h][1]
        t["regua7_piso"], t["regua7_teto"] = t["regua"] * cal_reg[7][0], t["regua"] * cal_reg[7][1]

    linhas = [("modelo, faixa do dia", "dia_piso", "dia_teto"),
              ("modelo, erros do passado", "passado_piso", "passado_teto"),
              ("régua, erros do mesmo horizonte", "regua_piso", "regua_teto"),
              ("régua, faixa de 7 dias em todos", "regua7_piso", "regua7_teto")]
    print(f"\n3. Cobertura por horizonte: quantas vezes a faixa de {a.nivel}% pegou a venda")
    print(f"  {'':34}" + "".join(f"{str(h) + ' dias':>9}" for h in HORIZONTES))
    for nome, piso, teto in linhas:
        print(f"  {nome:34}" + "".join(f"{pct(dentro(teste[h]['real'], teste[h][piso], teste[h][teto])):>9}"
                                         for h in HORIZONTES))
    folga = 2 * np.sqrt(nivel * (1 - nivel) / n)
    print(f"  com {n} dias, uma faixa de {a.nivel}% bem feita cai entre {pct(nivel - folga)} e "
          f"{pct(nivel + folga)} só pelo acaso (± 2 erros-padrão)")

    print("\n4. Acima do teto e largura média da faixa, em unidades, por horizonte")
    print(f"  {'':34}" + "".join(f"{str(h) + ' dias':>13}" for h in HORIZONTES))
    for nome, piso, teto in linhas:
        cel = [f"{pct(np.mean(teste[h]['real'] > teste[h][teto]))} | {br(np.mean(teste[h][teto] - teste[h][piso]), 0)}"
               for h in HORIZONTES]
        print(f"  {nome:34}" + "".join(f"{c:>13}" for c in cel))
    print(f"  em cada célula: % de dias acima do teto | largura média; a faixa bem feita deixa "
          f"{pct((1 - nivel) / 2)} acima do teto")
    erro = {h: float(np.mean(np.abs(teste[h]["real"] - teste[h]["regua"]))) for h in HORIZONTES}
    print("  erro médio da régua: " + ", ".join(f"{h} dias {br(erro[h])}" for h in HORIZONTES))
    erro = {h: float(np.mean(np.abs(teste[h]["real"] - teste[h]["modelo"]))) for h in HORIZONTES}
    print("  erro médio do modelo: " + ", ".join(f"{h} dias {br(erro[h])}" for h in HORIZONTES))

    # 5. Dias comuns e de evento
    t = teste[7]
    print("\n5. Dias comuns e dias de evento, 7 dias antes, faixa do dia do modelo")
    for nome, filtro in [("dias comuns", ~t["evento"]), ("dias de evento", t["evento"])]:
        s = t[filtro]
        print(f"  {len(s):>3} {nome:15} dentro {pct(dentro(s['real'], s['dia_piso'], s['dia_teto']))}, "
              f"acima do teto {int((s['real'] > s['dia_teto']).sum())}, abaixo do piso {int((s['real'] < s['dia_piso']).sum())}")
    fora = t[t["evento"] & ((t["real"] < t["dia_piso"]) | (t["real"] > t["dia_teto"]))]
    for _, r in fora.iterrows():
        print(f"      fora da faixa: {r['dia']:%d/%m} venda {br(r['real'], 0)}, faixa {br(r['dia_piso'], 0)} a {br(r['dia_teto'], 0)}")

    # 6. Cenários
    aj = P.ajuste(ORIGEM_CENARIO)
    print(f"\n6. Cenários da semana de {SEMANA[0]:%d/%m} a {SEMANA[-1]:%d/%m/%Y}, feitos na noite de {ORIGEM_CENARIO:%d/%m/%Y}")
    print("  cenário A: o calendário como está. Cenário B: ofertas no sábado e no domingo,")
    print("  com o efeito que o fim de semana da Black Friday teve no histórico "
          f"({'+' if M.efeito(aj, OFERTA_COLUNA) >= 0 else ''}{pct(M.efeito(aj, OFERTA_COLUNA))})")
    print(f"  {'dia':12}{'horizonte':>10}{'A: previsão':>13}{'A: faixa do dia':>18}{'B: previsão':>13}{'B: faixa do dia':>18}")
    soma = {"A": [0.0, 0.0, 0.0], "B": [0.0, 0.0, 0.0]}
    nomes_dia = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    for dia in SEMANA:
        pa, _, fa = M.prever(aj, d, ORIGEM_CENARIO, dia, nivel)
        if dia in OFERTA:
            pb, _, fb = M.prever(aj, d, ORIGEM_CENARIO, dia, nivel, mudar={OFERTA_COLUNA: 1})
            b = f"{br(pb):>13}{br(fb[0], 0) + ' a ' + br(fb[1], 0):>18}"
        else:
            pb, fb, b = pa, fa, f"{'igual a A':>13}{'':>18}"
        for k, (p, f) in {"A": (pa, fa), "B": (pb, fb)}.items():
            soma[k][0] += p
        rot = f"{nomes_dia[dia.dayofweek]} {dia:%d/%m}"
        print(f"  {rot:12}{(dia - ORIGEM_CENARIO).days:>10}{br(pa):>13}{br(fa[0], 0) + ' a ' + br(fa[1], 0):>18}{b}")
    print(f"  soma das previsões da semana: A {br(soma['A'][0], 0)}, B {br(soma['B'][0], 0)}")
    print("  a faixa de cada cenário é a dúvida dentro dele; qual cenário vai acontecer é decisão da loja,")
    print("  e a faixa não diz nada sobre isso")

    if a.salvar:
        pd.concat(teste.values()).to_csv(a.salvar, index=False, float_format="%.2f")
        print(f"\ngravado: {a.salvar}")


if __name__ == "__main__":
    main()
