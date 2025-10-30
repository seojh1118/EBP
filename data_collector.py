from pytrends.request import TrendReq
import pandas as pd
import time # time 모듈 추가
import os
import datetime

# 1. Google Trends 접속 객체 생성
pytrends = TrendReq(hl='ko-KR', tz=540)

# 2. 검색할 모든 단어 설정
keyword_list = ["느좋", "안습", "즐", "성덕", "사이다", "멘탈", 
                "갑분싸", "OMG", "팬아저", "팟", "반사", "버카충",
                "강추", "걍", "공구", "멘붕", "생파", "셀카", "알바",
                "얼짱", "엄친딸", "정모", "치맥", "지못미", "가즈아", "급식충",
                "국뽕", "레게노", "맘충", "불금", "어쩔티비", "졸부", "잼민이",
                 "진지충", "창렬", "탕진잼", "홍대병", "가성비", "갑툭튀", "낄끼빠빠"]

# 현재 날짜를 "YYYY-MM-DD" 형식의 문자열로 자동 생성
# 이 코드를 실행하는 시점의 날짜가 자동으로 설정됩니다.
end_date = datetime.date.today().strftime('%Y-%m-%d')

# 데이터 수집 시작 시점 설정
start_date = '2004-01-01'

# Timeframe 문자열 자동 생성: 'YYYY-MM-DD YYYY-MM-DD' 형식
TIME_FRAME = f'{start_date} {end_date}'

# 데이터를 저장할 빈 DataFrame 생성
all_trends_df = pd.DataFrame()
OUTPUT_FILE = "all_word_trends.csv"

# 기존 파일이 있으면 불러오기

if os.path.exists(OUTPUT_FILE):
    print(f"기존 파일 {OUTPUT_FILE} 로드 중...")
    all_trends_df = pd.read_csv(OUTPUT_FILE, index_col='date')
    all_trends_df.index = pd.to_datetime(all_trends_df.index)
    
    # 이미 수집된 단어는 keyword_list에서 제외
    existing_keywords = list(all_trends_df.columns)
    keyword_list = [k for k in keyword_list if k not in existing_keywords]
    
    print(f"이미 수집된 단어: {existing_keywords}")
    print(f"새롭게 수집할 단어: {keyword_list}")

# 3. 각 단어별로 데이터를 가져오는 반복문
for keyword in keyword_list:
    print(f"--- {keyword} 데이터 수집 중... ---")

    try:
        # Google Trends에 요청을 보냄 (timeframe 변수를 사용하도록 수정)
        pytrends.build_payload([keyword], cat=0, timeframe=TIME_FRAME, geo='KR')

        # 데이터 가져오기
        interest_over_time_df = pytrends.interest_over_time()

        # 'isPartial' 컬럼은 불필요하므로 제거
        if 'isPartial' in interest_over_time_df.columns:
            interest_over_time_df = interest_over_time_df.drop(columns=['isPartial'])

        # DataFrame에 합치기 (keyword를 컬럼 이름으로 사용)
        if all_trends_df.empty:
            all_trends_df = interest_over_time_df
        else:
            # 같은 날짜 기준으로 옆에 합치기
            all_trends_df = all_trends_df.merge(interest_over_time_df, left_index=True, right_index=True, how='outer')
        
        # 합친 후 바로 저장하여 누적 기록
        all_trends_df.to_csv(OUTPUT_FILE)
        print(f"✅ [{keyword}] 수집 성공. CSV 파일 저장됨.")
        
    except Exception as e:
        # 🚨 [수정됨] 오류가 발생해도 멈추지 않고 다음 단어로 넘어감
        print(f"❌ [{keyword}] 데이터 수집 실패: {e}")
        print("다음 단어로 넘어갑니다...")

    # 4. 요청 제한 방지: 5초 -> 10초로 대기 시간 늘림
    print("Google Trends 요청 제한 방지를 위해 10초 대기...")
    time.sleep(10) # 5초에서 10초로 늘림


# 5. 최종 데이터 확인 및 CSV 저장
print("\n--- 전체 획득 데이터 ---")
print(all_trends_df.head())
print(f"\n최종 데이터 크기: {all_trends_df.shape}")
all_trends_df.to_csv("all_word_trends.csv")
print("\n데이터 수집 완료. all_word_trends.csv 파일 생성됨.")