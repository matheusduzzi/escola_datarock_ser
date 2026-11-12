"""O que a Bia tem na mão na noite em que fecha a escala de janeiro.

Rode de dentro da pasta dessa aula:  python3 contrato.py
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

1. A noite da decisão: até que dia existe venda, até que dia vai o calendário e a distância
   entre essa noite e cada dia de janeiro de 2026.
2. A ordem dos dias: quanto a venda de um dia lembra a do mesmo dia da semana anterior,
   na ordem certa e com os dias embaralhados.
3. A frequência: a venda média de cada dia da semana em 2025 e o que a soma da semana esconde.
4. A distância: a mesma regra simples feita 7, 14, 35 e 63 dias antes do dia previsto.
5. A regra simples aplicada na noite de 01/12/2025 à primeira semana de janeiro, ao lado da
   venda média de janeiro de 2025, que também já existe nessa noite.
"""
from pathlib import Path

import numpy as np
import pandas as pd

LOJA = Path(__file__).resolve().parent.parent / "dados" / "loja"
ORIGEM = pd.Timestamp("2025-12-01")  # noite em que a Bia fecha a escala de janeiro
JANEIRO = pd.date_range("2026-01-01", "2026-01-31", freq="D")
NOMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d(t):
    return t.strftime("%d/%m/%Y")


venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
dias = pd.date_range("2024-01-01", "2025-12-31", freq="D")
serie = venda["unidades"].reindex(dias)
ultimo = venda["ultimo_registro"].reindex(dias)
fechada = cal["loja_fechada"].reindex(dias) == 1
# A loja fecha às 22h. Último pedido antes das 21h30 quer dizer que o sistema parou no meio do dia.
incompleto = ultimo.notna() & (ultimo.astype(str) < "21:30")
usavel = serie.mask(serie.isna() | fechada | incompleto)

# 1. A noite da decisão
conhecida = serie[:ORIGEM]
print(f"1. A noite da decisão: {d(ORIGEM)}, depois que a loja fecha")
print(f"   venda conhecida: de {d(conhecida.index[0])} a {d(ORIGEM)}, "
      f"{conhecida.notna().sum()} linhas em {len(conhecida)} dias")
print(f"   calendário conhecido: até {d(cal.index.max())}")
h = (JANEIRO - ORIGEM).days
print(f"   dias de janeiro de 2026: {len(JANEIRO)}, de {h.min()} a {h.max()} dias depois da noite da decisão")
cj = cal.loc[JANEIRO]
print(f"   janeiro no calendário: loja fechada em "
      f"{', '.join(t.strftime('%d/%m') for t in cj.index[cj['loja_fechada'] == 1])}; "
      f"dias com promoção: {(cj['promocao'] != '').sum()}")
cd = cal.loc[ORIGEM + pd.Timedelta(days=1):"2025-12-31"]
promo = cd.index[cd["promocao"] != ""]
print(f"   entre a decisão e janeiro: promoção de Natal de {promo[0].strftime('%d/%m')} a "
      f"{promo[-1].strftime('%d/%m')}; loja fechada em "
      f"{', '.join(t.strftime('%d/%m') for t in cd.index[cd['loja_fechada'] == 1])}")

# 2. A ordem dos dias
u25 = usavel["2025"]
par = pd.DataFrame({"dia": u25, "semana_antes": usavel.shift(7)["2025"]}).dropna()
embaralhado = np.random.default_rng(1).permutation(u25.dropna().to_numpy())
e = pd.Series(embaralhado)
r_ordem = par["dia"].corr(par["semana_antes"])
r_emb = e.corr(e.shift(7))
print("2. A ordem dos dias, 2025, só dias completos com a loja aberta")
print(f"   correlação da venda com a do mesmo dia da semana anterior: {br(r_ordem, 2)} ({len(par)} pares)")
print(f"   a mesma conta com os dias embaralhados: {br(r_emb, 2)}")

# 3. A frequência
print("3. A frequência: venda média por dia da semana em 2025 (dias completos, loja aberta)")
media = u25.groupby(u25.index.dayofweek).mean()
print("   " + "  ".join(f"{NOMES[i]} {br(media[i])}" for i in range(7)))
print(f"   sábado vende {br(media[5] / media[6], 2)} vezes o domingo; "
      f"a soma de uma semana média é {br(media.sum(), 0)} unidades")


# 4. A distância
def regra(dia, antes):
    """A venda do mesmo dia da semana, o mais recente que já tinha acontecido `antes` dias antes."""
    return usavel.get(dia - pd.Timedelta(days=antes))


print("4. A mesma regra feita N dias antes: repetir o mesmo dia da semana mais recente")
print("   avaliada de 01/09 a 26/10/2025, só nos dias completos")
for antes in (7, 14, 35, 63):
    erros = []
    for dia in pd.date_range("2025-09-01", "2025-10-26", freq="D"):
        real, prev = usavel[dia], regra(dia, antes)
        if pd.notna(real) and pd.notna(prev):
            erros.append(abs(real - prev))
    print(f"   {antes:>2} dias antes: erro médio {br(sum(erros) / len(erros))} unidades por dia "
          f"({len(erros)} dias avaliados)")

# 5. A regra simples na noite de 01/12/2025
print(f"5. A regra simples feita na noite de {d(ORIGEM)}, primeira semana de janeiro de 2026")
for dia in JANEIRO[:7]:
    nome = NOMES[dia.dayofweek]
    if cal.loc[dia, "loja_fechada"] == 1:
        print(f"   {dia.strftime('%d/%m')} {nome}: loja fechada no calendário, previsão 0")
        continue
    fonte = ORIGEM - pd.Timedelta(days=(ORIGEM.dayofweek - dia.dayofweek) % 7)
    nota = cal.loc[fonte, "promocao"] or ("dia incompleto" if incompleto[fonte] else "")
    print(f"   {dia.strftime('%d/%m')} {nome}: copia {fonte.strftime('%d/%m')}, "
          f"{int(serie[fonte])} unidades{' (' + nota + ')' if nota else ''}")
semana = serie[ORIGEM - pd.Timedelta(days=6):ORIGEM]
jan25 = usavel["2025-01"]
print(f"   média da semana que a regra copia ({semana.index[0].strftime('%d/%m')} a {d(ORIGEM)[:5]}): "
      f"{br(semana.mean())}")
print(f"   média de janeiro de 2025, que também já existe nessa noite: "
      f"{br(jan25.mean())} ({jan25.notna().sum()} dias completos)")
