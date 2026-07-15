"""
오늘의 띠별 운세 — IG 캐러셀 (사주 운세, 점수 없음).

띠(년생별, 1960~2013) 12띠 각각 **한 페이지**에 연애운(1)·재물운·건강운·총운 문구.
표지 1 + 띠별 12 = 13장 (IG 캐러셀 최대 20, 4:5=1080x1350). 점수/하트 없음.

콘텐츠는 매일 Claude Haiku 로 새로 생성(톤 세이프), 실패 시 내장 풀 회전 폴백.
게시: 각 jpg → upload_image(Cloudinary) → post_carousel → post_ledger.

실행: python scripts/fortune_saju_carousel.py [--dry-run]
"""

import base64
import json
import os
import sys
import time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

KST = timezone(timedelta(hours=9))
TOPIC_ID = "fortune_saju"

ANIMALS = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]
EMOJI = {"쥐": "🐭", "소": "🐮", "호랑이": "🐯", "토끼": "🐰", "용": "🐲", "뱀": "🐍",
         "말": "🐴", "양": "🐑", "원숭이": "🐵", "닭": "🐔", "개": "🐶", "돼지": "🐷"}

# 카테고리 순서 — 연애운 첫번째 (운영자 지시)
CATEGORIES = [("연애운", "💕", "#ff5fa2"), ("재물운", "💰", "#ffd94a"),
              ("건강운", "🍀", "#4ade80"), ("총운", "⭐", "#a78bfa")]
CAT_KEYS = [c[0] for c in CATEGORIES]


def zodiac_years() -> dict:
    out = {a: [] for a in ANIMALS}
    for y in range(1960, 2014):
        out[ANIMALS[(y - 1960) % 12]].append(f"{y % 100:02d}")
    return out


# ── 폴백 풀 (Claude 실패 시 띠·날짜로 회전) — 톤 세이프, 긍정, 점수 없음 ──
POOLS = {
    "연애운": ["설레는 만남이 찾아와요", "먼저 다가가면 좋은 흐름이에요", "눈맞춤 타이밍이 좋아요",
             "따뜻한 한마디가 마음을 열어요", "가벼운 연락이 설렘으로 이어져요", "여유로운 미소가 매력 포인트"],
    "재물운": ["작은 지출 관리가 이득이 돼요", "예상 밖 반가운 소식이 있어요", "알뜰함이 복이 되는 날",
             "계획 소비가 딱 맞아떨어져요", "굿딜을 만날 기운이에요", "차곡차곡 모으기 좋은 날"],
    "건강운": ["가벼운 산책이 활력을 줘요", "물을 자주 마시면 컨디션 업", "충분한 휴식이 보약이에요",
             "스트레칭 한 번이 개운해요", "일찍 자면 내일이 가벼워요", "따뜻한 차 한 잔이 도움 돼요"],
    "총운": ["잔잔하게 좋은 하루예요", "작은 행운이 곳곳에 따라요", "마음이 편안해지는 흐름",
            "긍정 에너지가 가득한 날", "차분하게 잘 풀리는 하루", "기분 좋은 신호가 많아요"],
}


def _fallback(today: date) -> dict:
    seed = today.timetuple().tm_yday
    out = {}
    for i, a in enumerate(ANIMALS):
        out[a] = {cat: POOLS[cat][(i + seed) % len(POOLS[cat])] for cat in CAT_KEYS}
    return out


SAFE_PROMPT = (
    "한국 IG 연예채널용 '오늘의 띠별 운세'를 JSON 으로만 출력.\n"
    "형식: {\"쥐\":{\"연애운\":\"...\",\"재물운\":\"...\",\"건강운\":\"...\",\"총운\":\"...\"}, ... 12띠 전부}.\n"
    "각 문구 12~22자, 긍정·따뜻·설렘 위주. 점수/숫자 없음. 겁주기·불안·미신단정·"
    "건강 진단/사고 언급 금지. 클릭베이트 금지어(충격/발칵/경악/오열/폭로/결국/도대체/역대급) 금지. 이모지 금지.\n"
    "12띠: 쥐 소 호랑이 토끼 용 뱀 말 양 원숭이 닭 개 돼지. 카테고리 순서: 연애운·재물운·건강운·총운."
)


