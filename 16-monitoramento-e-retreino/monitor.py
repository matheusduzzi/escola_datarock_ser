"""Painel de monitoramento do modelo da escala, aula «Monitoramento e retreino» do curso Séries temporais.

Refaz as revisões de segunda-feira de 2026 como elas teriam sido: cada previsão usa só a venda que
tinha fechado na noite da origem, e cada revisão só vê o que existia naquela manhã.

    python3 monitor.py                          # painel da escala, previsão 7 dias antes
    python3 monitor.py --horizonte 14           # outra distância: 7, 14, 21 ou 28
    python3 monitor.py --revisao 2026-03-16     # o painel como estava numa segunda-feira
    python3 monitor.py --salvar previsoes.csv   # uma linha por dia, distância e jeito de ajustar
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo  # noqa: E402

PRIMEIRO_DIA = pd.Timestamp("2026-02-02")   # 1ª segunda com as quatro distâncias feitas em 2026
ULTIMO_DIA = pd.Timestamp("2026-04-26")
LEITURA = pd.Timestamp("2026-04-27")        # o arquivo é a leitura da manhã dessa segunda
EM_PRODUCAO = pd.Timestamp("2026-01-01")    # pesos ajustados na manhã de 01/01, venda até 31/12
OBRA_DESDE = pd.Timestamp("2026-03-09")
HORIZONTES = [7, 14, 21, 28]
VIES_INVESTIGAR = 0.05      # uma semana fechada com viés de 5,0% ou mais, para cima ou para baixo: investigar
VIES_ATUALIZAR = 0.10       # duas semanas fechadas seguidas com 10,0% ou mais: atualizar
SEMANAS_PARA_ATUALIZAR = 2
FECHAMENTO_LIMITE = 0.10
JEITOS = ["pesos de 31/12", "retreino todo dia 1º", "retreino com a obra"]
EM_USO = JEITOS[2]          # antes do sinal de atualizar, é igual ao retreino do dia 1º
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def pct(x, casas=1, sinal=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    s = br(100 * x, casas) + "%"
    return ("+" + s) if sinal and x > 0 else s


def dm(t):
    return t.strftime("%d/%m")


class Ajustes:
    """Guarda um ajuste por manhã, para não refazer a mesma conta."""

    def __init__(self, d):
        self.d, self.cache = d, {}

    def em(self, quando, obra=False):
        chave = (quando, obra)
        if chave not in self.cache:
            self.cache[chave] = modelo.ajustar(self.d, quando, OBRA_DESDE if obra else None)
        return self.cache[chave]

    def para_origem(self, jeito, origem, atualizado_em):
        """Os pesos que estavam valendo na noite da `origem`, para cada jeito de ajustar."""
        manha = origem + pd.Timedelta(days=1)
        if jeito == JEITOS[0]:
            return self.em(EM_PRODUCAO)
        dia1 = pd.Timestamp(manha.year, manha.month, 1)
        if jeito == JEITOS[1] or atualizado_em is None or manha < atualizado_em:
            return self.em(max(dia1, EM_PRODUCAO))
        # com a obra: ajustado na segunda da atualização e, depois, toda segunda
        segunda = manha - pd.Timedelta(days=manha.dayofweek)
        return self.em(max(segunda, atualizado_em), obra=True)


def prever_tudo(d, aj, atualizado_em):
    linhas = []
    dias = pd.date_range(PRIMEIRO_DIA, ULTIMO_DIA)
    for h in HORIZONTES:
        for dia in dias:
            if d.at[dia, "fechada"]:
                continue
            origem = dia - pd.Timedelta(days=h)
            fech_origem = modelo.fechado_ate(d, origem + pd.Timedelta(days=1))
            linha = {"dia": dia, "horizonte": h, "origem": origem, "noite": d.at[dia, "noite"],
                     "real": d.at[dia, "real"], "fechada_em": d.at[dia, "fechada_em"],
                     "regua": modelo.regua(fech_origem, dia, h)}
            for j in JEITOS:
                p, piso, teto = modelo.prever(aj.para_origem(j, origem, atualizado_em), d, origem, dia)
                linha[j], linha[j + " piso"], linha[j + " teto"] = p, piso, teto
            linhas.append(linha)
    return pd.DataFrame(linhas)


def semana_de(dia):
    return dia - pd.Timedelta(days=dia.dayofweek)


def painel_semanal(P, h, ate):
    """Uma linha por semana de segunda a domingo, lida em duas segundas-feiras.

    Na 1ª segunda depois da semana, os últimos dias ainda não fecharam: o painel só tem o número
    da noite. Na 2ª segunda, a semana inteira já fechou. O sinal só sai da leitura fechada.
    Nenhuma leitura passa de `ate`.
    """
    linhas = []
    p = P[P["horizonte"] == h]
    prev = EM_USO
    for seg in pd.date_range(PRIMEIRO_DIA, ULTIMO_DIA, freq="7D"):
        r1, r2 = seg + pd.Timedelta(days=7), seg + pd.Timedelta(days=14)
        if r1 > ate:
            break
        s = p[(p["dia"] >= seg) & (p["dia"] < r1)]
        na_r1 = s["fechada_em"].notna() & (s["fechada_em"] < r1)
        na_r2 = s["fechada_em"].notna() & (s["fechada_em"] < r2)
        fechou = r2 <= ate and bool(na_r2.all())
        f = s[na_r2] if fechou else s.iloc[0:0]
        linhas.append({
            "semana": seg, "r1": r1, "r2": r2, "dias": len(s), "fechados_r1": int(na_r1.sum()),
            "vies_noite": modelo.vies(s["noite"], s[prev]),
            "vies_r1": modelo.vies(s[na_r1]["real"], s[na_r1][prev]) if na_r1.any() else np.nan,
            "fechou": fechou,
            "vies_fechado": modelo.vies(f["real"], f[prev]) if fechou else np.nan,
            "wmape_modelo": modelo.wmape(f["real"], f[prev]) if fechou else np.nan,
            "wmape_regua": modelo.wmape(f["real"], f["regua"]) if fechou else np.nan,
            "fechamento_max": float((1 - f["noite"] / f["real"]).max()) if fechou else np.nan,
        })
    t = pd.DataFrame(linhas)
    sinais, seguidas = [], 0
    for _, r in t.iterrows():
        partes = []
        if not r["fechou"]:
            sinais.append(f"fecha na revisão de {dm(r['r2'])}")
            continue
        if r["fechamento_max"] > FECHAMENTO_LIMITE:
            partes.append("dado: fechamento fora do normal")
        no_painel = round(abs(r["vies_fechado"]) * 100, 1) / 100     # a regra usa o número que aparece
        forte = no_painel >= VIES_ATUALIZAR
        seguidas = seguidas + 1 if forte else 0
        if no_painel >= VIES_INVESTIGAR:
            partes.append("investigar")
        if seguidas >= SEMANAS_PARA_ATUALIZAR:
            partes.append(f"atualizar ({seguidas}ª seguida acima de {pct(VIES_ATUALIZAR, 0)})")
        sinais.append("; ".join(partes) or "nada")
    t["sinal"] = sinais
    return t


def primeira_atualizacao(P):
    """A segunda-feira em que a regra de 7 dias pede atualizar pela primeira vez."""
    t = painel_semanal(P, 7, LEITURA)
    hit = t[t["sinal"].str.contains("atualizar")]
    return None if hit.empty else hit["r2"].iloc[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizonte", type=int, default=7, choices=HORIZONTES)
    ap.add_argument("--revisao", default=str(LEITURA.date()),
                    help="uma segunda-feira de 09/02 a 27/04/2026 (aaaa-mm-dd)")
    ap.add_argument("--salvar", help="grava as previsões num CSV")
    a = ap.parse_args()
    revisao = pd.Timestamp(a.revisao)
    if revisao.dayofweek != 0 or not (pd.Timestamp("2026-02-09") <= revisao <= LEITURA):
        ap.error("a revisão é uma segunda-feira de 2026-02-09 a 2026-04-27")
    h = a.horizonte

    d = modelo.carregar()
    aj = Ajustes(d)
    # 1ª passada: pesos de 31/12 e retreino do dia 1º, para achar a segunda em que a regra pede atualizar
    P0 = prever_tudo(d, aj, None)
    atualizado_em = primeira_atualizacao(P0)
    P = prever_tudo(d, aj, atualizado_em)

    # o que a revisão enxerga: venda fechada só se fechou antes daquela manhã
    vista = P.copy()
    nao_fechou = ~(vista["fechada_em"].notna() & (vista["fechada_em"] < revisao))
    vista.loc[nao_fechou, "real"] = np.nan
    vista.loc[vista["dia"] >= revisao, "noite"] = np.nan
    vista = vista[vista["dia"] < revisao]

    print(f"Painel do modelo da escala na revisão de segunda {dm(revisao)}/2026, previsão feita {h} dias antes")
    print("  modelo em uso: calendário + AR(1), retreinado todo dia 1º com a venda fechada;")
    print("  depois do sinal de atualizar, com as colunas da obra e retreinado toda segunda")
    print("  dias previstos desde 02/02; cada previsão usa só a venda que tinha fechado na noite da origem")

    # 1. fechamento
    p7 = vista[vista["horizonte"] == h]
    fech = p7[p7["real"].notna()]
    gap = 1 - fech["noite"] / fech["real"]
    demora = (fech["fechada_em"] - fech["dia"]).dt.days
    print("\n1. O fechamento da venda: quanto o número da noite fica abaixo do número fechado")
    print(f"  dias de 02/02 em diante fechados até essa manhã: {len(fech)}; ainda abertos: {int(p7['real'].isna().sum())}")
    normais = gap[gap <= FECHAMENTO_LIMITE]
    print(f"  diferença mediana: {pct(float(gap.median()))}; tirando os dias acima de {pct(FECHAMENTO_LIMITE, 0)},"
          f" de {pct(float(normais.min()))} a {pct(float(normais.max()))}")
    print("  dias para fechar: " + ", ".join(f"{k} dia{'s' if k > 1 else ''} em {int((demora == k).sum())}"
                                         for k in sorted(demora.unique())))
    atrasados = p7[p7["real"].isna() & (p7["dia"] < revisao - pd.Timedelta(days=3))]
    if len(atrasados):
        print(f"  abertos há mais de 3 dias: " + ", ".join(f"{DIAS_SEMANA[x.dayofweek]} {dm(x)}" for x in atrasados["dia"])
              + " (dado: perguntar ao caixa)")
    grandes = fech[gap > FECHAMENTO_LIMITE]
    for _, r in grandes.iterrows():
        print(f"  acima de {pct(FECHAMENTO_LIMITE, 0)}: {DIAS_SEMANA[r['dia'].dayofweek]} {dm(r['dia'])} noite {r['noite']:.0f}, "
              f"fechada {r['real']:.0f} ({pct(1 - r['noite'] / r['real'], 0)} abaixo), fechou em {dm(r['fechada_em'])}")

    # 2. semana a semana
    t = painel_semanal(P, h, revisao)
    print("\n2. Semana a semana, lida em duas segundas. Viés positivo: a previsão passou da venda")
    print(f"  regra: semana fechada com viés de {pct(VIES_INVESTIGAR)} ou mais, para cima ou para baixo, pede investigar;")
    print(f"  {SEMANAS_PARA_ATUALIZAR} semanas fechadas seguidas com {pct(VIES_ATUALIZAR)} ou mais pedem atualizar")
    print("                 1ª segunda: viés da semana        2ª segunda: semana fechada")
    print("  semana         fechados  com a noite  dos fechados     viés  WMAPE modelo  WMAPE régua  sinal")
    for _, r in t.iterrows():
        fim = r["semana"] + pd.Timedelta(days=6)
        print(f"  {dm(r['semana'])} a {dm(fim)}  {r['fechados_r1']:>4}/{r['dias']}  {pct(r['vies_noite'], sinal=True):>11}"
              f"  {pct(r['vies_r1'], sinal=True):>12}  {pct(r['vies_fechado'], sinal=True):>7}  {pct(r['wmape_modelo']):>12}  {pct(r['wmape_regua']):>11}  {r['sinal']}")

    f = t[t["fechou"]]
    perde = (f["wmape_regua"] < f["wmape_modelo"]).tolist()
    maior, atual, fim_maior = 0, 0, None
    for i, x in enumerate(perde):
        atual = atual + 1 if x else 0
        if atual > maior:
            maior, fim_maior = atual, i
    if len(f):
        sem = "semana fechada" if len(f) == 1 else "semanas fechadas"
        print(f"  a régua errou menos que o modelo em {sum(perde)} de {len(f)} {sem}", end="")
        if maior >= 2:
            ini = f["semana"].iloc[fim_maior - maior + 1]
            quarta = f["r2"].iloc[fim_maior - maior + 4] if maior >= 4 else None
            print(f"; a maior sequência foi de {maior} semanas, a partir da semana de {dm(ini)}", end="")
            if quarta is not None:
                print(f"; a 4ª seguida apareceu na revisão de {dm(quarta)}", end="")
        print()

    # 3. erro por horizonte e por mês
    print("\n3. Erro por distância e por mês, só dias fechados: WMAPE do modelo em uso | WMAPE da régua")
    print("  mês        " + "".join(f"{f'{x} dias':>17}" for x in HORIZONTES) + f"   faixa de 80%, {h} dias")
    v = vista[vista["real"].notna()]
    for mes, nome in [(2, "fevereiro"), (3, "março"), (4, "abril")]:
        cel = []
        for x in HORIZONTES:
            s = v[(v["horizonte"] == x) & (v["dia"].dt.month == mes)]
            cel.append(f"{pct(modelo.wmape(s['real'], s[EM_USO]))} | {pct(modelo.wmape(s['real'], s['regua']))}"
                       if len(s) else "-")
        m = v[(v["horizonte"] == h) & (v["dia"].dt.month == mes)]
        dentro = ((m["real"] >= m[EM_USO + " piso"]) & (m["real"] <= m[EM_USO + " teto"])).mean() if len(m) else np.nan
        cob = f"{pct(dentro, 0)} de {len(m)} dias" if len(m) else "-"
        print(f"  {nome:<10} " + "".join(f"{c:>17}" for c in cel) + f"   {cob:>16}")

    # 4. mudança de distribuição
    print(f"\n4. Venda fechada ÷ previsão dos pesos de 31/12, que não viram a obra, previsão {h} dias antes")
    print("  mês          seg a sex   sábado   domingo")
    s = v[v["horizonte"] == h]
    for mes, nome in [(2, "fevereiro"), (3, "março"), (4, "abril")]:
        m = s[s["dia"].dt.month == mes]
        if m.empty:
            continue
        grupos = [m[m["dia"].dt.dayofweek < 5], m[m["dia"].dt.dayofweek == 5], m[m["dia"].dt.dayofweek == 6]]
        razoes = [br(g["real"].sum() / g[JEITOS[0]].sum(), 2) for g in grupos]
        print(f"  {nome:<11} {razoes[0]:>10} {razoes[1]:>8} {razoes[2]:>9}")
    antes = s[s["dia"] < OBRA_DESDE]
    depois = s[s["dia"] >= OBRA_DESDE]
    if len(depois):
        for nome, g in [("seg a sex", lambda x: x["dia"].dt.dayofweek < 5), ("sáb e dom", lambda x: x["dia"].dt.dayofweek >= 5)]:
            a1, d1 = antes[g(antes)], depois[g(depois)]
            if d1.empty:
                print(f"  {nome}: antes de 09/03 {br(a1['real'].sum() / a1[JEITOS[0]].sum(), 2)} em {len(a1)} dias;"
                      " de 09/03 em diante, nenhum dia fechado")
                continue
            print(f"  {nome}: antes de 09/03 {br(a1['real'].sum() / a1[JEITOS[0]].sum(), 2)} em {len(a1)} dias;"
                  f" de 09/03 em diante {br(d1['real'].sum() / d1[JEITOS[0]].sum(), 2)} em {len(d1)} dias")

    # 5. atualizar
    print("\n5. Três jeitos de manter os pesos, nos mesmos dias fechados")
    if atualizado_em is None or atualizado_em > revisao:
        print("  a regra ainda não pediu atualizar nessa revisão")
    else:
        aj_ob = aj.em(atualizado_em, obra=True)
        print(f"  a regra pediu atualizar na revisão de {dm(atualizado_em)}. Nessa manhã, com a venda fechada:")
        for nome in modelo.OBRA:
            print(f"    {nome}: {pct(modelo.efeito(aj_ob, nome), 0, sinal=True)}")
        dia1 = (atualizado_em + pd.offsets.MonthBegin(1)).normalize()
        if dia1 <= revisao:
            aj_1 = aj.em(dia1)
            print(f"    sem as colunas da obra, o retreino de {dm(dia1)} mexe na tendência por ano:"
                  f" {pct(modelo.efeito(aj.em(EM_PRODUCAO), 'tendência'), 1, sinal=True)} nos pesos de 31/12,"
                  f" {pct(modelo.efeito(aj_1, 'tendência'), 1, sinal=True)} no retreino")
        s5 = v[v["origem"] >= atualizado_em - pd.Timedelta(days=1)]
        if s5.empty:
            print("  ainda não fechou nenhum dia previsto depois da atualização: a comparação sai nas próximas revisões")
            s5 = None
    if atualizado_em is not None and atualizado_em <= revisao and s5 is not None:
        print(f"  previsões feitas da noite de {dm(atualizado_em - pd.Timedelta(days=1))} em diante,"
              f" para dias que fecharam até essa manhã (WMAPE | viés, e quantos dias)")
        print("  jeito                    " + "".join(f"{f'{x} dias':>22}" for x in HORIZONTES[:3]))
        for j in JEITOS + ["regua"]:
            cel = []
            for x in HORIZONTES[:3]:
                q = s5[s5["horizonte"] == x]
                cel.append(f"{pct(modelo.wmape(q['real'], q[j]))} | {pct(modelo.vies(q['real'], q[j]), sinal=True)} | {len(q)}")
            nome = "régua (4 semanas)" if j == "regua" else j
            print(f"  {nome:<24} " + "".join(f"{c:>22}" for c in cel))
        print(f"  a 28 dias, a primeira previsão feita depois da atualização é para {dm(atualizado_em + pd.Timedelta(days=27))},"
              " que ainda não fechou")

    if a.salvar:
        P.to_csv(a.salvar, index=False, float_format="%.2f", date_format="%Y-%m-%d")
        print(f"\ngravado: {a.salvar} ({len(P)} linhas)")


if __name__ == "__main__":
    main()
