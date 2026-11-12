"""O teste da baseline da escala: a regra do contrato vale em todas as noites de escala?

Rode de dentro da pasta dessa aula:
    python3 teste_baseline.py                  # testa a função prever de minha_baseline.py
    python3 teste_baseline.py outro_arquivo.py # testa outro arquivo com a mesma função

O arquivo testado precisa ter a função  prever(usavel, calendario, origem, dia),  que devolve
(unidades previstas, dia copiado). Veja o começo do minha_baseline.py.

O teste usa 22 noites de escala, o dia 1 de cada mês de 01/03/2024 a 01/12/2025, e cada dia do mês seguinte.
Para cada dia, ele confere:
  1. a previsão tem número;
  2. no dia em que o calendário diz loja fechada, a previsão é 0 e não copia nenhum dia;
  3. nos outros, o dia copiado é do mesmo dia da semana, vem até a noite da origem, é usável
     (completo, loja aberta), não tem feriado nem promoção, e a previsão é a venda dele;
  4. com a venda inteira, até 31/12/2025, a resposta é a mesma que com a venda cortada na origem;
  5. chamada duas vezes, a função dá a mesma resposta.
Sai com código 0 quando passa e 1 quando falha.
"""
import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from naive import DIAS, ate, br, carregar, d, dm, mes_seguinte  # noqa: E402

ORIGENS = pd.date_range("2024-03-01", "2025-12-01", freq="MS")
REGRAS = {
    "sem número": "a previsão precisa dar um número em todo dia",
    "fechado": "no dia fechado, a previsão é 0 e não copia nenhum dia",
    "fonte": "o dia copiado precisa ser do mesmo dia da semana, até a origem, usável, sem feriado nem promoção, "
             "e a previsão precisa ser a venda dele",
    "futuro": "com a venda inteira a resposta mudou: a função usou venda depois da origem",
    "repete": "chamada duas vezes, a função deu respostas diferentes",
}


def carregar_funcao(arquivo):
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        caminho = (Path.cwd() / caminho) if (Path.cwd() / caminho).exists() else AQUI / caminho
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.prever


def numero(x):
    try:
        return x is not None and not math.isnan(float(x))
    except (TypeError, ValueError):
        return False


def mesmo(a, b):
    (va, fa), (vb, fb) = a, b
    iguais_v = (not numero(va) and not numero(vb)) or (numero(va) and numero(vb) and float(va) == float(vb))
    return iguais_v and fa == fb


def checar(prever, usavel, cal, origem, dia):
    """Devolve a lista de regras que a resposta desse dia quebra."""
    cortada = ate(usavel, origem)
    resp = prever(cortada, cal, origem, dia)
    if not isinstance(resp, tuple) or len(resp) != 2:
        return ["sem número"]
    valor, fonte = resp
    falhas = []
    if not numero(valor):
        falhas.append("sem número")
    elif cal.loc[dia, "loja_fechada"] == 1:
        if float(valor) != 0 or fonte is not None:
            falhas.append("fechado")
    else:
        ok = fonte is not None
        if ok:
            fonte = pd.Timestamp(fonte)
            ok = (fonte.dayofweek == dia.dayofweek and fonte <= origem and numero(usavel.get(fonte))
                  and cal.loc[fonte, "feriado"] == "" and cal.loc[fonte, "promocao"] == ""
                  and float(valor) == float(usavel[fonte]))
        if not ok:
            falhas.append("fonte")
    if not mesmo(resp, prever(usavel, cal, origem, dia)):
        falhas.append("futuro")
    if not mesmo(resp, prever(ate(usavel, origem), cal, origem, dia)):
        falhas.append("repete")
    return falhas


def main():
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "minha_baseline.py"
    prever = carregar_funcao(arquivo)
    usavel, _, cal = carregar()
    contagem = {r: 0 for r in REGRAS}
    exemplo = {}
    total = 0
    for origem in ORIGENS:
        for dia in mes_seguinte(origem):
            total += 1
            for r in checar(prever, usavel, cal, origem, dia):
                contagem[r] += 1
                if r not in exemplo:
                    resp = prever(ate(usavel, origem), cal, origem, dia)
                    exemplo[r] = (origem, dia, resp)
    print(f"Testando {Path(arquivo).name}: {len(ORIGENS)} noites de escala, de {d(ORIGENS[0])} a {d(ORIGENS[-1])}, "
          f"{total} dias previstos")
    for r, texto in REGRAS.items():
        print(f"   {r:<11} {contagem[r]:>4} dias com problema")
    if any(contagem.values()):
        for r, (origem, dia, resp) in exemplo.items():
            valor, fonte = resp if isinstance(resp, tuple) and len(resp) == 2 else (resp, None)
            fonte_txt = dm(pd.Timestamp(fonte)) if fonte is not None else "nenhum"
            print(f"   primeiro caso de '{r}': origem {d(origem)} {DIAS[origem.dayofweek]}, dia {dm(dia)}, "
                  f"resposta {br(float(valor), 1) if numero(valor) else 'vazio'}, copiou {fonte_txt}")
        primeiro = next(r for r in REGRAS if contagem[r])
        print(f"FALHOU: {REGRAS[primeiro]}")
        sys.exit(1)
    print("PASSOU")


if __name__ == "__main__":
    main()
