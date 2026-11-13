"""Põe o boosting na mesma comparação da aula 11: mesmas origens, mesmos dias, ajuste só com o passado.

Aula «Boosting temporal (extensão)» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 comparar_boosting.py                          # ajuste da semana, 7 dias antes
    python3 comparar_boosting.py --horizonte 14           # 14 dias antes (exercício)
    python3 comparar_boosting.py --motor lightgbm         # o mesmo ajuste no LightGBM, se instalado
    python3 comparar_boosting.py --motor xgboost          # ou no XGBoost
    python3 comparar_boosting.py --salvar previsoes.csv   # grava cada previsão

O boosting é reajustado a cada 7 noites, só com a venda até aquela noite. Em cada ajuste, os
últimos 56 dias do treino escolhem a folha mínima e o número de árvores. Nas noites do meio, ele
usa o último ajuste com as features novas, que só olham a venda até a origem.
Termina em pouco mais de um minuto com o motor do kit.
"""
import argparse
import sys

import numpy as np
import pandas as pd

import boosting as B
import modelos as M

PRIMEIRA_ORIGEM = pd.Timestamp("2025-08-31")
ULTIMO_DIA = pd.Timestamp("2025-12-31")
FALTA, SOBRA = 6.0, 2.0          # R$ por unidade, a estimativa da Bia na aula 08
REGUA = "mesmo dia, 4 semanas"
MODELO_SEMANA = "calendário + AR(1)"
BOOST = "boosting"
NOMES = [REGUA, MODELO_SEMANA, BOOST]
REAJUSTE = 7


