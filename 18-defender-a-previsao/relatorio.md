# Relatório: a previsão da escala da loja física

Preencha cada campo com um número da saída do `defender.py` e diga de qual parte ele veio. Cabe numa página. Quem lê é o diretor, que decide se a escala troca de previsão.

Comando que gerou os números: `python3 defender.py --horizonte ____`

## 1. A decisão

- O que se prevê: ______
- Quando a escala é montada, e quantos dias antes do dia previsto: ______
- Com que informação (venda até quando, calendário até quando): ______
- O custo do erro que a loja usa: faltar R$ ____ por unidade, sobrar R$ ____ por unidade

## 2. A régua e o modelo, nos mesmos dias

- Período e quantos dias entraram na conta: ______
- Quantos ficaram fora, e por quê: ______

| | WMAPE | viés | custo (R$) | semanas em que erra menos | erro a menos por dia |
|---|---|---|---|---|---|
| régua (mesmo dia, 4 semanas) | | | | é a régua | |
| Holt-Winters | | | | | |
| calendário + AR(1) | | | | | |

O que essa tabela mostra, em duas frases: ______

## 3. O número que vai para a escala

- A regra: ______
- O fator e de onde ele saiu: ______
- O custo, da régua como hoje até a regra nova: R$ ______ a menos em ____ dias
- Quanto disso vem só do fator, e quanto vem do modelo: ______
- Em quantos dias faltou gente com a regra nova: ______

## 4. A faixa

- Quantas vezes a faixa de 80% do modelo pegou a venda, e o que se espera pelo acaso: ______
- E a da régua: ______

## 5. Onde a previsão pode quebrar

Para cada limite, o número que mostra e o que a loja faz.

| Limite | O número | O que a loja faz |
|---|---|---|
| | | |
| | | |
| | | |

## 6. Como rodar de novo e quem acompanha

- Os arquivos e o comando: ______
- A data de corte do teste e o resultado do teste do futuro: ______
- Quem acompanha o erro, com que frequência, e o que faz a loja voltar para a régua: ______

## 7. A recomendação

Três frases no máximo: o que troca, a condição para trocar e o que fica rodando ao lado.
