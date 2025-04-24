import csv

with open('yourfile.csv', encoding='utf-8') as f:
    reader = csv.reader(f)
    first_row = next(reader)
    col_count = len(first_row)
    print(col_count)
