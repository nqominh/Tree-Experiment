# New Backend Shadow Comparison Report

- Question table count: 46
- Identical files: 0
- Changed files: 46
- Missing files: 0

- Result: DIFF

## Changed Files
- activitytime-table01.txt
- activitytime-table02.txt
- activitytime-table04.txt
- activitytime-table05.txt
- agriculture-table01.txt
- agriculture-table02.txt
- agriculture-table03.txt
- agriculture-table04.txt
- biology-table01.txt
- biology-table02.txt
- economy-table01.txt
- economy-table02.txt
- economy-table132.txt
- education-table01.txt
- education-table03.txt
- education-table04.txt
- education-table05.txt
- education-table06.txt
- employment-table03.txt
- employment-table04.txt
- employment-table06.txt
- employment-table07.txt
- employment-table09.txt
- employment-table14.txt
- employment-table16.txt
- employment-table18.txt
- employment-table21.txt
- employment-table22.txt
- employment-table23.txt
- employment-table25.txt
- employment-table27.txt
- environment-table02.txt
- geography-table01.txt
- health-table01.txt
- injuries-table04.txt
- injuries-table06.txt
- injuries-table08.txt
- injuries-table10.txt
- science-table01.txt
- society-table83.txt
- society-table84.txt
- welfare-table02.txt
- welfare-table04.txt
- welfare-table05.txt
- welfare-table07.txt
- welfare-table09.txt

## Diff Snippets (first 15 changed files)
### employment-table03.txt
```diff
--- old/employment-table03.txt

+++ new/employment-table03.txt

@@ -1,30 +1,43 @@

 [COLUMN STRUCTURE]
-Age, sex, and race
-  Age, sex, and race
-2023
-  Civilian
-noninsti-
-tutional
-population
-2023
-  Civilian labor force
-2023
-  Civilian labor force
-2023
-  Civilian labor force
-2023
-  Civilian labor force
-2023
-  Civilian labor force
-2023
-  Civilian labor force
-2023
-  Not
-in
-labor
-force
+Civilian noninsti- tutional population
+Civilian labor force
+  Total
+  Percent of population
+  Employed
+    Total
+    Percent of population
+  Unemployed
+    Number
+    Percent of labor force
+Not in labor force
 
 [ROW STRUCTURE]
-(none)
+16 years and over
+16 to 19 years
+16 to 17 years
+18 to 19 years
+20 to 24 years
+25 to 54 years
+25 to 34 years
+25 to 29 years
+30 to 34 years
+35 to 44 years
+35 to 39 years
+40 to 44 years
+45 to 54 years
+45 to 49 years
+50 to 54 years
+55 to 64 years
+55 to 59 years
+60 to 64 years
+65 years and over
+65 to 69 years
+70 to 74 years
+75 years and over
+Men
+Women
+WHITE
+BLACK OR AFRICAN AMERICAN
+ASIAN
 
 [TABLE HTML]
```

### employment-table04.txt
```diff
--- old/employment-table04.txt

+++ new/employment-table04.txt

@@ -1,14 +1,17 @@

 [COLUMN STRUCTURE]
-HOUSEHOLD DATA
-ANNUAL AVERAGES 
-4. Employment status of the Hispanic or Latino population by age and sex
+2023
+  Civilian noninsti- tutional population
+  Civilian labor force
+    Total
+    Percent of population
+    Employed
+      Total
+      Percent of population
+    Unemployed
+      Number
+      Percent of labor force
+  Not in labor force
 
 [ROW STRUCTURE]
-[Numbers in thousands]
-Age and sex
-Age and sex
-Age and sex
-Age and sex
-HISPANIC OR LATINO ETHNICITY
 16 years and over
 16 to 19 years
@@ -34,49 +37,5 @@

 75 years and over
 Men
-16 years and over
-16 to 19 years
-16 to 17 years
-18 to 19 years
-20 to 24 years
-25 to 54 years
-25 to 34 years
-25 to 29 years
-30 to 34 years
-35 to 44 years
-35 to 39 years
-40 to 44 years
-45 to 54 years
-45 to 49 years
-50 to 54 years
-55 to 64 years
-55 to 59 years
-60 to 64 years
-65 years and over
-65 to 69 years
-70 to 74 years
-75 years and over
 Women
-16 years and over
-16 to 19 years
-16 to 17 years
-18 to 19 years
-20 to 24 years
-25 to 54 years
-25 to 34 years
-25 to 29 years
-30 to 34 years
-35 to 44 years
-35 to 39 years
-40 to 44 years
-45 to 54 years
-45 to 49 years
-50 to 54 years
-55 to 64 years
-55 to 59 years
-60 to 64 years
-65 years and over
-65 to 69 years
-70 to 74 years
-75 years and over
 NOTE: Persons whose ethnicity is identified as Hispanic or Latino may be of any race. Updated population controls are introduced annually with the release of January data.
 
```

