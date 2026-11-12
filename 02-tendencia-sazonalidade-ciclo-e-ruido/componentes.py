"""As partes da venda diária da loja física e o que muda quando a venda é somada em semanas e meses.

Rode de dentro da pasta dessa aula:  python3 componentes.py
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

1. A mesma venda em três frequências: quanto o número varia no dia, na semana e no mês.
2. Tendência: a média dos dias comuns em 2024 e em 2025 e o mesmo mês de um ano para o outro.
3. Sazonalidade da semana: quanto cada dia da semana vende perto da média da semana dele, em cada ano.
4. Sazonalidade do ano: quanto cada mês vende perto da reta de crescimento, em cada ano.
5. Ruído: o que sobra depois de tirar a semana e o dia da semana, e se ele lembra o dia anterior.
6. Agregação: três casos em que o total da semana ou do mês conta outra história.

Dia comum: dia completo, com a loja aberta, sem feriado e sem promoção. As partes 3 a 5 usam a
média centrada de 7 dias, que olha 3 dias para trás e 3 para frente. Ela serve para entender a
série. Para prever, ela não serve: no dia da decisão os 3 dias seguintes ainda não aconteceram.
"""
from pathlib import Path

import numpy as np
import pandas as pd

LOJA = Path(__file__).resolve().parent.parent / "dados" / "loja"
NOMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=1):
    return ("+" if x > 0 else "") + br(100 * x, casas) + "%"


def dm(t):
    return t.strftime("%d/%m")


venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
dias = pd.date_range("2024-01-01", "2025-12-31", freq="D")
serie = venda["unidades"].reindex(dias)
ultimo = venda["ultimo_registro"].reindex(dias)
c = cal.reindex(dias)
fechada = c["loja_fechada"] == 1
incompleto = ultimo.notna() & (ultimo.astype(str) < "21:30")  # a loja fecha às 22h
usavel = serie.mask(serie.isna() | fechada | incompleto)
evento = (c["promocao"] != "") | (c["feriado"] != "")
comum = usavel.mask(evento)

# 1. Três frequências
print("1. A mesma venda em três frequências, 2025")
d25 = comum["2025"].dropna()
print(f"   dia comum: média {br(d25.mean())}, o dia varia {br(100 * d25.std() / d25.mean())}% em torno dela "
      f"({len(d25)} dias)")
problema = (serie.isna() | fechada | incompleto | evento).resample("W-SUN").sum()
semanas = serie.resample("W-SUN").sum(min_count=1)
limpas = semanas[(problema == 0) & (semanas.index >= "2024-01-07") & (semanas.index <= "2025-12-28")]
s25 = limpas["2025"]
print(f"   semana de segunda a domingo, só com os 7 dias comuns: média {br(s25.mean(), 0)}, "
      f"a semana varia {br(100 * s25.std() / s25.mean())}% ({len(s25)} semanas)")
total_mes = serie.resample("MS").sum()
linhas_mes = serie.resample("MS").count()
media_mes = usavel.resample("MS").mean()
print("   mês: total de unidades, linhas no arquivo e média por dia completo com a loja aberta")
for t in total_mes["2025"].index:
    print(f"      {MESES[t.month - 1]}/25  total {br(total_mes[t], 0):>5}  linhas {linhas_mes[t]:>2} de "
          f"{t.days_in_month}  média por dia {br(media_mes[t])}")

# 2. Tendência
print("2. Tendência: dias comuns")
ano = comum.groupby(comum.index.year).mean()
print(f"   média em 2024: {br(ano[2024])}   em 2025: {br(ano[2025])}   "
      f"de um ano para o outro: {pct(ano[2025] / ano[2024] - 1)}")
mm = comum.resample("MS").mean()
yoy = pd.Series(mm["2025"].to_numpy() / mm["2024"].to_numpy() - 1, index=range(12))
print("   mesmo mês, 2025 contra 2024: " + "  ".join(f"{MESES[i]} {pct(yoy[i], 0)}" for i in range(12)))
print(f"   o menor: {pct(yoy.min())} ({MESES[yoy.idxmin()]}); o maior: {pct(yoy.max())} "
      f"({MESES[yoy.idxmax()]}); a média dos 12: {pct(yoy.mean())}")

# 3. Sazonalidade da semana
m7 = usavel.rolling(7, center=True, min_periods=7).mean()
razao = (comum / m7).dropna()
print("3. Sazonalidade da semana: venda do dia dividida pela média centrada de 7 dias")
for a in (2024, 2025):
    r = razao[str(a)]
    f = r.groupby(r.index.dayofweek).mean()
    print(f"   {a}: " + "  ".join(f"{NOMES[i]} {br(f[i], 2)}" for i in range(7)))
fator = razao.groupby(razao.index.dayofweek).mean()
print(f"   os dois anos juntos: sábado {br(fator[5], 2)}, domingo {br(fator[6], 2)}; "
      f"o sábado vende {br(fator[5] / fator[6], 2)} vezes o domingo")
dif = {a: comum[str(a)][comum[str(a)].index.dayofweek == 5].mean() - comum[str(a)][comum[str(a)].index.dayofweek == 6].mean()
       for a in (2024, 2025)}
