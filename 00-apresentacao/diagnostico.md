# Diagnóstico: por onde começar em Séries temporais

A Bia é gerente da loja física da Loja Exemplo. Antes de me pedir a previsão de janeiro, ela me mandou três frases. "Em maio a loja vendeu 108 unidades por dia." "No sábado a gente vende uns 209, então deixo estoque para 209." "Rodei um teste na venda e deu p = 0,31, então está provado que ela anda sem voltar a um nível." Cada frase tinha uma conta por trás e uma leitura errada na frente. Antes de responder, eu refiz as contas. As cinco tarefas abaixo são essas contas.

Elas usam o que o curso pede de entrada: datas no pandas, uma função que só olha o passado, distribuição normal, intervalo de confiança e teste de hipótese. O diagnóstico não é prova e não tem nota. Ele mostra por onde você começa. Anote na [folha de respostas](minhas-respostas.md) a conta que fez, o comando que rodou e a saída que apareceu. Só depois compare com as respostas comentadas.

As tarefas 1 e 2 rodam de dentro da pasta `00-apresentacao/`:

```bash
cd 00-apresentacao
python3 tarefa1.py
python3 tarefa2.py
```

No Windows, troque `python3` por `py`. As tarefas 3, 4 e 5 são de lápis e papel ou calculadora. Se uma conta travar, a [revisão rápida](revisao-rapida.md) tem um exemplo curto de cada ideia.

## Tarefa 1. O calendário de maio

`dados/venda_maio.csv` tem a venda da loja física de 1º a 21 de maio de 2025. Uma linha é um dia, com a data e as unidades vendidas. O arquivo tem 18 linhas para 21 dias. Em três dias o sistema caiu e não gravou nada. Em 1º de maio a loja ficou fechada e a linha existe, com 0 unidades.

Em `tarefa1.py`, monte uma série com um dia por linha, de 1º a 21 de maio, em que o dia sem linha no arquivo fique vazio (`NaN`), e não zero. Depois calcule:

| Chave | O que é |
|---|---|
| `dias_no_calendario` | quantos dias a série tem |
| `dias_sem_registro` | quantos dias ficaram vazios |
| `dias_com_zero` | quantos dias têm venda igual a 0 |
| `media_21_dias` | o total dividido pelos 21 dias, como se o dia vazio fosse zero |
| `media_dias_com_registro` | o total dividido pelos dias que têm linha no arquivo |
| `media_dias_abertos` | o total dividido pelos dias com linha e com a loja aberta |

As médias levam uma casa decimal. Guarde tudo no dicionário `resultado` e mostre com `print(resultado)`. Anote na folha:

1. A saída de `print(resultado)`.
2. Qual das três médias responde "quanto a loja vende num dia aberto?" e por quê.
3. O que está errado na frase "em maio a loja vendeu 108 unidades por dia".

## Tarefa 2. Uma média que só olha para trás

A Bia decide a escala de cada dia de manhã, antes de a loja abrir. Ela quer a média das unidades dos 7 dias do calendário anteriores ao dia da decisão, sem contar o próprio dia, que ainda não aconteceu.

Em `tarefa2.py`, escreva a função `media_7_dias_antes(vendas, corte)`. Ela recebe a tabela lida do CSV e a data da decisão. Ela retorna dois valores: a média das unidades nos 7 dias anteriores, com uma casa decimal, e quantos desses 7 dias têm linha no arquivo. O programa já chama a função para 10 e 15 de maio e guarda o resultado em `resultado`. Anote na folha:

1. A saída de `print(resultado)`.
2. Quantos dos 7 dias entraram na média de 10 de maio e por quê.
3. Por que pegar as 7 últimas linhas do arquivo antes da data não dá a mesma conta.
4. O que muda se a média incluir o próprio dia da decisão.

## Tarefa 3. Quanto estoque deixar no sábado

Nos sábados de 2025 até a Black Friday, sem feriado e com o dia completo no sistema, a loja vendeu em média 209 unidades, com desvio-padrão de 25. Suponha que a venda de um sábado siga uma distribuição normal com essa média e esse desvio.

1. Entre quanto e quanto ficam 95% dos sábados? Use 1,96.
2. Se a Bia deixar estoque para 209 unidades, em que fração dos sábados falta peça?
3. Quanto estoque deixar para faltar peça em só 1 de cada 20 sábados? Use 1,645.
4. Os sábados de janeiro vendem menos que os de outubro. O que isso faz com o desvio de 25 e com a conta do item 3?

## Tarefa 4. A média dos sábados e o próximo sábado

A média de 209 vem de 46 sábados. A Bia quer saber duas coisas: "qual é a venda média de um sábado?" e "quanto vou vender no próximo sábado?".

1. Calcule o intervalo de 95% para a média dos sábados. Use 1,96 e o erro-padrão 25 dividido pela raiz de 46.
2. Calcule a faixa de 95% para a venda de um sábado novo. Use 1,96 vezes 25 vezes a raiz de (1 + 1/46).
3. Qual das duas faixas a Bia usa para montar a escala do próximo sábado? Por que a outra é tão mais estreita?

## Tarefa 5. O que um p-valor diz sobre a venda

Um colega rodou um teste na venda diária. A hipótese nula do teste é "a série anda sem voltar a um nível fixo". Com dois anos de dados, o p-valor deu 0,31.

1. A Bia escreveu "então está provado que a venda anda sem voltar a um nível". O que você responderia?
2. Com outra série, o p-valor deu 0,01. O colega escreveu "então a série é estável e qualquer modelo serve para sempre". O que essa conta mostra e o que ela não mostra?
3. Se você rodar o mesmo teste em 20 séries em que a hipótese nula é verdadeira, usando 5% como limite, em quantas você espera um p-valor abaixo de 0,05 só por acaso?

## Depois das cinco tarefas

Compare sua folha com as respostas comentadas da apresentação. A tabela da apresentação diz o que estudar para cada tarefa que travou.
