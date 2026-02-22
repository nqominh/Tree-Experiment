# 1. TASK CONTEXT
You are a precise table reasoning system. You are given a structured table with explicit column and row hierarchies, and you must answer a question strictly from the table data.

---

# 2. TONE CONTEXT
Be analytical, careful, and deterministic. Avoid speculation. Do not hallucinate values. The table is the ONLY source of truth.

---

# 3. BACKGROUND DATA

## How to Read the Table Structure

The table has two hierarchy sections before the HTML:

**[COLUMN STRUCTURE]** — Lists all column headers as an indented tree.
Each level of indentation (2 spaces) means a sub-column under the parent above it.

Example:
```
Average hours per day
  Married mothers
    Employed full time
    Employed part time
  Married fathers
    Employed full time
```
Means: "Employed full time" is under "Married mothers" which is under "Average hours per day".
The full column path is: `Average hours per day > Married mothers > Employed full time`

**[ROW STRUCTURE]** — Lists all row labels as an indented tree.
Same indentation rules apply. A deeper-indented row is a sub-category of the row above it.

Example:
```
Household activities
  Housework
  Food preparation
```
Means: "Housework" is a sub-category under "Household activities".

**[TABLE HTML]** — The raw HTML table. Use this to look up the actual cell values after identifying the correct row and column from the structure above.

---

# 4. DETAILED TASK DESCRIPTION & RULES

Step-by-step:
1. Read [COLUMN STRUCTURE] to find the column(s) relevant to the question. Note the full path.
2. Read [ROW STRUCTURE] to find the row(s) relevant to the question. Note the full path.
3. Locate the cell at the intersection of that row and column in the HTML table.
4. Perform any required calculation (mean, sum, difference, etc.).
5. Output the final answer.

Strict Rules:
- Do NOT use external knowledge.
- Do NOT assume or interpolate missing values. If a cell is empty or "No contacts", treat it as unavailable.
- If the answer is not derivable from the table, respond: `[Final Answer]: Not answerable`
- Numbers: output only the number, rounded as specified in the question. No units unless shown in the table.
- Text: match table wording exactly.
- Do NOT add explanation after `[Final Answer]:`.

---

# 5. EXAMPLES

**Example 1 — Multi-level column lookup:**
Column structure:
```
Average hours per day
  Married mothers
    Employed full time
```
Row structure:
```
Household activities
  Housework
```
Question: How many hours do employed full-time married mothers spend on Housework?
Reasoning: Column path = `Average hours per day > Married mothers > Employed full time`. Row = `Household activities > Housework`. Find the intersecting cell.
[Final Answer]: 0.81

---

**Example 2 — Percentage calculation:**
Question: What percentage of total holiday spending in North America came from air travel?
Reasoning: Air Spending for North America, Holiday-All = 4,138. Total Spending = 4,144. Percentage = 4138/4144 * 100 = 99.86%.
[Final Answer]: 99.86

---

**Example 3 — Not answerable:**
Question: What is the GDP growth for North America in 2020?
[Final Answer]: Not answerable

---

# 6. CONVERSATION HISTORY
This is an isolated question. No prior conversation context applies.

---

# 7. IMMEDIATE TASK

[COLUMN STRUCTURE]
Table 5.01: Visits and spending in £millions abroad by mode of travel, region of visit and purpose of visit 2023
  This worksheet contains one table. Freeze panes is turned on.
Region of Visit
Purpose of Visit
Air Visits
Air Spending
Sea Visits
Sea Spending
Channel Tunnel Visits
Channel Tunnel Spending
Total Visits
Total Spending

[ROW STRUCTURE]
(none — rows are identified by Region of Visit × Purpose of Visit)

