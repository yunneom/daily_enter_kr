"""
참여형(engagement) 데일리 오케스트레이터 — 요일 로테이션으로 5개 포맷 자동 게시.

로테이션 (KST 기준):
  월: unit      드림 유닛 빌더 (4x3 실물사진 그리드, 댓글로 1-3-2-1 조합)
  화: balance   밸런스게임 2문항 (텍스트 카드, 1/2 댓글 투표)
  수: pause     멈춰라 챌린지 (실물사진 고속 순환 릴스)
  목: chemi     케미 듀오 4팀 투표 (같은 그룹 2인 조합, 1~4 댓글 투표)
  금: balance
  토: pause
  일: chemi_result  목요일 투표 집계 → 결과 카드
  + 매월 15일: brandrep  브랜드평판 TOP10 카운트다운 릴스 (해당 월 데이터 1회)

사용:
  python scripts/engagement_daily.py                # 오늘 요일 포맷 자동
  python scripts/engagement_daily.py --format pause # 특정 포맷 강제
  python scripts/engagement_daily.py --dry-run      # 렌더만, 게시 안 함

안전 규칙 (완화 금지):
- 사진은 idol_photo.fetch_photo() 통과분만 (커먼즈 검증 + 만 18세 게이트)
- 인물 A vs B 외모/서열 비교 금지 — 밸런스게임은 상황/취향만
- 케미 = 같은 그룹 멤버 조합만 (검증 가능한 사실), 우정/무대 프레임 고정
- 클릭베이트 어휘 금지, 캡션에 사진 출처(attribution) 표기
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

KST = timezone(timedelta(hours=9))
OUT = ROOT / "output_enter" / "publish" / "engagement"
BAL_PATH = ROOT / "data" / "balance_questions.json"
OVERRIDES_PATH = ROOT / "data" / "idol_photo_overrides.json"
BRANDREP_PATH = ROOT / "data" / "girlgroup_brand_rep_top100.json"

HASHTAGS = "#걸그룹 #이상형월드컵 #케이팝 #kpop #아이돌 #밸런스게임"
WEB_URL = "https://dailyenterkr.com"


# ─────────────────────────────────────────────────────────────── 공통 유틸 ──
def _today():
    return datetime.now(KST).date()


def _seed_for(date, salt: str) -> random.Random:
    h = hashlib.sha256(f"{date.isoformat()}:{salt}".encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def _load_pool():
    """검증된 사진 멤버 풀 [(rank, member, group)] — overrides 기준."""
    ov = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    return [(int(r), v["member"], v["group"]) for r, v in ov.items()]


def _fetch_photos(members):
    """[(rank, member, group)] → [{rank, name, group, photo_path}] (게이트 통과분만 path)."""
    from idol_photo import fetch_photo
    out = []
    for rank, name, group in members:
        rec = fetch_photo(name)
        out.append({"rank": rank, "name": name, "group": group,
                    "photo_path": (rec or {}).get("path")})
    return out


def _already_posted(topic_id: str) -> bool:
    import post_ledger
    led = post_ledger.load_ledger()
    return any((e.get("topic_id") or "") == topic_id for e in led.get("entries", []))


def _ledger_media_id(topic_prefix: str):
    """topic_id 가 prefix 로 시작하는 가장 최근 엔트리의 media_id."""
    import post_ledger
    led = post_ledger.load_ledger()
    for e in reversed(led.get("entries", [])):
        if (e.get("topic_id") or "").startswith(topic_prefix) and e.get("ig_media_id"):
            return e["ig_media_id"], e.get("meta") or {}
    return None, {}


def _record(topic_id: str, title: str, style: str, media_id, youtube_id=None, meta=None):
    import post_ledger
    entry = {"ok": True, "topic_id": topic_id, "title": title, "style": style,
             "seed": None, "media_id": media_id, "youtube_id": youtube_id,
             "threads_id": None, "bgm": None}
    if meta:
        entry["meta"] = meta
    post_ledger.record_results([entry])


def _publisher():
    from post_instagram import InstagramPublisher
    ig_user = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user and ig_token):
        print("❌ INSTAGRAM_USER_ID/ACCESS_TOKEN 미설정")
        return None
    pub = InstagramPublisher(ig_user, ig_token)
    hc = pub.health_check()
    if not hc.get("ok"):
        print(f"❌ IG 토큰 무효: {hc.get('error', '')}")
        print("   → exchange_token.py 재발급 후 Secrets 업데이트 필요")
        return None
    return pub


def _bgm(date) -> Path:
    tracks = sorted((ROOT / "assets" / "bgm").glob("*.mp3"))
    if not tracks:
        return None
    return _seed_for(date, "bgm").choice(tracks)


def _attribution(members) -> str:
    try:
        from idol_photo import attribution_line
        return attribution_line(members)
    except Exception:
        return ""


def _post_carousel(jpgs, caption, first_comment, topic_id, title, style, dry, meta=None):
    if dry:
        print(f"🔍 dry-run — 카드 {len(jpgs)}장 렌더 완료, 게시 생략")
        for j in jpgs:
            print(f"   {j}")
        return 0
    from post_instagram import upload_image
    pub = _publisher()
    if pub is None:
        return 1
    urls = [upload_image(Path(j)) for j in jpgs]
    media_id = pub.post_carousel(urls, caption)
    print(f"✅ 캐러셀 게시 완료: {media_id}")
    _comment(pub, media_id, first_comment)
    _record(topic_id, title, style, media_id, meta=meta)
    return 0


def _post_reel(mp4, caption, first_comment, topic_id, title, style, dry,
               yt_title=None, meta=None):
    if dry:
        print(f"🔍 dry-run — 영상 렌더 완료: {mp4}, 게시 생략")
        return 0
    from post_instagram import upload_video
    pub = _publisher()
    if pub is None:
        return 1
    video_url = upload_video(Path(mp4))
    media_id = pub.post_reel(video_url, caption)
    print(f"✅ Reels 게시 완료: {media_id}")
    _comment(pub, media_id, first_comment)
    youtube_id = None
    try:
        import post_youtube
        if post_youtube.is_configured() and yt_title:
            youtube_id = post_youtube.upload_short(
                Path(mp4), yt_title, caption.split("\n")[0],
                ["kpop", "걸그룹", "shorts"])
            print(f"✅ YT Shorts: {youtube_id}")
    except Exception as e:
        print(f"⚠️ YT 업로드 실패(비치명): {e}")
    _record(topic_id, title, style, media_id, youtube_id=youtube_id, meta=meta)
    return 0


def _comment(pub, media_id, text):
    if not text:
        return
    time.sleep(5)
    try:
        pub.post_comment(media_id, text)
    except Exception as e:
        print(f"⚠️ 댓글 실패(비치명): {e}")


# ──────────────────────────────────────────────────────── 1) 밸런스게임 ──
def run_balance(date, dry):
    topic_id = f"eng_balance_{date.isoformat()}"
    if not dry and _already_posted(topic_id):
        print(f"✅ 오늘 밸런스게임 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_balance_card, make_cta_card
    bank = json.loads(BAL_PATH.read_text(encoding="utf-8"))["questions"]
    rng = _seed_for(date, "balance")
    # 날짜 시드 셔플 후 2문항 — 최근 14일 사용 문항 제외
    recent = set()
    try:
        import post_ledger
        led = post_ledger.load_ledger()
        for e in led.get("entries", []):
            if (e.get("topic_id") or "").startswith("eng_balance_"):
                for qi in (e.get("meta") or {}).get("q_idx", []):
                    recent.add(qi)
    except Exception:
        pass
    order = list(range(len(bank)))
    rng.shuffle(order)
    picks = [i for i in order if i not in recent][:2] or order[:2]
    qs = [bank[i] for i in picks]

    out = OUT / f"balance_{date.isoformat()}"
    jpgs = [make_text_cover(["오늘의", "밸런스게임"], "당신의 선택은? 1 or 2",
                            out / "00_cover.jpg", kicker="K-POP 덕질 편")]
    for n, q in enumerate(qs, 1):
        jpgs.append(make_balance_card(n, len(qs), q["q"], q["a"], q["b"],
                                      out / f"{n:02d}_q.jpg"))
    jpgs.append(make_cta_card(["문항별로 1 or 2", "댓글로 남겨주세요", "", "내일 또 새로운 밸런스로!"],
                              out / "09_cta.jpg", emphasis="당신의 픽은?"))
    caption = (f"오늘의 K-POP 밸런스게임 🎯\n"
               + "\n".join(f"Q{n}. {q['q']} — ① {q['a']} ② {q['b']}" for n, q in enumerate(qs, 1))
               + f"\n\n문항별 선택을 댓글로! (예: 1-2)\n\n{HASHTAGS}")
    return _post_carousel(jpgs, caption, "Q1, Q2 당신의 선택은? 예: 1-2",
                          topic_id, f"밸런스게임 {date.isoformat()}", "eng_balance",
                          dry, meta={"q_idx": picks})


# ─────────────────────────────────────────────────── 2) 멈춰라 챌린지 ──
def run_pause(date, dry):
    topic_id = f"eng_pause_{date.isoformat()}"
    if not dry and _already_posted(topic_id):
        print("✅ 오늘 퍼즈 챌린지 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_member_photo_card, make_cta_card
    from make_video import make_slideshow_video

    pool = _load_pool()
    rng = _seed_for(date, "pause")
    members = rng.sample(pool, min(12, len(pool)))
    cards_meta = _fetch_photos(members)
    # 사진 있는 멤버 우선 정렬 (없으면 그라디언트 카드 — 그래도 게임은 성립)
    with_photo = [m for m in cards_meta if m["photo_path"]]
    if len(with_photo) >= 8:
        cards_meta = with_photo

    out = OUT / f"pause_{date.isoformat()}"
    intro = make_text_cover(["화면을 멈춰서", "오늘의 최애 뽑기"], "지금 스크린샷 준비!",
                            out / "00_intro.jpg", kicker="멈춰라 챌린지")
    frames = []
    for i, m in enumerate(cards_meta):
        frames.append(make_member_photo_card(
            m["photo_path"], m["name"], m["group"],
            out / f"f{i:02d}.jpg", sub="오늘 당신을 응원하는 멤버"))
    outro = make_cta_card(["멈춘 화면 속 멤버가", "오늘의 최애!", "", "결과를 댓글로 인증해주세요"],
                          out / "99_outro.jpg", emphasis="누가 나왔나요?")

    cycles = 3
    paths = [intro] + frames * cycles + [outro]
    durations = [1.6] + [0.15] * (len(frames) * cycles) + [2.2]
    mp4 = make_slideshow_video(paths, out / "pause.mp4", durations=durations,
                               crossfade=0.0, bgm_path=_bgm(date), bgm_volume=0.4)
    names = [m["name"] for m in cards_meta]
    attribution = _attribution(names)
    caption = ("멈춰서 뽑는 오늘의 최애 ✋\n"
               "영상을 아무 때나 멈춰보세요 — 멈춘 화면의 멤버가 오늘 당신을 응원합니다.\n"
               "누가 나왔는지 댓글로 인증!\n\n"
               f"{HASHTAGS}"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_reel(mp4, caption, "몇 번 만에 최애가 나왔나요? 댓글로!",
                      topic_id, f"퍼즈 챌린지 {date.isoformat()}", "eng_pause", dry,
                      yt_title=f"화면을 멈춰서 오늘의 최애 뽑기 #{date.strftime('%m%d')}")


# ─────────────────────────────────────────────── 3) 드림 유닛 빌더 ──
def run_unit(date, dry):
    topic_id = f"eng_unit_{date.isoformat()}"
    if not dry and _already_posted(topic_id):
        print("✅ 오늘 유닛 빌더 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_unit_grid_card, make_cta_card, make_text_cover

    pool = _load_pool()
    rng = _seed_for(date, "unit")
    # 12명 — 같은 그룹이 한 행에 겹치지 않게 그리디 배치
    members = rng.sample(pool, min(12, len(pool)))
    cards_meta = _fetch_photos(members)
    rng.shuffle(cards_meta)
    rows = []
    remaining = list(cards_meta)
    for r in range(4):
        row, used_groups = [], set()
        for m in list(remaining):
            if len(row) >= 3:
                break
            if m["group"] in used_groups:
                continue
            row.append(m)
            used_groups.add(m["group"])
            remaining.remove(m)
        while len(row) < 3 and remaining:
            row.append(remaining.pop(0))
        rows.append([{"photo_path": m["photo_path"], "name": m["name"],
                      "group": m["group"]} for m in row])

    out = OUT / f"unit_{date.isoformat()}"
    grid = make_unit_grid_card(rows, out / "01_grid.jpg")
    rule = make_text_cover(["각 줄에서 1명씩", "나만의 4인조 완성"],
                           "댓글로 조합 남기기 — 예: 1-3-2-1",
                           out / "02_rule.jpg", kicker="드림 유닛 빌더")
    cta = make_cta_card(["정답은 없습니다", "당신의 조합이 곧 유닛!", "",
                         "가장 많이 나온 조합은", "다음 주에 공개"],
                        out / "03_cta.jpg", emphasis="너의 유닛을 보여줘")
    names = [c["name"] for row in rows for c in row]
    attribution = _attribution(names)
    caption = ("나만의 드림 유닛 만들기 🎤\n"
               "각 줄(1~4)에서 한 명씩 골라 4인조를 완성하세요.\n"
               "조합을 댓글로! 예: 1-3-2-1\n\n"
               f"{HASHTAGS}"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_carousel([grid, rule, cta], caption,
                          "당신의 유닛 조합은? 예: 1-3-2-1",
                          topic_id, f"드림 유닛 빌더 {date.isoformat()}", "eng_unit", dry)


# ─────────────────────────────────────────────── 4) 케미 듀오 투표 ──
def _weekly_duos(date):
    """이번 주(ISO 주차 시드) 같은 그룹 듀오 4팀 — 서로 다른 그룹."""
    pool = _load_pool()
    by_group = {}
    for rank, name, group in pool:
        by_group.setdefault(group, []).append((rank, name))
    eligible = {g: ms for g, ms in by_group.items() if len(ms) >= 2}
    iso = date.isocalendar()
    rng = _seed_for(date.fromisocalendar(iso[0], iso[1], 1), "chemi")
    groups = rng.sample(sorted(eligible), min(4, len(eligible)))
    duos = []
    for g in groups:
        pair = rng.sample(eligible[g], 2)
        duos.append({"group": g, "members": [{"rank": r, "name": n} for r, n in pair]})
    return duos, iso


def run_chemi(date, dry):
    iso = date.isocalendar()
    topic_id = f"eng_chemi_w{iso[0]}{iso[1]:02d}"
    if not dry and _already_posted(topic_id):
        print("✅ 이번 주 케미 투표 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_duo_card, make_cta_card
    duos, iso = _weekly_duos(date)
    out = OUT / f"chemi_w{iso[0]}{iso[1]:02d}"
    jpgs = [make_text_cover(["이 주의", "케미 듀오 4팀"], "가장 보고 싶은 듀오 무대는?",
                            out / "00_cover.jpg", kicker="케미 맛집 투표")]
    duo_names = []
    for i, duo in enumerate(duos, 1):
        fetched = _fetch_photos([(m["rank"], m["name"], duo["group"]) for m in duo["members"]])
        duo_names += [m["name"] for m in fetched]
        jpgs.append(make_duo_card(
            i, duo["group"],
            [{"photo_path": f["photo_path"], "name": f["name"]} for f in fetched],
            out / f"{i:02d}_duo.jpg", tagline="같은 팀, 다른 매력"))
    jpgs.append(make_cta_card(["1 ~ 4 중에서", "댓글로 투표해주세요", "", "결과는 일요일 발표!"],
                              out / "09_cta.jpg", emphasis="당신의 픽은?"))
    labels = [f"{i}. {d['group']} " + "·".join(m['name'] for m in d['members'])
              for i, d in enumerate(duos, 1)]
    attribution = _attribution(duo_names)
    caption = ("이 주의 케미 듀오 4팀 💜 어떤 듀오 무대가 가장 보고 싶나요?\n"
               + "\n".join(labels)
               + "\n\n번호를 댓글로! 결과는 일요일에 공개됩니다.\n\n"
               f"{HASHTAGS}"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_carousel(jpgs, caption, "1~4 번호로 투표! 결과는 일요일에",
                          topic_id, f"케미 듀오 투표 {iso[0]}-W{iso[1]}", "eng_chemi", dry,
                          meta={"duos": labels})


def run_chemi_result(date, dry):
    iso = date.isocalendar()
    vote_prefix = f"eng_chemi_w{iso[0]}{iso[1]:02d}"
    topic_id = f"{vote_prefix}_result"
    if not dry and _already_posted(topic_id):
        print("✅ 이번 주 케미 결과 이미 게시 — skip")
        return 0
    media_id, meta = _ledger_media_id(vote_prefix)
    if not media_id:
        print("⚠️ 이번 주 투표 게시물이 없어 결과 생략")
        return 0
    labels = meta.get("duos") or ["1", "2", "3", "4"]

    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    counts = {str(i): 0 for i in range(1, 5)}
    voters = set()
    if token:
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from worldcup_tally import fetch_all_comments
            for c in fetch_all_comments(media_id, token):
                m = re.search(r"[1-4]", c.get("text", ""))
                uid = c.get("username") or c.get("id")
                if m and uid not in voters:
                    voters.add(uid)
                    counts[m.group()] += 1
        except Exception as e:
            print(f"⚠️ 댓글 집계 실패: {e}")
    total = sum(counts.values())
    if total == 0 and not dry:
        print("⚠️ 유효 투표 0 — 결과 게시 생략 (다음 주 재도전)")
        return 0

    from make_engagement_cards import make_result_bar_card
    items = []
    for i in range(1, 5):
        pct = (counts[str(i)] / total * 100) if total else 0
        label = labels[i - 1] if i - 1 < len(labels) else str(i)
        label = re.sub(r"^\d+\.\s*", "", label)[:18]
        items.append({"label": label, "pct": pct})
    items.sort(key=lambda x: -x["pct"])
    out = OUT / f"chemi_w{iso[0]}{iso[1]:02d}"
    card = make_result_bar_card("케미 듀오 투표 결과", items, out / "10_result.jpg",
                                sub=f"총 {total}표 · 팔로워 픽")
    caption = (f"이 주의 케미 듀오 투표 결과 🏆\n1위: {items[0]['label']} ({items[0]['pct']:.0f}%)\n"
               f"총 {total}표 참여 감사합니다!\n다음 주 새로운 듀오로 돌아올게요.\n\n{HASHTAGS}")
    return _post_carousel([card], caption, "다음 주 보고 싶은 듀오를 추천해주세요!",
                          topic_id, f"케미 결과 {iso[0]}-W{iso[1]}", "eng_chemi_result", dry)


# ─────────────────────────────────── 5) 브랜드평판 카운트다운 ──
def run_brandrep(date, dry):
    data = json.loads(BRANDREP_PATH.read_text(encoding="utf-8"))
    period = data.get("period", "").replace(" ", "")
    topic_id = f"eng_brandrep_{period}"
    if not dry and _already_posted(topic_id):
        print(f"✅ {period} 브랜드평판 카운트다운 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_member_photo_card, make_cta_card
    from make_video import make_slideshow_video
    from idol_photo import fetch_photo

    top10 = sorted(data["rankings"], key=lambda r: r["rank"])[:10]
    out = OUT / f"brandrep_{period}"
    cover = make_text_cover([period.replace("년", "년 "), "걸그룹 브랜드평판", "TOP 10"],
                            "내 최애는 몇 위? 끝까지 확인!",
                            out / "00_cover.jpg", kicker="공식 데이터", accent_line_idx=2)
    frames, names = [cover], []
    for r in sorted(top10, key=lambda x: -x["rank"]):  # 10위 → 1위
        rec = fetch_photo(r["member"])
        names.append(r["member"])
        frames.append(make_member_photo_card(
            (rec or {}).get("path"), r["member"], r["group"],
            out / f"rank{r['rank']:02d}.jpg",
            sub=f"브랜드평판 지수 {r['score']:,}", big_text=f"{r['rank']}"))
    outro = make_cta_card(["출처: 한국기업평판연구소", f"{data.get('source_date','')} 발표", "",
                           "최애 순위 예측 성공했나요?", "댓글로 알려주세요"],
                          out / "99_outro.jpg", emphasis="1위까지 확인 완료!")
    frames.append(outro)
    durations = [1.8] + [2.2] * 10 + [2.5]
    mp4 = make_slideshow_video(frames, out / "brandrep.mp4", durations=durations,
                               crossfade=0.25, bgm_path=_bgm(date), bgm_volume=0.35)
    attribution = _attribution(names)
    caption = (f"{period} 걸그룹 개인 브랜드평판 TOP10 📊\n"
               "10위부터 1위까지 — 내 최애는 몇 위일까요?\n"
               f"출처: 한국기업평판연구소 ({data.get('source_date','')})\n\n"
               f"{HASHTAGS}"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_reel(mp4, caption, "최애 순위 맞히셨나요? 댓글로!",
                      topic_id, f"브랜드평판 TOP10 {period}", "eng_brandrep", dry,
                      yt_title=f"{period} 걸그룹 브랜드평판 TOP10 카운트다운")


# ──────────────────────────────────────────────────────────── main ──
FORMATS = {
    "balance": run_balance, "pause": run_pause, "unit": run_unit,
    "chemi": run_chemi, "chemi_result": run_chemi_result, "brandrep": run_brandrep,
}
ROTATION = {0: "unit", 1: "balance", 2: "pause", 3: "chemi",
            4: "balance", 5: "pause", 6: "chemi_result"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=sorted(FORMATS), default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    date = _today()
    fmt = args.format or ROTATION[date.weekday()]
    print(f"📅 {date} ({['월','화','수','목','금','토','일'][date.weekday()]}) → 포맷: {fmt}")
    rc = FORMATS[fmt](date, args.dry_run)

    # 매월 15일: 브랜드평판 추가 게시 (그 달 데이터 미게시분만)
    if args.format is None and date.day == 15:
        print("\n📊 15일 — 브랜드평판 카운트다운 추가 시도")
        rc = max(rc, run_brandrep(date, args.dry_run))
    return rc


if __name__ == "__main__":
    sys.exit(main())
