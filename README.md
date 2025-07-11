# chatgpt_o3_daily_scraper

ChatGPT 자동 리포트 생성기 📊  
하루 단위로 ChatGPT에 프롬프트를 보내고, 응답 결과를 MongoDB에 저장합니다.

---

## 📁 파일 구성

| 파일 | 설명 |
|------|------|
| `src/daily_scraper.py` | 핵심 실행 스크립트 |
| `requirements.txt` | 필요한 패키지 목록 |
| `.gitignore` | 불필요한 파일 제외 규칙 |

---

## ⚙️ 환경 설정

```python
# daily_scraper.py 내에서 직접 설정
chrome_driver_path = r"C:\chrome-data\chromedriver.exe"
user_data_dir      = r"C:\chrome-data\user-profile"
profile_name       = "Default"
mongo_uri          = "mongodb://localhost:27017/"
```

✅ ChatGPT 로그인 유지용 Chrome 프로필 필요  
(예시 실행법)

```bash
start chrome.exe ^
 --user-data-dir="C:\chrome-data\user-profile" ^
 --profile-directory="Default"
```

---

## 🚀 실행 방법

```bash
python src/daily_scraper.py
```

> 설정된 기간(`start_date` ~ `end_date`)에 대해 프롬프트를 전송하고, 응답 결과를 MongoDB에 저장합니다.

---

## 🧾 MongoDB 저장 예시

```json
{
  "report_date": "2024-11-15",
  "prompt": "...",
  "answer": "...",
  "created_at": "2025-07-11T01:23:45Z"
}
```

---

## 📦 설치 패키지

```bash
pip install -r requirements.txt
```
