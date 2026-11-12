# 06. Naive e naive sazonal

Os programas da aula «Naive e naive sazonal». Eles leem a venda e o calendário da loja em `../dados/loja/`, que vêm com o kit desde a apresentação.

| Arquivo | O que faz |
|---|---|
| `naive.py` | Faz o naive e o naive sazonal, mede o erro por horizonte, refaz a conta com o total da semana e grava as previsões de um mês num CSV com o sha256. |
| `teste_baseline.py` | Testa a sua regra da baseline da escala em 22 noites de escala. |
| `minha_baseline.py` | Onde você escreve a regra, no exercício. |
| `minhas-respostas.md` | A folha do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas. É o mesmo ambiente da apresentação: o `requirements.txt` da raiz do kit já instala o que essa aula usa.

## Como rodar

Na pasta dessa aula:

```bash
python3 naive.py
python3 naive.py --origem 2024-12-01
python3 naive.py --origem 2025-12-01 --saida previsoes_janeiro.csv
python3 teste_baseline.py
python3 naive.py --origem 2025-12-01 --regra minha_baseline.py --saida minhas_previsoes_janeiro.csv
```

O primeiro comando mostra as cinco partes da aula. O segundo faz o ensaio de janeiro de 2025 com o naive sazonal sem regra. O terceiro grava as previsões de janeiro de 2026 e mostra o sha256 do arquivo: rode duas vezes e veja que ele não muda.

Os dois últimos são do exercício. Antes de você escrever a regra, o `teste_baseline.py` termina com `FALHOU: a previsão precisa dar um número em todo dia` e código 1. Depois, ele precisa terminar com `PASSOU`.

Os programas também rodam da raiz do kit, por exemplo `python3 06-naive-e-naive-sazonal/naive.py`: eles acham `dados/loja` pelo próprio caminho. O `--saida` grava o arquivo na pasta de onde você rodou.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
