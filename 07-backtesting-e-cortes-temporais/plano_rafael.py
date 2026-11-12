"""O plano que o Rafael montou para testar o ajuste da semana, da prática guiada.

Ele pegou os dias de 2025, mandou um dia a cada cinco para o teste e deixou os outros para a escolha.
Cada dia é previsto 7 dias antes, e o treino vai até a véspera do dia previsto.

Teste o plano:  python3 cortes.py --plano plano_rafael.py --contrato semana
"""
import pandas as pd


def plano():
    cortes = []
    for i, dia in enumerate(pd.date_range("2025-01-01", "2025-12-31")):
        cortes.append({
            "parte": "teste" if i % 5 == 4 else "escolha",
            "origem": dia - pd.Timedelta(days=7),
            "treino_de": "2024-01-01",
            "treino_ate": dia - pd.Timedelta(days=1),
            "de": dia,
            "ate": dia,
        })
    return cortes
