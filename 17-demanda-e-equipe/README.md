# Demanda e equipe

O programa que transforma a previsão da venda em número de vendedores e a folha do exercício. Ele lê a venda de 2024 e 2025 e o calendário em `dados/loja`, na raiz do kit do curso.

| Arquivo | O que faz |
|---|---|
| `equipe.py` | Monta a escala de uma semana de janeiro de 2026, feita na noite de 31/12/2025. Para cada número de vendedores, mostra a chance de faltar, quantas unidades devem faltar, quanta capacidade deve ficar parada e quanto isso custa. Monta os cenários do fim de semana com e sem ofertas, com sobreaviso, e testa as regras de escala nos dias de 28/09 a 31/12/2025. |
| `modelo.py` | O modelo calendário + AR(1) e a faixa do dia da aula «Intervalos e cenários», com a função `distribuicao`, que retorna o centro e o desvio da venda do dia no log. Não imprime nada. |
| `meu-plano.md` | A folha do exercício: o plano da semana de 19 a 25/01. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O statsmodels não é necessário.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 equipe.py
python3 equipe.py --falta 12
python3 equipe.py --semana 2026-01-19 --diaria 100 --falta 5
python3 equipe.py --salvar teste.csv
```

O `equipe.py` termina em menos de dez segundos. As opções:

| Opção | O que muda | Padrão |
|---|---|---|
| `--semana` | a segunda-feira da semana: 2026-01-05, 2026-01-12 ou 2026-01-19 | 2026-01-12 |
| `--capacidade` | unidades que um vendedor atende num dia | 40 |
| `--diaria` | diária de um vendedor fixo, em reais | 80 |
| `--falta` | custo de cada unidade que passa da capacidade, em reais | 6 |
| `--aviso` | custo de deixar uma pessoa de sobreaviso, em reais | 20 |
| `--adicional` | quanto quem é chamado do sobreaviso custa a mais que um fixo, em reais | 30 |
| `--salvar` | grava o teste no passado em CSV, uma linha por dia | |

A semana vai até 28 dias depois de 31/12, porque a faixa do dia foi medida até 28 dias na aula «Intervalos e cenários». Outra data dá `--semana aceita 2026-01-05, 2026-01-12 ou 2026-01-19` e o programa para sem calcular. Ele importa o `modelo.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'modelo'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `--salvar` grava, para cada dia do teste, a origem, a venda, a previsão, o desvio no log (`desvio_log`), o número de vendedores de cada regra e o custo que a conta esperava com cada uma.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
