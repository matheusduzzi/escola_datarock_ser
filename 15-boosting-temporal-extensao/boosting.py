"""O boosting da aula «Boosting temporal (extensão)» do curso Séries temporais.

Este arquivo não imprime nada: o comparar_boosting.py importa daqui. Deixe os dois na mesma pasta,
junto com o modelos.py, que é o mesmo da aula 11.

Três partes:
  1. as features de cada dia previsto, feitas só com a venda até a noite da decisão (aula 09);
  2. o boosting de árvores, escrito com NumPy, para você ver cada passo;
  3. o mesmo ajuste chamado no LightGBM ou no XGBoost, se você tiver um deles instalado.
"""
import numpy as np
import pandas as pd

import modelos as M

CALENDARIO = ["dia_semana", "dia_do_ano", "Black Friday", "fim de semana da Black Friday", "Natal",
              "feriado com a loja aberta"]


# ---------- 1. as features, dentro do corte ----------

def features(d, horizonte):
    """Uma linha por dia previsto D. A venda mais nova que entra é a de D − horizonte, a noite da decisão.

    `base` é a média dos 28 dias que terminam na noite da decisão. O alvo do boosting é o log da
    venda dividida por essa base: quanto o dia fica acima ou abaixo do nível recente. A árvore
    aprende a proporção, e o nível vem da venda que já existe.
    """
    u = d["usavel"]
    passado = u.shift(horizonte)                       # na linha D, a venda de D − horizonte
    k0 = -(-horizonte // 7)                            # a primeira semana inteira que já existe
    t = pd.DataFrame(index=d.index)
    t["base"] = passado.rolling(28, min_periods=14).mean()
    t["lag"] = passado / t["base"]
    t["mesmo_dia_4"] = pd.concat([u.shift(7 * k) for k in range(k0, k0 + 4)], axis=1).mean(axis=1) / t["base"]
    t["mesmo_dia_1"] = u.shift(7 * k0) / t["base"]
    t["base_28_antes"] = passado.shift(28).rolling(28, min_periods=14).mean() / t["base"]
    t["dia_semana"] = d.index.dayofweek
    t["dia_do_ano"] = d.index.dayofyear
    for nome in CALENDARIO[2:]:
        t[nome] = d[nome].astype(float)
    return t


COLUNAS = ["lag", "mesmo_dia_4", "mesmo_dia_1", "base_28_antes"] + CALENDARIO


def alvo(d, t):
    """log(venda / base). Vazio no dia que não serve (aula 03) ou sem base."""
    return np.log(d["usavel"] / t["base"])


# ---------- 2. o boosting com NumPy ----------

PARAMETROS = {"arvores_max": 600, "taxa": 0.05, "profundidade": 3, "folha_min": 10, "lambda": 1.0,
              "faixas": 32, "paciencia": 50}
FOLHAS = (1, 3, 10, 30)    # as folhas mínimas que a validação testa em cada ajuste


def _faixas(X, n):
    """Os cortes candidatos de cada coluna: até n − 1 quantis dos valores do treino (o histograma)."""
    cortes = []
    for j in range(X.shape[1]):
        v = np.unique(X[:, j][~np.isnan(X[:, j])])
        if len(v) > n:
            v = np.unique(np.quantile(v, np.linspace(0, 1, n + 1)[1:-1]))
        else:
            v = (v[:-1] + v[1:]) / 2 if len(v) > 1 else v[:0]
        cortes.append(v)
    return cortes


def _arvore(Xb, g, linhas, prof, p, ncortes):
    """Uma árvore de regressão sobre o gradiente g, de cima para baixo, com o ganho do XGBoost.

    Em cada nó, para cada coluna, soma g por faixa (o histograma) e testa todo corte: o ganho é
    G_esq²/(n_esq + λ) + G_dir²/(n_dir + λ) − G²/(n + λ). Fica o corte de maior ganho.
    A folha vale −G/(n + λ), vezes a taxa. Com o erro quadrático (metade do quadrado), o gradiente
    é previsão − real e a hessiana de cada linha é 1: H vira o número de dias do nó.
    """
    G, n = g[linhas].sum(), len(linhas)
    folha = {"valor": -p["taxa"] * G / (n + p["lambda"])}
    if prof == 0 or n < 2 * p["folha_min"]:
        return folha
    ncol, nb = Xb.shape[1], int(ncortes.max()) + 1
    posicao = (Xb[linhas] + np.arange(ncol) * nb).ravel()      # todas as colunas num histograma só
    sg = np.bincount(posicao, weights=np.repeat(g[linhas], ncol), minlength=ncol * nb).reshape(ncol, nb)
    sn = np.bincount(posicao, minlength=ncol * nb).reshape(ncol, nb)
    ge, ne = np.cumsum(sg, axis=1)[:, :-1], np.cumsum(sn, axis=1)[:, :-1]
    gd, nd = G - ge, n - ne
    existe = np.arange(nb - 1)[None, :] < ncortes[:, None]     # corte k só existe se a coluna tem k + 1 cortes
    ok = existe & (ne >= p["folha_min"]) & (nd >= p["folha_min"])
    if not ok.any():
        return folha
    with np.errstate(all="ignore"):
        ganho = np.where(ok, ge * ge / (ne + p["lambda"]) + gd * gd / (nd + p["lambda"])
                         - G * G / (n + p["lambda"]), -np.inf)
    j, k = np.unravel_index(int(np.argmax(ganho)), ganho.shape)
    if not ganho[j, k] > 1e-12:
        return folha
    esq = linhas[Xb[linhas, j] <= k]
    dir_ = linhas[Xb[linhas, j] > k]
    return {"coluna": int(j), "faixa": int(k), "ganho": float(ganho[j, k]),
            "esq": _arvore(Xb, g, esq, prof - 1, p, ncortes),
            "dir": _arvore(Xb, g, dir_, prof - 1, p, ncortes)}


def _aplicar(no, Xb):
    out = np.empty(len(Xb))
    pilha = [(no, np.arange(len(Xb)))]
    while pilha:
        no, idx = pilha.pop()
        if "valor" in no:
            out[idx] = no["valor"]
            continue
        vai = Xb[idx, no["coluna"]] <= no["faixa"]
        pilha.append((no["esq"], idx[vai]))
        pilha.append((no["dir"], idx[~vai]))
    return out


def _binarizar(X, cortes):
    """Cada valor vira o número da faixa. Vazio vai para a faixa 0, como um valor pequeno."""
    Xb = np.zeros(X.shape, dtype=np.int64)
    for j, c in enumerate(cortes):
        col = np.where(np.isnan(X[:, j]), -np.inf, X[:, j])
        Xb[:, j] = np.searchsorted(c, col, side="left")
    return Xb


class Boosting:
    """Boosting de árvores de regressão com o erro quadrático: cada árvore corrige o que as anteriores erraram."""

    def __init__(self, **kw):
        self.p = {**PARAMETROS, **kw}

    def ajustar(self, X, y, arvores):
        self.cortes = _faixas(X, self.p["faixas"])
        self.inicio = float(np.mean(y))
        Xb = _binarizar(X, self.cortes)
        ncortes = np.array([len(c) for c in self.cortes])
        pred = np.full(len(y), self.inicio)
        self.arvores = []
        linhas = np.arange(len(y))
        for _ in range(arvores):
            g = pred - y                                   # o gradiente do erro quadrático
            a = _arvore(Xb, g, linhas, self.p["profundidade"], self.p, ncortes)
            pred += _aplicar(a, Xb)
            self.arvores.append(a)
        return self

    def prever(self, X, arvores=None):
        Xb = _binarizar(X, self.cortes)
        out = np.full(len(X), self.inicio)
        for a in self.arvores[:arvores]:
            out += _aplicar(a, Xb)
        return out

    def curva(self, X, y):
        """O erro quadrático médio em (X, y) depois de cada árvore."""
        Xb = _binarizar(X, self.cortes)
        out = np.full(len(X), self.inicio)
        erros = []
        for a in self.arvores:
            out += _aplicar(a, Xb)
            erros.append(float(np.mean((out - y) ** 2)))
        return np.array(erros)

    def importancia(self):
        """Soma do ganho de cada coluna em todas as árvores, em proporção do total."""
        soma = np.zeros(len(self.cortes))
        pilha = list(self.arvores)
        while pilha:
            no = pilha.pop()
            if "valor" not in no:
                soma[no["coluna"]] += no["ganho"]
                pilha += [no["esq"], no["dir"]]
        return soma / soma.sum()


# ---------- 3. o mesmo ajuste no kit, no LightGBM ou no XGBoost ----------

def _kit(n, folha, parar=False):
    m = Boosting(folha_min=folha)
    return m, (lambda X, y, Xva=None, yva=None: m.ajustar(X, y, n)), m.prever


def _lightgbm(n, folha, parar=False):
    import lightgbm as lgb
    p = PARAMETROS
    m = lgb.LGBMRegressor(n_estimators=n, learning_rate=p["taxa"], max_depth=p["profundidade"],
                          num_leaves=2 ** p["profundidade"], min_child_samples=folha,
                          reg_lambda=p["lambda"], max_bin=p["faixas"], random_state=0, verbose=-1)

    def fit(X, y, Xva=None, yva=None):
        if not parar:
            return m.fit(X, y)
        cb = [lgb.early_stopping(p["paciencia"], verbose=False)]
        try:                                           # 4.7.0 em diante: eval_X e eval_y
            return m.fit(X, y, eval_X=(Xva,), eval_y=(yva,), callbacks=cb)
        except TypeError:                              # versões anteriores: eval_set
            return m.fit(X, y, eval_set=[(Xva, yva)], callbacks=cb)
    return m, fit, m.predict


def _xgboost(n, folha, parar=False):
    import xgboost as xgb
    p = PARAMETROS
    extra = {"early_stopping_rounds": p["paciencia"]} if parar else {}   # no construtor, como na documentação da 3.4
    m = xgb.XGBRegressor(n_estimators=n, learning_rate=p["taxa"], max_depth=p["profundidade"],
                         min_child_weight=folha, reg_lambda=p["lambda"], max_bin=p["faixas"],
                         tree_method="hist", random_state=0, **extra)

    def fit(X, y, Xva=None, yva=None):
        if not parar:
            return m.fit(X, y)
        return m.fit(X, y, eval_set=[(Xva, yva)], verbose=False)
    return m, fit, m.predict


MOTORES = {"kit": _kit, "lightgbm": _lightgbm, "xgboost": _xgboost}


def motor_disponivel(nome):
    if nome == "kit":
        return True
    import importlib.util
    return importlib.util.find_spec(nome) is not None


def ajustar_fixo(motor, X, y, n, folha=None):
    """Ajusta com n árvores e a folha mínima dada, e retorna a função de previsão."""
    _, fit, prever = MOTORES[motor](n, PARAMETROS["folha_min"] if folha is None else folha)
    fit(X, y)
    return prever


def erro_validacao(motor, Xtr, ytr, Xva, yva, folha):
    """O menor erro quadrático na validação e o número de árvores em que ele aconteceu."""
    p = PARAMETROS
    m, fit, prever = MOTORES[motor](p["arvores_max"], folha, parar=True)
    fit(Xtr, ytr, Xva, yva)
    if motor == "kit":
        curva = m.curva(Xva, yva)
        k = int(np.argmin(curva))
        return float(curva[k]), k + 1
    n = int(m.best_iteration_) if motor == "lightgbm" else int(m.best_iteration) + 1
    return float(np.mean((prever(Xva) - yva) ** 2)), n


def melhor_config(motor, Xtr, ytr, Xva, yva, folhas=FOLHAS):
    """A folha mínima e o número de árvores que erram menos na validação, nunca no teste."""
    melhor = None
    for folha in folhas:
        erro, n = erro_validacao(motor, Xtr, ytr, Xva, yva, folha)
        if melhor is None or erro < melhor[0]:
            melhor = (erro, folha, n)
    return melhor[1], melhor[2]


# ---------- o ajuste numa origem ----------

VALIDACAO = 56     # os últimos 56 dias do treino escolhem o número de árvores


def treino_ate(d, t, y, origem, colunas=COLUNAS):
    """As linhas que existem na noite da origem: dias previstos até ela, com venda que serve."""
    ok = (t.index <= origem) & y.notna().to_numpy() & t[colunas].notna().all(axis=1).to_numpy()
    tr = t.index[ok]
    return t.loc[tr, colunas].to_numpy(float), y[tr].to_numpy(float), tr


def ajustar_na_origem(d, t, y, origem, motor="kit", colunas=COLUNAS, folhas=FOLHAS):
    """Ajusta só com o que existe na origem.

    Os últimos 56 dias desse treino escolhem a folha mínima e o número de árvores. Depois o modelo
    é ajustado de novo com o treino inteiro, para a venda mais recente entrar.
    Retorna a função de previsão, a folha e o número de árvores.
    """
    X, yy, datas = treino_ate(d, t, y, origem, colunas)
    corte = datas[-1] - pd.Timedelta(days=VALIDACAO)
    tr, va = datas <= corte, datas > corte
    folha, n = melhor_config(motor, X[tr], yy[tr], X[va], yy[va], folhas)
    return ajustar_fixo(motor, X, yy, n, folha), folha, n
