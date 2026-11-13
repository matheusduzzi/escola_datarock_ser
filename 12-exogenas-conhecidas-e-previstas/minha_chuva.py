"""Exercício da aula «Exógenas conhecidas e previstas»: a chuva que existe na noite da origem.

Rode de dentro da pasta da aula:
    python3 minha_chuva.py

Você escreve a função chuva_na_noite. O resto do arquivo já está pronto: ele põe a sua chuva no modelo
das entregas, compara com o calendário a 3 e a 21 dias, nas mesmas origens de comparar.py, e roda o
teste do futuro: refaz cada chuva com a chuva e as previsões de depois da origem trocadas.
"""
import numpy as np
import pandas as pd

import comparar as C
import exogenas as X

HORIZONTES = (3, 21)


def chuva_na_noite(d, prev, origem, dia):
    """A chance de chuva forte em `dia` que existe na noite da `origem`, de 0 a 1.

    Se a previsão publicada no dia da origem chega até `dia`, use a chance dela.
    Se não chega, use a fração de dias de chuva forte (coluna chuva) no mesmo mês de `dia`,
    contando só os dias até a origem, inclusive.
    """
    raise NotImplementedError("escreva chuva_na_noite antes de rodar")


def trocado(d, prev, origem):
    """O mundo trocado depois da origem: chuva ao contrário e previsões publicadas depois com a chance invertida."""
    c = d.copy()
    depois = c.index > origem
    c.loc[depois, "chuva"] = 1 - c.loc[depois, "chuva"]
    p = prev.copy()
    pub = p.index.get_level_values("publicada_em") > origem
    p[pub] = 1 - p[pub]
    return c, p


def main():
    d, prev = X.carregar(), X.carregar_previsao()
    testes = []
    for h in HORIZONTES:
        linhas = []
        for dia in pd.date_range(C.PRIMEIRA_ORIGEM + pd.Timedelta(days=h), X.FIM):
            origem = dia - pd.Timedelta(days=h)
            if d.at[dia, "fechada"]:
                continue
            chance = chuva_na_noite(d, prev, origem, dia)
            com = X.ajustar(d, origem, com_chuva=True)
            linhas.append({"real": d.at[dia, "entregas"], "calendário": X.prever(X.ajustar(d, origem, False), d, dia),
                           "com a sua chuva": X.prever(com, d, dia, chance), "chance": chance})
            testes.append((origem, dia, chance))
        p = pd.DataFrame(linhas)
        print(f"Previsões feitas {h} dias antes: {len(p)} dias com a loja aberta")
        for v in ("calendário", "com a sua chuva"):
            print(f"  {v:16} WMAPE {X.br(X.wmape(p['real'], p[v])):>5}%   viés {X.sinal(X.vies(p['real'], p[v]))}%")
        print(f"  a sua chance de chuva, em média: {X.br(100 * p['chance'].mean(), 0)}%\n")

    print("Teste do futuro: a mesma chuva, com a chuva e as previsões de depois da origem trocadas")
    mudou = []
    for origem, dia, chance in testes:
        c, p = trocado(d, prev, origem)
        if not np.isclose(chance, chuva_na_noite(c, p, origem, dia)):
            mudou.append((origem, dia))
    print(f"  mudou em {len(mudou)} de {len(testes)} dias previstos")
    if mudou:
        o, dia = mudou[0]
        print(f"  o primeiro: {dia:%d/%m/%Y}, previsto na noite de {o:%d/%m/%Y}. "
              "A sua função usa o que só existe depois da origem.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
