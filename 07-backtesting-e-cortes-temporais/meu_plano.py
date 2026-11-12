"""O plano da escala do mês, do exercício. Escreva a função plano().

Ela retorna uma lista de cortes. Cada corte é um dicionário com seis chaves:
    parte       "escolha" ou "teste"
    origem      a noite em que a previsão é feita, por exemplo "2024-02-01"
    treino_de   o primeiro dia de venda que a previsão pode ler
    treino_ate  o último dia de venda que a previsão pode ler
    de, ate     o primeiro e o último dia previstos nesse corte

As datas podem ser texto no formato "AAAA-MM-DD" ou pd.Timestamp.

Teste o plano:  python3 cortes.py --plano meu_plano.py --contrato mes
"""
import pandas as pd


def plano():
    cortes = []
    # Escreva aqui os cortes da escala do mês.
    return cortes
