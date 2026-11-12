"""O teste do corte para uma previsão: ela muda quando a venda depois da noite some?

Rode de dentro da pasta dessa aula:
    python3 teste_corte.py               # testa a função prever de minha_previsao.py
    python3 teste_corte.py rafael.py     # testa outro arquivo com a mesma função
    python3 teste_corte.py --corte 2025-10-01

O arquivo testado precisa ter a função  prever(usavel, comum, noite, dia),  que devolve a venda prevista
para `dia`, feita na noite `noite`. usavel e comum são as séries de carregar() do decompor.py.

Em cada uma das 31 noites até o corte, o teste chama prever duas vezes para o dia 35 dias depois:
uma com a venda cortada na noite e outra com a venda inteira, até 31/12/2025. Se os dois números
forem diferentes, a previsão usou venda que ainda não existia. O teste também exige um número
em todas as noites: uma previsão sempre vazia não usa o futuro, mas também não serve para a escala.
Sai com código 0 quando passa e 1 quando falha.
"""
import argparse
import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from decompor import ate, br, carregar, d  # noqa: E402

HORIZONTE = 35


def carregar_funcao(arquivo):
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        caminho = (Path.cwd() / caminho) if (Path.cwd() / caminho).exists() else AQUI / caminho
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.prever


def vazio(x):
    return x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x)


def main():
    ap = argparse.ArgumentParser(description="Teste do corte para uma função prever.")
    ap.add_argument("arquivo", nargs="?", default="minha_previsao.py")
    ap.add_argument("--corte", default="2025-10-01", help="última noite testada, AAAA-MM-DD (padrão: 2025-10-01)")
    args = ap.parse_args()
    corte = pd.Timestamp(args.corte)
    prever = carregar_funcao(args.arquivo)
    usavel, comum = carregar()
    noites = pd.date_range(corte - pd.Timedelta(days=30), corte, freq="D")
    print(f"teste do corte: {Path(args.arquivo).name}, {len(noites)} noites de {d(noites[0])} a {d(noites[-1])}, "
          f"dia previsto {HORIZONTE} dias depois de cada noite")
    mudou, sem_numero, casos = [], [], []
    for o in noites:
        dia = o + pd.Timedelta(days=HORIZONTE)
        no_corte = prever(ate(usavel, o), ate(comum, o), o, dia)
        com_tudo = prever(usavel, comum, o, dia)
        if vazio(no_corte):
            sem_numero.append(o)
            continue
        if vazio(com_tudo) or abs(float(no_corte) - float(com_tudo)) > 1e-9:
            mudou.append(o)
            if len(casos) < 3:
                casos.append(f"   noite {d(o)}, dia {d(dia)}: com a venda até a noite {br(float(no_corte))}; "
                             f"com a venda inteira {'vazio' if vazio(com_tudo) else br(float(com_tudo))}")
    print(f"   noites em que a previsão mudou com a venda depois da noite: {len(mudou)} de {len(noites)}")
    print("\n".join(casos)) if casos else None
    print(f"   noites sem número: {len(sem_numero)} de {len(noites)}")
    if mudou or sem_numero:
        print("FALHOU: " + ("a previsão usa venda que ainda não existia na noite" if mudou else
                            "a previsão precisa dar um número em toda noite"))
        raise SystemExit(1)
    print("PASSOU: a previsão só usa a venda até a noite")


if __name__ == "__main__":
    main()
