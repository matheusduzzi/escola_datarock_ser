"""Os dois cenários de chuva para uma semana de escala dos entregadores.

Rode de dentro da pasta da aula:
    python3 cenarios.py                                          # noite de 31/12/2025, semana de 05/01/2026
    python3 cenarios.py --origem 2025-12-01 --semana 2025-12-08  # uma semana que já passou

Na noite da origem, o modelo se ajusta com as entregas e a chuva até ali. Para cada dia da semana, ele
prevê dois cenários: seco e com chuva forte. A chance de chuva é a da previsão do tempo publicada
naquele dia; ela só vai até 14 dias. Cada entregador faz até 15 entregas por dia.
Se a semana já passou, a saída mostra também o que aconteceu.
"""
import argparse
import math

import pandas as pd

import exogenas as X

POR_ENTREGADOR = 15


def pessoas(entregas):
    return math.ceil(round(entregas, 6) / POR_ENTREGADOR)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origem", default="2025-12-31", help="noite em que a escala é montada (até 31/12/2025)")
    ap.add_argument("--semana", default="2026-01-05", help="primeiro dia da semana da escala")
    a = ap.parse_args()
    origem, inicio = pd.Timestamp(a.origem), pd.Timestamp(a.semana)
    if origem > X.FIM:
        raise SystemExit("o kit tem entregas e chuva até 31/12/2025: use uma origem até essa data")
    if inicio <= origem:
        raise SystemExit("a semana precisa começar depois da origem")
    semana = pd.date_range(inicio, periods=7)
    if semana[-1] > pd.Timestamp("2026-01-31"):
        raise SystemExit("o calendário da loja vai até 31/01/2026: escolha uma semana que termine até lá")
    d = X.carregar(ate=max(X.FIM, semana[-1]))
    prev = X.carregar_previsao()
    aj = X.ajustar(d, origem, com_chuva=True)
    passou = semana[-1] <= X.FIM

    print(f"Escala montada na noite de {origem:%d/%m/%Y}, semana de {semana[0]:%d/%m} a {semana[-1]:%d/%m/%Y}")
    print(f"  ajuste com as entregas e a chuva até {origem:%d/%m}; chuva forte multiplica as entregas por "
          f"{X.br(1 + X.efeito_chuva(aj), 2)}")
    print(f"  cada entregador faz até {POR_ENTREGADOR} entregas por dia\n")
    cab = f"  {'dia':10}{'calendário':16}{'chance':>7}{'seco':>7}{'chuva':>7}{'pela chance':>12}{'pessoas':>9}"
    print(cab + ("   aconteceu" if passou else ""))
    tot = {"seco": 0, "chuva": 0}
    for dia in semana:
        dsem = "seg ter qua qui sex sáb dom".split()[dia.dayofweek]
        evento = next((n for n in X.EVENTOS if d.at[dia, n]), "loja fechada" if d.at[dia, "fechada"] else "")
        evento = evento.replace("fim de semana da Black Friday", "fim de sem. BF").replace(
            "feriado com a loja aberta", "feriado")
        chance = X.previsao_da_noite(prev, origem, dia)
        seco, chuva = X.prever(aj, d, dia, 0.0), X.prever(aj, d, dia, 1.0)
        ps, pc = pessoas(seco), pessoas(chuva)
        tot["seco"] += ps
        tot["chuva"] += pc
        txt_chance = "  sem previsão" if chance != chance else f"{X.br(100 * chance, 0):>6}%"
        media = "" if chance != chance else X.br(X.prever(aj, d, dia, chance), 0)
        linha = (f"  {dsem} {dia:%d/%m}  {evento:16}{txt_chance:>7}{X.br(seco, 0):>7}{X.br(chuva, 0):>7}"
                 f"{media:>12}{f'{ps} ou {pc}':>9}")
        if passou:
            caiu = "chuva" if d.at[dia, "chuva"] == 1 else "seco"
            linha += f"   {X.br(d.at[dia, 'entregas'], 0):>3}, {caiu}"
        print(linha)
    print(f"\n  pessoas: entregadores no cenário seco ou no cenário com chuva; na semana, {tot['seco']} ou {tot['chuva']}")
    print("  pela chance: a média dos dois cenários, pesada pela chance de chuva da previsão")


if __name__ == "__main__":
    main()
