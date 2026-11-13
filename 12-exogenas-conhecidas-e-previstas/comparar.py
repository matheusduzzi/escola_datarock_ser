"""Compara três jeitos de pôr a chuva na previsão das entregas, nas mesmas origens.

Rode de dentro da pasta da aula:
    python3 comparar.py                  # escala montada 7 dias antes
    python3 comparar.py --horizonte 1    # na véspera

Em cada origem, de 31/08/2025 em diante, o modelo se ajusta com as entregas e a chuva até aquela noite.
As três versões só mudam no valor da chuva do dia previsto:
  calendário                 não usa a chuva
  com a chuva que caiu       usa a chuva do próprio dia previsto (só se sabe depois)
  com a previsão do tempo    usa a chance de chuva forte publicada na noite da origem
"""
import argparse

import numpy as np
import pandas as pd

import exogenas as X

PRIMEIRA_ORIGEM = pd.Timestamp("2025-08-31")
DISTANCIAS = [1, 2, 3, 5, 7, 10, 14]
VERSOES = ["calendário", "com a chuva que caiu", "com a previsão do tempo"]


def prever_tudo(d, prev, h):
    """Uma linha por dia previsto, com a origem, as entregas reais e as três previsões."""
    linhas = []
    for dia in pd.date_range(PRIMEIRA_ORIGEM + pd.Timedelta(days=h), X.FIM):
        origem = dia - pd.Timedelta(days=h)
        sem = X.ajustar(d, origem, com_chuva=False)
        com = X.ajustar(d, origem, com_chuva=True)
        linhas.append({"dia": dia, "origem": origem, "real": d.at[dia, "entregas"], "fechada": d.at[dia, "fechada"],
                       "chuva": d.at[dia, "chuva"],
                       "chance na origem": X.previsao_da_noite(prev, origem, dia),
                       "calendário": X.prever(sem, d, dia),
                       "com a chuva que caiu": X.prever(com, d, dia, d.at[dia, "chuva"]),
                       "com a previsão do tempo": X.prever(com, d, dia, X.previsao_da_noite(prev, origem, dia)),
                       "efeito": X.efeito_chuva(com)})
    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=7, help="dias entre a origem e o dia previsto (1 a 14)")
    ap.add_argument("--salvar", help="grava uma linha por dia previsto neste CSV")
    a = ap.parse_args()
    h = a.horizonte
    if not 1 <= h <= 14:
        raise SystemExit("a previsão do tempo do kit vai de 1 a 14 dias: use --horizonte entre 1 e 14")
    d, prev = X.carregar(), X.carregar_previsao()
    p = prever_tudo(d, prev, h)
    av = p[~p["fechada"]]
    print(f"Previsões feitas {h} {'dia' if h == 1 else 'dias'} antes, origens de {p['origem'].iloc[0]:%d/%m/%Y} "
          f"a {p['origem'].iloc[-1]:%d/%m/%Y}")
    print(f"  {len(av)} dias com a loja aberta, de {av['dia'].iloc[0]:%d/%m} a {av['dia'].iloc[-1]:%d/%m/%Y}; "
          f"{int(av['chuva'].sum())} com chuva forte")
    print("  em cada origem, o modelo se ajusta só com as entregas e a chuva até aquela noite")

    print("\n1. O erro nos mesmos dias")
    print(f"  {'':26}{'WMAPE':>7}{'viés':>8}   {'dias de chuva':>13}{'dias secos':>12}")
    chuva, seco = av[av["chuva"] == 1], av[av["chuva"] == 0]
    for v in VERSOES:
        print(f"  {v:26}{X.br(X.wmape(av['real'], av[v])):>6}%{X.sinal(X.vies(av['real'], av[v])):>7}%   "
              f"{X.br(X.wmape(chuva['real'], chuva[v])):>12}%{X.br(X.wmape(seco['real'], seco[v])):>11}%")
    print("  viés: soma de (previsão − real) sobre as entregas; o WMAPE das colunas da direita é só nesses dias")

    print("\n2. O que o ajuste aprendeu da chuva")
    print(f"  chuva forte multiplica as entregas por {X.br(1 + p['efeito'].iloc[0], 2)} na primeira origem "
          f"e por {X.br(1 + p['efeito'].iloc[-1], 2)} na última")
    print(f"  a chance de chuva forte que a previsão dava na origem, em média: "
          f"{X.br(100 * chuva['chance na origem'].mean(), 0)}% nos dias em que choveu, "
          f"{X.br(100 * seco['chance na origem'].mean(), 0)}% nos secos")

    print("\n3. A previsão do tempo, de quão longe (todas as previsões publicadas em 2025)")
    print(f"  {'dias antes':>10}{'chance média quando choveu':>29}{'quando não choveu':>20}")
    pr = prev.reset_index()
    pr["chuva"] = d["chuva"].reindex(pr["para_o_dia"]).to_numpy()
    pr["dias"] = (pr["para_o_dia"] - pr["publicada_em"]).dt.days
    pr = pr[pr["chuva"].notna()]
    for k in DISTANCIAS:
        q = pr[pr["dias"] == k]
        print(f"  {k:>10}{X.br(100 * q.loc[q['chuva'] == 1, 'chance'].mean(), 0):>28}%"
              f"{X.br(100 * q.loc[q['chuva'] == 0, 'chance'].mean(), 0):>19}%")
    print("  a previsão do tempo vai só até 14 dias à frente")

    if a.salvar:
        p.drop(columns=["efeito"]).to_csv(a.salvar, index=False, float_format="%.2f", date_format="%Y-%m-%d")
        print(f"\ngravado: {a.salvar}, {len(p)} linhas")


if __name__ == "__main__":
    main()
