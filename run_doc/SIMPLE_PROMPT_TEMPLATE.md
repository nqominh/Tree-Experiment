# Role Play
Suppose you are an expert in table analysis and your task is to provide answers to questions based on the content of the table.

# Chain-of-thought
Let's think step by step:
1. Fully understand the question and extract the necessary information.
2. Clearly understand the content of the table, including the structure of the table, the meaning and formatting of each row and column header.
3. Based on the question, select the row and column headers in the table that are most relevant to it and find the corresponding cells based on them.
4. According to the requirements of the question, perform statistical, calculation, ranking, or other operations on the cells you selected.

# Output Control
1. The final answer should be one-line and strictly follow the format: "[Final Answer]: AnswerName1, AnswerName2...".
2. Ensure the "AnswerName" is a number or entity name, as short as possible, without any explanation.
3. Note: If the answer involves decimals, always keep it to two decimals.

# Table
{html_section}

# Question
{question}

Emphasize: you need to make sure your final answer is formatted in this way: [Final Answer]: AnswerName1, AnswerName2...
