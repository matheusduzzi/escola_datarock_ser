"""Os números do relatório que defende a previsão da escala, do contrato até os limites.

Aula «Defender a previsão» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 defender.py                         # escala montada 7 dias antes
    python3 defender.py --horizonte 14          # escala montada 14 dias antes (exercício)
    python3 defender.py --salvar previsoes.csv  # grava cada previsão e o número da escala

Os modelos são os da aula «Modelo contra baseline», no modelos.py dessa pasta, sem mudança.
A primeira origem é a noite de 31/08/2025. Cada dia previsto sai da venda até a noite da
origem, que é o dia menos o horizonte. A régua e o modelo preveem os mesmos dias.

O fator da escala e a faixa de 80% saem dos erros do passado: as previsões dos dias de
01/03 a 31/08/2025, feitas do mesmo jeito e com o mesmo horizonte. Tudo isso já existia na
noite de 31/08/2025.
"""
import argparse
import sys

import numpy as np
import pandas as pd

import modelos as M

PRIMEIRA_ORIGEM = pd.Timestamp("2025-08-31")
ULTIMO_DIA = pd.Timestamp("2025-12-31")
CALIBRA = (pd.Timestamp("2025-03-01"), pd.Timestamp("2025-08-31"))
FIM_CALENDARIO = pd.Timestamp("2026-01-31")
FALTA, SOBRA = 6.0, 2.0              # R$ por unidade, a estimativa da Bia na aula 08
ALVO = FALTA / (FALTA + SOBRA)        # 0,75: a escala cobre a venda em 75% dos dias
REGUA, HW, MODELO = "mesmo dia, 4 semanas", "Holt-Winters", "calendário + AR(1)"
NOMES = [REGUA, HW, MODELO]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
PROMOCOES = M.EVENTOS[:3]             # as colunas que vêm do marketing; o feriado é sempre conhecido


