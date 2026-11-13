"""Gera as entregas do bairro, a chuva e a previsão do tempo da aula «Exógenas conhecidas e previstas».

Só biblioteca padrão (Python 3.9 ou mais novo). Rodar duas vezes dá os mesmos arquivos, byte a byte.
Lê o calendário da loja em dados/loja/calendario.csv, na raiz do kit do curso.

    python3 dados/gerar.py                 # escreve na pasta dados/ dessa aula
    python3 dados/gerar.py --saida /tmp/x  # escreve em outra pasta

Como os dados nascem (o mecanismo):
- a loja física entrega no bairro, de moto, os pedidos feitos por telefone e mensagem;
- o nível começa em 45 entregas por dia e sobe 12% por ano, em linha reta;
- cada dia da semana multiplica o nível (sexta 1,08, sábado 1,20), e uma onda anual pequena sobe no
  fim do ano;
- a Black Friday multiplica o dia por 1,6 e o fim de semana seguinte por 1,2; de 15 a 24 de dezembro,
  1,2 (Natal); feriado com a loja aberta, 1,15 (as pessoas ficam em casa e pedem mais);
- dia de loja fechada não tem entrega;
- dia de chuva forte (5 mm ou mais) multiplica as entregas por 1,40;
- sobre a conta, um ruído multiplicativo normal com desvio de 6%, sorteado dia a dia.

A chuva: um estado do tempo que tem memória de um dia para o outro (correlação 0,5) decide se chove
5 mm ou mais. A chance de chuva forte muda com o mês, de 6% em julho a 40% em janeiro. A chuva da
cidade é inventada; os números não são de nenhuma cidade real.

A previsão do tempo: publicada todo dia de 2025, para cada um dos 14 dias seguintes. Ela dá a chance
de chover 5 mm ou mais. Quanto mais longe o dia, menos ela sabe do estado do tempo daquele dia
(correlação 0,95 para amanhã, 0,47 para daqui a 7 dias, 0,02 para daqui a 14). Ela é honesta: entre os
dias com 30% de chance, chove em cerca de 30%. Longe, ela fica perto da chance do mês.

chuva.csv vai até 31/12/2025: a chuva de 2026 ainda não aconteceu. A previsão publicada em 31/12/2025
vai até 14/01/2026.
"""
import argparse
import csv
import datetime as dt
import math
import pathlib
import random
from statistics import NormalDist

SEMENTE = 1212
INICIO = dt.date(2024, 1, 1)
FIM = dt.date(2025, 12, 31)
FIM_PREVISAO = dt.date(2026, 1, 14)
PRIMEIRA_PREVISAO = dt.date(2025, 1, 1)
DIAS_DE_PREVISAO = 14

NIVEL_INICIAL = 45.0
CRESCIMENTO_ANO = 0.12
DIA_DA_SEMANA = [0.92, 0.90, 0.93, 0.97, 1.08, 1.20, 1.00]  # segunda a domingo
ONDA_ANUAL = 0.05
PICO_ANUAL = 350
EVENTOS = {"Black Friday": 1.6, "fim de semana da Black Friday": 1.2, "Natal": 1.2}
FERIADO_ABERTO = 1.15
CHUVA_FORTE_MM = 5.0
EFEITO_CHUVA = 1.40
RUIDO = 0.06

CHANCE_DO_MES = [0.40, 0.38, 0.32, 0.18, 0.12, 0.08, 0.06, 0.07, 0.14, 0.22, 0.28, 0.36]
MEMORIA = 0.5
CORRELACAO_PREVISAO = [0.95, 0.90, 0.84, 0.76, 0.67, 0.57, 0.47, 0.37, 0.28, 0.20, 0.13, 0.08, 0.04, 0.02]

N = NormalDist()


def datas(inicio, fim):
    d = inicio
    while d <= fim:
        yield d
        d += dt.timedelta(days=1)


def calendario(caminho):
    with open(caminho, encoding="utf-8") as f:
        return {dt.date.fromisoformat(r["data"]): r for r in csv.DictReader(f)}


def gerar(saida, cal):
    rng = random.Random(SEMENTE)
    # o estado do tempo de cada dia, até o último dia que a previsão alcança
    estado, z = {}, 0.0
    for d in datas(INICIO, FIM_PREVISAO):
        z = MEMORIA * z + math.sqrt(1 - MEMORIA ** 2) * rng.gauss(0, 1)
        estado[d] = z
    limite = {d: N.inv_cdf(1 - CHANCE_DO_MES[d.month - 1]) for d in estado}
    chuva = {}
    for d in datas(INICIO, FIM_PREVISAO):
        u, leve = rng.random(), rng.random()
        if estado[d] > limite[d]:
            chuva[d] = round(CHUVA_FORTE_MM + rng.expovariate(1 / 12), 1)
        elif leve < 0.3:
            chuva[d] = round(0.2 + 4.7 * u, 1)
        else:
            chuva[d] = 0.0

    entregas = []
    for d in datas(INICIO, FIM):
        ruido = rng.gauss(0, RUIDO)
        c = cal[d]
        if c["loja_fechada"] == "1":
            entregas.append([d.isoformat(), 0])
            continue
        t = (d - INICIO).days
        m = NIVEL_INICIAL * (1 + CRESCIMENTO_ANO * t / 365) * DIA_DA_SEMANA[d.weekday()]
        m *= 1 + ONDA_ANUAL * math.cos(2 * math.pi * (d.timetuple().tm_yday - PICO_ANUAL) / 365.25)
        m *= EVENTOS.get(c["promocao"], 1.0)
        if c["feriado"]:
            m *= FERIADO_ABERTO
        if chuva[d] >= CHUVA_FORTE_MM:
            m *= EFEITO_CHUVA
        entregas.append([d.isoformat(), max(0, round(m * (1 + ruido)))])

    previsoes = []
    for e in datas(PRIMEIRA_PREVISAO, FIM):
        for h in range(1, DIAS_DE_PREVISAO + 1):
            alvo = e + dt.timedelta(days=h)
            r = CORRELACAO_PREVISAO[h - 1]
            sinal = r * estado[alvo] + math.sqrt(1 - r * r) * rng.gauss(0, 1)
            p = 1 - N.cdf((limite[alvo] - r * sinal) / math.sqrt(1 - r * r))
            previsoes.append([e.isoformat(), alvo.isoformat(), round(100 * p)])

    escrever(saida / "entregas.csv", ["data", "entregas"], entregas)
    escrever(saida / "chuva.csv", ["data", "chuva_mm"],
             [[d.isoformat(), f"{chuva[d]:.1f}"] for d in datas(INICIO, FIM)])
    escrever(saida / "previsao_chuva.csv", ["publicada_em", "para_o_dia", "chance_chuva_forte"], previsoes)
    fortes = sum(1 for d in datas(INICIO, FIM) if chuva[d] >= CHUVA_FORTE_MM)
    return len(entregas), fortes, len(previsoes)


def escrever(caminho, cabecalho, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cabecalho)
        w.writerows(linhas)


def main():
    aqui = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default=str(aqui))
    saida = pathlib.Path(ap.parse_args().saida)
    saida.mkdir(parents=True, exist_ok=True)
    cal = calendario(aqui.parent.parent / "dados" / "loja" / "calendario.csv")
    n, fortes, prev = gerar(saida, cal)
    print(f"entregas={n} dias_de_chuva_forte={fortes} previsoes={prev}")


if __name__ == "__main__":
    main()