print(f"   sábado menos domingo, em unidades: {br(dif[2024])} em 2024 e {br(dif[2025])} em 2025 "
      f"({pct(dif[2025] / dif[2024] - 1)})")

# 4. Sazonalidade do ano
t = (comum.index - dias[0]).days.to_numpy()
ok = comum.notna().to_numpy()
inclinacao, intercepto = np.polyfit(t[ok], comum.to_numpy()[ok], 1)
reta = pd.Series(intercepto + inclinacao * t, index=dias)
print("4. Sazonalidade do ano: dias comuns divididos pela reta de crescimento e pelo dia da semana")
print(f"   a reta: {br(reta.iloc[0])} em 01/01/2024 e {br(reta.iloc[-1])} em 31/12/2025, "
      f"{br(inclinacao * 365)} unidades a mais por dia a cada ano")
sem_ano = comum / (reta * fator.reindex(dias.dayofweek).to_numpy())
indice = sem_ano.resample("MS").mean()
for a in ("2024", "2025"):
    print(f"   {a}: " + "  ".join(f"{MESES[k.month - 1]} {br(indice[k], 2)}" for k in indice[a].index))
duplo = indice.groupby(indice.index.month).mean()
print(f"   os dois anos juntos: o mês mais fraco é {MESES[duplo.idxmin() - 1]} ({br(duplo.min(), 2)}); "
      f"o mais forte, {MESES[duplo.idxmax() - 1]} ({br(duplo.max(), 2)})")

# 5. Ruído
esperado = m7 * fator.reindex(dias.dayofweek).to_numpy()
ruido = comum / esperado - 1
print("5. Ruído: dia comum contra a média centrada de 7 dias vezes o peso do dia da semana")
rr = ruido.dropna()
print(f"   o que sobra varia {br(100 * rr.std())}% em torno do esperado ({len(rr)} dias)")
print(f"   correlação do que sobra com o do dia anterior: {br(ruido.autocorr(1), 2)}; "
      f"com o do mesmo dia da semana anterior: {br(ruido.autocorr(7), 2)}")

# 6. Agregação
print("6. Agregação: o total conta outra história")
abr, mai = pd.Timestamp("2025-04-01"), pd.Timestamp("2025-05-01")
sem_linha = serie["2025-05"].isna()
print(f"   maio contra abril de 2025: total {pct(total_mes[mai] / total_mes[abr] - 1)}; média por dia "
      f"completo {pct(media_mes[mai] / media_mes[abr] - 1)}")
print(f"      maio: {sem_linha.sum()} dias sem linha ({', '.join(dm(x) for x in sem_linha.index[sem_linha])}) "
      f"e loja fechada em {', '.join(dm(x) for x in fechada['2025-05'].index[fechada['2025-05']])}")
s0, s1 = pd.Timestamp("2025-05-05"), pd.Timestamp("2025-05-11")
n0 = serie[s0:s1].count()
seguinte = serie[s1 + pd.Timedelta(days=1):s1 + pd.Timedelta(days=7)]
print(f"   semana de {dm(s0)} a {s1.strftime('%d/%m/%Y')}: {br(semanas[s1], 0)} unidades em {n0} linhas, "
      f"{br(semanas[s1] / n0)} por linha")
print(f"      a semana seguinte, {dm(seguinte.index[0])} a {dm(seguinte.index[-1])}: {br(seguinte.sum(), 0)} em "
      f"{seguinte.count()} linhas, {br(seguinte.mean())} por linha")
jul, ago = pd.Timestamp("2025-07-01"), pd.Timestamp("2025-08-01")
peso = {m: fator.reindex(pd.date_range(m, m + pd.offsets.MonthEnd(0)).dayofweek).sum() for m in (jul, ago)}
cinco = [NOMES[i] for i in pd.date_range(ago, ago + pd.offsets.MonthEnd(0)).dayofweek[28:]]
print(f"   agosto contra julho de 2025: total {pct(total_mes[ago] / total_mes[jul] - 1)}; agosto tem cinco "
      f"{', '.join(cinco)}; só a mistura de dias da semana dá {pct(peso[ago] / peso[jul] - 1)}")
nov = pd.Timestamp("2025-11-01")
print(f"   novembro de 2025: média por dia completo {br(media_mes[nov])}; só dias comuns "
      f"{br(comum['2025-11'].mean())}; a Black Friday, 28/11, vendeu {br(serie['2025-11-28'], 0)}")

# 7. Um dia montado pelas partes
dia = pd.Timestamp("2025-06-14")
print(f"7. Um dia montado pelas partes: sábado, {dia.strftime('%d/%m/%Y')}")
print(f"   média centrada de 7 dias ({dm(dia - pd.Timedelta(days=3))} a {dm(dia + pd.Timedelta(days=3))}): "
      f"{br(m7[dia])}, o nível dessa semana, com a tendência e a onda do ano dentro")
nivel, peso_sab = round(m7[dia], 1), round(fator[5], 3)  # a conta com os números como aparecem na tela
conta = nivel * peso_sab
print(f"   peso do sábado: {br(peso_sab, 3)}; esperado: {br(nivel)} x {br(peso_sab, 3)} = {br(conta)}")
print(f"   vendeu {br(serie[dia], 0)}; o que sobra: {br(serie[dia] - conta)} unidades, {pct(serie[dia] / conta - 1)}")
