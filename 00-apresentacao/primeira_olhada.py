"""Primeira olhada na venda diária da loja física, antes de qualquer modelo.

Rode de dentro da pasta 00-apresentacao:  python3 primeira_olhada.py

1. Quantos dias o calendário tem e quantos o arquivo tem, e o que acontece nos que não batem.
2. Duas previsões simples, avaliadas em setembro e outubro de 2025, com a previsão feita
   7 dias antes do dia e 35 dias antes do dia.
"""
import pandas as pd

vendas = pd.read_csv("../dados/loja/venda_diaria.csv", parse_dates=["data"])
dias = pd.date_range("2024-01-01", "2025-12-31", freq="D")
serie = vendas.set_index("data")["unidades"].reindex(dias)
ultimo = vendas.set_index("data")["ultimo_registro"].reindex(dias)

sem_linha = serie.isna()
fechado = serie == 0
# A loja fecha às 22h. Último pedido gravado antes das 21h30 quer dizer que o sistema parou no meio do dia.
incompleto = ultimo.notna() & (ultimo.astype(str) < "21:30")

print("1. O calendário e o arquivo")
print(f"   dias no calendário: {len(dias)}   linhas no arquivo: {len(vendas)}")
print(f"   sem linha (sistema caiu): {sem_linha.sum()}")
print(f"   venda zero (loja fechada): {fechado.sum()}")
print(f"   dia incompleto (parou antes das 21h30): {incompleto.sum()}")
completo = serie.mask(sem_linha | fechado | incompleto)
print(f"   dias completos: {completo.notna().sum()}")


def avaliar(horizonte):
    """Erro médio das duas previsões quando a previsão é feita `horizonte` dias antes do dia."""
    erros_semana, erros_media = [], []
    for dia in pd.date_range("2025-09-01", "2025-10-26", freq="D"):
        real = completo[dia]
        ultimo_dia_conhecido = dia - pd.Timedelta(days=horizonte)
        # mesmo dia da semana, o mais recente que já aconteceu na hora da previsão
        mesmo_dia_semana = completo[ultimo_dia_conhecido]
        if pd.isna(real) or pd.isna(mesmo_dia_semana):
            continue
        janela = completo[ultimo_dia_conhecido - pd.Timedelta(days=27): ultimo_dia_conhecido]
        erros_semana.append(abs(real - mesmo_dia_semana))
        erros_media.append(abs(real - janela.mean()))
    return len(erros_semana), sum(erros_semana) / len(erros_semana), sum(erros_media) / len(erros_media)


print("2. Duas previsões simples, de 1/9 a 26/10/2025, só nos dias completos")
for horizonte in (7, 35):
    n, e_semana, e_media = avaliar(horizonte)
    print(f"   previsão feita {horizonte} dias antes ({n} dias avaliados)")
    print(f"      mesmo dia da semana mais recente: erro médio {e_semana:.1f} unidades por dia")
    print(f"      média dos 28 dias até a previsão: erro médio {e_media:.1f} unidades por dia")