### employment-table06.txt
```diff
--- old/employment-table06.txt

+++ new/employment-table06.txt

@@ -1,13 +1,18 @@

 [COLUMN STRUCTURE]
-HOUSEHOLD DATA
-ANNUAL AVERAGES 
-6. Employment status of the Hispanic or Latino population by sex, age, and detailed ethnic group
+Hispanic or Latino ethnicity
+  Total(1)
+    2022
+    2023
+  Mexican
+    2022
+    2023
+  Puerto Rican
+    2022
+    2023
+  Cuban
+    2022
+    2023
 
 [ROW STRUCTURE]
-[Numbers in thousands]
-Employment status, sex, and age
-Employment status, sex, and age
-Employment status, sex, and age
-TOTAL
 Civilian noninstitutional population
 Civilian labor force
@@ -19,48 +24,8 @@

 Not in labor force
 Men, 16 years and over
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
-Not in labor force
 Men, 20 years and over
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
-Not in labor force
 Women, 16 years and over
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
-Not in labor force
 Women, 20 years and over
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
-Not in labor force
 Both sexes, 16 to 19 years
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
-Not in labor force
 Footnotes:
 (1) Includes persons of Central or South American origin and of other Hispanic or Latino ethnicity, not shown separately.
```

### employment-table07.txt
```diff
--- old/employment-table07.txt

+++ new/employment-table07.txt

@@ -1,19 +1,16 @@

 [COLUMN STRUCTURE]
-HOUSEHOLD DATA
-ANNUAL AVERAGES
-7. Employment status of the civilian noninstitutional population 25 years and over by educational attainment, sex, race, and Hispanic or Latino ethnicity
+2023
+  Less than a high school diploma
+  High school graduates, no college(1)
+  Some college or associate degree
+    Total
+    Some college, no degree
+    Associate degree
+  Bachelor's degree and higher
+    Total(2)
+    Bachelor's degree only
+    Advanced degree
 
 [ROW STRUCTURE]
-[Numbers in thousands]
-Employment status,
- sex, race, and Hispanic
- or Latino ethnicity
-Employment status,
- sex, race, and Hispanic
- or Latino ethnicity
-Employment status,
- sex, race, and Hispanic
- or Latino ethnicity
-TOTAL
 Civilian noninstitutional population
 Civilian labor force
@@ -24,51 +21,9 @@

 Unemployment rate
 Men
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
 Women
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
 White
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
 Black or African American
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
 Asian
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
-Employment-population ratio
-Unemployed
-Unemployment rate
 Hispanic or Latino ethnicity
-Civilian noninstitutional population
-Civilian labor force
-Participation rate
-Employed
```

