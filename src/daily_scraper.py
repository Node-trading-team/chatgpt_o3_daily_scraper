"""
ChatGPT Selenium 자동 수집 → MongoDB 저장 (멀티-데이, 새 채팅 버전)
rev. 2025-07-10 (c)
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException,
)
from datetime import datetime, timedelta
import time, traceback
from pymongo import MongoClient

# ────────── 사용자 설정 ──────────
chrome_driver_path  = r"C:\chrome-data\chromedriver.exe"
user_data_dir       = r"C:\chrome-data\user-profile"
profile_name        = "Default"
chatgpt_url         = "https://chat.openai.com"

start_date          = "2024-11-15"   # YYYY-MM-DD
end_date            = "2025-11-16"
delay_between_days  = 15             # (초)

mongo_uri           = "mongodb://localhost:27017/"
db_name             = "ai_responses_db"
col_name            = "News_community_data"
# ────────────────────────────────

# ───── MongoDB 연결 ─────
mongo_client = MongoClient(mongo_uri)
mongo_col    = mongo_client[db_name][col_name]

# ───── Selenium 옵션 ─────
opts = Options()
opts.add_argument("--start-maximized")
opts.add_argument(f"--user-data-dir={user_data_dir}")
opts.add_argument(f"--profile-directory={profile_name}")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)

service = Service(executable_path=chrome_driver_path)
driver  = webdriver.Chrome(service=service, options=opts)

# ───── 헬퍼 ─────
def ymd_iter(s: datetime, e: datetime):
    while s <= e:
        yield s
        s += timedelta(days=1)

def korean_ymd(d: datetime) -> str:
    return d.strftime("%Y년 %m월 %d일")

def safe_find(selector, many=False, timeout=20):
    try:
        waiter = WebDriverWait(driver, timeout)
        return waiter.until(
            (lambda d: d.find_elements(By.CSS_SELECTOR, selector))
            if many else
            (lambda d: d.find_element(By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        return [] if many else None

def insert_to_db(date_obj: datetime, prompt_txt: str, answer_txt: str):
    doc = {
        "report_date": date_obj.strftime("%Y-%m-%d"),
        "prompt": prompt_txt,
        "answer": answer_txt,
        "created_at": datetime.utcnow(),
    }
    res = mongo_col.update_one(
        {"report_date": doc["report_date"]},
        {"$set": doc},
        upsert=True,
    )
    oid = res.upserted_id or mongo_col.find_one({"report_date": doc["report_date"]})["_id"]
    print(f"✅ {doc['report_date']} MongoDB 저장 (ObjectId={oid})")

# ───── 프롬프트 빌더 ─────
def build_prompt(date_obj: datetime) -> str:
    ymd = korean_ymd(date_obj)
    return "\n".join([
        f"다음 조건에 따라 {ymd} 하루 동안의 암호화폐 커뮤니티 및 뉴스 흐름을 종합적으로 분석해줘. 데이터는 사실에 기반하여 논리적으로 정리하고, 시장 반응과 정서 변화가 어떻게 연결되는지를 중심으로 설명해줘.",
        "명시되지 않거나 부정확하고 불명확한 데이터는 생략하고, 확인 가능한 데이터만으로 분석을 진행해줘.",
        "",
        "[시간 범위]",
        f"- {ymd} (UTC 기준 00:00 ~ 23:59)",
        "",
        "[분석 대상 커뮤니티/소스]",
        "- Reddit (cryptocurrency, bitcoin, ethtrader, CryptoMarkets)",
        "- Bitcointalk, Steemit, CryptoCompare Forum 등 주요 암호화폐 커뮤니티",
        "",
        "[요청 분석 항목]",
        "1. 해당 하루 동안 커뮤니티에서 가장 많이 언급된 주제/이슈 3가지와 그 배경 (사건, 발표, 뉴스 등)",
        "2. 커뮤니티 전체의 감정 분포 (긍정/부정/혼합) 및 어떤 사건이 어떤 감정을 유도했는지에 대한 해석",
        "3. 주로 언급된 코인 (예: BTC, ETH 등)과 그날의 가격 변동성, 기술적 분석 언급 유무",
        "4. 주요 뉴스 기사, 규제 발표, 해킹 사건 등 외부 요인과 커뮤니티 반응 간의 상관성",
        "",
        "[출력 형식]",
        "- [핵심 토픽 요약] (이슈별로 배경, 반응, 여파까지 요약)",
        "- [감정 분석 결과] (주요 감정, 변동 추이 및 대표 인용)",
        "- [주요 인용/밈/반응 예시] (실제 커뮤니티 내 언급 사례)",
        "- [당일 시장 반영 요인] (가격 변화와 커뮤니티 정서 간 인과관계 요약)",
    ])

# ───── 새 채팅 열기 ─────
def open_new_chat():
    """
    ChatGPT 홈으로 이동해 새 대화가 열릴 때까지 대기
    (동일 세션에서 URL만 새로 불러오는 방식이 가장 안정적)
    """
    driver.get(chatgpt_url)
    if not safe_find('div.ProseMirror#prompt-textarea', timeout=60):
        raise RuntimeError("입력창 로드 실패 — 로그인 세션 확인 필요")
    time.sleep(0.5)  # UI 안정 대기

# ───── 채팅 보내기 & 완성본 수집 ─────
def send_prompt_and_get_answer(date_obj: datetime):
    prompt_txt = build_prompt(date_obj)

    input_box = safe_find('div.ProseMirror#prompt-textarea', timeout=30)
    if not input_box:
        print("❌ 입력창 찾기 실패"); return None

    input_box.click(); time.sleep(0.2)
    # 새 채팅은 텍스트 초기 상태이므로 input_box.clear() 생략 가능
    for line in prompt_txt.split("\n"):
        input_box.send_keys(line); input_box.send_keys(Keys.SHIFT, Keys.ENTER)
    input_box.send_keys(Keys.ENTER)
    print(f"⏳ {date_obj.date()} 프롬프트 전송")

    assist_sel = 'div[data-message-author-role="assistant"]'

    try:
        WebDriverWait(driver, 180).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, assist_sel)) > 0
        )
    except TimeoutException:
        print("⚠️ 응답 버블 생성 타임아웃"); return None

    # 스트리밍 모니터
    stable_t, max_t, min_chars = 20, 240, 120
    last_txt, last_ts, t0 = "", time.time(), time.time()

    while True:
        try:
            bubbles = driver.find_elements(By.CSS_SELECTOR, assist_sel)
            cur = "\n\n".join(b.text.strip() for b in bubbles)
        except (NoSuchElementException, StaleElementReferenceException):
            time.sleep(0.5); continue

        if cur != last_txt:
            last_txt, last_ts = cur, time.time()
        elif len(cur) >= min_chars and (time.time() - last_ts > stable_t):
            answer_txt = cur
            break

        if time.time() - t0 > max_t:
            print("⚠️ 최대 대기 초과, 부분 결과만 수집")
            answer_txt = cur
            break

        if bubbles:
            driver.execute_script("arguments[0].scrollIntoView(false);", bubbles[-1])
        time.sleep(1)

    return prompt_txt, answer_txt

# ───── 실행 ─────
try:
    s_date = datetime.strptime(start_date, "%Y-%m-%d")
    e_date = datetime.strptime(end_date,   "%Y-%m-%d")

    for d in ymd_iter(s_date, e_date):
        try:
            open_new_chat()  # *** 새 채팅을 먼저 열어 줌 ***
            res = send_prompt_and_get_answer(d)
            if res:
                prompt_txt, answer_txt = res
                insert_to_db(d, prompt_txt, answer_txt)
            else:
                print(f"❌ {d.date()} : 응답 확보 실패 (DB 저장 생략)")
        except Exception as inner:
            print(f"❌ {d.date()} 처리 중 오류:", inner)
            traceback.print_exc()

        if d < e_date:
            time.sleep(delay_between_days)

except KeyboardInterrupt:
    print("\n🛑 사용자 중단")
except Exception as e:
    print("❌ 치명적 오류:", e)
    traceback.print_exc()
finally:
    driver.quit()
    mongo_client.close()
    print("🚪 브라우저 세션 ‧ MongoDB 연결 종료")
