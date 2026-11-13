"""Transforma a previsão da venda em vendedores, com o custo de sobrar e o de faltar.

Aula «Demanda e equipe» do curso Séries temporais.

Rode de dentro da pasta da aula:
    python3 equipe.py                         # a escala de 12 a 18/01/2026, feita na noite de 31/12/2025
    python3 equipe.py --semana 2026-01-19     # outra semana de janeiro (segunda-feira de 05/01 a 19/01)
    python3 equipe.py --dia 2026-01-15        # a parte 2 com outro dia da semana
    python3 equipe.py --diaria 100 --falta 5  # outros custos
    python3 equipe.py --salvar teste.csv      # grava o teste no passado, uma linha por dia

A venda de cada dia sai do modelo da aula «Intervalos e cenários»: o centro e o desvio no log,
os mesmos que dão a faixa do dia. Com isso, para cada número de vendedores, a conta diz a chance
de faltar, quantas unidades devem faltar, quanta capacidade deve ficar parada e quanto isso custa.

O custo do erro é o da aula «MAE, RMSE, MAPE e WMAPE»: cada unidade que passa da capacidade custa
`--falta` (a venda perdida) e cada unidade de capacidade parada custa a diária dividida pela
capacidade de um vendedor. O sobreaviso soma o que ele custa a mais que um vendedor fixo.

O teste no passado usa os dias de 28/09 a 31/12/2025, previstos 14 dias antes, com o modelo
ajustado só com a venda até a noite da origem, como na aula «Intervalos e cenários».
"""
import argparse
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

import modelo as M