### employment-table09.txt
```diff
--- old/employment-table09.txt

+++ new/employment-table09.txt

@@ -1,28 +1,23 @@

 [COLUMN STRUCTURE]
-Occupation
 Total
-  16 years
-and over
+  16 years and over
+    2022
+    2023
 Men
-  16 years
-and over
-  16 years
-and over
-  20 years
-and over
-  20 years
-and over
+  16 years and over
+    2022
+    2023
+  20 years and over
+    2022
+    2023
 Women
-  16 years
-and over
-  16 years
-and over
-  20 years
-and over
-  20 years
-and over
+  16 years and over
+    2022
+    2023
+  20 years and over
+    2022
+    2023
 
 [ROW STRUCTURE]
-Occupation
 Total
 Management, professional, and related occupations
```

### employment-table14.txt
```diff
--- old/employment-table14.txt

+++ new/employment-table14.txt

@@ -1,16 +1,17 @@

 [COLUMN STRUCTURE]
-Category
-Hispanic or Latino ethnicity
-  Total(1)
-  Total(1)
-  Mexican
-  Mexican
-  Puerto Rican
-  Puerto Rican
-  Cuban
-  Cuban
+Total(1)
+  2022
+  2023
+Mexican
+  2022
+  2023
+Puerto Rican
+  2022
+  2023
+Cuban
+  2022
+  2023
 
 [ROW STRUCTURE]
-Category
 Total, 16 years and over
 Men
@@ -51,10 +52,8 @@

 Self-employed workers, unincorporated
 Nonagricultural industries
-Wage and salary workers(3)
 Government
 Private industries
 Private households
 Other industries
-Self-employed workers, unincorporated
 FULL- OR PART-TIME STATUS(4)
 Full-time workers
```

### employment-table16.txt
```diff
--- old/employment-table16.txt

+++ new/employment-table16.txt

@@ -1,32 +1,33 @@

 [COLUMN STRUCTURE]
-Age and sex
-  Age and sex
-2023
-  Agriculture and related industries
-2023
-  Agriculture and related industries
-2023
-  Agriculture and related industries
-2023
-  Agriculture and related industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
-2023
-  Nonagricultural industries
+Agriculture and related industries
+  Total
+  Wage and salary workers(1)
+  Self- employed workers, unincor- porated
+  Unpaid family workers
+Nonagricultural industries
+  Total
+  Wage and salary workers(1)
+    Total
+    Private industries
+      Total
+      Private household workers
+      Other private industries
+    Govern- ment
+  Self- employed workers, unincor- porated
+  Unpaid family workers
 
 [ROW STRUCTURE]
-(none)
+Total, 16 years and over
+16 to 19 years
+16 to 17 years
+18 to 19 years
+20 to 24 years
+25 to 34 years
+35 to 44 years
+45 to 54 years
+55 to 64 years
+65 years and over
+Men, 16 years and over
+Women, 16 years and over
 
 [TABLE HTML]
```

### employment-table18.txt
```diff
--- old/employment-table18.txt

+++ new/employment-table18.txt

@@ -1,16 +1,25 @@

 [COLUMN STRUCTURE]
-HOUSEHOLD DATA
-ANNUAL AVERAGES
-17. Employed persons by industry, sex, race, and occupation
+2023
+  Total employed
+  Management, professional, and related occupations
+    Management, business, and financial operations occupations
+    Professional and related occupations
+  Service occupations
+    Protective service occupations
+    Service occupations, except protective
+  Sales and office occupations
+    Sales and related occupations
+    Office and adminis- trative support occupations
+  Natural resources, construction, and maintenance occupations
+    Farming, fishing, and forestry occupations
+    Construc- tion and extraction occupations
+    Instal- lation, mainte- nance, and repair occupations
+  Production, transportation, and material moving occupations
+    Production occupations
+    Transpor- tation and material moving occupations
 
 [ROW STRUCTURE]
-[In thousands]
-Industry, sex, and race
-Industry, sex, and race
-Industry, sex, and race
-TOTAL
 Agriculture and related
-Mining, quarrying, and
-oil and gas extraction
+Mining, quarrying, and oil and gas extraction
 Construction
 Manufacturing
@@ -31,108 +40,8 @@

 Public administration
 Men
-Agriculture and related
-Mining, quarrying, and
-oil and gas extraction
-Construction
-Manufacturing
-Durable goods
-Nondurable goods
-Wholesale and retail trade
-Wholesale trade
-Retail trade
-Transportation and utilities
-Information
-Financial activities
-Professional and business services
-Education and health services
-Leisure and hospitality
-Other services
-Other services, except private households
-Private households
-Public administration
 Women
-Agriculture and related
-Mining, quarrying, and
-oil and gas extraction
-Construction
-Manufacturing
-Durable goods
-Nondurable goods
-Wholesale and retail trade
-Wholesale trade
-Retail trade
-Transportation and utilities
-Information
-Financial activities
-Professional and business services
-Education and health services
-Leisure and hospitality
-Other services
-Other services, except private households
```

