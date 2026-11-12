"""Separa a venda da loja física em nível, peso do dia da semana e sobra, com a data de corte escrita.

Rode de dentro da pasta dessa aula:  python3 decompor.py
Com outra noite de decisão:         python3 decompor.py --corte 2025-10-01
(também roda da raiz do kit: o programa acha dados/loja pelo próprio caminho)

1. O corte: o que existia na noite da decisão e o que só aparece depois.
2. A separação com tudo, até 31/12/2025: a foto da série inteira.
3. A mesma separação só com a venda até o corte, de dois jeitos: média centrada e média dos 7 dias até o dia.
4. O teste do corte: em cada noite, apaga a venda depois dela, calcula a parte de novo e vê se o valor mudou.
5. Quanto cada jeito parece errar em setembro e outubro de 2025, nos mesmos dias.
6. O nível na noite do corte, com e sem os dias de feriado e promoção.

O nível é a média de 7 dias seguidos, só com dias completos e a loja aberta (a coluna usavel da aula 03).
O peso do dia da semana sai só dos dias comuns, sem feriado e sem promoção, como na aula 02.
"""
import argparse
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
LOJA = AQUI.parent / "dados" / "loja"
INICIO, FIM = "2024-01-01", "2025-12-31"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def d(t):
    return f"{t:%d/%m/%Y}"


def carregar(loja=LOJA):
    """A venda no calendário: usavel (dia completo, loja aberta) e comum (usavel sem feriado e sem promoção)."""
    venda = pd.read_csv(loja / "venda_diaria.csv", parse_dates=["data"]).set_index("data")
    cal = pd.read_csv(loja / "calendario.csv", parse_dates=["data"], keep_default_na=False).set_index("data")
    dias = pd.date_range(INICIO, FIM, freq="D")
    serie = venda.reindex(dias)
    fechada = cal["loja_fechada"].reindex(dias) == 1
    hora = pd.to_datetime(serie["ultimo_registro"], format="%H:%M", errors="coerce")
    completo = (hora.dt.hour * 60 + hora.dt.minute >= 21 * 60 + 30) & (serie["unidades"] > 0) & ~fechada
    usavel = serie["unidades"].where(completo)
    evento = (cal["feriado"].reindex(dias) != "") | (cal["promocao"].reindex(dias) != "")
    comum = usavel.where(~evento)
    return usavel, comum


def ate(serie, noite):
    """A série como ela estava na noite: o que vem depois some."""
    return serie[:noite]


def nivel_centrado(usavel):
    """Média do dia com os 3 de antes e os 3 de depois. Fica vazia quando falta um dos 7."""
    return usavel.rolling(7, center=True, min_periods=7).mean()


def nivel_passado(usavel):
    """Média do dia com os 6 de antes. Fica vazia quando falta um dos 7."""
    return usavel.rolling(7, min_periods=7).mean()


def pesos(comum, nivel):
    """Média de (venda do dia comum / nível do dia) por dia da semana, com média 1 entre os 7 dias."""
    razao = (comum / nivel).dropna()
    p = razao.groupby(razao.index.dayofweek).mean()
    return p / p.mean()


def pesos_ate(usavel, comum, noite):
    """Os pesos calculados só com a venda até a noite, com o nível dos 7 dias até o dia."""
    return pesos(ate(comum, noite), nivel_passado(ate(usavel, noite)))


def nivel_sem_eventos(usavel, comum, noite, janela=14):
    """Dias comuns dos 14 dias até a noite, cada um dividido pelo peso do seu dia (pesos até a noite)."""
    trecho = comum[noite - pd.Timedelta(days=janela - 1):noite].dropna()
    if len(trecho) < 7:
        return float("nan")
    p = pesos_ate(usavel, comum, noite)
    return (trecho / p.reindex(trecho.index.dayofweek).to_numpy()).mean()


# As partes que o teste do corte confere. Cada uma recebe a venda (usavel, comum) e a noite,
# e devolve o número que ela daria para aquela noite.
PARTES = {
    "nível centrado": lambda u, c, o: nivel_centrado(u).get(o),
    "nível dos 7 dias até o dia": lambda u, c, o: nivel_passado(u).get(o),
    "nível sem eventos": nivel_sem_eventos,
    "peso do dia, série inteira": lambda u, c, o: pesos(c, nivel_centrado(u))[o.dayofweek],
    "peso do dia, até a noite": lambda u, c, o: pesos_ate(u, c, o)[o.dayofweek],
}


def testar_corte(parte, usavel, comum, noites):
    """Compara a parte calculada com a venda cortada na noite e com a venda inteira.

    Devolve (noites em que mudou, noites com algum número, primeiro caso que mudou ou None).
    """
    mudou, total, caso = 0, 0, None
    for o in noites:
        no_corte = parte(ate(usavel, o), ate(comum, o), o)
        com_tudo = parte(usavel, comum, o)
        if pd.isna(no_corte) and pd.isna(com_tudo):
            continue
        total += 1
        if pd.isna(no_corte) != pd.isna(com_tudo) or abs(no_corte - com_tudo) > 1e-9:
            mudou += 1
            caso = caso or (o, no_corte, com_tudo)
    return mudou, total, caso


def fmt(x, casas):
    return "vazio" if pd.isna(x) else br(x, casas)


