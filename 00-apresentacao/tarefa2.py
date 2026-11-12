"""Tarefa 2 do diagnóstico: a média dos 7 dias antes da decisão.

Rode de dentro da pasta 00-apresentacao:  python3 tarefa2.py
"""
import pandas as pd

vendas = pd.read_csv("dados/venda_maio.csv", parse_dates=["data"])


def media_7_dias_antes(vendas, corte):
    """Média das unidades nos 7 dias do calendário anteriores a `corte`, sem contar o próprio dia.

    Retorna dois valores: (média com uma casa decimal, quantos desses 7 dias têm linha no arquivo).
    """
    return None


resultado = {corte: media_7_dias_antes(vendas, corte) for corte in ["2025-05-10", "2025-05-15"]}
print(resultado)