[TABLE HTML]
<table border="0" cellpadding="0" cellspacing="0" id="sheet0" class="sheet0 gridlines">
        <col class="col0">
        <col class="col1">
        <col class="col2">
        <col class="col3">
        <col class="col4">
        <col class="col5">
        <col class="col6">
        <col class="col7">
        <col class="col8">
        <col class="col9">
        <col class="col10">
        <thead>
          <tr class="row0">
            <th class="column0 style4 s">Table 5.01: Visits and spending in £millions abroad by mode of travel, region of visit and purpose of visit 2023</th>
            <th class="column1 style4 null"></th>
            <th class="column2 style5 null"></th>
            <th class="column3 style5 null"></th>
            <th class="column4 style5 null"></th>
            <th class="column5 style5 null"></th>
            <th class="column6 style5 null"></th>
            <th class="column7 style5 null"></th>
            <th class="column8 style5 null"></th>
            <th class="column9 style5 null"></th>
            <th class="column10">&nbsp;</th>
          </tr>
          <tr class="row3">
            <th class="column0 style7 s">Region of Visit</th>
            <th class="column1 style7 s">Purpose of Visit</th>
            <th class="column2 style8 s">Air Visits</th>
            <th class="column3 style8 s">Air Spending</th>
            <th class="column4 style8 s">Sea Visits</th>
            <th class="column5 style8 s">Sea Spending</th>
            <th class="column6 style8 s">Channel Tunnel Visits</th>
            <th class="column7 style8 s">Channel Tunnel Spending</th>
            <th class="column8 style8 s">Total Visits</th>
            <th class="column9 style8 s">Total Spending</th>
            <th class="column10">&nbsp;</th>
          </tr>
        </thead>
        <tbody>
          <tr class="row4">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">Holiday - All</td>
            <td class="column2 style11 n">2,292,000</td>
            <td class="column3 style11 n">4,138</td>
            <td class="column4 style11 n">3,000</td>
            <td class="column5 style11 n">6</td>
            <td class="column6 style11 s">No contacts</td>
            <td class="column7 style11 s">No contacts</td>
            <td class="column8 style11 n">2,295,000</td>
            <td class="column9 style11 n">4,144</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row5">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">Holiday - Inclusive tour</td>
            <td class="column2 style11 n">687,000</td>
            <td class="column3 style11 n">1,457</td>
            <td class="column4 style11 n">2,000</td>
            <td class="column5 style11 n">5</td>
            <td class="column6 style11 s">No contacts</td>
            <td class="column7 style11 s">No contacts</td>
            <td class="column8 style11 n">689,000</td>
            <td class="column9 style11 n">1,463</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row6">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">Business</td>
            <td class="column2 style11 n">779,000</td>
            <td class="column3 style11 n">1,438</td>
            <td class="column4 style11 s">No contacts</td>
            <td class="column5 style11 s">No contacts</td>
            <td class="column6 style11 s">No contacts</td>
            <td class="column7 style11 s">No contacts</td>
            <td class="column8 style11 n">779,000</td>
            <td class="column9 style11 n">1,438</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row7">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">Visit friends or relatives</td>
            <td class="column2 style11 n">1,399,000</td>
            <td class="column3 style11 n">1,278</td>
            <td class="column4 style11 n">1,000</td>
            <td class="column5 style11 n">1</td>
            <td class="column6 style11 n">1,000</td>
            <td class="column7 style11 n">2</td>
            <td class="column8 style11 n">1,401,000</td>
            <td class="column9 style11 n">1,281</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row8">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">Miscellaneous</td>
            <td class="column2 style11 n">62,000</td>
            <td class="column3 style11 n">91</td>
            <td class="column4 style11 s">No contacts</td>
            <td class="column5 style11 s">No contacts</td>
            <td class="column6 style11 s">No contacts</td>
            <td class="column7 style11 s">No contacts</td>
            <td class="column8 style11 n">62,000</td>
            <td class="column9 style11 n">91</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row9">
            <td class="column0 style9 s">North America</td>
            <td class="column1 style10 s">All visits</td>
            <td class="column2 style11 n">4,531,000</td>
            <td class="column3 style11 n">6,945</td>
            <td class="column4 style11 n">4,000</td>
            <td class="column5 style11 n">6</td>
            <td class="column6 style11 n">1,000</td>
            <td class="column7 style11 n">2</td>
            <td class="column8 style11 n">4,537,000</td>
            <td class="column9 style11 n">6,954</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row10">
            <td class="column0 style9 s">Europe</td>
            <td class="column1 style10 s">Holiday - All</td>
            <td class="column2 style11 n">40,311,000</td>
            <td class="column3 style11 n">30,212</td>
            <td class="column4 style11 n">2,908,000</td>
            <td class="column5 style11 n">1,911</td>
            <td class="column6 style11 n">3,014,000</td>
            <td class="column7 style11 n">2,540</td>
            <td class="column8 style11 n">46,233,000</td>
            <td class="column9 style11 n">34,662</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row40">
            <td class="column0 style9 s">Total World</td>
            <td class="column1 style10 s">Holiday - All</td>
            <td class="column2 style11 n">48,647,000</td>
            <td class="column3 style11 n">43,514</td>
            <td class="column4 style11 n">3,865,000</td>
            <td class="column5 style11 n">3,737</td>
            <td class="column6 style11 n">3,017,000</td>
            <td class="column7 style11 n">2,552</td>
            <td class="column8 style11 n">55,529,000</td>
            <td class="column9 style11 n">49,804</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row41">
            <td class="column0 style9 s">Total World</td>
            <td class="column1 style10 s">Holiday - Inclusive tour</td>
            <td class="column2 style11 n">20,269,000</td>
            <td class="column3 style11 n">19,163</td>
            <td class="column4 style11 n">1,429,000</td>
            <td class="column5 style11 n">2,232</td>
            <td class="column6 style11 n">486,000</td>
            <td class="column7 style11 n">678</td>
            <td class="column8 style11 n">22,184,000</td>
            <td class="column9 style11 n">22,073</td>
            <td class="column10">&nbsp;</td>
          </tr>
          <tr class="row45">
            <td class="column0 style9 s">Total World</td>
            <td class="column1 style10 s">All visits</td>
            <td class="column2 style11 n">75,858,000</td>
            <td class="column3 style11 n">64,187</td>
            <td class="column4 style11 n">5,330,000</td>
            <td class="column5 style11 n">4,523</td>
            <td class="column6 style11 n">5,017,000</td>
            <td class="column7 style11 n">3,726</td>
            <td class="column8 style11 n">86,205,000</td>
            <td class="column9 style11 n">72,436</td>
            <td class="column10">&nbsp;</td>
          </tr>
        </tbody>
    </table>

**Question:**
Infer the percentage of spending contributed by air travel for holiday-inclusive tours in North America.

---

# 8. THINKING (Scratchpad)
Before answering, work through these steps:
- Step 1: Identify the target row using [ROW STRUCTURE] or row labels: Region = "North America", Purpose = "Holiday - Inclusive tour"
- Step 2: Identify the target columns: "Air Spending" and "Total Spending"
- Step 3: Look up both values from the HTML table
- Step 4: Calculate: Air Spending / Total Spending × 100
- Step 5: Verify the result is fully supported by the table

Then output ONLY:

[Final Answer]: <number>
