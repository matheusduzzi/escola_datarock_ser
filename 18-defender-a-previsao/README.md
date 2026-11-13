# Defender a previsão

O programa que monta os números do relatório, o modelo do relatório e o roteiro de defesa. O programa lê a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `modelos.py` | Os modelos da aula «Modelo contra baseline», sem nenhuma mudança: a régua (mesmo dia, 4 semanas), o Holt-Winters e o calendário + AR(1). Não imprime nada. |
| `defender.py` | Faz as previsões de todas as origens, de 31/08/2025 em diante, e imprime as seis partes do relatório: régua e modelos nos mesmos dias, o número da escala, a faixa de 80%, onde a previsão pode quebrar, o teste do futuro e a primeira semana de janeiro. |
| `relatorio.md` | O modelo do relatório, em branco. Você preenche no exercício. |
| `roteiro-defesa.md` | As perguntas que o diretor vai fazer, com espaço para a resposta e o número que a mostra. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. O statsmodels não é necessário.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 defender.py
python3 defender.py --horizonte 14
python3 defender.py --salvar previsoes.csv
```

O `defender.py` termina em poucos segundos. Ele importa o `modelos.py` da mesma pasta: deixe os dois juntos. Se aparecer `No module named 'modelos'`, você está rodando uma cópia fora da pasta da aula. No Windows, troque `python3` por `py`.

O `--horizonte` aceita de 1 a 28 dias, que é até onde a aula «Intervalos e cenários» mediu a faixa. Fora disso, o programa para com uma mensagem e não imprime número nenhum.

O `--salvar` grava uma linha por dia previsto, com a origem, a venda real, a previsão de cada modelo e o número da escala. Abra no pandas ou numa planilha.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
