"""As tabelas de features da aula «Features disponíveis na decisão» do curso Séries temporais.

Rode de dentro da pasta da aula:  python3 features.py
Lê a venda da loja física e o calendário em dados/loja, na raiz do kit. Monta duas tabelas:
a do Rafael, feita do jeito rápido, e a da aula, só com o que existe na noite da decisão.
A previsão de cada dia é feita 7 dias antes, depois que a loja fecha.
"""
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent.parent
LOJA = KIT / "dados" / "loja"
HORIZONTE = 7


def carregar():
    """A venda como está no arquivo (uma linha por dia com registro) e o calendário inteiro."""
    venda = pd.read_csv(LOJA / "venda_diaria.csv", parse_dates=["data"], dtype={"ultimo_registro": str})
    cal = pd.read_csv(LOJA / "calendario.csv", parse_dates=["data"], keep_default_na=False)
    return venda, cal


# ---------- o que vale para as duas tabelas ----------

def por_dia(venda, cal):
    """Põe a venda no calendário: um dia por linha, com o dia sem registro vazio.

    Retorna a venda de cada dia (real) e a venda que pode alimentar uma previsão (usavel):
    vazia no dia sem registro, no dia incompleto e no dia de loja fechada (aula 03).
    """
    dias = pd.DatetimeIndex(cal["data"])
    v = venda.set_index("data")
    real = v["unidades"].reindex(dias).astype(float)
    ultimo = v["ultimo_registro"].reindex(dias)
    incompleto = ultimo.notna() & (ultimo < "21:30")
    fechada = cal.set_index("data")["loja_fechada"] == 1
    usavel = real.where(~(real.isna() | incompleto | fechada))
    return real, usavel


def calendario(cal):
    """O que o calendário diz sobre o dia previsto. A loja sabe isso antes: está planejado."""
    c = cal.set_index("data")
    return pd.DataFrame({
        "dia_semana": c.index.dayofweek,             # 0 é segunda, 6 é domingo
        "feriado": (c["feriado"] != "").astype(int),
        "loja_fechada": c["loja_fechada"].astype(int),
        "promocao": (c["promocao"] != "").astype(int),
    }, index=c.index)


# ---------- a tabela do Rafael ----------

def tabela_do_rafael(venda, cal):
    """Do jeito rápido: tudo calculado de uma vez sobre os dois anos, sem pensar na noite da decisão."""
    real, usavel = por_dia(venda, cal)
    t = calendario(cal)
    cheia = usavel.interpolate()                    # tapa os buracos com a reta entre os vizinhos
    t["pedidos_dia"] = venda.set_index("data")["pedidos"].reindex(t.index).astype(float)
    t["lag1"] = cheia.shift(1)                      # a venda de ontem
    t["lag7"] = cheia.shift(7)                      # a venda de 7 dias antes, com os buracos tapados
    t["media_7"] = cheia.rolling(7, min_periods=1).mean()                    # inclui o próprio dia
    t["media_7_esq"] = cheia.rolling(7, min_periods=1, closed="left").mean()  # tira o próprio dia
    t["media_mes"] = cheia.groupby(t.index.to_period("M")).transform("mean")
    return t


# ---------- a tabela da aula ----------

def features(venda, cal):
    """Só o que existe na noite da decisão, 7 dias antes do dia previsto.

    Na linha do dia D, a venda mais nova que entra é a de D - 7. Por isso tudo começa com shift(7).
    """
    real, usavel = por_dia(venda, cal)
    t = calendario(cal)
    passado = usavel.shift(HORIZONTE)               # na linha D, a venda de D - 7
    t["lag7"] = passado
    t["lag14"] = usavel.shift(14)
    janela = passado.rolling(28, min_periods=1)     # os 28 dias que terminam em D - 7
    t["media_28"] = janela.mean()
    t["dias_28"] = janela.count()                   # quantos desses 28 dias serviram
    t["media_dsem_4"] = pd.concat([usavel.shift(7 * k) for k in (1, 2, 3, 4)], axis=1).mean(axis=1)
    return t


def no_corte(funcao, venda, cal, origem, horizonte=HORIZONTE):
    """A linha do dia previsto, calculada como na noite da origem: a venda depois dela não existe."""
    cortada = venda[venda["data"] <= origem]
    return funcao(cortada, cal).loc[origem + pd.Timedelta(days=horizonte)]


