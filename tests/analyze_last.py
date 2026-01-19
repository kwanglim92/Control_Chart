import pandas as pd

df = pd.read_excel('Industrial Check List v3.21.1.xlsx', sheet_name='Last', header=None)
print('Shape:', df.shape)
print()

for i in range(min(40, len(df))):
    row_data = df.iloc[i].tolist()
    # NaN이 아닌 값만 출력
    non_null = [v for v in row_data if pd.notna(v)]
    if non_null:
        print(f'Row {i}: {non_null}')
