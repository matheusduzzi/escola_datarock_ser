"""O teste de Dickey-Fuller aumentado, escrito com NumPy, linha a linha.

Segue a receita do adfuller do statsmodels 0.15.0 (statsmodels.tsa.stattools.adfuller):
- a regressão: diferença de hoje contra o nível de ontem, as diferenças dos dias anteriores e,
  conforme a opção, uma constante ("c") ou uma constante e uma reta no tempo ("ct");
- o número de diferenças anteriores: escolhido de 0 até 12 x (n/100) elevado a 1/4, pelo menor AIC,
  com todas as tentativas na mesma amostra; depois a regressão escolhida roda de novo com todas as
  linhas que ela permite;
- a estatística: o t do coeficiente do nível de ontem;
- o p-valor: a aproximação de MacKinnon (1994), com os coeficientes do statsmodels;
- os valores críticos de 1%, 5% e 10%: MacKinnon (2010), corrigidos pelo tamanho da amostra.

Se você tiver o statsmodels instalado, compare: adfuller(x, regression="c", autolag="AIC").
"""
import math

import numpy as np

# MacKinnon (1994), uma série (N = 1), como em statsmodels/tsa/adfvalues.py (v0.15.0)
_TAU_MAX = {"c": 2.74, "ct": 0.7}
_TAU_MIN = {"c": -18.83, "ct": -16.18}
_TAU_STAR = {"c": -1.61, "ct": -2.89}
_PEQUENO = {"c": [2.1659, 1.4412, 3.8269 * 1e-2], "ct": [3.2512, 1.6047, 4.9588 * 1e-2]}
_GRANDE = {"c": [1.7339, 9.3202 * 1e-1, -1.2745 * 1e-1, -1.0368 * 1e-2],
           "ct": [2.5261, 6.1654 * 1e-1, -3.7956 * 1e-1, -6.0285 * 1e-2]}
# MacKinnon (2010), uma série: valor = b0 + b1/n + b2/n^2 + b3/n^3, para 1%, 5% e 10%
_CRITICOS = {"c": [[-3.43035, -6.5393, -16.786, -79.433],
                   [-2.86154, -2.8903, -4.234, -40.040],
                   [-2.56677, -1.5384, -2.809, 0.0]],
             "ct": [[-3.95877, -9.0531, -28.428, -134.155],
                    [-3.41049, -4.3904, -9.036, -45.374],
                    [-3.12705, -2.5856, -3.925, -22.380]]}


def p_valor(tau, regressao="c"):
    """O p-valor aproximado de MacKinnon para a estatística tau."""
    if tau > _TAU_MAX[regressao]:
        return 1.0
    if tau < _TAU_MIN[regressao]:
        return 0.0
    coef = _PEQUENO[regressao] if tau <= _TAU_STAR[regressao] else _GRANDE[regressao]
    z = sum(c * tau ** i for i, c in enumerate(coef))
    return 0.5 * math.erfc(-z / math.sqrt(2))  # a normal acumulada, sem perder a cauda


def criticos(n, regressao="c"):
    """Os valores críticos de 1%, 5% e 10% para n linhas na regressão."""
    return {nivel: sum(b / n ** i for i, b in enumerate(linha))
            for nivel, linha in zip(("1%", "5%", "10%"), _CRITICOS[regressao])}


def _regressao(x, dx, lags, linhas, regressao):
    """Monta y e X: a diferença de hoje contra (constante, reta, nível de ontem, diferenças anteriores)."""
    fim = len(dx)
    idx = np.arange(fim - linhas, fim)  # posições em dx
    colunas = [np.ones(linhas)]
    if regressao == "ct":
        colunas.append(np.arange(1, linhas + 1, dtype=float))
    colunas.append(x[idx])  # nível de ontem: x[t-1] quando dx[t-1] = x[t] - x[t-1]
    for k in range(1, lags + 1):
        colunas.append(dx[idx - k])
    return dx[idx], np.column_stack(colunas), len(colunas) - lags - 1


def _ols(y, X):
    # o errstate cala um aviso falso de algumas bibliotecas de álgebra do macOS; o isfinite confere a conta
    with np.errstate(all="ignore"):
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        ssr = float(resid @ resid)
        xtx_inv = np.linalg.inv(X.T @ X)
    if not (np.isfinite(beta).all() and np.isfinite(ssr) and np.isfinite(xtx_inv).all()):
        raise ArithmeticError("a regressão do teste não deu números finitos")
    n, k = X.shape
    return beta, xtx_inv, ssr, n, k


def adf(serie, regressao="c", max_lags=None):
    """Roda o teste. serie: lista, array ou Series sem vazio, em ordem de tempo.

    Retorna um dicionário com estatistica, p_valor, lags (diferenças anteriores usadas),
    n (linhas da regressão), criticos e coef_nivel (o coeficiente do nível de ontem).
    """
    if regressao not in ("c", "ct"):
        raise ValueError('regressao precisa ser "c" (constante) ou "ct" (constante e reta)')
    x = np.asarray(serie, dtype=float)
    if np.isnan(x).any():
        raise ValueError("a série tem dia vazio; o teste precisa de todos os dias em sequência")
    if x.max() == x.min():
        raise ValueError("a série é constante")
    n_total = len(x)
    det = len(regressao)
    if max_lags is None:
        max_lags = int(math.ceil(12.0 * (n_total / 100.0) ** 0.25))
        max_lags = min(n_total // 2 - det - 1, max_lags)
    dx = np.diff(x)
    linhas_busca = len(dx) - max_lags
    melhor = None
    for lags in range(0, max_lags + 1):  # mesma amostra para comparar o AIC
        y, X, _ = _regressao(x, dx, lags, linhas_busca, regressao)
        _, _, ssr, n, k = _ols(y, X)
        aic = n * math.log(ssr / n) + 2 * k  # mesmo critério do AIC de mínimos quadrados, sem a constante
        if melhor is None or (aic, lags) < melhor:
            melhor = (aic, lags)
    lags = melhor[1]
    y, X, pos = _regressao(x, dx, lags, len(dx) - lags, regressao)
    beta, xtx_inv, ssr, n, k = _ols(y, X)
    erro_padrao = math.sqrt(ssr / (n - k) * xtx_inv[pos, pos])
    tau = float(beta[pos] / erro_padrao)
    return {"estatistica": tau, "p_valor": p_valor(tau, regressao), "lags": lags, "n": n,
            "criticos": criticos(n, regressao), "coef_nivel": float(beta[pos])}
