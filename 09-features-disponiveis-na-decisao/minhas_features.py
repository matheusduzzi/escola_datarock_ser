"""Exercício «O ajuste com duas semanas de aviso». Escreva o seu código na função features_14.

Rode de dentro da pasta da aula:  python3 minhas_features.py
O programa mostra as colunas da sua tabela e roda o teste do futuro com a decisão 14 dias antes.
"""
import sys

import features as ft
import teste_futuro as tf

HORIZONTE = 14


def features_14(venda, cal):
    """A tabela da Bia: a decisão é na noite de 14 dias antes do dia previsto."""
    real, usavel = ft.por_dia(venda, cal)
    t = ft.calendario(cal)
    # Tarefa 2: acrescente aqui lag14, lag21, media_28, dias_28 e media_dsem_4.

    return t


if __name__ == "__main__":
    tabela = features_14(*ft.carregar())
    print("colunas:", ", ".join(tabela.columns))
    codigo = tf.relatorio("as suas features", features_14, HORIZONTE)

    # Tarefa 3: compare a regressão da aula (7 dias) com a sua (14 dias), nos mesmos dias.
    # Dica: ft.regressao({"7 dias": ..., "14 dias": ...}, real) com real = ft.por_dia(venda, cal)[0]

    sys.exit(codigo)
