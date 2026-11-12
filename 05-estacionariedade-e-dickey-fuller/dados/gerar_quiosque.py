"""Gera a venda diária do quiosque da Loja Exemplo no shopping, usada no exercício da aula 05.

Só biblioteca padrão (Python 3.9 ou mais novo). Rodar duas vezes dá o mesmo arquivo, byte a byte.

    python3 gerar_quiosque.py                 # escreve quiosque.csv nesta pasta
    python3 gerar_quiosque.py --saida /tmp/x  # escreve em outra pasta

Faça o exercício antes de ler o resto.

Como os dados nascem (o mecanismo):
- de 03/06/2024 a 30/11/2025, 546 dias no calendário;
- o nível é de 80 unidades por dia e não cresce;
- cada dia da semana multiplica o nível: sábado 1,45, domingo 1,30, segunda e terça 0,85;
- a partir de 01/07/2025, quando o shopping abriu a ala nova, todo dia vende 25% a mais;
- o ruído é multiplicativo e tem memória curta: o log do ruído de hoje é 0,4 vez o de ontem mais um
  sorteio normal com desvio de 0,07;
- em 25/12/2024 e 01/01/2025 o shopping fechou: a linha existe com 0 unidades e fechado = 1;
- em 4 dias o sistema caiu e o dia não tem linha.

Hipóteses que uma loja de verdade não garante: o degrau de 01/07/2025 é instantâneo e fica; o peso do
dia da semana é igual antes e depois dele; nenhuma tendência, promoção ou onda do ano.
"""
import argparse
import csv
import datetime as dt
import math
import pathlib
import random

SEMENTE = 505
INICIO = dt.date(2024, 6, 3)
FIM = dt.date(2025, 11, 30)
NIVEL = 80.0
DIA_DA_SEMANA = [0.85, 0.85, 0.90, 0.95, 1.10, 1.45, 1.30]  # segunda a domingo
ALA_NOVA = dt.date(2025, 7, 1)
DEGRAU = 1.25
MEMORIA = 0.4
RUIDO = 0.07
FECHADO = [dt.date(2024, 12, 25), dt.date(2025, 1, 1)]
SEM_LINHA = [dt.date(2024, 9, 10), dt.date(2025, 2, 18), dt.date(2025, 4, 3), dt.date(2025, 10, 14)]


def gerar(saida):
    rng = random.Random(SEMENTE)
    linhas, ruido, d = [], 0.0, INICIO
    while d <= FIM:
        ruido = MEMORIA * ruido + rng.gauss(0, RUIDO)
        media = NIVEL * DIA_DA_SEMANA[d.weekday()] * (DEGRAU if d >= ALA_NOVA else 1.0)
        if d in FECHADO:
            linhas.append([d.isoformat(), 0, 1])
        elif d not in SEM_LINHA:
            linhas.append([d.isoformat(), round(media * math.exp(ruido)), 0])
        d += dt.timedelta(days=1)
    with open(saida / "quiosque.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["data", "unidades", "fechado"])
        w.writerows(linhas)
    return len(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default=str(pathlib.Path(__file__).resolve().parent))
    saida = pathlib.Path(ap.parse_args().saida)
    saida.mkdir(parents=True, exist_ok=True)
    n = gerar(saida)
    print(f"quiosque={n} linhas dias_no_calendario={(FIM - INICIO).days + 1} sem_linha={len(SEM_LINHA)} "
          f"fechado={len(FECHADO)}")


if __name__ == "__main__":
    main()
