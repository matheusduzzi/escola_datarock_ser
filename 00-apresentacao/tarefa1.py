"""Tarefa 1 do diagnóstico: o calendário de 1º a 21 de maio.

Rode de dentro da pasta 00-apresentacao:  python3 tarefa1.py
"""
import pandas as pd

vendas = pd.read_csv("dados/venda_maio.csv", parse_dates=["data"])
print(vendas.head())
print(f"linhas no arquivo: {len(vendas)}")

# Monte aqui a série com um dia por linha, de 2025-05-01 a 2025-05-21,
# com o dia sem linha no arquivo vazio (NaN), e não zero.
calendario = None

# Guarde as respostas neste dicionário, com as chaves do enunciado:
# dias_no_calendario, dias_sem_registro, dias_com_zero,
# media_21_dias, media_dias_com_registro, media_dias_abertos
resultado = None

print(resultado)