### employment-table22.txt
```diff
--- old/employment-table22.txt

+++ new/employment-table22.txt

@@ -1,12 +1,14 @@

 [COLUMN STRUCTURE]
-HOUSEHOLD DATA
-ANNUAL AVERAGES 
-20. Persons at work 1 to 34 hours in all and in nonagricultural industries by reason for working less than 35 hours and usual full- or part-time status
+2023
+  All industries
+    Total
+    Usually work full time
+    Usually work part time
+  Nonagricultural industries
+    Total
+    Usually work full time
+    Usually work part time
 
 [ROW STRUCTURE]
-[Numbers in thousands]
-Reason for working less than 35 hours
-Reason for working less than 35 hours
-Reason for working less than 35 hours
 Total, at work 1 to 34 hours
 Economic reasons
@@ -27,5 +29,5 @@

 Average hours, economic reasons
 Average hours, noneconomic reasons
-NOTE:  Full time is 35 hours or more per week; part time is less than 35 hours. Updated population controls are introduced annually with the release of January data. Dash indicates no data or data that do not meet publication criteria (value not shown where base is less than 35,000).
+NOTE: Full time is 35 hours or more per week; part time is less than 35 hours. Updated population controls are introduced annually with the release of January data. Dash indicates no data or data that do not meet publication criteria (value not shown where base is less than 35,000).
 
 [TABLE HTML]
```

### employment-table21.txt
```diff
--- old/employment-table21.txt

+++ new/employment-table21.txt

@@ -1,20 +1,28 @@

 [COLUMN STRUCTURE]
-Hours of work
-  Hours of work
-2023
-  Persons at work
-2023
-  Persons at work
-2023
-  Persons at work
-2023
-  Percent distribution
-2023
-  Percent distribution
-2023
-  Percent distribution
+Persons at work
+  All industries
+  Agriculture and related industries
+  Nonagricultural industries
+Percent distribution
+  All industries
+  Agriculture and related industries
+  Nonagricultural industries
 
 [ROW STRUCTURE]
-(none)
+Total, persons at work
+1 to 34 hours
+1 to 4 hours
+5 to 14 hours
+15 to 29 hours
+30 to 34 hours
+35 hours and over
+35 to 39 hours
+40 hours
+41 hours and over
+41 to 48 hours
+49 to 59 hours
+60 hours and over
+Average hours, total at work
+Average hours, persons who usually work full time
 
 [TABLE HTML]
```

### employment-table23.txt
```diff
--- old/employment-table23.txt

+++ new/employment-table23.txt

@@ -1,28 +1,36 @@

 [COLUMN STRUCTURE]
-Industry and class of worker
-  Industry and class of worker
-2023
+Total at work
+Worked 1 to 34 hours
   Total
-at
-work
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked
-35 hours
-or more
-2023
-  Average hours
-2023
-  Average hours
+  For economic reasons
+  For noneconomic reasons
+    Usually work full time
+    Usually work part time
+Worked 35 hours or more
+Average hours
+  Total at work
+  Persons who usually work full time
 
 [ROW STRUCTURE]
-(none)
+Total, nonagricultural industries
+Wage and salary workers(1)
+Mining, quarrying, and oil and gas extraction
+Construction
+Manufacturing
+Durable goods
+Nondurable goods
+Wholesale and retail trade
+Transportation and utilities
+Information
+Financial activities
+Professional and business services
+Education and health services
+Leisure and hospitality
+Other services
+Other services, except private households
+Private households
+Public administration
+Self-employed workers, unincorporated
+Unpaid family workers
 
 [TABLE HTML]
```

