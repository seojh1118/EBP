import speech_recognition as sr
r = sr.Recognizer()

with sr.Microphone() as source:
    print("마이크에 소음이 없는지 잠시 대기합니다...")
    # 소음을 듣고 주변 소음 수준을 동적으로 조정
    r.adjust_for_ambient_noise(source, duration=1.0) 
    print("말씀하세요! (3초간 녹음됩니다)")
    
    try:
        audio = r.listen(source, timeout=5, phrase_time_limit=3)
    except sr.WaitTimeoutError:
        print("입력이 없어 종료합니다.")
        exit()

print("음성 인식을 시도합니다...")

try:
    text = r.recognize_google(audio, language='ko-KR')
    print(f"✅ 인식된 단어 (STT 성공): '{text}'")
    
    print(f"이 '{text}' 단어를 Streamlit 앱의 분석 입력으로 사용합니다.")
    
except sr.UnknownValueError:
    print("❌ 음성을 인식할 수 없습니다.")
except sr.RequestError as e:
    print(f"❌ Google Speech Recognition 서비스에 연결할 수 없습니다; {e}")
