"""Mede o que a decisão sobre Prophet e redes neurais precisa saber, no ajuste da semana (previsão feita 7 dias antes).

Aula «Prophet e redes neurais» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 criterio.py

Não roda Prophet nem rede neural. Mede, com a venda da loja, as quatro coisas que a decisão
pede: quanto histórico existe, quantos números cada tipo de modelo estima com ele, quanto erro
ainda sobra para um modelo novo tirar e quanto custa testar. As previsões são as da aula
«Modelo contra baseline»: origens de 31/08 a 24/12/2025, cada ajuste só com a venda até a
noite da origem, e os mesmos dias para todas as versões.
"""
import math
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

import modelo as M

PRIMEIRA_ORIGEM = pd.Timestamp("2025-08-31")
ULTIMA_ORIGEM = pd.Timestamp("2025-12-24")
HORIZONTE = 7
UM_ANO, MEIO_ANO = pd.Timedelta(days=365), pd.Timedelta(days=180)

# Números que cada tipo de modelo estima, pela documentação de cada biblioteca (fontes.md da aula).
# Prophet com os padrões: tendência (k e m), 25 pontos de mudança, onda da semana de ordem 3
# (6 pesos), um peso por evento e o desvio do erro. A onda do ano tem ordem 10 (20 pesos) e só
# liga sozinha com 730 dias ou mais do primeiro ao último dia do histórico.
PROPHET_PONTOS_DE_MUDANCA = 25
PROPHET_ORDEM_SEMANA, PROPHET_ORDEM_ANO = 3, 10
PROPHET_DIAS_ONDA_DO_ANO = 730
PROPHET_GRADE = 4 * 4            # a grade de ajuste do exemplo da documentação


def numeros_prophet(eventos, onda_do_ano):
    return 2 + PROPHET_PONTOS_DE_MUDANCA + 2 * PROPHET_ORDEM_SEMANA + eventos + 1 + (
        2 * PROPHET_ORDEM_ANO if onda_do_ano else 0)


def numeros_rede_densa(entradas, neuronios):
    """Uma camada escondida: pesos e viés de cada neurônio, mais a saída."""
    return (entradas + 1) * neuronios + neuronios + 1


def numeros_lstm(neuronios, entradas=1):
    """Uma camada LSTM do PyTorch (4 portas, dois vieses por porta) e uma saída linear."""
    return 4 * neuronios * (entradas + neuronios + 2) + neuronios + 1


REDE_INICIOS = 5                 # cada rede treinada 5 vezes, com pontos de partida diferentes


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def sinal(x, casas=1):
    return ("+" if x >= 0 else "−") + br(abs(x), casas)


def prever_versao(d, ordem, janela):
    """Uma linha por dia previsto, com a previsão de uma versão do modelo do ajuste da semana."""
    linhas = []
    for dia in pd.date_range(PRIMEIRA_ORIGEM + pd.Timedelta(days=HORIZONTE), ULTIMA_ORIGEM + pd.Timedelta(days=HORIZONTE)):
        origem = dia - pd.Timedelta(days=HORIZONTE)
        aj = M.ajustar(d, origem, desde=origem - janela if janela is not None else None, ordem=ordem)
        linhas.append({"dia": dia, "origem": origem, "real": d.at[dia, "real"],
                       "avaliado": bool(not np.isnan(d.at[dia, "real"]) and not d.at[dia, "incompleto"]),
                       "prev": M.prever(aj, d, origem, dia), "numeros": aj["numeros"]})
    return pd.DataFrame(linhas)


def autocorrelacao(s, k):
    """Correlação do resíduo com ele mesmo k dias antes, só nos pares de dias que existem."""
    s = s.reindex(pd.date_range(s.index[0], s.index[-1]))
    par = pd.concat([s, s.shift(k)], axis=1).dropna().to_numpy()
    return float(np.corrcoef(par[:, 0], par[:, 1])[0, 1])


