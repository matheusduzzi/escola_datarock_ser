"""Exercício «Guarda-chuva na prateleira». Escreva o seu código embaixo de cada tarefa.

Rode de dentro da pasta da aula:  python3 minha_analise.py
"""
import numpy as np
import pandas as pd

g = pd.read_csv("dados/guarda_chuva.csv", parse_dates=["data"])
print(f"{len(g)} dias, de {g['data'].min():%d/%m/%Y} a {g['data'].max():%d/%m/%Y}; colunas: {', '.join(g.columns)}")

real = g["vendidos"].to_numpy(float)

# Tarefa 1: venda 0, 2, 1, 12, 0 e previsão 2 todo dia. Faça à mão primeiro e depois confira aqui.

# Tarefa 2: MAE, RMSE, MAPE (dias com venda > 0), WMAPE, faltou e sobrou de prev_media e prev_mediana.

# Tarefa 3: custo com R$ 15 por unidade que faltou e R$ 1 por unidade que sobrou.