def br(x, casas=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def sinal(x, casas=1):
    return ("+" if x >= 0 else "−") + br(abs(x), casas)


def pct(x, casas=1):
    return br(x, casas) + "%"


def carregar():
    """A venda e o calendário de modelos.carregar, com janeiro de 2026 a mais, sem venda.

    Janeiro entra só com o calendário: é a próxima escala, e a loja já sabe dos feriados e das
    promoções planejadas. A venda de janeiro fica vazia.
    """
    d = M.carregar()
    cal = pd.read_csv(M.LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(M.INICIO, FIM_CALENDARIO)
    d = d.reindex(dias)
    c = cal.reindex(dias)
    d["incompleto"] = d["incompleto"].eq(True)
    d["fechada"] = c["loja_fechada"] == 1
    for nome in PROMOCOES:
        d[nome] = c["promocao"] == nome
    d[M.EVENTOS[3]] = (c["feriado"] != "") & ~d["fechada"]
    d["evento"] = d[M.EVENTOS].any(axis=1)
    return d


def prever_dias(d, dias, horizonte, hw, sem_promocao=False):
    """Uma linha por dia: a venda real e a previsão de cada modelo, feita na noite da origem.

    Com sem_promocao, o modelo prevê o dia sem as colunas de promoção, como se o marketing
    tivesse posto a promoção no calendário depois da escala. O ajuste continua com o passado
    como ele foi.
    """
    sem = d.copy()
    for nome in PROMOCOES:
        sem[nome] = False
    linhas, cache = [], {}
    for dia in dias:
        origem = dia - pd.Timedelta(days=horizonte)
        if origem not in cache:
            cache[origem] = M.regressao_ajustar(d, origem)
        ajuste = cache[origem]
        real = d.at[dia, "real"]
        linha = {"dia": dia, "origem": origem, "real": real,
                 "avaliado": bool(not np.isnan(real) and not d.at[dia, "incompleto"]),
                 "fechada": bool(d.at[dia, "fechada"]), "evento": bool(d.at[dia, "evento"]),
                 REGUA: M.mesmo_dia_4_semanas(d, dia, horizonte),
                 HW: M.holt_winters_prever(hw, d, origem, dia)[0],
                 MODELO: M.regressao_prever(ajuste, sem if sem_promocao else d, origem, dia),
                 "efeito_bf": M.efeito(ajuste, "Black Friday")}
        if linha["fechada"]:             # o calendário já sabe: loja fechada, previsão zero
            for nome in NOMES:
                linha[nome] = 0.0
        linhas.append(linha)
    return pd.DataFrame(linhas)


def mesmos_dias(p, so_abertos=False):
    """Só os dias com venda real completa e previsão de todos os modelos, como na aula 11.

    O dia de loja fechada entra no erro e no custo: todos preveem zero e acertam. Na faixa e nos
    erros do passado ele sai (so_abertos), porque cairia sempre dentro e a razão seria 0 ÷ 0.
    """
    ok = p["avaliado"] & p[NOMES].notna().all(axis=1)
    return p[ok & ~p["fechada"]] if so_abertos else p[ok]


def wmape(real, prev):
    return float(np.sum(np.abs(real - prev)) / np.sum(real) * 100)


def custo(real, prev):
    erro = real - prev                  # positivo: faltou gente; negativo: sobrou
    return float(FALTA * erro.clip(lower=0).sum() + SOBRA * (-erro).clip(lower=0).sum())


def razoes(c, nome):
    """Venda real ÷ previsão, nos dias da calibração. É o erro do passado de cada modelo."""
    return (c["real"] / c[nome]).to_numpy()


def semana_a_semana(av, nome):
    """Semanas em que o modelo erra menos que a régua, e a média por dia com ± 2 erros-padrão."""
    semana = (av["dia"] - av["dia"].iloc[0]).dt.days // 7
    ganho = (av["real"] - av[REGUA]).abs() - (av["real"] - av[nome]).abs()
    por_semana = ganho.groupby(semana)
    medias = por_semana.mean()
    faixa = 2 * medias.std(ddof=1) / np.sqrt(len(medias))
    return int((por_semana.sum() > 0).sum()), len(medias), float(ganho.mean()), float(faixa)


def teste_do_futuro(d, horizonte):
    """Troca a venda depois da origem por lixo e refaz a previsão feita nela, uma origem por semana.

    Se algum modelo olhasse a venda depois da origem, a previsão mudaria. Retorna quantas
    origens foram testadas, quantas previsões foram refeitas e quantas mudaram.
    """
    hw = M.holt_winters_passada(d)
    origens = pd.date_range(PRIMEIRA_ORIGEM, ULTIMO_DIA - pd.Timedelta(days=horizonte), freq="7D")
    refeitos = mudaram = 0
    for origem in origens:
        dia = pd.DatetimeIndex([origem + pd.Timedelta(days=horizonte)])
        lixo = d.copy()
        depois = lixo.index > origem
        lixo.loc[depois, "real"] = lixo.loc[depois, "real"] * 3 + 50
        lixo.loc[depois, "usavel"] = lixo.loc[depois, "usavel"] * 3 + 50
        certo = prever_dias(d, dia, horizonte, hw)[NOMES].to_numpy()
        sujo = prever_dias(lixo, dia, horizonte, M.holt_winters_passada(lixo))[NOMES].to_numpy()
        refeitos += certo.size
        mudaram += int((np.abs(certo - sujo) > 1e-9).sum())
    return len(origens), refeitos, mudaram


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=7, help="dias entre a origem e o dia previsto (padrão 7)")
    ap.add_argument("--salvar", help="grava as previsões e o número da escala nesse CSV")
    a = ap.parse_args()
    h = a.horizonte
    if not 1 <= h <= 28:
        sys.exit("o horizonte precisa ficar entre 1 e 28 dias: a aula 13 mediu a faixa até 28")
    d = carregar()
    hw = M.holt_winters_passada(d)

    teste = prever_dias(d, pd.date_range(PRIMEIRA_ORIGEM + pd.Timedelta(days=h), ULTIMO_DIA), h, hw)
    av = mesmos_dias(teste)
    calib = mesmos_dias(prever_dias(d, pd.date_range(*CALIBRA), h, hw), so_abertos=True)

    print(f"Defesa da previsão da escala, feita {h} dias antes")
    print(f"  origens de {teste['origem'].iloc[0]:%d/%m/%Y} a {teste['origem'].iloc[-1]:%d/%m/%Y}; "
          f"{len(teste)} dias previstos, de {teste['dia'].iloc[0]:%d/%m} a {teste['dia'].iloc[-1]:%d/%m/%Y}")
    fora = teste[~teste.index.isin(av.index)]
    print(f"  {len(av)} entram na conta, os mesmos para os três; ficam fora {len(fora)} sem venda real completa")
    print(f"  erros do passado: {len(calib)} dias de {CALIBRA[0]:%d/%m} a {CALIBRA[1]:%d/%m/%Y}, "
          f"previstos do mesmo jeito\n")

    print("1. Régua e modelos nos mesmos dias")
    print(f"  {'':22}{'WMAPE':>8}{'viés':>8}{'custo (R$)':>12}{'semanas em que erra menos':>28}{'erro a menos por dia':>23}")
    for nome in NOMES:
        r, f = av["real"], av[nome]
        vies = (f - r).sum() / r.sum() * 100
        if nome == REGUA:
            sem, faixa = "é a régua", ""
        else:
            v, n, g, e = semana_a_semana(av, nome)
            sem, faixa = f"{v} de {n}", f"{sinal(g)} ± {br(e)}"
        print(f"  {nome:22}{pct(wmape(r, f)):>8}{sinal(vies) + '%':>8}{br(custo(r, f), 0):>12}{sem:>28}{faixa:>23}")
    print(f"  custo: faltar R$ {br(FALTA, 0)}, sobrar R$ {br(SOBRA, 0)} por unidade (aula 08)\n")

    print(f"2. O número da escala: previsão vezes o fator que cobre a venda em {br(ALVO * 100, 0)}% dos dias")
    print(f"  {'':34}{'fator':>7}{'custo (R$)':>12}{'dias em que faltou':>21}")
    planos = {}
    for nome in (REGUA, MODELO):
        fator = float(np.quantile(razoes(calib, nome), ALVO))
        for rotulo, k in ((f"{nome}, a previsão", 1.0), (f"{nome}, com o fator", fator)):
            plano = av[nome] * k
            planos[rotulo] = plano
            faltou = int((av["real"] > plano).sum())
            print(f"  {rotulo:34}{br(k, 3):>7}{br(custo(av['real'], plano), 0):>12}"
                  f"{f'{faltou} de {len(av)}':>21}")
        planos[nome] = fator
    hoje = custo(av["real"], av[REGUA])
    regua_fator = custo(av["real"], av[REGUA] * planos[REGUA])
    novo = custo(av["real"], av[MODELO] * planos[MODELO])
    print(f"  da régua como a Bia usa hoje para o modelo com o fator: R$ {br(hoje - novo, 0)} a menos "
          f"em {len(av)} dias")
    print(f"    o fator sozinho, na própria régua: R$ {br(hoje - regua_fator, 0)}; "
          f"o modelo, com o fator nos dois: R$ {br(regua_fator - novo, 0)}\n")

    print("3. A faixa de 80% pelos erros do passado: quantas vezes pegou a venda")
    ab = mesmos_dias(teste, so_abertos=True)
    folga = 2 * np.sqrt(0.8 * 0.2 / len(ab)) * 100
    print(f"  {len(ab)} dias com a loja aberta; piso e teto: a previsão vezes os quantis de 10% e 90% "
          f"de venda ÷ previsão no passado")
    for nome in (REGUA, MODELO):
        q10, q90 = np.quantile(razoes(calib, nome), [0.1, 0.9])
        dentro = ((ab["real"] >= ab[nome] * q10) & (ab["real"] <= ab[nome] * q90)).mean() * 100
        acima = (ab["real"] > ab[nome] * q90).mean() * 100
        print(f"  {nome:22} dentro {pct(dentro, 0):>4}, acima do teto {pct(acima, 0):>4}, "
              f"largura média {br(float((ab[nome] * (q90 - q10)).mean()))}")
    print(f"  com {len(ab)} dias, uma faixa de 80% bem feita cai entre {pct(80 - folga, 0)} e "
          f"{pct(80 + folga, 0)} só pelo acaso\n")

    print("4. Onde a previsão pode quebrar")
    for rotulo, parte in (("comuns", av[~av["evento"]]), ("de evento", av[av["evento"]])):
        print(f"  {len(parte)} dias {rotulo}: régua {pct(wmape(parte['real'], parte[REGUA]))}, "
              f"modelo {pct(wmape(parte['real'], parte[MODELO]))}")
    mes = av["dia"].dt.month
    print("  WMAPE do modelo por mês: " + ", ".join(
        f"{m:02d} {pct(wmape(av['real'][mes == m], av[MODELO][mes == m]))}" for m in sorted(mes.unique())))
    sem = mesmos_dias(prever_dias(d, av["dia"], h, hw, sem_promocao=True))
    dias_promo = av["dia"].isin(d.index[d[PROMOCOES].any(axis=1)])
    print(f"  se a promoção entrar no calendário depois da escala ({int(dias_promo.sum())} dias de promoção): "
          f"modelo {pct(wmape(sem['real'], sem[MODELO]))} no período, custo R$ {br(custo(sem['real'], sem[MODELO]), 0)} "
          f"contra R$ {br(custo(av['real'], av[MODELO]), 0)}")
    bf = pd.Timestamp("2025-11-28")
    if bf in set(teste["dia"]):
        x = teste.set_index("dia").loc[bf]
        print(f"  Black Friday 28/11, venda {br(x['real'], 0)}: modelo {br(x[MODELO], 0)}, régua {br(x[REGUA], 0)}; "
              f"efeito {sinal(x['efeito_bf'] * 100, 0)}%, aprendido com 1 dia, o de 2024\n")
    else:
        print()

    print("5. Teste do futuro: a venda depois da origem trocada por lixo, uma origem por semana")
    n_origens, refeitos, mudaram = teste_do_futuro(d, h)
    print(f"  {n_origens} origens, {refeitos} previsões refeitas (régua, Holt-Winters e modelo), {mudaram} mudaram\n")

    print(f"6. A próxima escala: a primeira semana de janeiro, cada dia feito {h} dias antes")
    jan = pd.date_range("2026-01-01", "2026-01-07")
    jan = jan[jan - pd.Timedelta(days=h) <= ULTIMO_DIA]
    if len(jan) == 0:
        print("  com esse horizonte, nenhum dia de janeiro tem origem até 31/12/2025")
    else:
        pj = prever_dias(d, jan, h, hw)
        print(f"  {'dia':12}{'origem':>8}{'régua':>8}{'modelo':>8}{'escala':>8}")
        for _, x in pj.iterrows():
            esc = 0.0 if x["fechada"] else x[MODELO] * planos[MODELO]
            nota = "  loja fechada" if x["fechada"] else ""
            print(f"  {DIAS[x['dia'].dayofweek]} {x['dia']:%d/%m}" + f"{x['origem']:%d/%m}".rjust(9) + f"{br(x[REGUA], 0):>8}{br(x[MODELO], 0):>8}{br(esc, 0):>8}{nota}")
        print(f"  escala = modelo × {br(planos[MODELO], 3)}, arredondado; a venda de janeiro ainda não existe")

    if a.salvar:
        out = teste[["dia", "origem", "real", "avaliado", "fechada", "evento"] + NOMES].copy()
        out["escala"] = np.where(out["fechada"], 0.0, out[MODELO] * planos[MODELO])
        out.to_csv(a.salvar, index=False, float_format="%.4f")
        print(f"\ngravado: {a.salvar}, {len(out)} linhas")


if __name__ == "__main__":
    main()