def br(x, casas=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def sinal(x, casas=1):
    return ("+" if x >= 0 else "−") + br(abs(x), casas)


def wmape(real, prev):
    return float(np.sum(np.abs(real - prev)) / np.sum(real) * 100)


def custo(real, prev):
    erro = real - prev
    return float(FALTA * erro.clip(lower=0).sum() + SOBRA * (-erro).clip(lower=0).sum())


def dias_previstos(h):
    return pd.date_range(PRIMEIRA_ORIGEM + pd.Timedelta(days=h), ULTIMO_DIA)


def boosting_nas_origens(d, t, y, h, motor, colunas=B.COLUNAS, prever_nivel=None, folhas=B.FOLHAS):
    """A previsão do boosting em cada dia, feita na origem, com o último reajuste até ela.

    Retorna as previsões e, para cada ajuste, (noite do ajuste, folha mínima, número de árvores).
    """
    prev, ultimo, ajustes = {}, None, []
    for dia in dias_previstos(h):
        origem = dia - pd.Timedelta(days=h)
        if ultimo is None or (origem - ultimo).days >= REAJUSTE:
            f, folha, n = B.ajustar_na_origem(d, t, y, origem, motor, colunas, folhas)
            ultimo = origem
            ajustes.append((origem, folha, n))
        if d.at[dia, "fechada"]:
            prev[dia] = 0.0
            continue
        x = f(t.loc[[dia], colunas].to_numpy(float))[0]
        prev[dia] = float(prever_nivel(x, t, dia) if prever_nivel else np.exp(x) * t.at[dia, "base"])
    return pd.Series(prev), ajustes


def prever_tudo(d, h, motor):
    t = B.features(d, h)
    y = B.alvo(d, t)
    boost, ajustes = boosting_nas_origens(d, t, y, h, motor)
    linhas = []
    for dia in dias_previstos(h):
        origem = dia - pd.Timedelta(days=h)
        ajuste = M.regressao_ajustar(d, origem)
        linha = {"dia": dia, "origem": origem, "real": d.at[dia, "real"],
                 "avaliado": bool(not np.isnan(d.at[dia, "real"]) and not d.at[dia, "incompleto"]),
                 "fechada": bool(d.at[dia, "fechada"]), "evento": bool(d.at[dia, "evento"]),
                 REGUA: M.mesmo_dia_4_semanas(d, dia, h),
                 MODELO_SEMANA: M.regressao_prever(ajuste, d, origem, dia), BOOST: boost[dia]}
        if linha["fechada"]:
            linha[REGUA] = linha[MODELO_SEMANA] = 0.0
        linhas.append(linha)
    return pd.DataFrame(linhas), t, y, ajustes


def mesmas_origens(p):
    return p[p["avaliado"] & p[NOMES].notna().all(axis=1)]


def quadro(p, nomes):
    r = p["real"]
    print(f"  {'':22}{'MAE':>8}{'WMAPE':>9}{'viés':>8}{'custo (R$)':>13}")
    for nome in nomes:
        f = p[nome]
        vies = (f - r).sum() / r.sum() * 100
        print(f"  {nome:22}{br(np.mean(np.abs(r - f))):>8}{br(wmape(r, f), 1) + '%':>9}"
              f"{sinal(vies) + '%':>8}{br(custo(r, f), 0):>13}")


def semana_a_semana(av, contra, nome):
    ganho = (av["real"] - av[contra]).abs() - (av["real"] - av[nome]).abs()
    por_semana = ganho.groupby(av["semana"])
    medias = por_semana.mean()
    faixa = 2 * medias.std(ddof=1) / np.sqrt(len(medias))
    return int((por_semana.sum() > 0).sum()), len(medias), ganho.mean(), faixa


def embaralhada(d, t, y, motor, colunas=B.COLUNAS, arvores=300, partes=5):
    """O atalho: validação cruzada com os dias embaralhados, em 2024 e 2025 inteiros (folha 10, 300 árvores)."""
    X, yy, datas = B.treino_ate(d, t, y, ULTIMO_DIA, colunas)
    base = t.loc[datas, "base"].to_numpy()
    real = d.loc[datas, "usavel"].to_numpy()
    ordem = np.random.default_rng(0).permutation(len(yy))
    prev = np.empty(len(yy))
    for teste in np.array_split(ordem, partes):
        treino = np.setdiff1d(ordem, teste)
        prev[teste] = B.ajustar_fixo(motor, X[treino], yy[treino], arvores)(X[teste])
    return wmape(real, np.exp(prev) * base), len(yy)


def no_nivel(d, t, h, motor, dias):
    """O outro atalho: o alvo é a venda do dia, e a tendência entra como coluna."""
    t2 = t.copy()
    for c in ("lag", "mesmo_dia_4", "mesmo_dia_1", "base_28_antes"):
        t2[c] = t[c] * t["base"]
    t2["tendencia"] = (d.index - M.INICIO).days
    cols = ["base", "lag", "mesmo_dia_4", "mesmo_dia_1", "base_28_antes", "tendencia"] + B.CALENDARIO
    y2 = d["usavel"].astype(float)
    prev, _ = boosting_nas_origens(d, t2, y2, h, motor, cols, prever_nivel=lambda x, t_, dia: x)
    return prev.reindex(dias)


def teste_do_futuro(d, h, funcao, origens):
    """Apaga a venda depois de cada origem, refaz as colunas e conta os dias em que alguma mudou."""
    tudo = funcao(d, h)
    mudou = 0
    for o in origens:
        dia = o + pd.Timedelta(days=h)
        c = d.copy()
        c.loc[c.index > o, ["real", "usavel"]] = np.nan
        a, b = funcao(c, h).loc[dia], tudo.loc[dia]
        if not all((np.isnan(x) and np.isnan(z)) or np.isclose(x, z) for x, z in zip(a, b)):
            mudou += 1
    return mudou


def com_ontem(d, h):
    """As colunas da aula mais a venda de ontem do dia previsto: na noite da decisão, ela não existe."""
    t = B.features(d, h)
    t["ontem"] = d["usavel"].shift(1) / t["base"]
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=7, help="dias entre a origem e o dia previsto (padrão 7)")
    ap.add_argument("--motor", choices=sorted(B.MOTORES), default="kit",
                    help="kit (NumPy, padrão), lightgbm ou xgboost")
    ap.add_argument("--salvar", help="grava as previsões nesse CSV, uma linha por dia previsto")
    a = ap.parse_args()
    h, motor = a.horizonte, a.motor
    if not B.motor_disponivel(motor):
        print(f"O {motor} não está instalado nesse Python. Instale com:  python3 -m pip install {motor}\n"
              f"Ou rode sem --motor, com o boosting do kit.", file=sys.stderr)
        sys.exit(2)
    np.seterr(all="ignore")
    d = M.carregar()
    p, t, y, ajustes = prever_tudo(d, h, motor)
    av = mesmas_origens(p)
    print(f"Previsões feitas {h} dias antes, origens de {p['origem'].iloc[0]:%d/%m/%Y} a {p['origem'].iloc[-1]:%d/%m/%Y}")
    print(f"  {len(p)} dias previstos; {len(av)} entram na conta, os mesmos para os três modelos")
    print(f"  boosting: motor {motor}, reajustado a cada {REAJUSTE} noites ({len(ajustes)} ajustes), "
          f"só com a venda até a noite do ajuste\n")

    print("1. Fora da amostra, nos mesmos dias")
    quadro(av, NOMES)
    print(f"  custo: faltar R$ {br(FALTA, 0)}, sobrar R$ {br(SOBRA, 0)} por unidade\n")

    print("2. Dias comuns e dias de evento")
    for rotulo, parte in (("comuns", av[~av["evento"]]), ("de evento", av[av["evento"]])):
        print(f"  {len(parte)} dias {rotulo}: " + ", ".join(
            f"{nome} {br(wmape(parte['real'], parte[nome]), 1)}%" for nome in NOMES))
    bf = pd.Timestamp("2025-11-28")
    if bf in set(av["dia"]):
        x = av.set_index("dia").loc[bf]
        print(f"  Black Friday 28/11, venda {br(x['real'], 0)}: " + ", ".join(
            f"{nome} {br(x[nome], 0)}" for nome in NOMES))
    print()

    print("3. Semana a semana, dia contra dia")
    av = av.assign(semana=(av["dia"] - av["dia"].iloc[0]).dt.days // 7)
    print(f"  {'':34}{'semanas em que erra menos':>27}{'erro a menos por dia':>23}")
    for contra in (REGUA, MODELO_SEMANA):
        venceu, n, media, faixa = semana_a_semana(av, contra, BOOST)
        print(f"  {'boosting contra ' + contra:34}{f'{venceu} de {n}':>27}{sinal(media) + ' ± ' + br(faixa, 1):>23}")
    print("  erro a menos por dia: média e ± 2 erros-padrão das médias semanais, em unidades\n")

    print("4. O mesmo boosting medido de quatro jeitos")
    emb, n_emb = embaralhada(d, t, y, motor)
    nivel = no_nivel(d, t, h, motor, av["dia"])
    por_folha = {}
    for folha in B.FOLHAS:
        so, _ = boosting_nas_origens(d, t, y, h, motor, folhas=(folha,))
        por_folha[folha] = wmape(av["real"].to_numpy(), so.reindex(av["dia"]).to_numpy())
    f_teste = min(por_folha, key=por_folha.get)
    print(f"  validação cruzada embaralhada, 5 partes, {n_emb} dias de 2024 e 2025:  {br(emb, 1)}%")
    print(f"  alvo na venda do dia, com a tendência como coluna:                {br(wmape(av['real'].to_numpy(), nivel.to_numpy()), 1)}%")
    print(f"  folha mínima escolhida pelo próprio teste (a melhor de {len(B.FOLHAS)}, folha {f_teste}): {br(por_folha[f_teste], 1)}%")
    print(f"  folha e árvores escolhidas só com o treino, em cada ajuste (parte 1): {br(wmape(av['real'], av[BOOST]), 1)}%")
    print("  com cada folha fixa: " + ", ".join(f"{f} dia{'s' if f > 1 else ''} {br(v, 1)}%" for f, v in por_folha.items()) + "\n")

    print("5. O que cada ajuste escolheu")
    folhas_esc = [f for _, f, _ in ajustes]
    arv = [n for _, _, n in ajustes]
    print(f"  {len(ajustes)} ajustes; folha mínima: " + ", ".join(
        f"{f} em {folhas_esc.count(f)}" for f in B.FOLHAS if folhas_esc.count(f)))
    print(f"  árvores por ajuste: de {min(arv)} a {max(arv)}")
    print(f"  folha de cada ajuste, de {ajustes[0][0]:%d/%m} a {ajustes[-1][0]:%d/%m}: " + " ".join(str(f) for f in folhas_esc))
    bf = pd.Timestamp("2025-11-28")
    o_bf = bf - pd.Timedelta(days=h)
    if PRIMEIRA_ORIGEM <= o_bf:
        ultimo, folha, n = max(x for x in ajustes if x[0] <= o_bf)
        X, yy, datas = B.treino_ate(d, t, y, ultimo)
        val = datas[datas > datas[-1] - pd.Timedelta(days=B.VALIDACAO)]
        print(f"  o ajuste da noite de {ultimo:%d/%m}, que fez a previsão da Black Friday:")
        if motor == "kit":
            m = B.Boosting(folha_min=folha).ajustar(X, yy, n)
            imp = sorted(zip(B.COLUNAS, m.importancia()), key=lambda z: -z[1])[:4]
            print(f"    folha mínima {folha}, {n} árvores; colunas que mais cortaram: "
                  + ", ".join(f"{c} {br(v * 100, 0)}%" for c, v in imp))
        else:
            print(f"    folha mínima {folha}, {n} árvores")
        print(f"    no treino, {int(d.loc[datas, 'Black Friday'].sum())} dia de Black Friday e "
              f"{int(d.loc[datas, 'Natal'].sum())} de Natal; nos {B.VALIDACAO} dias de validação, "
              f"{int(d.loc[val, 'evento'].sum())} dias de evento")
    print()

    print("6. Teste do futuro das colunas do boosting")
    origens = sorted(set(list(p["origem"].iloc[::9]) + ([o_bf] if PRIMEIRA_ORIGEM <= o_bf else [])))
    print(f"  {len(origens)} origens; a venda depois de cada uma é apagada e as colunas são refeitas")
    print(f"  colunas da aula: mudaram em {teste_do_futuro(d, h, B.features, origens)} de {len(origens)}")
    print(f"  colunas da aula + venda de ontem: mudaram em {teste_do_futuro(d, h, com_ontem, origens)} de {len(origens)}")

    if a.salvar:
        cols = ["dia", "origem", "real", "avaliado", "fechada", "evento"] + NOMES
        p[cols].to_csv(a.salvar, index=False, float_format="%.4f")
        print(f"\ngravado: {a.salvar}, {len(p)} linhas")


if __name__ == "__main__":
    main()
