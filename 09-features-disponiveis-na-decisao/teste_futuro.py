"""O teste que pega informação do futuro, da aula «Features disponíveis na decisão».

Rode de dentro da pasta da aula:
    python3 teste_futuro.py rafael          # a tabela do Rafael, decisão 7 dias antes
    python3 teste_futuro.py aula            # a tabela da aula, decisão 7 dias antes
    python3 teste_futuro.py aula --h 14     # a mesma tabela, se a decisão fosse 14 dias antes

A ideia: para cada dia previsto de 2025, volte à noite da decisão, apague toda a venda que veio
depois dela e calcule a linha de novo. Se alguma coluna muda, ela usava o que ainda não existia.
O calendário fica inteiro, porque a loja já conhece feriados, dias fechados e promoções planejadas.
Sai com código 0 quando nenhuma coluna muda e com código 1 quando alguma muda.
"""
import argparse
import sys

import numpy as np
import pandas as pd

import features as ft

# o caso mostrado de cada coluna: a Black Friday; se ela não mudou, o dia 7 depois da queda do sistema (15/09)
EXEMPLOS = (pd.Timestamp("2025-11-28"), pd.Timestamp("2025-09-22"))


def iguais(a, b):
    """Vazio com vazio conta como igual; número com número, até o arredondamento."""
    if pd.isna(a) or pd.isna(b):
        return bool(pd.isna(a) and pd.isna(b))
    return bool(np.isclose(a, b))


def testar(funcao, horizonte, venda=None, cal=None, inicio="2025-01-01", fim="2025-12-31"):
    """Para cada dia previsto entre início e fim, compara a linha com tudo e a linha no corte.

    Retorna, por coluna, a lista de (origem, dia previsto, valor no corte, valor com tudo) que mudaram.
    """
    if venda is None:
        venda, cal = ft.carregar()
    com_tudo = funcao(venda, cal)
    mudou = {coluna: [] for coluna in com_tudo.columns}
    dias = pd.date_range(inicio, fim)
    for dia in dias:
        origem = dia - pd.Timedelta(days=horizonte)
        linha = ft.no_corte(funcao, venda, cal, origem, horizonte)
        for coluna in com_tudo.columns:
            if not iguais(linha[coluna], com_tudo.loc[dia, coluna]):
                mudou[coluna].append((origem, dia, linha[coluna], com_tudo.loc[dia, coluna]))
    return mudou, dias


def relatorio(nome, funcao, horizonte):
    mudou, dias = testar(funcao, horizonte)
    print(f"Teste do futuro: {nome}, decisão {horizonte} dias antes do dia previsto")
    print(f"  {len(dias)} cortes: dias previstos de {dias[0]:%d/%m/%Y} a {dias[-1]:%d/%m/%Y}")
    print("  em cada corte, a venda depois da noite da decisão é apagada; o calendário fica inteiro")
    print(f"  {'coluna':16}{'cortes em que mudou':>20}")
    for coluna, casos in mudou.items():
        print(f"  {coluna:16}{len(casos):>20}")
    ruins = {c: casos for c, casos in mudou.items() if casos}
    if not ruins:
        print("  resultado: nenhuma coluna mudou quando o futuro foi apagado")
        return 0
    print(f"  resultado: {len(ruins)} coluna(s) usam venda de depois da decisão")
    print("  um caso de cada (decisão -> dia previsto: valor no corte | valor com tudo)")
    for coluna, casos in ruins.items():
        origem, dia, no_corte, com_tudo = next((c for ex in EXEMPLOS for c in casos if c[1] == ex), casos[0])
        print(f"    {coluna:14}{origem:%d/%m} -> {dia:%d/%m}: {ft.br(no_corte):>8} | {ft.br(com_tudo)}")
    return 1


TABELAS = {"rafael": ("tabela do Rafael", ft.tabela_do_rafael), "aula": ("tabela da aula", ft.features)}

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Teste que pega informação do futuro numa tabela de features.")
    p.add_argument("tabela", choices=sorted(TABELAS))
    p.add_argument("--h", type=int, default=ft.HORIZONTE, help="dias entre a decisão e o dia previsto")
    a = p.parse_args()
    nome, funcao = TABELAS[a.tabela]
    sys.exit(relatorio(nome, funcao, a.h))
