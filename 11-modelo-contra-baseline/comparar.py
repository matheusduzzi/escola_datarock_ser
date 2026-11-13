"""Compara os dois modelos da aula 10 com a previsão que a Bia já usa, fora da amostra.

Aula «Modelo contra baseline» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 comparar.py                                  # ajuste da semana: cada dia previsto 7 dias antes
    python3 comparar.py --horizonte 14                   # ajuste feito 14 dias antes (exercício)
    python3 comparar.py --salvar previsoes.csv           # grava cada previsão, uma linha por dia previsto

A primeira origem é a noite de 31/08/2025, o último dia que a aula 10 usou para escolher as
famílias. Toda origem até 31/12/2025 menos o horizonte prevê o dia que fica `horizonte` dias
depois. Todos os modelos preveem os mesmos dias, feitos nas mesmas noites.
"""
import argparse

import numpy as np
import pandas as pd

import modelos as M

PRIMEIRA_ORIGEM = pd.Timestamp("2025-08-31")
ULTIMO_DIA = pd.Timestamp("2025-12-31")
FALTA, SOBRA = 6.0, 2.0          # R$ por unidade, a estimativa da Bia na aula 08
REGUA = "mesmo dia, 4 semanas"
NOMES = ["semana passada", REGUA, "Holt-Winters", "calendário + AR(1)"]


