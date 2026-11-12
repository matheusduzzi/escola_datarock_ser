"""Põe a venda diária da loja física no calendário e diz, dia a dia, o que cada número é.

Rode de dentro da pasta dessa aula:  python3 auditar.py
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

1. O calendário: um dia por linha, de 01/01/2024 a 31/12/2025, e as linhas do arquivo.
2. A situação de cada dia: completo, sem registro, loja fechada, incompleto, e dois casos que
   pedem pergunta ao sistema (zero com a loja aberta e venda com a loja fechada).
3. Os dias que não são completos, um por um, com o mesmo dia da semana antes e depois.
4. A cobertura de cada mês: quantos dias a loja abriu e em quantos a venda veio inteira.
5. O que muda na conta quando o vazio vira zero.
6. O arquivo serie_auditada.csv, com a série no calendário e a situação de cada dia.

Dia completo: a loja abriu e o último pedido saiu às 21h30 ou depois (a loja vende das 10h às 22h).
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
LOJA = AQUI.parent / "dados" / "loja"
INICIO, FIM = "2024-01-01", "2025-12-31"
CORTE = 21 * 60 + 30  # 21h30, em minutos desde a meia-noite
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def minutos(hora):
    """'21:54' vira 1314. Vazio continua vazio."""
    h = pd.to_datetime(hora, format="%H:%M", errors="coerce")
    return h.dt.hour * 60 + h.dt.minute


def dia(t):
    return f"{t:%d/%m/%Y} {DIAS[t.dayofweek]}"


venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"])
cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False)

# 1. O calendário
print("1. O calendário")
dias = pd.date_range(INICIO, FIM, freq="D")
repetidas = int(venda["data"].duplicated().sum())
fora = int((~venda["data"].isin(dias)).sum())
print(f"   dias de {dias[0]:%d/%m/%Y} a {dias[-1]:%d/%m/%Y}: {len(dias)}")
print(f"   linhas no arquivo: {len(venda)}   datas repetidas: {repetidas}   datas fora do calendário: {fora}")
if repetidas or fora:
    estranhas = venda["data"][venda["data"].duplicated(keep=False) | ~venda["data"].isin(dias)]
    print("   pare aqui: um dia precisa ter no máximo uma linha, dentro do calendário. Veja com quem cuida do "
          "sistema: " + ", ".join(sorted({f"{t:%d/%m/%Y}" for t in estranhas})))
    raise SystemExit(1)
serie =venda.set_index("data").reindex(dias)
serie.index.name = "data"
serie = serie.join(cal.set_index("data")[["feriado", "loja_fechada"]])
tem_linha = serie["unidades"].notna()
print(f"   dias sem linha depois do reindex: {int((~tem_linha).sum())}")

# 2. A situação de cada dia
fechada = serie["loja_fechada"] == 1
fim_do_dia = minutos(serie["ultimo_registro"])
situacao = pd.Series("completo", index=dias)
situacao[~tem_linha & ~fechada] = "sem registro"
situacao[fechada] = "loja fechada"
situacao[fechada & tem_linha & (serie["unidades"] > 0)] = "venda com a loja fechada"
situacao[tem_linha & ~fechada & (serie["unidades"] == 0)] = "zero com a loja aberta"
# sem a hora do último pedido, nada mostra que o dia fechou: conta como incompleto
situacao[tem_linha & ~fechada & (serie["unidades"] > 0) & ~(fim_do_dia >= CORTE)] = "incompleto"
serie["situacao"] = situacao
serie["usavel"] = serie["unidades"].where(situacao == "completo")
ordem = ["completo", "sem registro", "loja fechada", "incompleto", "zero com a loja aberta",
         "venda com a loja fechada"]
print("2. A situação de cada dia")
conta = situacao.value_counts()
for nome in ordem:
    print(f"   {nome:<25} {int(conta.get(nome, 0)):>3}")
print(f"   {'total':<25} {len(situacao):>3}")
completos = fim_do_dia[situacao == "completo"]
print(f"   último pedido nos dias completos: de {int(completos.min()) // 60}h{int(completos.min()) % 60:02d} "
      f"a {int(completos.max()) // 60}h{int(completos.max()) % 60:02d}")

# 3. Os dias que não são completos
print("3. Os dias que não são completos (mesmo dia da semana: 7 dias antes e 7 dias depois)")
for t in serie.index[situacao != "completo"]:
    antes = serie["unidades"].get(t - pd.Timedelta(days=7), "fora")
    depois = serie["unidades"].get(t + pd.Timedelta(days=7), "fora")
    u = "vazio" if pd.isna(serie.at[t, "unidades"]) else br(serie.at[t, "unidades"], 0)
    hora = serie.at[t, "ultimo_registro"]
    hora = f"até {hora}" if isinstance(hora, str) else "sem hora"
    viz = "  ".join(x if isinstance(x, str) else "vazio" if pd.isna(x) else br(x, 0) for x in (antes, depois))
    print(f"   {dia(t)}  {situacao[t]:<13} unidades {u:>5}  {hora:<9}  vizinhos {viz}")
inc = serie.index[situacao == "incompleto"]
print(f"   os {len(inc)} incompletos caem em: {', '.join(sorted({DIAS[t.dayofweek] for t in inc}))}")

# 4. A cobertura de cada mês
print("4. A cobertura de cada mês: dias completos sobre os dias em que a loja abriu")
print("   mês     dias  linhas  abertos  completos  sem registro  incompletos  cobertura")
mes = pd.DataFrame({
    "dias": situacao.resample("MS").size(),
    "linhas": tem_linha.resample("MS").sum(),
    "abertos": (~fechada).resample("MS").sum(),
    "completos": (situacao == "completo").resample("MS").sum(),
    "sem_registro": (situacao == "sem registro").resample("MS").sum(),
    "incompletos": (situacao == "incompleto").resample("MS").sum(),
})
mes["cobertura"] = mes["completos"] / mes["abertos"]
mes[mes.columns[:-1]] = mes[mes.columns[:-1]].astype(int)
for t, m in mes.astype(object).iterrows():
    marca = "" if m["cobertura"] == 1 else "  <"
    print(f"   {MESES[t.month - 1]}/{t:%y}  {m['dias']:>4}  {m['linhas']:>6}  {m['abertos']:>7}  {m['completos']:>9}"
          f"  {m['sem_registro']:>12}  {m['incompletos']:>11}  {br(100 * m['cobertura']):>8}%{marca}")
for ano in (2024, 2025):
    a = mes[mes.index.year == ano].drop(columns="cobertura").sum()
    print(f"   {ano}: {a['completos']} dias completos em {a['abertos']} abertos, cobertura "
          f"{br(100 * a['completos'] / a['abertos'])}%; {12 - int((mes[mes.index.year == ano]['cobertura'] == 1).sum())}"
          f" meses abaixo de 100%")

# 5. O vazio que vira zero
print("5. O que muda quando o vazio vira zero, 2025")
z = serie["unidades"].fillna(0)["2025"]
crua = serie["unidades"]["2025"]
boa = serie["usavel"]["2025"]
ter = lambda x: x[x.index.dayofweek == 1]
print(f"   média por dia:  vazio vira zero {br(z.mean())} ({len(z)} dias)   só as linhas {br(crua.mean())} "
      f"({crua.count()})   só os completos {br(boa.mean())} ({boa.count()})")
print(f"   média da terça: vazio vira zero {br(ter(z).mean())} ({len(ter(z))} terças)   só as linhas "
      f"{br(ter(crua).mean())} ({ter(crua).count()})   só as completas {br(ter(boa).mean())} ({ter(boa).count()})")
for prevista in (pd.Timestamp("2025-05-13"), pd.Timestamp("2025-12-09")):
    base = prevista - pd.Timedelta(days=7)
    copia = serie["unidades"].fillna(0)[base]
    print(f"   repetir a semana anterior para {dia(prevista)}: copia {dia(base)} ({situacao[base]}) = "
          f"{br(copia, 0)}; vendeu {br(serie.at[prevista, 'unidades'], 0)}")

# 6. O arquivo
saida = AQUI / "serie_auditada.csv"
colunas = ["pedidos", "unidades", "ultimo_registro", "feriado", "loja_fechada", "situacao", "usavel"]
serie[colunas].to_csv(saida, date_format="%Y-%m-%d", float_format="%.0f")
print(f"6. {saida.name}: {len(serie)} linhas, uma por dia; colunas data, {', '.join(colunas)}")