# ---------- uma regressão para ver o efeito ----------

def regressao(tabelas, real):
    """Ajusta uma regressão linear em 2024 e mede o erro em 2025, nos mesmos dias para todas as tabelas.

    A regressão acha um peso para cada coluna; a previsão é a soma das colunas vezes os pesos.
    A coluna dia_semana fica de fora: o número do dia não é uma quantidade, e a média do mesmo dia
    da semana já leva esse efeito.
    """
    ok = real.notna()
    for t in tabelas.values():
        ok &= t.drop(columns="dia_semana").notna().all(axis=1)
    treino = ok & (real.index < "2025-01-01")
    teste = ok & (real.index >= "2025-01-01") & (real.index <= "2025-12-31")
    saida = {}
    for nome, t in tabelas.items():
        x = t.drop(columns="dia_semana").to_numpy(float)
        x = np.column_stack([x, np.ones(len(x))])
        pesos = np.linalg.lstsq(x[treino.to_numpy()], real[treino].to_numpy(float), rcond=None)[0]
        prev = (x[teste.to_numpy()] * pesos).sum(axis=1)
        r = real[teste].to_numpy(float)
        saida[nome] = (np.mean(np.abs(r - prev)), np.sum(np.abs(r - prev)) / np.sum(r) * 100)
    return saida, int(treino.sum()), int(teste.sum())


# ---------- saída ----------

def br(x, casas=2):
    if pd.isna(x):
        return "vazio"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mostrar_linha(nome, linha):
    print(f"  {nome}")
    for coluna, valor in linha.items():
        casas = 0 if coluna in ("dia_semana", "feriado", "loja_fechada", "promocao", "dias_28") else 2
        print(f"    {coluna:14}{br(valor, casas):>10}")


def main():
    venda, cal = carregar()
    real, usavel = por_dia(venda, cal)
    rafael = tabela_do_rafael(venda, cal)
    aula = features(venda, cal)

    dia = pd.Timestamp("2025-11-28")
    origem = dia - pd.Timedelta(days=HORIZONTE)
    print(f"1. A linha da Black Friday, {dia:%d/%m/%Y}; a decisão é na noite de {origem:%d/%m/%Y}")
    print(f"  venda real do dia: {real[dia]:.0f} unidades")
    mostrar_linha("tabela do Rafael", rafael.loc[dia])
    mostrar_linha("tabela da aula", aula.loc[dia])
    print()

    dias_2025 = (real.index >= "2025-01-01") & (real.index <= "2025-12-31") & usavel.notna().to_numpy()
    print(f"2. Correlação de cada coluna com a venda, nos {dias_2025.sum()} dias de 2025 com venda completa")
    for nome, t in (("tabela do Rafael", rafael), ("tabela da aula", aula)):
        print(f"  {nome}")
        for coluna in t.columns.drop(["dia_semana", "feriado", "loja_fechada"]):
            print(f"    {coluna:14}{br(t.loc[dias_2025, coluna].corr(real[dias_2025]), 3):>8}")
    print()

    erros, n_treino, n_teste = regressao({"tabela do Rafael": rafael, "tabela da aula": aula}, real)
    print(f"3. Regressão linear ajustada em {n_treino} dias de 2024 e medida em {n_teste} dias de 2025, os mesmos para as duas")
    print(f"  {'':20}{'MAE':>8}{'WMAPE':>9}")
    for nome, (mae, wmape) in erros.items():
        print(f"  {nome:20}{br(mae):>8}{br(wmape, 1) + '%':>9}")
    print()

    linhas = venda.set_index("data")["unidades"]
    sete_linhas = pd.Series(linhas.index, index=linhas.index).shift(7)
    em_2025 = sete_linhas[sete_linhas.index >= "2025-01-01"]
    errados = em_2025[(em_2025.index - em_2025) != pd.Timedelta(days=7)]
    print("4. Linha não é dia: shift(7) direto no arquivo, que não tem linha nos dias sem registro")
    print(f"  dias de 2025 no arquivo: {len(em_2025)}; em {len(errados)} deles, 7 linhas atrás não é 7 dias atrás")
    for d, antes in list(errados.items())[:3]:
        print(f"    {d:%d/%m/%Y}: 7 linhas atrás é {antes:%d/%m/%Y}, {(d - antes).days} dias antes")


if __name__ == "__main__":
    main()
