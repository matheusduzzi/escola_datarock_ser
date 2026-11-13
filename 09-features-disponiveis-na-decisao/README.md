# Features disponíveis na decisão

Os programas da aula e do exercício. Eles leem a venda da loja física e o calendário em `dados/loja`, na raiz do kit do curso. Essa pasta não traz cópia dos dados.

| Arquivo | O que faz |
|---|---|
| `features.py` | Monta a tabela do Rafael e a tabela da aula. Mostra a linha da Black Friday, a correlação de cada coluna com a venda, o erro de uma regressão com cada tabela e o efeito do `shift` no arquivo sem os dias faltando. |
| `teste_futuro.py` | O teste que pega informação do futuro. Para cada dia previsto de 2025, apaga a venda depois da noite da decisão e calcula a linha de novo. |
| `minhas_features.py` | O arquivo de partida do exercício, com a função `features_14` para completar. |
| `minhas-respostas.md` | A folha de respostas do exercício. |

## Do que você precisa

Python 3.9 ou mais novo, com o pandas, como no resto do curso. O NumPy vem junto. Não precisa de mais nada.

## Como rodar

De dentro da pasta dessa aula:

```bash
python3 features.py
python3 teste_futuro.py rafael
python3 teste_futuro.py aula
python3 teste_futuro.py aula --h 14
```

O `teste_futuro.py` sai com código 0 quando nenhuma coluna muda e com código 1 quando alguma muda. Com a tabela do Rafael e com a tabela da aula em `--h 14`, o código 1 é o resultado certo: as duas usam venda de depois da decisão. No terminal, `echo $?` logo depois mostra o código. No Windows, troque `python3` por `py` e use `echo %errorlevel%`.

Cada rodada do teste calcula a tabela 366 vezes: uma com tudo e uma em cada corte. Leva cerca de um segundo.

## O exercício

```bash
python3 minhas_features.py
```

Antes de você mexer, a saída começa com `colunas: dia_semana, feriado, loja_fechada, promocao` e o teste passa com código 0. Isso não termina a tarefa: uma tabela só com o calendário não usa a venda. O exercício pede as cinco colunas de venda e o teste passando com elas.

Se aparecer `No module named 'features'`, você está rodando uma cópia do `minhas_features.py` fora da pasta da aula. Ele precisa ficar ao lado do `features.py` e do `teste_futuro.py`.

## Se precisar de ajuda

Deixe um comentário na aula. Conte o objetivo, o comando que você rodou, a saída que apareceu e o que já tentou, sem dados pessoais.
