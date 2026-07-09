"""
오늘의 띠별 연애운 — IG 캐러셀 (사주 연애운).

띠(년생별, 1960~2013) 12띠 각각 그날의 연애운을 정리해 캐러셀로 게시.
표지 1 + 내용 6(2띠/슬라이드) + CTA 1 = 8장 (IG 캐러셀 2~10장 한도, 4:5=1080x1350).

콘텐츠는 매일 Claude Haiku 로 새로 생성(톤 세이프), 실패 시 내장 폴백.
게시: 각 jpg → upload_image(Cloudinary) → post_carousel → post_ledger.

실행: python scripts/fortune_saju_carousel.py [--dry-run]
"""

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
TOPIC_ID = "fortune_saju_love"

ANIMALS = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]
EMOJI = {"쥐": "🐭", "소": "🐮", "호랑이": "🐯", "토끼": "🐰", "용": "🐲", "뱀": "🐍",
         "말": "🐴", "양": "🐑", "원숭이": "🐵", "닭": "🐔", "개": "🐶", "돼지": "🐷"}


def zodiac_years() -> dict:
    """1960~2013 년생을 띠별로 (yy 2자리) 매핑. 1960=쥐."""
    out = {a: [] for a in ANIMALS}
    for y in range(1960, 2014):
        out[ANIMALS[(y - 1960) % 12]].append(f"{y % 100:02d}")
    return out


# ── 내장 폴백 (Claude 생성 실패 시) — 톤 세이프, 긍정 ──
FALLBACK = {
    "쥐": ("가벼운 인사가 설렘으로 이어져요", 5, "코럴 핑크 립"),
    "소": ("천천히 다가가면 마음이 열려요", 3, "따뜻한 라떼 한 잔"),
    "호랑이": ("먼저 웃으면 분위기가 부드러워져요", 4, "화이트 니트"),
    "토끼": ("오늘은 눈맞춤 타이밍이 좋아요", 5, "반짝이는 이어링"),
    "용": ("당당한 매력이 시선을 끌어요", 4, "골드 액세서리"),
    "뱀": ("솔직한 한마디가 거리를 좁혀요", 3, "데님 재킷"),
    "말": ("서두르지 말고 여유를 즐겨봐요", 2, "가벼운 산책 한 바퀴"),
    "양": ("작은 배려가 호감을 키워줘요", 4, "파스텔 톤 소품"),
    "원숭이": ("재치 있는 대화로 분위기 업", 5, "플레이리스트 공유"),
    "닭": ("차분하게 기다리면 기회가 와요", 3, "손편지 한 줄"),
    "개": ("진심이 통하는 하루가 될 거예요", 4, "라벤더 향"),
    "돼지": ("느긋한 미소가 상대를 편하게 해요", 2, "달달한 디저트"),
}

SAFE_PROMPT = (
    "한국 IG 연예채널용 '오늘의 띠별 연애운' 12띠 카피를 JSON 으로만 출력.\n"
    "형식: {\"쥐\":{\"line\":\"...\",\"hearts\":2~5,\"lucky\":\"...\"}, ... 12띠 전부}.\n"
    "line: 오늘의 연애운 한 줄 14~24자, 긍정·설렘 위주. "
    "겁주기·불안·미신단정·건강/사고 언급 금지. "
    "클릭베이트 금지어(충격/발칵/경악/오열/폭로/결국/도대체/역대급) 금지. 이모지 금지.\n"
    "lucky: 오늘의 행운 포인트(색/아이템/행동) 짧게. hearts: 2~5 골고루(전부 5 금지).\n"
    "12띠: 쥐 소 호랑이 토끼 용 뱀 말 양 원숭이 닭 개 돼지."
)


