"""Gera a venda diária e o calendário da Loja Exemplo usados no curso Séries temporais.

Só biblioteca padrão (Python 3.9 ou mais novo). Rodar duas vezes dá os mesmos arquivos, byte a byte.

    python3 gerar.py                 # escreve nesta pasta
    python3 gerar.py --saida /tmp/x  # escreve em outra pasta

Como os dados nascem (o mecanismo):
- dois anos de loja, de 01/01/2024 a 31/12/2025, 731 dias no calendário;
- o nível começa em 120 unidades por dia e sobe 15% por ano, em linha reta (tendência);
- cada dia da semana multiplica o nível: sábado vende 1,45 vez, domingo 0,70 vez (sazonalidade semanal);
- uma onda anual sobe no fim do ano e desce em fevereiro (sazonalidade anual), e de 15 a 24 de
  dezembro a venda ganha mais 35% (Natal);
- a Black Friday multiplica o dia por 2,6 e o sábado e o domingo seguintes por 1,4;
- feriado com a loja aberta vende 80% do normal; em 1º de janeiro, 1º de maio e 25 de dezembro a
  loja fecha e o dia entra com 0 pedidos e 0 unidades;
- sobre a conta, um ruído multiplicativo normal com desvio de 8%, sorteado dia a dia, independente;
- em 9 dias o sistema caiu e o dia não tem linha no arquivo;
- em 6 dias o sistema parou de gravar no meio do dia: a linha existe, mas só tem as vendas até a
  hora em `ultimo_registro` (num dia completo, o último pedido sai entre 21h30 e 21h59).

Hipóteses que o gerador assume e uma loja de verdade não garante: tendência em linha reta, efeito
do dia da semana igual o ano todo, ruído sem memória de um dia para o outro e nenhuma ruptura
(loja nova na rua, troca de sistema, mudança de preço).

calendario.csv vai até 31/01/2026, um mês além das vendas: são as datas que a loja já conhece
antes de prever (feriados, dias fechados e promoções planejadas).
"""
import argparse
import csv
import datetime as dt
import math
import pathlib
import random

SEMENTE = 2024
INICIO = dt.date(2024, 1, 1)
FIM = dt.date(2025, 12, 31)
FIM_CALENDARIO = dt.date(2026, 1, 31)

NIVEL_INICIAL = 120.0
CRESCIMENTO_ANO = 0.15
DIA_DA_SEMANA = [0.92, 0.90, 0.95, 1.00, 1.12, 1.45, 0.70]  # segunda a domingo
ONDA_ANUAL = 0.12      # amplitude da onda anual
PICO_ANUAL = 350       # dia do ano do pico da onda (meados de dezembro)
NATAL = 1.35
BLACK_FRIDAY = 2.6
FIM_DE_SEMANA_BF = 1.4
FERIADO_ABERTO = 0.80
RUIDO = 0.08
UNIDADES_POR_PEDIDO = 1.55

FERIADOS = {
    dt.date(2024, 1, 1): "Confraternização Universal",
    dt.date(2024, 2, 12): "Carnaval",
    dt.date(2024, 2, 13): "Carnaval",
    dt.date(2024, 3, 29): "Sexta-feira Santa",
    dt.date(2024, 4, 21): "Tiradentes",
    dt.date(2024, 5, 1): "Dia do Trabalho",
    dt.date(2024, 5, 30): "Corpus Christi",
    dt.date(2024, 9, 7): "Independência",
    dt.date(2024, 10, 12): "Nossa Senhora Aparecida",
    dt.date(2024, 11, 2): "Finados",
    dt.date(2024, 11, 15): "Proclamação da República",
    dt.date(2024, 11, 20): "Consciência Negra",
    dt.date(2024, 12, 25): "Natal",
    dt.date(2025, 1, 1): "Confraternização Universal",
    dt.date(2025, 3, 3): "Carnaval",
    dt.date(2025, 3, 4): "Carnaval",
    dt.date(2025, 4, 18): "Sexta-feira Santa",
    dt.date(2025, 4, 21): "Tiradentes",
    dt.date(2025, 5, 1): "Dia do Trabalho",
    dt.date(2025, 6, 19): "Corpus Christi",
    dt.date(2025, 9, 7): "Independência",
    dt.date(2025, 10, 12): "Nossa Senhora Aparecida",
    dt.date(2025, 11, 2): "Finados",
    dt.date(2025, 11, 15): "Proclamação da República",
    dt.date(2025, 11, 20): "Consciência Negra",
    dt.date(2025, 12, 25): "Natal",
    dt.date(2026, 1, 1): "Confraternização Universal",
}
FECHADA = {(1, 1), (5, 1), (12, 25)}
BLACK_FRIDAYS = [dt.date(2024, 11, 29), dt.date(2025, 11, 28)]

