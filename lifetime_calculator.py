import pandas as pd
import numpy as np 
# from konlpy.tag import Okt # KoNLPy는 오류, 주석 처리

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
    
    # 3-2. 단어 길이 (피처 1)
    word = column.replace(" ", "") # 공백 제거 후 길이 계산
    word_len = len(word)
    
    # 3-3. 최대 관심도가 0인 경우 (수집 실패 또는 유행 없음)
    if peak_value == 0:
        lifetime_data[column] = 0 # 수명 0으로 처리
        max_rising_slope = 0
        total_active_months_raw = 0
    
    else:
        # 3-4. 유행 시작점(Start) 찾기
        start_threshold = peak_value * 0.1 # 최대치의 10%
        start_index = series[series >= start_threshold].first_valid_index()

        # 3-5. 유행 종료점(End) 찾기
        end_threshold = peak_value * 0.05 # 최대치의 5% (기존 로직 유지)
        end_index = None
        
        if start_index is not None:
            # [수정] '시작점' 이후의 모든 데이터를 가져옴
            after_start_series = series[series.index >= start_index]
            
            # [수정] 5% 임계값 아래로 떨어진 '첫 번째' 지점을 end_index로 설정 (단순 로직)
            end_index = after_start_series[after_start_series < end_threshold].first_valid_index()
        
        # 3-6. 최대 상승 기울기 (피처 2)
        max_rising_slope = 0.0
        if start_index is not None and start_index < peak_date_index:
            rising_period = series.loc[start_index:peak_date_index]
            if len(rising_period) > 1:
                slopes = rising_period.diff().fillna(0) # 차분(변화량)
                max_slope_val = slopes[slopes > 0].max() # 상승하는 변화량 중 최대값
                if not pd.isna(max_slope_val):
                    max_rising_slope = max_slope_val

        # 3-7. [참고] 총 활성 개월 수 (Data Leakage 가능성 있음)
        total_active_months_raw = (series > start_threshold).sum()
        
        # 3-8. 수명(Y) 계산
        if start_index and end_index:
            # 기간 차이를 개월 수로 변환
            lifetime_months = (end_index.year - start_index.year) * 12 + (end_index.month - start_index.month)
            lifetime_status = max(0, lifetime_months)
        elif start_index: # 시작은 했으나 아직 안 끝남
            lifetime_status = 'Ongoing' 
        else: # 시작점 불명
            lifetime_status = 0
            
    # Y축 데이터 저장
    lifetime_data[column] = lifetime_status 

    # X축 피쳐 데이터 저장 (Peak_Value 추가)
    feature_data.append({
        'Word': column, 
        'Word_Length': word_len, 
        'Max_Rising_Slope': max_rising_slope,
        'Peak_Value': peak_value,
        'Total_Active_Months_Raw': total_active_months_raw 
    })

# 4. 결과 출력 및 합치기
lifetime_df = pd.DataFrame(lifetime_data.items(), columns=['Word', 'Lifetime (Months)'])
feature_df = pd.DataFrame(feature_data)

# 5. Word 컬럼을 기준으로 두 DataFrame 병합
final_df = pd.merge(feature_df, lifetime_df, on='Word')

# 6. CSV 파일로 저장
final_df.to_csv('final_training_dataset.csv', index=False, encoding='utf-8-sig')

print("\n--- 최종 훈련 데이터셋 (final_training_dataset.csv) ---")
print(final_df.head())
print(f"\n✅ (3-Feature) {len(final_df)}개 단어의 피처 및 수명 계산 완료. CSV 저장 성공.")
