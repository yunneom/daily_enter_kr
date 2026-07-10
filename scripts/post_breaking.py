"""
속보 뉴스 카드 1건 게시 — 재사용형 (반응형 breaking-news 게시).

data/breaking_news.json 을 읽어 프리미엄 뉴스 카드(1080x1350, 4:5)를 렌더 →
IG 단일 이미지 게시. photo_url 있으면 상단에 실물사진 합성(없으면 디자인-only).

사용: (1) data/breaking_news.json 수정 → git push (breaking_news.yml paths 트리거) 로 즉시 게시.
      (2) 로컬 미리보기: python scripts/post_breaking.py --dry-run
멱등: 같은 topic_id 가 ledger 에 있으면 skip.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

DATA = ROOT / "data" / "breaking_news.json"


def _photo_data_uri(url: str) -> str:
    """photo_url → base64 data URI. direct → wsrv 프록시 폴백. 실패 시 ''."""
    if not url:
        return ""
    import requests
    enc = quote(url, safe="")
    for u in (url, f"https://wsrv.nl/?url={enc}&w=1080&output=jpg"):
        try:
            r = requests.get(u, timeout=20, headers={"User-Agent": "daily_enter_kr/1.0"})
            if r.ok and len(r.content) > 2000:
                return "data:image/jpeg;base64," + base64.b64encode(r.content).decode()
        except Exception:
            continue
    print("  ⚠️ 사진 로드 실패 — 디자인-only 카드로 진행")
    return ""


def build_html(d: dict) -> str:
    photo = _photo_data_uri(d.get("photo_url", ""))
    hero = (f'<div style="height:560px; margin:-88px -70px 34px; background-image:url({photo});'
            f'background-size:cover; background-position:center 22%; position:relative;">'
            f'<div style="position:absolute; inset:0; background:linear-gradient(180deg,'
            f'rgba(8,6,24,.15) 0%,rgba(8,6,24,.35) 55%,#0c0a24 100%);"></div></div>'
            if photo else '<div style="height:20px;"></div>')
    heads = "<br>".join(d["headline_lines"])
    pts = "\n".join(
        f'<li style="font-size:32px; color:rgba(255,255,255,.82); margin-bottom:14px;'
        f' padding-left:34px; position:relative;">'
        f'<span style="position:absolute; left:0; color:#ffd94a;">·</span>{p}</li>'
        for p in d.get("points", []))
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box;
     font-family:'Pretendard','Apple SD Gothic Neo','Noto Sans KR',sans-serif; }}
body {{ width:1080px; height:1350px; overflow:hidden; color:#fff;
  background:linear-gradient(165deg,#141033 0%,#1b0b3e 45%,#0c0a24 100%);
  display:flex; flex-direction:column; padding:88px 70px 60px; }}
.badge {{ display:inline-block; align-self:flex-start; background:#ff3b3b; color:#fff;
  font-size:28px; font-weight:800; letter-spacing:2px; padding:10px 26px; border-radius:12px; }}
.h1 {{ font-size:92px; font-weight:900; line-height:1.1; margin-top:26px; }}
.h1 b {{ color:#ffd94a; }}
.sub {{ font-size:40px; font-weight:800; color:#ffd94a; margin-top:20px; }}
.pts {{ list-style:none; margin-top:34px; }}
.foot {{ margin-top:auto; }}
.src {{ font-size:25px; color:rgba(255,255,255,.5); }}
.hd {{ font-size:29px; color:rgba(255,255,255,.72); font-weight:800; margin-top:10px; }}
</style></head><body>
  {hero}
  <div style="flex:1; display:flex; flex-direction:column; justify-content:center;">
    <div class="badge">{d.get('badge','속보')}</div>
    <div class="h1"><b>{heads}</b></div>
    <div class="sub">{d.get('sub','')}</div>
    <ul class="pts">{pts}</ul>
  </div>
  <div class="foot">
    <div class="src">출처: {d.get('source','')}</div>
    <div class="hd">@daily_enter_kr</div>
  </div>
</body></html>"""


def render_jpg(html: str, out: Path) -> Path:
    from playwright.sync_api import sync_playwright
    out.parent.mkdir(parents=True, exist_ok=True)
    hp = out.with_suffix(".html")
    hp.write_text(html, encoding="utf-8")
    chrome = os.environ.get("PW_CHROME")
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        pg.goto(hp.resolve().as_uri())
        pg.wait_for_timeout(900)
        pg.screenshot(path=str(out), type="jpeg", quality=92)
        b.close()
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    d = json.loads(DATA.read_text(encoding="utf-8"))
    tid = d["topic_id"]

    if not dry:
        import post_ledger
        led = post_ledger.load_ledger()
        if any((e.get("topic_id") or "") == tid for e in led.get("entries", [])):
            print(f"✅ {tid} 이미 게시됨 — skip")
            return 0

    out = ROOT / "output_enter" / "publish" / "breaking" / f"{tid}.jpg"
    render_jpg(build_html(d), out)
    print(f"✓ 카드 렌더: {out.relative_to(ROOT)} ({out.stat().st_size // 1024}KB)")
    if dry:
        print("🔍 dry-run — 게시 안 함")
        return 0

    from post_instagram import InstagramPublisher, upload_image
    import post_ledger
    iu, it = os.environ.get("INSTAGRAM_USER_ID"), os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (iu and it):
        print("❌ IG 미설정")
        return 1
    pub = InstagramPublisher(iu, it)
    if not pub.health_check().get("ok"):
        print("❌ IG 토큰 무효")
        return 1
    url = upload_image(out)
    media_id = pub.post_single_image(url, d["caption"])
    print(f"✅ 속보 카드 게시 완료! {media_id}")
    post_ledger.record_results([{
        "ok": True, "topic_id": tid, "title": " ".join(d["headline_lines"]),
        "style": "breaking_news", "seed": None, "media_id": media_id,
        "youtube_id": None, "threads_id": None, "bgm": None,
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
