"""Exercício da aula «Modelo contra baseline»: o seu modelo contra a régua, fora da amostra.

Rode de dentro da pasta da aula:
    python3 minha_comparacao.py                 # ajuste feito 14 dias antes (o exercício)
    python3 minha_comparacao.py --horizonte 7

O Rafael propôs um modelo: "a média do mesmo dia da semana em todo o histórico". Você escreve
a função meu_modelo. O resto do arquivo já está pronto: ele compara o seu modelo com a régua
nos mesmos dias de comparar.py e roda o teste do futuro da aula 09.
"""
import argparse

import numpy as np
import pandas as pd

import comparar as C
import modelos as M


def meu_modelo(d, origem, dia):
    """A média da venda que serve (coluna usavel) nos dias com o mesmo dia da semana de `dia`.

    Use só os dias até a `origem`, inclusive. Retorne um número (float).
    """
    raise NotImplementedError("escreva meu_modelo antes de rodar")


def cortado(d, origem):
    """A loja como ela estava na noite da origem: a venda depois dela apagada, o calendário inteiro."""
    c = d.copy()
    c.loc[c.index > origem, ["real", "usavel"]] = np.nan
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=14)
    h = ap.parse_args().horizonte
    d = M.carregar()
    linhas = []
    for dia in pd.date_range(C.PRIMEIRA_ORIGEM + pd.Timedelta(days=h), C.ULTIMO_DIA):
        origem = dia - pd.Timedelta(days=h)
        fechada = bool(d.at[dia, "fechada"])
        linhas.append({"dia": dia, "origem": origem, "real": d.at[dia, "real"],
                       "avaliado": bool(not np.isnan(d.at[dia, "real"]) and not d.at[dia, "incompleto"]),
                       "fechada": fechada,
                       "régua": 0.0 if fechada else M.mesmo_dia_4_semanas(d, dia, h),
                       "meu modelo": 0.0 if fechada else meu_modelo(d, origem, dia)})
    p = pd.DataFrame(linhas)
    av = p[p["avaliado"] & p[["régua", "meu modelo"]].notna().all(axis=1)]
    print(f"Previsões feitas {h} dias antes: {len(av)} dias, de {av['dia'].iloc[0]:%d/%m} a {av['dia'].iloc[-1]:%d/%m/%Y}")
    for nome in ("régua", "meu modelo"):
        r, f = av["real"], av[nome]
        print(f"  {nome:12} WMAPE {C.br(C.wmape(r, f), 1)}%   viés {C.sinal((f - r).sum() / r.sum() * 100)}%   "
              f"custo R$ {C.br(C.custo(r, f), 0)}")
    semana = (av["dia"] - av["dia"].iloc[0]).dt.days // 7
    ganho = ((av["real"] - av["régua"]).abs() - (av["real"] - av["meu modelo"]).abs()).groupby(semana)
    medias = ganho.mean()
    print(f"  o seu modelo erra menos que a régua em {int((ganho.sum() > 0).sum())} de {len(medias)} semanas; "
          f"erro a menos por dia {C.sinal(av['real'].sub(av['régua']).abs().sub(av['real'].sub(av['meu modelo']).abs()).mean())}"
          f" ± {C.br(2 * medias.std(ddof=1) / np.sqrt(len(medias)), 1)}")

    print("\nTeste do futuro: a mesma previsão, com a venda depois de cada origem apagada")
    mudou = [dia for dia, origem in zip(p["dia"], p["origem"]) if not d.at[dia, "fechada"]
             and not np.isclose(meu_modelo(d, origem, dia), meu_modelo(cortado(d, origem), origem, dia))]
    print(f"  mudou em {len(mudou)} de {len(p)} dias previstos")
    if mudou:
        print(f"  o primeiro: {mudou[0]:%d/%m/%Y}. Seu modelo usa venda de depois da origem.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
