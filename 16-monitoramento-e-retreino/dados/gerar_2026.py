"""Gera a venda de 2026 da loja física da Loja Exemplo, usada na aula «Monitoramento e retreino».

Só biblioteca padrão (Python 3.9 ou mais novo). Rodar duas vezes dá os mesmos arquivos, byte a byte.

    python3 gerar_2026.py                 # escreve nesta pasta
    python3 gerar_2026.py --saida /tmp/x  # escreve em outra pasta

Faça a aula antes de abrir esse arquivo. Depois compare o que o painel achou com o que foi sorteado.

Como os dados nascem (o mecanismo):
- a venda continua a de 2024 e 2025: o mesmo nível com a mesma subida por ano, o mesmo peso de
  cada dia da semana, a mesma onda do ano e o mesmo ruído de 8%, com as contas do gerar.py de
  dados/loja, na raiz do kit;
- feriados de 2026 com a loja aberta (Carnaval, Sexta-feira Santa, Tiradentes) vendem 80% do
  normal; em 1º de janeiro e 1º de maio a loja fecha;
- a partir da segunda-feira 09/03/2026, uma obra da prefeitura fecha a calçada da frente da loja:
  de segunda a sexta a venda cai para 82% do que seria, e no sábado e no domingo, para 92%;
- a venda de um dia só fecha de 1 a 3 dias depois: pedidos pagos por link, trocas e ajustes do
  caixa entram depois da noite. O número lido às 22h fica de 1% a 5% abaixo do número fechado;
- de terça 10/02 a sábado 14/02/2026, o caixa ficou sem sincronizar. Parte das vendas foi anotada
  no papel e lançada na sexta 20/02: nesses cinco dias, o número da noite ficou de 35% a 45% abaixo
  do fechado, e o dia só fechou em 20/02;
- o arquivo é a leitura da manhã de segunda-feira, 27/04/2026: os dias que ainda não fecharam
  têm a venda da noite e a venda fechada vazia.

venda_2026.csv: data, unidades_noite (o número lido às 22h do dia), unidades (o número fechado,
vazio se ainda não fechou) e fechada_em (o dia em que fechou, vazio se ainda não fechou).
calendario_2026.csv: as mesmas colunas do calendario.csv de dados/loja, de 01/01 a 31/05/2026.
"""
import argparse
import csv
import datetime as dt
import importlib.util
import pathlib
import random

AQUI = pathlib.Path(__file__).resolve().parent
LOJA = AQUI.parent.parent / "dados" / "loja"

SEMENTE = 2026
INICIO = dt.date(2026, 1, 1)
FIM = dt.date(2026, 4, 26)
LEITURA = dt.date(2026, 4, 27)        # manhã da segunda-feira em que o arquivo foi lido
FIM_CALENDARIO = dt.date(2026, 5, 31)

FERIADOS_2026 = {
    dt.date(2026, 1, 1): "Confraternização Universal",
    dt.date(2026, 2, 16): "Carnaval",
    dt.date(2026, 2, 17): "Carnaval",
    dt.date(2026, 4, 3): "Sexta-feira Santa",
    dt.date(2026, 4, 21): "Tiradentes",
    dt.date(2026, 5, 1): "Dia do Trabalho",
}
OBRA_INICIO = dt.date(2026, 3, 9)
OBRA_DIA_UTIL = 0.82
OBRA_FIM_DE_SEMANA = 0.92
FECHAMENTO = (0.01, 0.05)             # quanto o número da noite fica abaixo do fechado
CAIXA_SEM_SINCRONIZAR = (dt.date(2026, 2, 10), dt.date(2026, 2, 14))
LANCAMENTO_DO_PAPEL = dt.date(2026, 2, 20)
NO_PAPEL = (0.35, 0.45)


def mecanismo_da_loja():
    """O gerar.py de dados/loja, carregado como módulo: as mesmas contas de 2024 e 2025."""
    spec = importlib.util.spec_from_file_location("gerar_loja", LOJA / "gerar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def datas(inicio, fim):
    d = inicio
    while d <= fim:
        yield d
        d += dt.timedelta(days=1)


def media_esperada(loja, d):
    m = loja.media_esperada(d)          # nível, tendência, dia da semana, onda do ano, promoções
    if d in FERIADOS_2026 and d not in loja.FERIADOS:
        m *= loja.FERIADO_ABERTO
    if d >= OBRA_INICIO:
        m *= OBRA_DIA_UTIL if d.weekday() < 5 else OBRA_FIM_DE_SEMANA
    return m


def gerar(saida):
    loja = mecanismo_da_loja()
    rng = random.Random(SEMENTE)
    linhas = []
    for d in datas(INICIO, FIM):
        ruido = rng.gauss(0, loja.RUIDO)
        falta = rng.uniform(*FECHAMENTO)
        papel = rng.uniform(*NO_PAPEL)
        demora = rng.randint(1, 3)
        if (d.month, d.day) in loja.FECHADA:
            linhas.append([d.isoformat(), 0, 0, d.isoformat()])
            continue
        fechada = max(0, round(media_esperada(loja, d) * (1 + ruido)))
        fechada_em = d + dt.timedelta(days=demora)
        noite = round(fechada * (1 - falta))
        if CAIXA_SEM_SINCRONIZAR[0] <= d <= CAIXA_SEM_SINCRONIZAR[1]:
            noite = round(fechada * (1 - papel))
            fechada_em = LANCAMENTO_DO_PAPEL
        if fechada_em >= LEITURA:
            linhas.append([d.isoformat(), noite, "", ""])
        else:
            linhas.append([d.isoformat(), noite, fechada, fechada_em.isoformat()])

    with open(saida / "venda_2026.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["data", "unidades_noite", "unidades", "fechada_em"])
        w.writerows(linhas)

    cal = []
    for d in datas(INICIO, FIM_CALENDARIO):
        fechada = 1 if (d.month, d.day) in loja.FECHADA else 0
        cal.append([d.isoformat(), FERIADOS_2026.get(d, ""), fechada, ""])
    with open(saida / "calendario_2026.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["data", "feriado", "loja_fechada", "promocao"])
        w.writerows(cal)
    return linhas, cal


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", default=str(AQUI))
    saida = pathlib.Path(ap.parse_args().saida)
    saida.mkdir(parents=True, exist_ok=True)
    linhas, cal = gerar(saida)
    abertos = sum(1 for l in linhas if l[3] == "")
    print(f"venda_2026={len(linhas)} fechados={len(linhas) - abertos} abertos={abertos} calendario={len(cal)}")


if __name__ == "__main__":
    main()