ORIGEM = pd.Timestamp("2025-12-31")
SEMANAS = [pd.Timestamp("2026-01-05"), pd.Timestamp("2026-01-12"), pd.Timestamp("2026-01-19")]
OFERTA_COLUNA = "fim de semana da Black Friday"
TESTE = (pd.Timestamp("2025-09-28"), pd.Timestamp("2025-12-31"))
HORIZONTE_TESTE = 14
N = NormalDist()
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def br(x, casas=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "vazio"
    if abs(x) < 0.5 * 10 ** -casas:
        x = 0.0                                  # sem "−0" na saída
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def pct(x):
    return f"{br(100 * x, 0)}%"


def nome_regra(nome, cfg):
    """O nome da regra na saída: «cobrir o alvo» mostra a porcentagem do alvo."""
    return f"cobrir {pct(cfg.alvo)}" if nome == "cobrir o alvo" else nome


def rotulo(dia):
    return f"{DIAS[dia.dayofweek]} {dia:%d/%m}"


# ---------- a conta de um dia ----------

def quantil(mu, desvio, q):
    """A venda que fica acima de uma fração q dos dias: exp(mu + z × desvio)."""
    return math.exp(mu + N.inv_cdf(q) * desvio)


def acima(mu, desvio, c):
    """Quanto a venda passa de c, em média: a parte da distribuição acima de c (o que falta)."""
    if c <= 0:
        return math.exp(mu + desvio ** 2 / 2) - c
    d2 = (mu - math.log(c)) / desvio
    return math.exp(mu + desvio ** 2 / 2) * N.cdf(d2 + desvio) - c * N.cdf(d2)


def conta(mu, desvio, vendedores, cfg):
    """Para um número de vendedores: chance de faltar, unidades que faltam e paradas, e o custo."""
    cap = vendedores * cfg.capacidade
    media = math.exp(mu + desvio ** 2 / 2)
    faltam = acima(mu, desvio, cap)
    parada = max(cap - media + faltam, 0.0)      # a conta pode dar −0,000…1 por arredondamento
    chance = 1 - N.cdf((math.log(cap) - mu) / desvio) if cap > 0 else 1.0
    c_falta, c_sobra = cfg.falta * faltam, cfg.sobra * parada
    return {"vendedores": vendedores, "capacidade": cap, "chance": chance, "faltam": faltam,
            "parada": parada, "c_falta": c_falta, "c_sobra": c_sobra, "total": c_falta + c_sobra}


def melhor(mu, desvio, cfg, extra=0.0, a_partir=0):
    """O número de vendedores de menor custo esperado. `extra` soma um custo por vendedor acima de `a_partir`."""
    teto = math.ceil(quantil(mu, desvio, 0.999) / cfg.capacidade) + 1
    opcoes = []
    for n in range(max(1, a_partir), teto + 1):
        c = conta(mu, desvio, n, cfg)
        opcoes.append((c["total"] + extra * (n - a_partir), n))
    return min(opcoes)[1]


def regras(mu, desvio, cfg):
    """As quatro regras para escalar: pela previsão, pelo teto do alvo, pelo menor custo e pelo teto de 90%."""
    cap = cfg.capacidade
    return {"pela previsão": math.ceil(math.exp(mu) / cap),
            "cobrir o alvo": math.ceil(quantil(mu, desvio, cfg.alvo) / cap),
            "menor custo": melhor(mu, desvio, cfg),
            "cobrir 90%": math.ceil(quantil(mu, desvio, 0.90) / cap)}


# ---------- as partes da saída ----------

def parte_regra(cfg):
    print("1. A regra da loja e o custo do erro")
    print(f"  um vendedor dá conta de {cfg.capacidade} unidades por dia; a diária é R$ {br(cfg.diaria)}")
    print(f"  sobrar: R$ {br(cfg.sobra, 2)} por unidade de capacidade parada (R$ {br(cfg.diaria)} ÷ {cfg.capacidade})")
    print(f"  faltar: R$ {br(cfg.falta, 2)} por unidade que passou da capacidade")
    print(f"  alvo se a capacidade fosse contínua: cobrir a venda em {br(cfg.falta, 2)} ÷ ({br(cfg.falta, 2)} + "
          f"{br(cfg.sobra, 2)}) = {pct(cfg.alvo)} dos dias")
    print(f"  sobreaviso: R$ {br(cfg.aviso)} por pessoa avisada; quem é chamado custa R$ {br(cfg.adicional)} "
          "a mais que um fixo")


def parte_um_dia(d, aj, dia, cfg):
    mu, s = M.distribuicao(aj, d, ORIGEM, dia)
    prev, _, faixa = M.prever(aj, d, ORIGEM, dia, 0.8)
    print(f"\n2. Um dia: {rotulo(dia)}/{dia:%Y}, previsto na noite de {ORIGEM:%d/%m/%Y} ({(dia - ORIGEM).days} dias antes)")
    print(f"  previsão {br(prev, 1)}; faixa do dia de 80%: {br(faixa[0], 1)} a {br(faixa[1], 1)}")
    print(f"  metade dos dias vende mais que {br(quantil(mu, s, 0.5), 1)}; 1 em 4, mais que {br(quantil(mu, s, 0.75), 1)}; "
          f"1 em 10, mais que {br(quantil(mu, s, 0.90), 1)}")
    print(f"  {'vendedores':>10}{'capacidade':>12}{'chance de faltar':>18}{'faltam':>9}{'parada':>9}"
          f"{'faltar R$':>11}{'sobrar R$':>11}{'total R$':>10}")
    m = melhor(mu, s, cfg)
    for n in range(max(1, m - 2), m + 3):
        c = conta(mu, s, n, cfg)
        marca = "  menor custo" if n == m else ""
        print(f"  {n:>10}{c['capacidade']:>12}{pct(c['chance']):>18}{br(c['faltam'], 1):>9}{br(c['parada'], 1):>9}"
              f"{br(c['c_falta']):>11}{br(c['c_sobra']):>11}{br(c['total']):>10}{marca}")
    print("  faltam e parada são unidades esperadas: a média do que falta e do que sobra nos dias possíveis")


def parte_semana(d, aj, semana, cfg):
    print(f"\n3. A escala de {semana[0]:%d/%m} a {semana[-1]:%d/%m/%Y}, cenário A (o calendário como está), "
          f"feita na noite de {ORIGEM:%d/%m}")
    print(f"  {'dia':10}{'previsão':>9}{'teto ' + pct(cfg.alvo):>10}{'pela previsão':>15}{nome_regra('cobrir o alvo', cfg):>12}{'menor custo':>13}"
          f"{'chance de faltar':>18}{'faltar R$':>11}{'sobrar R$':>11}{'total R$':>10}")
    soma = {"vend": 0, "c_falta": 0.0, "c_sobra": 0.0, "faltam": 0.0, "parada": 0.0}
    escala = {}
    for dia in semana:
        mu, s = M.distribuicao(aj, d, ORIGEM, dia)
        r = regras(mu, s, cfg)
        c = conta(mu, s, r["menor custo"], cfg)
        escala[dia] = r["menor custo"]
        for k in ("c_falta", "c_sobra", "faltam", "parada"):
            soma[k] += c[k]
        soma["vend"] += r["menor custo"]
        print(f"  {rotulo(dia):10}{br(math.exp(mu), 1):>9}{br(quantil(mu, s, cfg.alvo), 1):>10}"
              f"{r['pela previsão']:>15}{r['cobrir o alvo']:>12}{r['menor custo']:>13}{pct(c['chance']):>18}"
              f"{br(c['c_falta']):>11}{br(c['c_sobra']):>11}{br(c['total']):>10}")
    print(f"  semana pelo menor custo: {soma['vend']} diárias (R$ {br(soma['vend'] * cfg.diaria)}); "
          f"esperado: faltam {br(soma['faltam'])} unidades (R$ {br(soma['c_falta'])}), "
          f"param {br(soma['parada'])} (R$ {br(soma['c_sobra'])}); custo do erro R$ {br(soma['c_falta'] + soma['c_sobra'])}")
    for nome in ("pela previsão", "cobrir o alvo", "cobrir 90%"):
        tot, vend = 0.0, 0
        for dia in semana:
            mu, s = M.distribuicao(aj, d, ORIGEM, dia)
            n = regras(mu, s, cfg)[nome]
            vend += n
            tot += conta(mu, s, n, cfg)["total"]
        print(f"  semana pela regra «{nome_regra(nome, cfg)}»: {vend} diárias; custo do erro esperado R$ {br(tot)}")
    return escala


def parte_cenarios(d, aj, semana, cfg, oferta):
    fim = [dia for dia in semana if dia.dayofweek >= 5]
    efeito = M.efeito(aj, OFERTA_COLUNA)
    print(f"\n4. Cenário B: ofertas em {' e '.join(rotulo(x) for x in fim)}, decididas depois da escala")
    print(f"  o efeito suposto é o do fim de semana da Black Friday no histórico ({'+' if efeito >= 0 else ''}{pct(efeito)})")
    linhas = {"1. fixos pelo A, sem sobreaviso": [0.0, 0.0, 0, 0],
              "2. fixos pelo A + sobreaviso": [0.0, 0.0, 0, 0],
              "3. fixos pelo B": [0.0, 0.0, 0, 0]}
    print(f"  {'dia':10}{'previsão A':>11}{'previsão B':>11}{'fixos A':>9}{'fixos B':>9}{'sobreaviso':>12}")
    for dia in fim:
        mua, sa = M.distribuicao(aj, d, ORIGEM, dia)
        mub, sb = M.distribuicao(aj, d, ORIGEM, dia, mudar={OFERTA_COLUNA: 1} if oferta else None)
        na, nb = melhor(mua, sa, cfg), melhor(mub, sb, cfg)
        k = melhor(mub, sb, cfg, extra=cfg.aviso + cfg.adicional, a_partir=na) - na
        print(f"  {rotulo(dia):10}{br(math.exp(mua), 1):>11}{br(math.exp(mub), 1):>11}{na:>9}{nb:>9}{k:>12}")
        op = {"1. fixos pelo A, sem sobreaviso": (conta(mua, sa, na, cfg)["total"], conta(mub, sb, na, cfg)["total"], na, 0),
              "2. fixos pelo A + sobreaviso": (conta(mua, sa, na, cfg)["total"] + cfg.aviso * k,
                                               conta(mub, sb, na + k, cfg)["total"] + (cfg.aviso + cfg.adicional) * k, na, k),
              "3. fixos pelo B": (conta(mua, sa, nb, cfg)["total"], conta(mub, sb, nb, cfg)["total"], nb, 0)}
        for nome, (ca, cb, n, kk) in op.items():
            linhas[nome][0] += ca
            linhas[nome][1] += cb
            linhas[nome][2] += n
            linhas[nome][3] += kk
    print("  custo do erro esperado no fim de semana, somando o sobreaviso")
    print(f"  {'jeito de escalar':34}{'fixos':>7}{'sobreaviso':>12}{'se for A':>11}{'se for B':>11}")
    for nome, (ca, cb, n, k) in linhas.items():
        print(f"  {nome:34}{n:>7}{k:>12}{'R$ ' + br(ca):>11}{'R$ ' + br(cb):>11}")
    v = list(linhas.values())

    def empate(x, y):
        ganho_b, perda_a = x[1] - y[1], y[0] - x[0]
        if ganho_b <= 0:
            return None
        return perda_a / (perda_a + ganho_b)

    p12, p23 = empate(v[0], v[1]), empate(v[1], v[2])
    if p12 is not None:
        print(f"  o 2 fica mais barato que o 1 se a chance de oferta passar de {pct(p12)}")
    if p23 is not None:
        print(f"  o 3 fica mais barato que o 2 se a chance de oferta passar de {pct(p23)}")
    else:
        print("  o 3 nunca fica mais barato que o 2")


def parte_teste(d, cfg, salvar=None):
    ini, fim = TESTE
    cache, linhas = {}, []
    for dia in pd.date_range(ini, fim):
        if d.at[dia, "fechada"] or np.isnan(d.at[dia, "real"]) or d.at[dia, "incompleto"]:
            continue
        origem = dia - pd.Timedelta(days=HORIZONTE_TESTE)
        if origem not in cache:
            cache[origem] = M.ajustar(d, origem)
        mu, s = M.distribuicao(cache[origem], d, origem, dia)
        real = float(d.at[dia, "real"])
        linha = {"dia": dia, "origem": origem, "real": real, "previsao": math.exp(mu), "desvio_log": s}
        for nome, n in regras(mu, s, cfg).items():
            linha[nome] = n
            linha[f"esperado {nome}"] = conta(mu, s, n, cfg)["total"]
        linhas.append(linha)
    t = pd.DataFrame(linhas)
    print(f"\n5. O teste no passado: {len(t)} dias de {ini:%d/%m} a {fim:%d/%m/%Y}, previstos {HORIZONTE_TESTE} dias antes")
    print(f"  {'regra':15}{'diárias':>9}{'dias com falta':>16}{'faltaram':>10}{'parados':>9}"
          f"{'faltar R$':>11}{'sobrar R$':>11}{'total R$':>10}{'a conta esperava':>18}")
    for nome in ("pela previsão", "cobrir o alvo", "menor custo", "cobrir 90%"):
        cap = t[nome] * cfg.capacidade
        falt = np.maximum(t["real"] - cap, 0)
        par = np.maximum(cap - t["real"], 0)
        print(f"  {nome_regra(nome, cfg):15}{int(t[nome].sum()):>9}{str(int((falt > 0).sum())) + ' de ' + str(len(t)):>16}"
              f"{br(falt.sum()):>10}{br(par.sum()):>9}{br(cfg.falta * falt.sum()):>11}{br(cfg.sobra * par.sum()):>11}"
              f"{br(cfg.falta * falt.sum() + cfg.sobra * par.sum()):>10}{'R$ ' + br(t['esperado ' + nome].sum()):>18}")
    print("  dias de loja fechada e dias sem venda completa ficam fora, como na aula «Intervalos e cenários»")

    def custo_dia(nome):
        cap = t[nome] * cfg.capacidade
        return cfg.falta * np.maximum(t["real"] - cap, 0) + cfg.sobra * np.maximum(cap - t["real"], 0)

    base = custo_dia("menor custo")
    print("  menor custo menos cada regra, dia a dia, com a folga do acaso (2 erros-padrão da soma)")
    for nome in ("pela previsão", "cobrir o alvo", "cobrir 90%"):
        dif = base - custo_dia(nome)
        k = int((t["menor custo"] != t[nome]).sum())
        folga = 2 * float(dif.std(ddof=1)) * math.sqrt(len(dif)) if k > 1 else 0.0
        print(f"    contra «{nome_regra(nome, cfg)}»: R$ {br(float(dif.sum()))} ± {br(folga)}, "
              f"em {k} dias com escala diferente")
    if salvar:
        t.to_csv(salvar, index=False, float_format="%.4f")
        print(f"\ngravado: {salvar}")


def main():
    p = argparse.ArgumentParser(description="Vendedores por dia a partir da distribuição da venda.")
    p.add_argument("--semana", default="2026-01-12", help="segunda-feira da semana: 2026-01-05, 2026-01-12 ou 2026-01-19")
    p.add_argument("--dia", help="o dia da parte 2, dentro da semana (padrão: a segunda-feira)")
    p.add_argument("--capacidade", type=int, default=40, help="unidades que um vendedor atende num dia")
    p.add_argument("--diaria", type=float, default=80.0, help="diária de um vendedor fixo, em reais")
    p.add_argument("--falta", type=float, default=6.0, help="custo de cada unidade que passa da capacidade")
    p.add_argument("--aviso", type=float, default=20.0, help="custo de deixar uma pessoa de sobreaviso")
    p.add_argument("--adicional", type=float, default=30.0, help="quanto quem é chamado custa a mais que um fixo")
    p.add_argument("--salvar", help="grava o teste no passado em CSV")
    a = p.parse_args()
    semana0 = pd.Timestamp(a.semana)
    if semana0 not in SEMANAS:
        p.error("--semana aceita 2026-01-05, 2026-01-12 ou 2026-01-19 (até 28 dias depois de 31/12)")
    if a.capacidade <= 0 or a.diaria <= 0 or a.falta <= 0 or a.aviso < 0 or a.adicional < 0:
        p.error("capacidade, diária e falta precisam ser maiores que zero; aviso e adicional, zero ou mais")
    a.sobra = a.diaria / a.capacidade
    a.alvo = a.falta / (a.falta + a.sobra)

    d = M.carregar()
    aj = M.ajustar(d, ORIGEM)
    semana = list(pd.date_range(semana0, semana0 + pd.Timedelta(days=6)))
    dia = pd.Timestamp(a.dia) if a.dia else semana[0]
    if dia not in semana:
        p.error(f"--dia precisa estar na semana de {semana[0]:%Y-%m-%d} a {semana[-1]:%Y-%m-%d}")
    parte_regra(a)
    parte_um_dia(d, aj, dia, a)
    parte_semana(d, aj, semana, a)
    parte_cenarios(d, aj, semana, a, oferta=True)
    parte_teste(d, a, a.salvar)


if __name__ == "__main__":
    main()