def generate_fortunes(today: date) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=2000,
                messages=[{"role": "user",
                           "content": f"{SAFE_PROMPT}\n오늘 날짜: {today.isoformat()}"}])
            txt = msg.content[0].text
            data = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
            out = {}
            for a in ANIMALS:
                d = data[a]
                out[a] = {cat: str(d[cat])[:26] for cat in CAT_KEYS}
            print("✓ Claude Haiku 로 12띠 운세 생성")
            return out
        except Exception as ex:
            print(f"⚠️ Haiku 생성 실패 → 폴백: {type(ex).__name__}: {ex}")
    return _fallback(today)


# ── 슬라이드 HTML (1080x1350) ──
_SHELL = """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box;
     font-family:'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
body {{ width:1080px; height:1350px; overflow:hidden; color:#f5f0ff; position:relative;
  background:
    radial-gradient(90% 55% at 82% -8%, rgba(255,183,77,.14) 0%, transparent 60%),
    radial-gradient(120% 70% at 12% 108%, rgba(124,58,237,.32) 0%, transparent 62%),
    radial-gradient(130% 82% at 50% -8%, #43206e 0%, #251243 44%, #0d0620 100%);
  display:flex; flex-direction:column; padding:{pad}; }}
/* 별밤 — 3겹 점광 (움직이는 느낌의 반짝임 밀도차) */
body::before {{ content:""; position:absolute; inset:0; pointer-events:none; background-image:
  radial-gradient(2px 2px at 8% 12%, rgba(255,255,255,.9) 40%, transparent 60%),
  radial-gradient(1.6px 1.6px at 78% 7%, rgba(255,255,255,.75) 40%, transparent 60%),
  radial-gradient(1.4px 1.4px at 30% 26%, rgba(255,217,74,.8) 40%, transparent 60%),
  radial-gradient(2px 2px at 92% 33%, rgba(255,255,255,.6) 40%, transparent 60%),
  radial-gradient(1.3px 1.3px at 15% 55%, rgba(255,255,255,.5) 40%, transparent 60%),
  radial-gradient(1.8px 1.8px at 62% 18%, rgba(196,181,253,.85) 40%, transparent 60%),
  radial-gradient(1.2px 1.2px at 45% 8%, rgba(255,255,255,.65) 40%, transparent 60%),
  radial-gradient(1.5px 1.5px at 85% 72%, rgba(255,217,74,.5) 40%, transparent 60%),
  radial-gradient(1.2px 1.2px at 6% 84%, rgba(255,255,255,.45) 40%, transparent 60%),
  radial-gradient(1.7px 1.7px at 55% 92%, rgba(196,181,253,.5) 40%, transparent 60%),
  radial-gradient(1.1px 1.1px at 38% 68%, rgba(255,255,255,.4) 40%, transparent 60%),
  radial-gradient(1.4px 1.4px at 70% 48%, rgba(255,255,255,.35) 40%, transparent 60%); }}
/* 하단 지평 광 */
body::after {{ content:""; position:absolute; left:-10%; right:-10%; bottom:-24%; height:44%;
  background:radial-gradient(50% 60% at 50% 100%, rgba(255,183,77,.16) 0%, transparent 70%);
  pointer-events:none; }}
{extra}
</style></head><body>{body}</body></html>"""


