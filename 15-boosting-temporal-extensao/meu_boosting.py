"""O exercício da aula «Boosting temporal (extensão)»: uma coluna nova para o ajuste com 14 dias de antecedência.

Rode de dentro da pasta da aula:  python3 meu_boosting.py

Escreva a função `minha_coluna`. O resto do arquivo já está pronto:
  1. roda o teste do futuro na sua coluna, com a decisão 14 dias antes do dia previsto;
  2. se ela passar, faz a comparação fora da amostra do boosting com e sem a sua coluna,
     nos mesmos dias, e mostra a régua ao lado.
Se a coluna usar venda de depois da noite da decisão, o programa mostra o primeiro dia em que
ela mudou e sai com erro, sem rodar a comparação.
"""
import sys

import numpy as np
import pandas as pd

import boosting as B
import comparar_boosting as C
import modelos as M

HORIZONTE = 14


def minha_coluna(d, horizonte):
    """A média do mesmo dia da semana nas 8 semanas mais recentes que já existem na noite da decisão,
    dividida pela base (a média dos 28 dias que terminam nessa noite).

    d: a tabela de modelos.carregar(), um dia por linha; use a coluna "usavel".
    Retorna uma Series com o mesmo índice de d. Na linha do dia D, só pode entrar venda até
    D − horizonte.
    """
    raise NotImplementedError("escreva a função minha_coluna")


def com_a_minha(d, h):
    t = B.features(d, h)
    t["minha_coluna"] = minha_coluna(d, h)
    return t


def testar_futuro(d, h):
    dias = C.dias_previstos(h)
    origens = [dia - pd.Timedelta(days=h) for dia in dias[::3]]
    tudo = minha_coluna(d, h)
    for o in origens:
        dia = o + pd.Timedelta(days=h)
        c = d.copy()
        c.loc[c.index > o, ["real", "usavel"]] = np.nan
        a, b = minha_coluna(c, h).loc[dia], tudo.loc[dia]
        if not ((np.isnan(a) and np.isnan(b)) or np.isclose(a, b)):
            return len(origens), (o, dia, a, b)
    return len(origens), None


def main():
    np.seterr(all="ignore")
    h = HORIZONTE
    d = M.carregar()
    n, caso = testar_futuro(d, h)
    print(f"Teste do futuro da sua coluna, decisão {h} dias antes: {n} origens")
    if caso:
        o, dia, a, b = caso
        print(f"  mudou na origem {o:%d/%m/%Y}, dia previsto {dia:%d/%m/%Y}: "
              f"{C.br(a, 3)} com o futuro apagado, {C.br(b, 3)} com tudo")
        print("  Sua coluna usa venda de depois da noite da decisão.")
        sys.exit(1)
    print("  nenhuma linha mudou com o futuro apagado\n")

    t = com_a_minha(d, h)
    y = B.alvo(d, t)
    dias = C.dias_previstos(h)
    sem, _ = C.boosting_nas_origens(d, t, y, h, "kit")
    com, _ = C.boosting_nas_origens(d, t, y, h, "kit", B.COLUNAS + ["minha_coluna"])
    real = d["real"].reindex(dias)
    ok = (real.notna() & ~d["incompleto"].reindex(dias)).to_numpy()
    r = real[ok].to_numpy()
    regua = np.array([0.0 if d.at[x, "fechada"] else M.mesmo_dia_4_semanas(d, x, h) for x in dias[ok]])
    print(f"Fora da amostra, {ok.sum()} dias de {dias[0]:%d/%m} a {dias[-1]:%d/%m/%Y}, os mesmos para os três")
    for nome, f in (("régua", regua), ("boosting sem a sua coluna", sem.reindex(dias)[ok].to_numpy()),
                    ("boosting com a sua coluna", com.reindex(dias)[ok].to_numpy())):
        print(f"  {nome:28}WMAPE {C.br(C.wmape(r, f), 1)}%   custo R$ {C.br(C.custo(pd.Series(r), pd.Series(f)), 0)}")


if __name__ == "__main__":
    main()
