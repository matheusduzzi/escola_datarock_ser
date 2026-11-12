"""A previsão que o Rafael mandou para a escala. Ele separou a venda e depois cortou na noite.

Rode o teste do corte nela:  python3 teste_corte.py rafael.py
"""
from decompor import pesos


def prever(usavel, comum, noite, dia):
    """Nível mais recente até a noite vezes o peso do dia da semana previsto."""
    nivel = usavel.rolling(7, center=True, min_periods=4).mean()   # 4 dias bastam, para o fim não ficar vazio
    peso = pesos(comum, nivel)
    return nivel[:noite].dropna().iloc[-1] * peso[dia.dayofweek]