def br(x, casas=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def sinal(x, casas=1):
    return ("+" if x >= 0 else "−") + br(abs(x), casas)


def prever_tudo(d, horizonte, hw):
    """Uma linha por dia previsto: a venda real e a previsão de cada modelo, feita na origem."""
    linhas = []
    for dia in pd.date_range(PRIMEIRA_ORIGEM + pd.Timedelta(days=horizonte), ULTIMO_DIA):
        origem = dia - pd.Timedelta(days=horizonte)
        ajuste = M.regressao_ajustar(d, origem)
        hw_prev, params = M.holt_winters_prever(hw, d, origem, dia)
        linha = {"dia": dia, "origem": origem, "real": d.at[dia, "real"],
                 "avaliado": bool(not np.isnan(d.at[dia, "real"]) and not d.at[dia, "incompleto"]),
                 "fechada": bool(d.at[dia, "fechada"]), "evento": bool(d.at[dia, "evento"]),
                 "semana passada": M.semana_passada(d, dia, horizonte),
                 REGUA: M.mesmo_dia_4_semanas(d, dia, horizonte),
                 "Holt-Winters": hw_prev,
                 "calendário + AR(1)": M.regressao_prever(ajuste, d, origem, dia),
                 "hw_params": params, "ar_fi": ajuste["fi"],
                 "efeito_bf": M.efeito(ajuste, "Black Friday")}
        if linha["fechada"]:             # o calendário já sabe: loja fechada, previsão zero
            for nome in NOMES:
                linha[nome] = 0.0
        linhas.append(linha)
    return pd.DataFrame(linhas)


def hw_com(hw, d, linhas, j, h):
    """A previsão do Holt-Winters com a combinação j da GRADE fixa, nos dias de `linhas`."""
    fi = M.GRADE[j][3]
    soma_fi = sum(fi ** i for i in range(1, h + 1))
    prev = []
    for origem, dia, fechada in zip(linhas["origem"], linhas["dia"], linhas["fechada"]):
        io = d.index.get_loc(origem)
        nivel, incl, sazon = hw["estados"][io, j, 0], hw["estados"][io, j, 1], hw["estados"][io, j, 2:]
        prev.append(0.0 if fechada else float(np.exp(nivel + soma_fi * incl + sazon[dia.dayofweek])))
    return np.array(prev)


def mesmas_origens(p):
    """Só os dias com venda real completa e com previsão de todos os modelos."""
    return p[p["avaliado"] & p[NOMES].notna().all(axis=1)]


def wmape(real, prev):
    return float(np.sum(np.abs(real - prev)) / np.sum(real) * 100)


def custo(real, prev):
    erro = real - prev                  # positivo: faltou gente; negativo: sobrou
    return float(FALTA * erro.clip(lower=0).sum() + SOBRA * (-erro).clip(lower=0).sum())


def quadro(p):
    r = p["real"]
    print(f"  {'':22}{'MAE':>8}{'WMAPE':>9}{'viés':>8}{'custo (R$)':>13}")
    for nome in NOMES:
        f = p[nome]
        vies = (f - r).sum() / r.sum() * 100
        print(f"  {nome:22}{br(np.mean(np.abs(r - f))):>8}{br(wmape(r, f), 1) + '%':>9}"
              f"{sinal(vies) + '%':>8}{br(custo(r, f), 0):>13}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=7, help="dias entre a origem e o dia previsto (padrão 7)")
    ap.add_argument("--salvar", help="grava as previsões nesse CSV, uma linha por dia previsto")
    a = ap.parse_args()
    h = a.horizonte
    d = M.carregar()
    hw = M.holt_winters_passada(d)
    p = prever_tudo(d, h, hw)
    av = mesmas_origens(p)
    print(f"Previsões feitas {h} dias antes, origens de {p['origem'].iloc[0]:%d/%m/%Y} a {p['origem'].iloc[-1]:%d/%m/%Y}")
    print(f"  {len(p)} dias previstos, de {p['dia'].iloc[0]:%d/%m} a {p['dia'].iloc[-1]:%d/%m/%Y}")
    print(f"  {len(av)} entram na conta, os mesmos para os quatro modelos; ficam fora {len(p) - len(av)} "
          f"sem venda real completa")
    print(f"  em cada origem, cada modelo se ajusta só com a venda até aquela noite\n")

    print("1. Fora da amostra, nos mesmos dias")
    quadro(av)
    print(f"  viés: soma de (previsão − real) sobre a venda; custo: faltar R$ {br(FALTA, 0)}, sobrar R$ {br(SOBRA, 0)} por unidade\n")

    print("2. Dias comuns e dias de evento (promoção ou feriado com a loja aberta)")
    for rotulo, parte in (("comuns", av[~av["evento"]]), ("de evento", av[av["evento"]])):
        print(f"  {len(parte)} dias {rotulo}: " + ", ".join(
            f"{nome} {br(wmape(parte['real'], parte[nome]), 1)}%" for nome in NOMES))
    bf = pd.Timestamp("2025-11-28")
    if bf in set(av["dia"]):
        x = av.set_index("dia").loc[bf]
        print(f"  Black Friday 28/11, venda {br(x['real'], 0)}: " + ", ".join(
            f"{nome} {br(x[nome], 0)}" for nome in NOMES))
    print()

    print(f"3. Semana a semana, contra a régua ({REGUA})")
    av = av.assign(semana=(av["dia"] - av["dia"].iloc[0]).dt.days // 7)
    erro_regua = (av["real"] - av[REGUA]).abs()
    print(f"  {av['semana'].nunique()} semanas de dias previstos")
    print(f"  {'':22}{'semanas em que erra menos':>27}{'erro a menos por dia':>23}")
    for nome in NOMES:
        if nome == REGUA:
            continue
        ganho = erro_regua - (av["real"] - av[nome]).abs()     # positivo: o modelo errou menos
        por_semana = ganho.groupby(av["semana"])
        venceu = int((por_semana.sum() > 0).sum())
        medias = por_semana.mean()
        faixa = 2 * medias.std(ddof=1) / np.sqrt(len(medias))
        print(f"  {nome:22}{f'{venceu} de {len(medias)}':>27}{sinal(ganho.mean()) + ' ± ' + br(faixa, 1):>23}")
    print("  erro a menos por dia: média e ± 2 erros-padrão das médias semanais, em unidades\n")

    print("4. Três números de erro para o mesmo Holt-Winters, e só o último é a resposta")
    r, f = M.holt_winters_erro_ajuste(hw, d, PRIMEIRA_ORIGEM)
    print(f"  erro do ajuste, 1 dia à frente dentro do treino até {PRIMEIRA_ORIGEM:%d/%m/%Y}:  {br(wmape(r, f), 1)}%")
    pelo_teste = [wmape(av["real"], hw_com(hw, d, av, j, h)) for j in range(len(M.GRADE))]
    print(f"  parâmetros escolhidos pelo próprio teste (a melhor de {len(M.GRADE)} combinações): "
          f"{br(min(pelo_teste), 1)}%")
    print(f"  parâmetros escolhidos só com o treino, em cada origem:                 "
          f"{br(wmape(av['real'], av['Holt-Winters']), 1)}%")
    r, f = M.regressao_erro_ajuste(M.regressao_ajustar(d, PRIMEIRA_ORIGEM), d, PRIMEIRA_ORIGEM)
    print(f"  para comparar, calendário + AR(1): erro do ajuste {br(wmape(r, f), 1)}%, "
          f"fora da amostra {br(wmape(av['real'], av['calendário + AR(1)']), 1)}%\n")

    print("5. O que o ajuste escolheu em cada origem")
    ps = p["hw_params"]
    print(f"  Holt-Winters: {ps.nunique()} combinações diferentes de (alfa, beta, gama, fi) nas {len(p)} origens")
    for rot, i in (("primeira", 0), ("última", len(p) - 1)):
        al, be, ga, fi = ps.iloc[i]
        print(f"    {rot} origem, {p['origem'].iloc[i]:%d/%m}: alfa {br(al)}, beta {br(be, 3)}, gama {br(ga)}, fi {br(fi)}")
    print(f"  calendário + AR(1): fi do resíduo entre {br(p['ar_fi'].min(), 3)} e {br(p['ar_fi'].max(), 3)}; "
          f"com {h} dias de distância, o último resíduo entra multiplicado por "
          + (f"{br(p['ar_fi'].abs().max() ** h, 4)} ou menos" if p['ar_fi'].abs().max() ** h >= 1e-4 else "menos de 0,0001"))
    bf = pd.Timestamp("2025-11-28")
    if bf in set(p["dia"]):
        e = p.set_index("dia").at[bf, "efeito_bf"]
        print(f"  efeito da Black Friday na origem de {bf - pd.Timedelta(days=h):%d/%m}: {sinal(e * 100, 0)}%, "
              f"aprendido com 1 dia, o de 2024")

    if a.salvar:
        cols = ["dia", "origem", "real", "avaliado", "fechada", "evento"] + NOMES
        p[cols].to_csv(a.salvar, index=False, float_format="%.4f")
        print(f"\ngravado: {a.salvar}, {len(p)} linhas")


if __name__ == "__main__":
    main()