def main():
    d = M.carregar()
    print(f"Previsões feitas {HORIZONTE} dias antes, origens de {PRIMEIRA_ORIGEM:%d/%m} a {ULTIMA_ORIGEM:%d/%m/%Y}")
    print("  em cada origem, cada versão se ajusta só com a venda até aquela noite\n")

    # 1. Volume
    print("1. Quanto histórico a loja tem")
    for rotulo, origem in (("primeira origem", PRIMEIRA_ORIGEM), ("última origem", ULTIMA_ORIGEM)):
        h = d.loc[:origem, "usavel"].dropna()
        corridos = (h.index[-1] - h.index[0]).days
        print(f"  {rotulo}, {origem:%d/%m/%Y}: {len(h)} dias com venda que serve; do primeiro ao último, "
              f"{corridos} dias corridos ({br(corridos / M.ANO, 2)} anos)")
    print(f"  o Prophet só liga a onda do ano sozinho com {PROPHET_DIAS_ONDA_DO_ANO} dias corridos ou mais")
    print("  uma série só: a venda total da loja física")
    h = d.loc[:PRIMEIRA_ORIGEM]
    h = h[h["usavel"].notna()]
    print(f"  dias de cada evento no histórico da primeira origem: " + ", ".join(
        f"{nome} {int(h[nome].sum())}" for nome in M.EVENTOS) + "\n")

    # 2. Quantos números cada um estima
    aj0 = M.ajustar(d, PRIMEIRA_ORIGEM)
    aj10 = M.ajustar(d, PRIMEIRA_ORIGEM, ordem=10)
    dias0 = aj0["dias"]
    eventos = sum(1 for nome in M.EVENTOS if nome in aj0["nomes"])
    print(f"2. Quantos números cada modelo estima com os {dias0} dias da primeira origem")
    print(f"  {'':52}{'números':>9}{'dias por número':>17}")
    tipos = [("calendário + AR(1), o modelo do ajuste da semana", aj0["numeros"]),
             ("calendário com a onda do ano de ordem 10", aj10["numeros"]),
             ("Prophet com os padrões (sem a onda do ano)", numeros_prophet(eventos, False)),
             ("Prophet com a onda do ano ligada", numeros_prophet(eventos, True)),
             ("rede densa: 28 dias de entrada, 16 neurônios", numeros_rede_densa(28, 16)),
             ("LSTM de uma camada com 64 neurônios", numeros_lstm(64))]
    for nome, n in tipos:
        por = dias0 / n
        print(f"  {nome:52}{br(n, 0):>9}{br(por, 1 if por < 10 else 0) if por >= 0.1 else br(por, 3):>17}")
    print("  o Prophet e as redes encolhem os pesos durante o ajuste; a conta mostra o tamanho do modelo,\n"
          "  não quanto ele vai errar\n")

    # 3. Mais números ou menos histórico
    t0 = time.perf_counter()
    base = prever_versao(d, 2, None)
    segundos = time.perf_counter() - t0
    versoes = [("calendário + AR(1)", "tudo", base),
               ("onda do ano de ordem 10", "tudo", prever_versao(d, 10, None)),
               ("calendário + AR(1)", "último ano", prever_versao(d, 2, UM_ANO)),
               ("onda do ano de ordem 10", "último ano", prever_versao(d, 10, UM_ANO)),
               ("calendário + AR(1)", "180 dias", prever_versao(d, 2, MEIO_ANO))]
    ok = base["avaliado"]
    for _, _, p in versoes:
        ok &= p["avaliado"] & p["prev"].notna()
    dias = base.loc[ok, "dia"]
    semana = ((dias - dias.iloc[0]).dt.days // 7).to_numpy()
    real = base.loc[ok, "real"].to_numpy()
    erro_base = np.abs(real - base.loc[ok, "prev"].to_numpy())
    print(f"3. O modelo do ajuste da semana com mais números ou com menos histórico, nos mesmos {ok.sum()} dias")
    print(f"  {'':26}{'histórico':>12}{'números':>9}{'WMAPE':>8}{'custo (R$)':>12}{'semanas melhor':>16}{'erro a menos por dia':>23}")
    for nome, janela, p in versoes:
        f = p.loc[ok, "prev"].to_numpy()
        n = p.loc[ok, "numeros"]
        nums = br(n.iloc[0], 0) if n.min() == n.max() else f"{br(n.min(), 0)} a {br(n.max(), 0)}"
        linha = f"  {nome:26}{janela:>12}{nums:>9}{br(M.wmape(real, f)) + '%':>8}{br(M.custo(real, f), 0):>12}"
        if p is base:
            print(linha + f"{'referência':>16}{'':>23}")
            continue
        ganho = pd.Series(erro_base - np.abs(real - f))          # positivo: a versão errou menos
        por_semana = ganho.groupby(semana)
        medias = por_semana.mean()
        faixa = 2 * medias.std(ddof=1) / math.sqrt(len(medias))
        venceu = int((por_semana.sum() > 0).sum())
        print(linha + f"{f'{venceu} de {len(medias)}':>16}{sinal(ganho.mean(), 2) + ' ± ' + br(faixa, 2):>23}")
    print("  erro a menos por dia: contra o modelo do ajuste da semana, média e ± 2 erros-padrão das médias semanais\n")

    # 4. O que sobra para um modelo novo tirar
    r = aj0["residuo"]
    n = len(r)
    limite = 2 / math.sqrt(n)
    acf = {k: autocorrelacao(r, k) for k in range(1, 29)}
    sigma = aj0["desvio_choque"]
    piso = (2 * NormalDist().cdf(sigma) - 1) * 100          # tamanho médio de um choque normal, uns 0,8 desvio
    erro_ajuste = M.wmape(real, base.loc[ok, "prev"].to_numpy())
    print(f"4. O que sobra para um modelo novo tirar")
    print(f"  resíduo do modelo do ajuste da semana, ajustado até {PRIMEIRA_ORIGEM:%d/%m/%Y}: correlação com o resíduo de k dias antes")
    print("   " + "  ".join(f"k={k}: {sinal(acf[k], 2)}" for k in (1, 2, 3, 7, 14, 21, 28)))
    fora = [k for k in acf if abs(acf[k]) > limite]
    print(f"  com {n} dias, até ± {br(limite, 2)} cabe no acaso; de 28 correlações, {len(fora)} " + ("passou" if len(fora) == 1 else "passaram") + " disso: "
          + ", ".join(f"k={k} ({sinal(acf[k], 2)})" for k in fora))
    print(f"  de 28 correlações sem nada para achar, umas 1 ou 2 passam do limite só pelo acaso (5% de 28)")
    print(f"  desvio do choque de cada dia, no log: {br(sigma, 3)}")
    print(f"  erro médio que fica se o resto for só choque: perto de {br(piso)}% da venda")
    mae = float(np.mean(erro_base))
    print(f"  erro do modelo do ajuste da semana nos {ok.sum()} dias: {br(erro_ajuste)}%, {br(mae, 2)} unidades por dia\n")

    # 5. Quanto vale ganhar
    c = M.custo(real, base.loc[ok, "prev"].to_numpy())
    print(f"5. Quanto vale ganhar, se um modelo novo encolher todos os erros na mesma proporção")
    print(f"  custo do erro do modelo do ajuste da semana nos {ok.sum()} dias: R$ {br(c, 0)}")
    for rotulo, fator in ((f"até o piso, de {br(erro_ajuste)}% para {br(piso)}%", piso / erro_ajuste),
                          ("10% a menos de erro", 0.9)):
        economia = c * (1 - fator)
        print(f"  {rotulo:38} R$ {br(economia, 0)} nesses dias, uns R$ {br(economia * 365 / ok.sum(), 0)} por ano; "
              f"{br(mae * (1 - fator), 2)} unidade a menos de erro por dia")
    print()

    # 6. Custo de testar
    origens = len(base)
    print(f"6. Quantos ajustes o teste pede, com as mesmas {origens} origens")
    print(f"  {'':52}{'ajustes':>9}")
    for nome, n in (("calendário + AR(1), uma vez por origem", origens),
                    (f"Prophet com a grade da documentação ({PROPHET_GRADE} combinações)", origens * PROPHET_GRADE),
                    (f"rede treinada {REDE_INICIOS} vezes por origem", origens * REDE_INICIOS),
                    (f"rede com {PROPHET_GRADE} combinações, {REDE_INICIOS} vezes cada", origens * PROPHET_GRADE * REDE_INICIOS)):
        print(f"  {nome:52}{br(n, 0):>9}")
    print(f"  os {origens} ajustes do modelo do ajuste da semana levaram {br(segundos)} s nesta máquina")


if __name__ == "__main__":
    main()