def generate_fortunes(today: date) -> dict:
    """{animal: (line, hearts, lucky)}. Claude Haiku 우선, 실패 시 폴백."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=1200,
                messages=[{"role": "user",
                           "content": f"{SAFE_PROMPT}\n오늘 날짜: {today.isoformat()}"}],
            )
            txt = msg.content[0].text
            s, e = txt.find("{"), txt.rfind("}")
            data = json.loads(txt[s:e + 1])
            out = {}
            for a in ANIMALS:
                d = data[a]
                h = max(2, min(5, int(d["hearts"])))
                out[a] = (str(d["line"])[:26], h, str(d["lucky"])[:18])
            print("✓ Claude Haiku 로 12띠 연애운 생성")
            return out
        except Exception as ex:
            print(f"⚠️ Haiku 생성 실패 → 폴백 사용: {type(ex).__name__}: {ex}")
    return dict(FALLBACK)


# ── 슬라이드 HTML (1080x1350, 4:5 캐러셀 규격) ──
_SHELL = """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box;
     font-family:'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
body {{ width:1080px; height:1350px; overflow:hidden; color:#f3ecff;
  background:radial-gradient(125% 80% at 50% -6%,#4a1d7a 0%,#26123f 46%,#0f0720 100%);
  display:flex; flex-direction:column; padding:{pad}; }}
{extra}
</style></head><body>{body}</body></html>"""


def _hearts(n):
    return ('<span style="color:#ff5fa2;">' + "♥" * n + "</span>"
            '<span style="color:rgba(255,255,255,.22);">' + "♡" * (5 - n) + "</span>")


def cover_html(date_str: str) -> str:
    body = f"""
    <div style="margin:auto; text-align:center;">
      <div style="display:inline-block; background:#ffd94a; color:#2a0f47; font-size:32px;
        font-weight:800; letter-spacing:2px; padding:12px 34px; border-radius:40px;">재미로 보는</div>
      <div style="font-size:104px; font-weight:900; line-height:1.08; margin-top:30px;
        background:linear-gradient(90deg,#fff,#ffd94a); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;">오늘의<br>띠별 연애운</div>
      <div style="font-size:38px; color:rgba(243,236,255,.72); font-weight:600; margin-top:26px;">
        {date_str} · 12띠 전체 체크</div>
      <div style="font-size:30px; color:rgba(243,236,255,.5); margin-top:44px;">← 좌우로 넘겨서 내 띠 찾기</div>
    </div>"""
    return _SHELL.format(pad="80px 60px", extra="", body=body)


def _tti_card(animal, line, hearts, lucky, years) -> str:
    yrs = "·".join(years) + "년생"
    return f"""
    <div style="background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.1);
      border-radius:26px; padding:34px 40px; display:flex; flex-direction:column; gap:14px;">
      <div style="display:flex; align-items:center; gap:20px;">
        <span style="font-size:76px;">{EMOJI[animal]}</span>
        <div style="display:flex; flex-direction:column; gap:4px;">
          <span style="font-size:52px; font-weight:900;">{animal}띠</span>
          <span style="font-size:26px; color:rgba(243,236,255,.6); font-weight:600;">{yrs}</span>
        </div>
        <span style="margin-left:auto; font-size:38px; letter-spacing:2px;">{_hearts(hearts)}</span>
      </div>
      <div style="font-size:42px; font-weight:800; line-height:1.25;">{line}</div>
      <div style="font-size:28px; color:#ffd94a; font-weight:700;">오늘의 행운 · {lucky}</div>
    </div>"""


def content_html(pair, fortunes, years) -> str:
    cards = "\n".join(
        _tti_card(a, fortunes[a][0], fortunes[a][1], fortunes[a][2], years[a])
        for a in pair)
    body = f"""
    <div style="text-align:center; margin-bottom:28px;">
      <span style="font-size:34px; font-weight:800; color:#ffd94a; letter-spacing:1px;">오늘의 연애운</span>
    </div>
    <div style="flex:1; display:flex; flex-direction:column; justify-content:center; gap:30px;">
      {cards}
    </div>"""
    return _SHELL.format(pad="72px 56px", extra="", body=body)


def cta_html() -> str:
    body = f"""
    <div style="margin:auto; text-align:center;">
      <div style="font-size:88px; font-weight:900; line-height:1.12;
        background:linear-gradient(90deg,#fff,#ffd94a); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;">내 띠는<br>몇 점?</div>
      <div style="font-size:40px; color:rgba(243,236,255,.8); font-weight:700; margin-top:30px;">
        댓글로 알려줘요</div>
      <div style="font-size:30px; color:rgba(243,236,255,.55); margin-top:46px;">
        저장하고 친구도 태그해봐요</div>
      <div style="font-size:34px; color:rgba(243,236,255,.75); font-weight:800; margin-top:60px;">
        @daily_enter_kr</div>
      <div style="font-size:24px; color:rgba(243,236,255,.4); margin-top:12px;">재미로 보는 오늘의 연애운</div>
    </div>"""
    return _SHELL.format(pad="80px 60px", extra="", body=body)


def build_slides_html(fortunes, date_str) -> list:
    years = zodiac_years()
    pairs = [ANIMALS[i:i + 2] for i in range(0, 12, 2)]  # 6쌍 (2띠씩)
    html = [cover_html(date_str)]
    html += [content_html(p, fortunes, years) for p in pairs]
    html.append(cta_html())
    return html  # 8장


def render_jpgs(html_list, out_dir: Path) -> list:
    """HTML 리스트 → 1080x1350 jpg (Playwright)."""
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    chrome = os.environ.get("PW_CHROME")  # 로컬 커스텀 경로(선택)
    jpgs = []
    with sync_playwright() as p:
        launch = {"executable_path": chrome} if chrome else {}
        b = p.chromium.launch(**launch)
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
        f"오늘의 띠별 연애운 · {date_str}\n\n"
        "당신의 띠는 몇 점일까요. 가볍게 재미로 보는 오늘의 연애운이에요.\n"
        "내 띠 결과가 궁금하면 저장하고 친구도 태그해봐요.\n\n"
        "#띠별운세 #오늘의운세 #연애운 #띠별연애운 #데일리운세 "
        "#운세스타그램 #오늘의연애운 #재미로보는운세 #띠운세 #소통스타그램"
    )


def main() -> int:
    dry = "--dry-run" in sys.argv
    today = datetime.now(KST).date()
    date_str = f"{today.year}년 {today.month}월 {today.day}일"

    if not dry:
        import post_ledger
        led = post_ledger.load_ledger()
        # 하루 1회 — 오늘 이미 게시했으면 skip
        tprefix = f"{TOPIC_ID}_{today.isoformat()}"
        if any((e.get("topic_id") or "").startswith(tprefix)
               for e in led.get("entries", [])):
            print(f"✅ {tprefix} 이미 게시됨 — skip")
            return 0

    fortunes = generate_fortunes(today)
    html_list = build_slides_html(fortunes, date_str)
    out_dir = ROOT / "output_enter" / "publish" / "fortune_saju"
    jpgs = render_jpgs(html_list, out_dir)
    print(f"✓ 슬라이드 {len(jpgs)}장 렌더: {out_dir.relative_to(ROOT)}/")
    if not (2 <= len(jpgs) <= 10):
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
    print(f"✅ 사주 연애운 캐러셀 게시 완료! {media_id}")
    time.sleep(5)
    try:
        pub.post_comment(media_id, "내 띠는 몇 점? 댓글로 알려줘요")
    except Exception as e:
        print(f"⚠️ 댓글 실패(비치명): {e}")

    post_ledger.record_results([{
        "ok": True, "topic_id": f"{TOPIC_ID}_{today.isoformat()}",
        "title": f"오늘의 띠별 연애운 {date_str}", "style": "fortune_carousel",
        "seed": None, "media_id": media_id,
        "youtube_id": None, "threads_id": None, "bgm": None,
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