SEM_REGISTRO = [
    dt.date(2024, 3, 12), dt.date(2024, 3, 13), dt.date(2024, 7, 8), dt.date(2024, 10, 21),
    dt.date(2025, 2, 17), dt.date(2025, 5, 6), dt.date(2025, 5, 7), dt.date(2025, 5, 8),
    dt.date(2025, 9, 15),
]
# dia incompleto: hora em que o sistema parou de gravar
INCOMPLETOS = {
    dt.date(2024, 4, 16): "13:05",
    dt.date(2024, 8, 27): "15:40",
    dt.date(2025, 3, 25): "12:20",
    dt.date(2025, 6, 10): "16:45",
    dt.date(2025, 10, 7): "14:10",
    dt.date(2025, 12, 2): "11:50",
}
ABRE, FECHA = 10 * 60, 22 * 60  # a loja vende das 10h às 22h


def datas(inicio, fim):
    d = inicio
    while d <= fim:
        yield d
        d += dt.timedelta(days=1)


def promocao(d):
    for bf in BLACK_FRIDAYS:
        if d == bf:
            return "Black Friday"
        if d in (bf + dt.timedelta(days=1), bf + dt.timedelta(days=2)):
            return "fim de semana da Black Friday"
    if d.month == 12 and 15 <= d.day <= 24:
        return "Natal"
    return ""


def media_esperada(d):
    t = (d - INICIO).days
    nivel = NIVEL_INICIAL * (1 + CRESCIMENTO_ANO * t / 365)
    anual = 1 + ONDA_ANUAL * math.cos(2 * math.pi * (d.timetuple().tm_yday - PICO_ANUAL) / 365.25)
    m = nivel * DIA_DA_SEMANA[d.weekday()] * anual
    p = promocao(d)
    if p == "Black Friday":
        m *= BLACK_FRIDAY
    elif p == "fim de semana da Black Friday":
        m *= FIM_DE_SEMANA_BF
    elif p == "Natal":
        m *= NATAL
    if d in FERIADOS:
        m *= FERIADO_ABERTO
    return m


def gerar(saida):
    rng = random.Random(SEMENTE)
    vendas = []
    for d in datas(INICIO, FIM):
        ruido = rng.gauss(0, RUIDO)
        minuto_final = rng.randint(21 * 60 + 30, 21 * 60 + 59)
        razao = rng.gauss(0, 0.04)
        if d in SEM_REGISTRO:
            continue
        if (d.month, d.day) in FECHADA:
            vendas.append([d.isoformat(), 0, 0, ""])
            continue
        unidades = max(0, round(media_esperada(d) * (1 + ruido)))
        ultimo = f"{minuto_final // 60:02d}:{minuto_final % 60:02d}"
        if d in INCOMPLETOS:
            ultimo = INCOMPLETOS[d]
            h, mi = map(int, ultimo.split(":"))
            fracao = (h * 60 + mi - ABRE) / (FECHA - ABRE)
            unidades = round(unidades * fracao)
        pedidos = round(unidades / (UNIDADES_POR_PEDIDO * (1 + razao)))
        vendas.append([d.isoformat(), pedidos, unidades, ultimo])

    with open(saida / "venda_diaria.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["data", "pedidos", "unidades", "ultimo_registro"])
        w.writerows(vendas)

    calendario = []
    for d in datas(INICIO, FIM_CALENDARIO):
        fechada = 1 if (d.month, d.day) in FECHADA else 0
        calendario.append([d.isoformat(), FERIADOS.get(d, ""), fechada, promocao(d)])
    with open(saida / "calendario.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["data", "feriado", "loja_fechada", "promocao"])
        w.writerows(calendario)
    return len(vendas), len(calendario)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default=str(pathlib.Path(__file__).resolve().parent))
    saida = pathlib.Path(ap.parse_args().saida)
    saida.mkdir(parents=True, exist_ok=True)
    n_vendas, n_cal = gerar(saida)
    dias = (FIM - INICIO).days + 1
    print(f"venda_diaria={n_vendas} dias_no_calendario={dias} sem_registro={dias - n_vendas} "
          f"calendario={n_cal}")


if __name__ == "__main__":
    main()