def cover_html(date_str: str) -> str:
    body = f"""
    <div style="position:absolute; inset:34px; border:1.5px solid rgba(255,217,74,.28);
      border-radius:30px; pointer-events:none;"></div>
    <div style="position:absolute; inset:46px; border:1px solid rgba(255,217,74,.14);
      border-radius:24px; pointer-events:none;"></div>
    <div style="margin:auto; text-align:center; position:relative;">
      <div style="font-size:40px; letter-spacing:14px; color:rgba(255,217,74,.85);">✦ ✦ ✦</div>
      <div style="display:inline-block; margin-top:26px; background:linear-gradient(90deg,#ffd94a,#ffb74d);
        color:#2a0f47; font-size:31px; font-weight:800; letter-spacing:3px; padding:13px 38px;
        border-radius:40px; box-shadow:0 8px 30px -6px rgba(255,183,77,.55);">재미로 보는</div>
      <div style="font-size:110px; font-weight:900; line-height:1.06; margin-top:34px;
        background:linear-gradient(180deg,#fff 20%,#ffd94a 90%); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent; text-shadow:0 10px 60px rgba(255,217,74,.25);">오늘의<br>띠별 운세</div>
      <div style="display:flex; align-items:center; justify-content:center; gap:18px; margin-top:30px;">
        <span style="height:1px; width:90px; background:linear-gradient(90deg,transparent,#ffd94a);"></span>
        <span style="font-size:36px; color:rgba(245,240,255,.85); font-weight:700;">{date_str}</span>
        <span style="height:1px; width:90px; background:linear-gradient(270deg,transparent,#ffd94a);"></span>
      </div>
      <div style="font-size:29px; color:rgba(245,240,255,.6); font-weight:600; margin-top:14px;
        letter-spacing:2px;">연애 · 재물 · 건강 · 총운</div>
      <div style="margin-top:52px; display:inline-flex; align-items:center; gap:12px;
        background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.16);
        padding:14px 32px; border-radius:40px; font-size:28px; color:rgba(245,240,255,.75);">
        ← 넘겨서 내 띠 찾기</div>
    </div>"""
    return _SHELL.format(pad="80px 60px", extra="", body=body)


def tti_html(animal: str, cats: dict, years: list) -> str:
    yrs = "·".join(years) + "년생"
    rows = ""
    for name, ico, color in CATEGORIES:
        rows += f"""
      <div style="display:flex; align-items:center; gap:22px; position:relative;
        background:linear-gradient(135deg, rgba(255,255,255,.085), rgba(255,255,255,.035));
        border:1px solid rgba(255,255,255,.13); border-left:5px solid {color};
        border-radius:22px; padding:26px 30px; box-shadow:0 10px 34px -14px rgba(0,0,0,.55);">
        <span style="font-size:46px; line-height:1; filter:drop-shadow(0 4px 12px {color}66);">{ico}</span>
        <div style="display:flex; flex-direction:column; gap:7px;">
          <span style="font-size:25px; font-weight:800; color:{color}; letter-spacing:3px;">{name}</span>
          <span style="font-size:39px; font-weight:700; line-height:1.28;">{cats.get(name,'')}</span>
        </div>
      </div>"""
    body = f"""
    <div style="position:absolute; inset:30px; border:1px solid rgba(255,217,74,.16);
      border-radius:28px; pointer-events:none;"></div>
    <div style="text-align:center; margin-bottom:24px; position:relative;">
      <div style="width:190px; height:190px; margin:0 auto; border-radius:50%; position:relative;
        background:radial-gradient(circle at 38% 30%, rgba(255,255,255,.16), rgba(255,255,255,.04));
        border:2px solid rgba(255,217,74,.55);
        box-shadow:0 0 60px -8px rgba(255,217,74,.35), inset 0 0 30px rgba(255,217,74,.08);
        display:flex; align-items:center; justify-content:center;">
        <span style="font-size:104px; line-height:1;">{EMOJI[animal]}</span>
        <span style="position:absolute; inset:-13px; border:1px dashed rgba(255,217,74,.3);
          border-radius:50%;"></span>
      </div>
      <div style="font-size:62px; font-weight:900; margin-top:18px; letter-spacing:1px;
        background:linear-gradient(180deg,#fff 30%,#ffd94a); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;">{animal}띠</div>
      <div style="display:inline-block; margin-top:8px; font-size:25px; color:rgba(245,240,255,.72);
        font-weight:600; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.14);
        padding:7px 22px; border-radius:30px;">{yrs}</div>
    </div>
    <div style="flex:1; display:flex; flex-direction:column; justify-content:center; gap:17px;
      position:relative;">{rows}</div>
    <div style="text-align:center; font-size:25px; color:rgba(245,240,255,.5); margin-top:18px;
      position:relative;">@daily_enter_kr · 재미로 보는 오늘의 운세</div>"""
    return _SHELL.format(pad="60px 56px", extra="", body=body)


