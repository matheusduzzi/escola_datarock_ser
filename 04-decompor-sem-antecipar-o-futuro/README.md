# 04. Decompor sem antecipar o futuro

Os programas da aula «Decompor sem antecipar o futuro». Eles leem a venda e o calendário da loja em `../dados/loja/`, que vêm com o kit desde a apresentação.

| Arquivo | O que faz |
|---|---|
| `decompor.py` | Separa a venda em nível, peso do dia da semana e sobra, com a data de corte escrita, e roda o teste do corte em cada parte. |
| `teste_corte.py` | Testa uma função `prever`: ela muda quando a venda depois da noite some? |
| `rafael.py` | A previsão que o Rafael mandou. Ela não passa no teste. |
| `minha_previsao.py` | Onde você escreve a sua previsão, no exercício. |
| `minhas-respostas.md` | A folha do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas. É o mesmo ambiente da apresentação: o `requirements.txt` da raiz do kit já instala o que essa aula usa. O statsmodels não é preciso aqui: a separação é feita no pandas, linha a linha, para você ver cada conta.

## Como rodar

Na pasta dessa aula:

```bash
python3 decompor.py
python3 decompor.py --corte 2025-10-01
python3 teste_corte.py rafael.py
python3 teste_corte.py
```

O primeiro comando usa a noite de 01/12/2025, a da escala de janeiro. O segundo usa a noite de 01/10/2025, a do exercício. O teste do `rafael.py` termina com `FALHOU` e código 1: é o que a aula mostra. O último testa o seu `minha_previsao.py`. Antes de você escrever a função, ele termina com `FALHOU: a previsão precisa dar um número em toda noite`. Depois de escrever, ele precisa terminar com `PASSOU`.

Os programas também rodam da raiz do kit, por exemplo `python3 04-decompor-sem-antecipar-o-futuro/decompor.py`: eles acham `dados/loja` pelo próprio caminho.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
