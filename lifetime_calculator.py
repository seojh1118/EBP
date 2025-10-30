import pandas as pd
import numpy as np 
# from konlpy.tag import Okt # KoNLPy는 현재 오류로 인해 주석 처리

# 1. 데이터 로드 및 전처리
df = pd.read_csv('all_word_trends.csv', index_col='date', parse_dates=True)
df = df.fillna(0) # 결측값(NaN)을 0으로 채움

# 'isPartial' 컬럼은 불필요하므로 제거 (컬럼명이 있다면)
if 'isPartial' in df.columns:
    df = df.drop(columns=['isPartial'])

# 2. 데이터 로드 확인
print("--- 데이터 로드 및 결측치 처리 확인 ---")
print(df.head())
print(df.shape)
print(df.isnull().sum()) 

# 3. 수명 (Y축) 계산 및 라벨링
lifetime_data = {}
feature_data = [] # X축 피쳐 데이터를 모을 리스트

for column in df.columns:
    series = df[column]
    
    # 3-1. 정점(Peak) 찾기
    peak_value = series.max()
    peak_date_index = series.idxmax()
    
    # 3-2. 단어 길이 (X 피쳐 1)
    word = column.replace(" ", "") # 공백 제거 후 길이 계산
    word_len = len(word)
    
    # 3-3. 최대 관심도가 0인 경우 (수집 실패 또는 유행 없음)
    if peak_value == 0:
        lifetime_data[column] = 0 # 수명 0으로 처리
        
        feature_data.append({
            'Word': column, 
            'Word_Length': word_len, 
            'Max_Rising_Slope': 0.0,
            'Total_Active_Months_Raw': 0.0 
        })
        continue # 다음 단어로 이동

    # 4. 피쳐(X축) 계산
    
    # 4-1. 유행 시작점(Start) 찾기 (10% 임계값)
    start_threshold = peak_value * 0.1
    start_index = series[series >= start_threshold].first_valid_index()
    
    # 4-2. 유행 소멸점(End) 임계값 (5% 임계값)
    end_threshold = peak_value * 0.05
            
    # 4-3. 최대 상승 기울기 (X 피쳐 2)
    max_rising_slope = 0.0
    if start_index is not None and start_index < peak_date_index:
        rising_period = series.loc[start_index:peak_date_index]
        if len(rising_period) > 1:
            max_slope = rising_period.diff().max()
            if not pd.isna(max_slope):
                max_rising_slope = max(0.0, max_slope)
    
    # 4-4. [신규] 총 활성 개월 수 (X 피쳐 3)
    total_active_months_raw = (series > 0).sum()
    
    
    # 5. 🔽 [수정됨] 수명 (Lifetime - Y축) 계산
    lifetime_months = 0
    lifetime_status = 0 # 0: 소멸 (기본값)
    end_index = None
    
    if start_index is not None:
        # [수정] '시작점' 이후의 모든 데이터를 가져옴
        after_start_series = series[series.index >= start_index]
        
        # [수정] 5% 임계값 아래로 떨어진 '첫 번째' 지점을 end_index로 설정 (단순 로직)
        end_index = after_start_series[after_start_series < end_threshold].first_valid_index()
    
        if start_index and end_index:
            # 기간 차이를 개월 수로 변환
            lifetime_months = (end_index.year - start_index.year) * 12 + (end_index.month - start_index.month)
            lifetime_status = max(0, lifetime_months)
        else:
            # end_index를 못찾음 (아직 소멸 안됨)
            lifetime_status = 'Ongoing' 
    else:
        # start_index가 None (유행 시작점 불명) -> 수명 0 처리
        lifetime_status = 0
            
    # Y축 데이터 저장
    lifetime_data[column] = lifetime_status 

    # X축 피쳐 데이터 저장
    feature_data.append({
        'Word': column, 
        'Word_Length': word_len, 
        'Max_Rising_Slope': max_rising_slope,
        'Total_Active_Months_Raw': total_active_months_raw
    })

# 6. 결과 출력 및 합치기
lifetime_df = pd.DataFrame(lifetime_data.items(), columns=['Word', 'Lifetime (Months)'])
feature_df = pd.DataFrame(feature_data)

# 'Word'를 기준으로 두 DataFrame 병합
final_dataset = pd.merge(lifetime_df, feature_df, on='Word')

# 7. CSV 파일로 저장
output_file = 'final_training_dataset.csv'
final_dataset.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n--- 최종 훈련 데이터셋 생성 완료 (v2) ---")
print(final_dataset.head())
print(f"✅ 데이터가 {output_file} 에 저장되었습니다.")