from pytrends.request import TrendReq
import pandas as pd
import time
import os
import datetime

pytrends = TrendReq(hl='ko-KR', tz=540)

# 2. 검색할 모든 단어 설정
keyword_list = ["느좋", "안습", "즐", "성덕", "사이다", "멘탈", 
                "갑분싸", "OMG", "팬아저", "팟", "반사", "버카충",
                "강추", "걍", "공구", "멘붕", "생파", "셀카", "알바",
                "얼짱", "엄친딸", "정모", "치맥", "지못미", "가즈아", "급식충",
                "국뽕", "레게노", "맘충", "불금", "어쩔티비", "졸부", "잼민이",
                 "진지충", "창렬", "탕진잼", "홍대병", "가성비", "갑툭튀", "낄끼빠빠"]

end_date = datetime.date.today().strftime('%Y-%m-%d')
start_date = '2004-01-01'
TIME_FRAME = f'{start_date} {end_date}'

all_trends_df = pd.DataFrame()
OUTPUT_FILE = "all_word_trends.csv"


if os.path.exists(OUTPUT_FILE):
    print(f"기존 파일 {OUTPUT_FILE} 로드 중...")
    all_trends_df = pd.read_csv(OUTPUT_FILE, index_col='date')
    all_trends_df.index = pd.to_datetime(all_trends_df.index)
    
    # 이미 수집된 단어 -> keyword_list에서 제외
    existing_keywords = list(all_trends_df.columns)
    keyword_list = [k for k in keyword_list if k not in existing_keywords]
    
    print(f"이미 수집된 단어: {existing_keywords}")
    print(f"새롭게 수집할 단어: {keyword_list}")

for keyword in keyword_list:
    print(f"--- {keyword} 데이터 수집 중... ---")

    try:
        # Google Trends에 요청
        pytrends.build_payload([keyword], cat=0, timeframe=TIME_FRAME, geo='KR')

        # 데이터 가져오기
        interest_over_time_df = pytrends.interest_over_time()

        if 'isPartial' in interest_over_time_df.columns:
            interest_over_time_df = interest_over_time_df.drop(columns=['isPartial'])

        if all_trends_df.empty:
            all_trends_df = interest_over_time_df
        else:
            all_trends_df = all_trends_df.merge(interest_over_time_df, left_index=True, right_index=True, how='outer')

        all_trends_df.to_csv(OUTPUT_FILE)
        print(f"✅ [{keyword}] 수집 성공. CSV 파일 저장됨.")
        
    except Exception as e:
        print(f"❌ [{keyword}] 데이터 수집 실패: {e}")
        print("다음 단어로 넘어갑니다...")
      
    print("Google Trends 요청 제한 방지를 위해 10초 대기...")
    time.sleep(10)


print("\n--- 전체 획득 데이터 ---")
print(all_trends_df.head())
print(f"\n최종 데이터 크기: {all_trends_df.shape}")
all_trends_df.to_csv("all_word_trends.csv")
print("\n데이터 수집 완료. all_word_trends.csv 파일 생성됨.")