def build_slides_html(fortunes: dict, date_str: str) -> list:
    years = zodiac_years()
    html = [cover_html(date_str)]
    html += [tti_html(a, fortunes[a], years[a]) for a in ANIMALS]  # 12띠
    return html  # 13장


def render_jpgs(html_list, out_dir: Path) -> list:
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    chrome = os.environ.get("PW_CHROME")
    jpgs = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        for i, h in enumerate(html_list):
            hp = out_dir / f"slide_{i:02d}.html"
            hp.write_text(h, encoding="utf-8")
            pg = b.new_page(viewport={"width": 1080, "height": 1350})
            pg.goto(hp.resolve().as_uri())
            pg.wait_for_timeout(700)
            jp = out_dir / f"slide_{i:02d}.jpg"
            pg.screenshot(path=str(jp), type="jpeg", quality=92)
            pg.close()
            jpgs.append(jp)
        b.close()
    return jpgs


def build_caption(date_str: str) -> str:
    return (
        f"오늘의 띠별 운세 · {date_str}\n\n"
        "연애·재물·건강·총운까지, 내 띠 운세를 확인해보세요.\n"
        "가볍게 재미로 보는 오늘의 운세예요. 저장하고 친구도 태그해봐요.\n\n"
        "#띠별운세 #오늘의운세 #연애운 #재물운 #데일리운세 "
        "#운세스타그램 #띠운세 #소통스타그램 #오늘의연애운"
    )


def main() -> int:
    dry = "--dry-run" in sys.argv
    today = datetime.now(KST).date()
    date_str = f"{today.year}년 {today.month}월 {today.day}일"

    if not dry:
        import post_ledger
        led = post_ledger.load_ledger()
        tstr = today.isoformat()
        # 하루 1회 — 구/신 토픽id 무관하게 '오늘 fortune 게시됨'이면 skip (당일 중복 방지)
        if any("fortune" in (e.get("topic_id") or "")
               and (e.get("posted_at") or "").startswith(tstr)
               for e in led.get("entries", [])):
            print(f"✅ 오늘({tstr}) 운세 이미 게시됨 — skip")
            return 0

    fortunes = generate_fortunes(today)
    html_list = build_slides_html(fortunes, date_str)
    out_dir = ROOT / "output_enter" / "publish" / "fortune_saju"
    jpgs = render_jpgs(html_list, out_dir)
    print(f"✓ 슬라이드 {len(jpgs)}장 렌더: {out_dir.relative_to(ROOT)}/")
    if not (2 <= len(jpgs) <= 20):
        print(f"❌ 캐러셀 장수 범위 위반: {len(jpgs)}")
        return 1

    if dry:
        print("🔍 dry-run — 렌더만, 게시 안 함")
        return 0

    from post_instagram import InstagramPublisher, upload_image
    import post_ledger
    ig_user = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return 1
    pub = InstagramPublisher(ig_user, ig_token)
    if not pub.health_check().get("ok"):
        print("❌ IG 토큰 무효")
        return 1

    urls = [upload_image(j) for j in jpgs]
    print(f"✓ {len(urls)}장 업로드 완료")
    media_id = pub.post_carousel(urls, build_caption(date_str))
    print(f"✅ 오늘의 띠별 운세 캐러셀 게시 완료! {media_id}")
    time.sleep(5)
    try:
        pub.post_comment(media_id, "내 띠 운세 어때요? 댓글로 공유해요")
    except Exception as e:
        print(f"⚠️ 댓글 실패(비치명): {e}")

    post_ledger.record_results([{
        "ok": True, "topic_id": f"{TOPIC_ID}_{today.isoformat()}",
        "title": f"오늘의 띠별 운세 {date_str}", "style": "fortune_carousel",
        "seed": None, "media_id": media_id,
        "youtube_id": None, "threads_id": None, "bgm": None,
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
