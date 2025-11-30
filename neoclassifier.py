import pandas as pd
import numpy as np
import re
import requests
import datetime
from pytrends.request import TrendReq

class NeologismClassifier:
    def __init__(self, dictionary_api_key=None):
        self.api_key = dictionary_api_key
        # °¡ÁßÄ¡ ¼³Á¤
        self.weights = {
            'w1': 0.4, # »çÀü ¹ÌµîÀç
            'w2': 0.4, # Æ®·»µå ½ÅÁ¶¾î¼º
            'w3': 0.2  # ÇüÅÂÀû Æ¯Â¡
        }
        # Æ®·»µå ½ºÄÚ¾î ÆÄ¶ó¹ÌÅÍ
        self.trend_params = {'alpha': 0.5, 'beta': 0.4, 'gamma': 0.1}
        
    # ---------------------------------------------------------
    # 1´Ü°è:±¹¸³±¹¾î¿ø APIÇÊÅÍ
    # --------------------------------------------------------
    def _check_dictionary(self, word):
        """
        »çÀü¿¡ µîÀçµÇ¾î ÀÖÀ¸¸é 0Á¡, ¾øÀ¸¸é 1Á¡ ¹ÝÈ¯
        API Å°°¡ ¾ø°Å³ª Åë½Å ½ÇÆÐ ½Ã º¸¼öÀûÀ¸·Î 0.5 ¹ÝÈ¯
        """
        if not self.api_key:
            return 0.5 # API Å° ¾øÀ½

        url = "https://stdict.korean.go.kr/api/search.do"
        params = {
            "key": self.api_key,
            "q": word,
            "req_type": "json",
            "advanced": "y",
            "method": "exact"
        }
        
        try:
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                # °á°ú°¡ ÀÖÀ¸¸é(total > 0) µîÀçµÈ ´Ü¾î -> Á¡¼ö 0
                # °á°ú°¡ ¾øÀ¸¸é(total = 0) ¹ÌµîÀç ´Ü¾î -> Á¡¼ö 1
                try:
                    data = response.json()
                    return 0.0 if data.get('channel', {}).get('total', 0) > 0 else 1.0
                except:
                    # JSON ÆÄ½Ì ¿¡·¯ ½Ã
                    return 1.0 
            return 0.5
        except Exception:
            return 0.5

    # ---------------------------------------------------------
    # 2´Ü°è: Æ®·»µå ±â¹Ý ½ÅÁ¶¾î
    # ---------------------------------------------------------
    def _calculate_trend_score(self, trend_series):
        """
        trend_series: pandas Series (index=date, value=interest)
        """
        if trend_series is None or len(trend_series) < 30:
            return 0.0
            
        # µ¥ÀÌÅÍ ºÐ¸®
        recent_data = trend_series.iloc[-30:] # ÃÖ±Ù 30ÀÏ
        past_data = trend_series.iloc[:-30]   # °ú°Å µ¥ÀÌÅÍ
        
        # (1) Recent Growth Rate 
        x = np.arange(len(recent_data))
        y = recent_data.values
        if len(y) > 1:
            slope, _ = np.polyfit(x, y, 1)
        else:
            slope = 0
        recent_growth = max(0, slope) # À½¼ö ±â¿ï±â´Â 0 Ã³¸®
        
        # Á¤±ÔÈ­ (ÃÖ´ë ±â¿ï±â¸¦ 100 Á¤µµ·Î °¡Á¤ÇÏ°í 0~1 scaling)
        recent_growth_norm = min(recent_growth / 10.0, 1.0) 

        # (2) Baseline History
        past_mean = past_data.mean() if not past_data.empty else 0
        
        # (3) Novelty Ratio
        recent_mean = recent_data.mean()
        novelty = 0
        if past_mean < 1: # °ú°Å¿¡ °ÅÀÇ ¾È ¾²¿´´Ù¸é
            novelty = 1.0 if recent_mean > 5 else 0.0 # ÃÖ±Ù¿¡ ¶¹À¸¸é ³ôÀº Á¡¼ö
        else:
            novelty = min(recent_mean / past_mean, 5.0) / 5.0 # ºñÀ² Ä¸ÇÎ
            
        # °ø½Ä Àû¿ë: Newness = ¥á * Recent + ¥â * Novelty - ¥ã * Past
        alpha, beta, gamma = self.trend_params['alpha'], self.trend_params['beta'], self.trend_params['gamma']
        
        score = (alpha * recent_growth_norm) + (beta * novelty) - (gamma * (past_mean / 100.0))
        return max(0.0, min(1.0, score)) # 0~1 »çÀÌ·Î Å¬¸®ÇÎ

    # ---------------------------------------------------------
    # 3´Ü°è: ¾ð¾î ÇüÅÂÀû Æ¯Â¡
    # ---------------------------------------------------------
    def _analyze_morphology(self, word):
        score = 0
        
        # (1) ÃÊ¼º/¾à¾î ¿©ºÎ
        if re.search(r'^[¤¡-¤¾]+$', word):
            score += 2 # °­·ÂÇÑ ½ÅÈ£
            
        # (2) ÀÚÀ½/¸ðÀ½ º¯Çü ¹Ýº¹
        if re.search(r'([¤¡-¤¾¤¿-¤Ó])\1{2,}', word):
            score += 1
            
        # (3) "¤·"À¸·Î ³¡³ª´Â ºñÇ¥ÁØ ¾î¸» °¨Áö
        # À¯´ÏÄÚµå °ø½Ä: (ÇÕ - 0xAC00) % 28 == 11
        if len(word) > 0:
            last_char = word[-1]
            if '°¡' <= last_char <= 'ÆR':
                char_code = ord(last_char) - 0xAC00
                jongseong = char_code % 28
                if jongseong == 11: # '¤·' ¹ÞÄ§
                    # ¿¹: Å·¹Þ'´É', ¾Ë'°Ú'´É°¡ µî
                    score += 0.5

        # (4) ±ÛÀÚ¼ö 
        if 2 <= len(word) <= 4:
            score += 0.5
            
        # Á¤±ÔÈ­ 
        normalized_score = min(score / 3.0, 1.0)
        return normalized_score

    # ---------------------------------------------------------
    # ÃÖÁ¾ ÆÇº°
    # ---------------------------------------------------------
    def predict_is_neologism(self, word, trend_series=None):
        """
        ÃÖÁ¾ Á¡¼ö °è»ê ¹× ÆÇº°
        trend_series°¡ NoneÀÌ¸é Æ®·»µå Á¡¼ö´Â 0 Ã³¸®
        """
        # 1. »çÀü Á¡¼ö 
        s1 = self._check_dictionary(word)
        
        # 2. Æ®·»µå Á¡¼ö
        if trend_series is not None:
            s2 = self._calculate_trend_score(trend_series)
        else:
            s2 = 0.0 # º¸¼öÀû Á¢±Ù
            
        # 3. ÇüÅÂ Á¡¼ö
        s3 = self._analyze_morphology(word)
        
        # °¡ÁßÄ¡ ÇÕ»ê
        final_score = (self.weights['w1'] * s1) + \
                      (self.weights['w2'] * s2) + \
                      (self.weights['w3'] * s3)
                      
        result = {
            "word": word,
            "is_neologism": final_score > 0.6, # Threshold
            "final_score": round(final_score, 2),
            "details": {
                "dict_score": s1,
                "trend_score": round(s2, 2),
                "morph_score": round(s3, 2)
            }
        }
        return result