def main():
    ap = argparse.ArgumentParser(description="Separa a venda em partes, com a data de corte escrita.")
    ap.add_argument("--corte", default="2025-12-01", help="noite da decisão, AAAA-MM-DD (padrão: 2025-12-01)")
    corte = pd.Timestamp(ap.parse_args().corte)
    if not pd.Timestamp("2024-03-01") <= corte <= pd.Timestamp(FIM):
        raise SystemExit(f"corte {d(corte)} fora da venda: use uma data de 01/03/2024 a 31/12/2025")
    usavel, comum = carregar()

    # 1. O corte
    print(f"1. O corte: noite de {d(corte)} {DIAS[corte.dayofweek]}, depois que a loja fecha")
    antes, depois = ate(usavel, corte), usavel[corte + pd.Timedelta(days=1):]
    print(f"   venda que existe nessa noite: de 01/01/2024 a {d(corte)}, {len(antes)} dias, "
          f"{antes.notna().sum()} completos com a loja aberta")
    if len(depois):
        print(f"   no arquivo, mas ainda não aconteceu nessa noite: {d(depois.index[0])} a {d(depois.index[-1])}, "
              f"{len(depois)} dias")
    else:
        print("   no arquivo, mas ainda não aconteceu nessa noite: nada; o corte é o último dia da venda")

    # 2. Com tudo
    nc_tudo = nivel_centrado(usavel)
    p_tudo = pesos(comum, nc_tudo)
    print("2. A separação com tudo, até 31/12/2025 (média centrada de 7 dias; pesos com todos os dias comuns)")
    print(f"   último dia com nível: {d(nc_tudo.last_valid_index())}")
    print("   peso do dia: " + "  ".join(f"{DIAS[i]} {br(p_tudo[i], 3)}" for i in range(7)))

    # 3. Só até o corte
    u_c, c_c = ate(usavel, corte), ate(comum, corte)
    nc_c, np_c = nivel_centrado(u_c), nivel_passado(u_c)
    p_cc, p_cp = pesos(c_c, nc_c), pesos(c_c, np_c)
    print(f"3. A mesma separação só com a venda até {d(corte)}")
    print(f"   média centrada: último dia com nível {d(nc_c.last_valid_index())}; "
          f"os dias depois dele precisam de venda que ainda não existe")
    print("      peso do dia: " + "  ".join(f"{DIAS[i]} {br(p_cc[i], 3)}" for i in range(7)))
    ult = np_c.last_valid_index()
    print(f"   média dos 7 dias até o dia: último dia com nível {d(ult)}, nível {br(np_c[ult])}")
    print("      peso do dia: " + "  ".join(f"{DIAS[i]} {br(p_cp[i], 3)}" for i in range(7)))
    dif = max((p_tudo - p_cc).abs().max(), (p_tudo - p_cp).abs().max())
    print(f"   maior diferença entre um peso com tudo e o mesmo peso até o corte: {br(dif, 3)}")

    # 4. O teste do corte
    noites = pd.date_range(corte - pd.Timedelta(days=91), corte, freq="D")
    print(f"4. O teste do corte: {len(noites)} noites, de {d(noites[0])} a {d(noites[-1])}")
    print("   em cada noite, a venda depois dela é apagada e a parte é calculada de novo")
    print("   parte                          noites em que mudou")
    casos = []
    for nome, parte in PARTES.items():
        mudou, total, caso = testar_corte(parte, usavel, comum, noites)
        print(f"   {nome:<30} {mudou:>3} de {total}")
        if caso:
            casas = 3 if nome.startswith("peso") else 1
            casos.append(f"   {nome}, noite de {d(caso[0])}: no corte {fmt(caso[1], casas)}; "
                         f"com tudo {fmt(caso[2], casas)}")
    if casos:
        print("   o primeiro caso de cada parte que mudou:")
        print("\n".join(casos))

    # 5. Quanto cada jeito parece errar
    print("5. Quanto cada jeito parece errar: 01/09 a 26/10/2025, os mesmos dias para todos")
    nomes = ["separação com tudo, no próprio dia", "repetir o dia da semana, 7 dias antes",
             "separação até a noite, 7 dias antes", "repetir o dia da semana, 35 dias antes",
             "separação até a noite, 35 dias antes"]
    linhas = []
    for t in pd.date_range("2025-09-01", "2025-10-26", freq="D"):
        if pd.isna(usavel.get(t)):
            continue
        linha = [usavel[t], nc_tudo.get(t) * p_tudo[t.dayofweek]]
        for h in (7, 35):
            o = t - pd.Timedelta(days=h)
            linha.append(usavel.get(o))
            linha.append(nivel_sem_eventos(usavel, comum, o) * pesos_ate(usavel, comum, o)[t.dayofweek])
        linhas.append(linha)
    tab = pd.DataFrame(linhas, columns=["real", nomes[0], nomes[1], nomes[2], nomes[3], nomes[4]]).dropna()
    print(f"   dias completos em que os cinco jeitos têm número: {len(tab)}")
    for nome in nomes:
        print(f"   {nome:<38} erro médio {br((tab[nome] - tab['real']).abs().mean()):>5} unidades por dia")
    print(f"   a separação com tudo erra {br(100 * (tab['real'] / tab[nomes[0]] - 1).abs().mean())}% por dia, "
          f"em média")

    # 6. O nível na noite do corte
    print(f"6. O nível na noite de {d(corte)}")
    semana = u_c[ult - pd.Timedelta(days=6):ult]
    eventos = [t for t in semana.index if pd.isna(comum.get(t))]
    extra = (", ".join(f"{t:%d/%m} ({br(usavel[t], 0)})" for t in eventos) if eventos else "nenhum")
    print(f"   média dos 7 dias até {d(ult)}: {br(np_c[ult])}; dias de feriado ou promoção dentro: {extra}")
    janela = c_c[corte - pd.Timedelta(days=13):corte].dropna()
    print(f"   nível sem eventos: os {len(janela)} dias comuns dos 14 dias até a noite, cada um dividido pelo peso "
          f"do seu dia: {fmt(nivel_sem_eventos(usavel, comum, corte), 1)}")


if __name__ == "__main__":
    main()