### employment-table25.txt
```diff
--- old/employment-table25.txt

+++ new/employment-table25.txt

@@ -1,28 +1,32 @@

 [COLUMN STRUCTURE]
-Occupation and sex
-  Occupation and sex
-2023
+Total at work
+Worked 1 to 34 hours
   Total
-at
-work
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked 1 to 34 hours
-2023
-  Worked
-35 hours
-or more
-2023
-  Average hours
-2023
-  Average hours
+  For economic reasons
+  For noneconomic reasons
+    Usually work full time
+    Usually work part time
+Worked 35 hours or more
+Average hours
+  Total at work
+  Persons who usually work full time
 
 [ROW STRUCTURE]
-(none)
+Total, 16 years and over
+Management, professional, and related occupations
+Management, business, and financial operations occupations
+Professional and related occupations
+Service occupations
+Sales and office occupations
+Sales and related occupations
+Office and administrative support occupations
+Natural resources, construction, and maintenance occupations(1)
+Construction and extraction occupations
+Installation, maintenance, and repair occupations
+Production, transportation, and material moving occupations
+Production occupations
+Transportation and material moving occupations
+Men, 16 years and over
+Women, 16 years and over
 
 [TABLE HTML]
```

### employment-table27.txt
```diff
--- old/employment-table27.txt

+++ new/employment-table27.txt

@@ -1,4 +1,3 @@

 [COLUMN STRUCTURE]
-Occupation
 Total unemployed
   2022
@@ -6,12 +5,14 @@

 Unemployment rates
   Total
-  Total
+    2022
+    2023
   Men
-  Men
+    2022
+    2023
   Women
-  Women
+    2022
+    2023
 
 [ROW STRUCTURE]
-Occupation
 Total, 16 years and over(1)
 Management, professional, and related occupations
```

### economy-table132.txt
```diff
--- old/economy-table132.txt

+++ new/economy-table132.txt

@@ -1,37 +1,18 @@

 [COLUMN STRUCTURE]
-Table 1C. Chained Consumer Price Index for All Urban Consumers (C-CPI-U): U.S. city average, by expenditure category and commodity and service group
+Item and group
+  Expenditure category
+Relative importance 2022
+Unadjusted indexes
+  Dec. 2024
+  Jan. 2024
+Unadjusted percent change to Jan. 2024 from--
+  Jan. 2023
+  Dec. 2024
 
 [ROW STRUCTURE]
-0
 0
 1
 2
 3
-3
-2
-1
-2
-2
-2
-1
-1
-2
-3
-2
-1
-2
-2
-1
-1
-2
-2
-1
-0
-0
-0
-1
-0
-1
-0
 
 [TABLE HTML]
```

### injuries-table04.txt
```diff
--- old/injuries-table04.txt

+++ new/injuries-table04.txt

@@ -1,8 +1,7 @@

 [COLUMN STRUCTURE]
-Worker Characteristics
 Total fatal injuries (number)
-Event or exposure(1)
-  Transportation incidents(2)
-  Violence and other injuries by persons or animals(3)
+Event or exposure (1)
+  Transportation incidents (2)
+  Violence and other injuries by persons or animals (3)
   Contact with objects and equipment
   Falls, slips, trips
@@ -13,6 +12,6 @@

 Total
 Employee status
-Wage and salary(4)
-Self-employed(5)
+Wage and salary (4)
+Self-employed (5)
 Gender
 Women
@@ -28,5 +27,5 @@

 55 to 64 years
 65 years and over
-Race or ethnic origin(6)
+Race or ethnic origin (6)
 White, non-Hispanic
 Black or African-American, non-Hispanic
```
