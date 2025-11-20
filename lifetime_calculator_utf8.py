import pandas as pd
import numpy as np
import os

# 1. 원본 데이터 로드
try:
    df = pd.read_csv('all_word_trends.csv', index_col='date', parse_dates=True)
except FileNotFoundError:
    print("❌ ERROR: 'all_word_trends.csv' 파일을 찾을 수 없습니다.")
    print("먼저 data_collector.py를 실행하세요.")
    exit()

feature_data = [] # X 피처 (초기 단서)
lifetime_data = [] # Y (수명)

print("데이터셋 분석 및 피처 계산 시작...")

# 2. 각 단어별로 반복하며 피처 및 수명 계산
for column in df.columns:
    series = df[column].dropna()
    if series.empty:
        continue

    # --- 3. [X 피처] '초기 단서' 계산 ---
    
    # [피처 1: Word_Length]
    word_len = len(column.replace(" ", ""))

    # '초기 1년치' 데이터만 추출 (신조어 예측과 동일한 조건)
    try:
        start_date = series.first_valid_index()
        one_year_later = start_date + pd.DateOffset(years=1)
        initial_series = series.loc[start_date:one_year_later]
    except Exception as e:
        print(f"'{column}' 단어 1년치 데이터 추출 실패: {e}")
        continue
        
    if initial_series.empty:
        continue

    # [피처 2: Max_Rising_Slope] (초기 1년간 최대 상승 기울기)
    slopes = initial_series.diff().fillna(0)
    max_rising_slope = slopes[slopes > 0].max()
    max_rising_slope = 0 if pd.isna(max_rising_slope) or max_rising_slope == 0 else max_rising_slope
    
    # [피처 3: Initial_Volatility] (초기 1년간 변동성)
    initial_volatility = initial_series.std()
    initial_volatility = 0 if pd.isna(initial_volatility) else initial_volatility

    # [피처 4: Initial_Decay_Rate] (초기 1년간 하락 속도)
    peak_index = initial_series.idxmax()
    after_peak_series = initial_series.loc[peak_index:]
    initial_decay_rate = 0
    if len(after_peak_series) > 1:
        initial_decay_rate = after_peak_series.mean()
        initial_decay_rate = 0 if pd.isna(initial_decay_rate) else initial_decay_rate

    # --- 4. [Y 피처] '전체 수명' 계산 ---
    
    peak_value = series.max()
    if peak_value < 10: # 유의미한 유행이 아니면 제외
        continue
        
    peak_date = series.idxmax()

    # 유행 시작점 (Peak의 10%)
    start_threshold = peak_value * 0.1
    start_date = series[series > start_threshold].first_valid_index()

    # 유행 소멸점 (Peak의 1% 미만)
    end_threshold = peak_value * 0.01
    
    if start_date is None:
        continue

    # 소멸점 찾기 (Peak 이후)
    after_peak_series_full = series.loc[peak_date:]
    end_date_series = after_peak_series_full[after_peak_series_full < end_threshold]
    
    final_months = 'Ongoing' # 기본값 (진행형)
    
    if not end_date_series.empty:
        end_date = end_date_series.first_valid_index()
        if end_date is not None:
            # 수명 계산 (월 단위)
            lifetime = (end_date - start_date)
            final_months = int(lifetime.days / 30)
            if final_months <= 0: # 1달 미만은 1로 처리
                final_months = 1

    # 5. 데이터 저장
    feature_data.append({
        'Word': column, 
        'Word_Length': word_len, 
        'Max_Rising_Slope': max_rising_slope,
        'Initial_Volatility': initial_volatility,
        'Initial_Decay_Rate': initial_decay_rate,
        'Lifetime (Months)': final_months
    })

# 6. CSV 파일로 저장
final_df = pd.DataFrame(feature_data)
final_df = final_df.set_index('Word')

print("\n--- 4-Feature 기반 훈련 데이터셋 ---")
print(final_df.head())

final_df.to_csv('final_training_dataset.csv')
print(f"\n✅ 'final_training_dataset.csv' 파일 생성 완료! (총 {len(final_df)}개 단어)")