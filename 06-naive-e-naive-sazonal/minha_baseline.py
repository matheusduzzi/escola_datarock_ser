"""A baseline da escala, com a regra do contrato. É aqui que você escreve, no exercício.

A função prever recebe:
  usavel      a venda usável até a noite da origem (a série de carregar() do naive.py, já cortada)
  calendario  o calendário inteiro, com feriado, loja_fechada e promocao, que a loja conhece antes
  origem      a noite em que a previsão é feita
  dia         o dia previsto
e retorna dois valores: (unidades previstas, dia copiado). No dia em que a loja fecha, o dia copiado é None.

Depois rode:  python3 teste_baseline.py
"""
import pandas as pd  # noqa: F401


def prever(usavel, calendario, origem, dia):
    return None, None  # troque pela sua regra
