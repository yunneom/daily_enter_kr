"""
참여형(engagement) 데일리 오케스트레이터 — 요일 로테이션으로 포맷 자동 게시.

로테이션 (KST 기준, 2026-09 축소 편성 — ROTATION 참고):
  금: quiz      걸그룹 상식 등급전 (5문항 퀴즈 릴스, 0~5 댓글)
  (휴면 — --format 으로 수동만: unit 드림 유닛 / balance 밸런스게임 / pause 멈춰라 /
   chemi 케미 듀오 투표 / chemi_result 결과. 반응 0 으로 편성 제외)
  + 매월 2일: rookie    신인 걸그룹 브랜드평판 랭킹 릴스 (해당 월 데이터 1회)
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

# 해시태그는 날짜 시드로 풀에서 6개를 뽑아 매 게시마다 조합이 달라지게 한다 —
# 모든 게시물에 똑같은 태그 문자열이 붙는 건 IG 가 보는 반복/스팸 신호 중 하나.
_HASHTAG_POOL = ["#걸그룹", "#케이팝", "#kpop", "#아이돌", "#kpopgirlgroup", "#4세대걸그룹",
                 "#5세대걸그룹", "#걸그룹추천", "#아이돌추천", "#덕질", "#최애", "#kpopidol",
                 "#girlgroup", "#케이팝걸그룹"]


def _rotating_hashtags(n: int = 6) -> str:
    today = datetime.now(KST).date()
    rng = random.Random(int(hashlib.sha256(f"{today.isoformat()}:tags".encode()).hexdigest()[:12], 16))
    picks = ["#걸그룹"] + rng.sample([t for t in _HASHTAG_POOL if t != "#걸그룹"], n - 1)
    return " ".join(picks)


HASHTAGS = _rotating_hashtags()

# "팔로우할 이유 = 다음 걸 볼 이유" — 편성표를 예고로 노출해 시리즈성을 만든다.
# 2026-09 편성 축소 후: 월·수·금 18:00 만원 조합(매트릭스) / 금 11:30 상식 등급전 /
# 매월 1일 컴백 캘린더 · 2일 신인 랭킹 · 15일 브랜드평판.
_NEXT_TEASER = {
    0: "수요일 18:00 만원 조합 새 편",       # 월
    1: "수요일 18:00 만원 조합 새 편",       # 화
    2: "금요일 11:30 상식 등급전",           # 수
    3: "내일 11:30 상식 등급전",             # 목
    4: "월요일 18:00 만원 조합 새 편",       # 금
    5: "월요일 18:00 만원 조합 새 편",       # 토
    6: "내일 18:00 만원 조합 새 편",         # 일
}


def _follow_loop(date) -> str:
    """캡션 말미 공통 팔로우 루프 — 예고 + 저장 프레임."""
    teaser = _NEXT_TEASER.get(date.weekday(), "")
    lines = ["🔔 월·수·금 18:00 만원 조합 · 금 11:30 상식 등급전"]
    if teaser:
        lines.append(f"⏭ {teaser}")
    lines.append("🔖 저장해두면 다음 편 나왔을 때 비교하기 편해요")
    return "\n".join(lines)
WEB_URL = "https://dailyenterkr.com"


# ─────────────────────────────────────────────────────────────── 공통 유틸 ──
def _today():
    return datetime.now(KST).date()


def _seed_for(date, salt: str) -> random.Random:
    h = hashlib.sha256(f"{date.isoformat()}:{salt}".encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def _load_pool():
    """실사 사용 가능한 멤버 풀 [(rank, member, group)].

    overrides(사람이 검증한 커먼즈 파일) ∩ 저장소에 실제로 커밋된 사진.
    커밋 캐시에 없는 멤버는 애초에 뽑지 않는다 — 폴백 카드가 섞이는 것을 사전에
    막고, 캐시가 아직 다 안 찼어도 확보분만으로 정상 게시가 이어지게 한다.
    (런타임 실패에 대비한 최종 방어선은 _require_all_photos.)
    """
    from idol_photo import repo_cached_photo
    ov = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    pool = [(int(r), v["member"], v["group"]) for r, v in ov.items()
            if repo_cached_photo(v["member"], v["group"])]
    if not pool:
        raise PhotoCoverageError(
            "실사 캐시가 비어 있습니다 — warm_photo_cache 워크플로우를 먼저 실행하세요.")
    return pool


class PhotoCoverageError(Exception):
    """실사 사진을 확보하지 못한 멤버가 있어 게시를 중단한다."""


def _fetch_photos(members):
    """[(rank, member, group)] → [{rank, name, group, photo_path}] (게이트 통과분만 path)."""
    from idol_photo import fetch_photo, repo_cached_photo
    out = []
    for rank, name, group in members:
        # 소속까지 대조해 동명이인 오표기를 차단한다.
        rec = repo_cached_photo(name, group) or fetch_photo(name)
        out.append({"rank": rank, "name": name, "group": group,
                    "photo_path": (rec or {}).get("path")})
    return out


def _require_all_photos(fetched, fmt: str):
    """실사 전원 확보 강제 — 한 명이라도 없으면 게시하지 않고 중단한다.

    운영자 요구(2026-07): 그라디언트 폴백이 섞인 카드는 올리지 말고 알릴 것.
    여기서 예외를 던지면 main() 이 exit 1 → 워크플로우 실패 → GitHub 이슈 자동 생성.
    """
    missing = [f"{m['group']} {m['name']}(#{m['rank']})" for m in fetched if not m.get("photo_path")]
    if missing:
        raise PhotoCoverageError(
            f"[{fmt}] 실사 미확보 {len(missing)}/{len(fetched)}명: " + ", ".join(missing)
        )


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
    _require_all_photos(cards_meta, "pause")

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
               f"{_follow_loop(date)}\n\n{HASHTAGS}"
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
    _require_all_photos(cards_meta, "unit")
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
               f"{_follow_loop(date)}\n\n{HASHTAGS}"
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
        _require_all_photos(fetched, "chemi")
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
               f"{_follow_loop(date)}\n\n{HASHTAGS}"
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

    # 자유 라이선스 실사가 검증된 멤버만 카운트다운에 올린다. 검증 사진이 없는
    # 멤버(예: 커먼즈에 개인 식별 가능한 파일이 없는 경우)를 넣으면 폴백 카드가
    # 섞여 나가므로 제외하고, 제외 사실은 캡션에 명시해 오해가 없게 한다.
    ov_names = {name for _, name, _ in _load_pool()}
    ordered = sorted(data["rankings"], key=lambda r: r["rank"])
    top10 = [r for r in ordered if r["member"] in ov_names][:10]
    if len(top10) < 10:
        raise PhotoCoverageError(
            f"[brandrep] 실사 검증 멤버가 {len(top10)}명뿐이라 TOP10 구성 불가")
    skipped = [r["member"] for r in ordered[: top10[-1]["rank"]] if r["member"] not in ov_names]
    _require_all_photos(
        _fetch_photos([(r["rank"], r["member"], r["group"]) for r in top10]), "brandrep")
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
    skip_note = (f"\n(사진 사용이 가능한 멤버 기준 — {', '.join(skipped)} 제외)"
                 if skipped else "")
    caption = (f"{period} 걸그룹 개인 브랜드평판 TOP10 📊\n"
               "10위부터 1위까지 — 내 최애는 몇 위일까요?\n"
               f"출처: 한국기업평판연구소 ({data.get('source_date','')}){skip_note}\n\n"
               f"{_follow_loop(date)}\n\n{HASHTAGS}"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_reel(mp4, caption, "최애 순위 맞히셨나요? 댓글로!",
                      topic_id, f"브랜드평판 TOP10 {period}", "eng_brandrep", dry,
                      yt_title=f"{period} 걸그룹 브랜드평판 TOP10 카운트다운")


# ─────────────────────────────── 6) 컴백 캘린더 (저장형 자산) ──
# 2026-W34 트렌드 스카우트 채택안 1번 — "저장 0을 깨라". 데이터는
# data/comeback_calendar.json (2개 이상 출처 교차 확인된 확정 일정만, 수기 갱신).
CAL_PATH = ROOT / "data" / "comeback_calendar.json"


def run_calendar(date, dry):
    data = json.loads(CAL_PATH.read_text(encoding="utf-8"))
    # 지난 일정은 자동 제외 — 오늘 이후만
    entries = [e for e in data["entries"] if e["date"] >= date.isoformat()]
    topic_id = f"eng_calendar_{data['updated']}"
    if not dry and _already_posted(topic_id):
        print("✅ 이 버전 캘린더 이미 게시 — skip (데이터 갱신 시 updated 날짜 변경)")
        return 0
    if len(entries) < 2:
        print(f"⚠️ 남은 확정 일정 {len(entries)}건 — 캘린더 게시 생략 (데이터 갱신 필요)")
        return 0
    from make_engagement_cards import make_text_cover, make_calendar_card, make_cta_card
    out = OUT / f"calendar_{data['updated']}"
    cover = make_text_cover(["다가오는", "걸그룹 컴백"], f"{data['period']} · 확정 {len(entries)}건",
                            out / "00_cover.jpg", kicker="저장해두고 챙기세요")
    cal = make_calendar_card(data["period"], entries, out / "01_cal.jpg",
                             disclaimer=data.get("disclaimer", ""))
    cta = make_cta_card(["빠진 일정이 있다면", "댓글로 제보해주세요", "",
                         "제보 반영해서 갱신본으로 올립니다"],
                        out / "02_cta.jpg", emphasis="🔖 저장 필수")
    listing = " · ".join(f"{int(e['date'][5:7])}/{int(e['date'][8:10])} {e['name']}"
                         for e in entries)
    caption = (f"걸그룹 컴백 캘린더 📅 {data['period']}\n"
               f"{listing}\n\n"
               f"저장해두면 놓칠 일 없어요. 빠진 일정은 댓글로 제보 — 갱신본에 반영합니다.\n"
               f"({data.get('disclaimer','')})\n\n"
               f"{_follow_loop(date)}\n\n{HASHTAGS}")
    return _post_carousel([cover, cal, cta], caption,
                          "빠진 컴백 일정 제보 받아요 ⬇️ 갱신본에 반영!",
                          topic_id, f"컴백 캘린더 {data['period']}", "eng_calendar", dry)


# ─────────────── 6.5) 신인 걸그룹 브랜드평판 카운트다운 (월간, 릴스) ──
# 2026-09 신설 — 한국기업평판연구소 "신인 아이돌그룹 브랜드평판"(보이+걸 통합
# TOP30, 매월 1일경 발표)에서 걸그룹만 발췌한 월간 랭킹. 데이터는
# data/rookie_girlgroup_brand_rep.json (뉴스 매체 2곳 이상 교차 검증 후 수기 갱신).
# 사진은 개인이 아니라 "그룹 단체 사진"(assets/group_photos/, 커먼즈 자유
# 라이선스 + 다운로드 시점 재검증) — 단체 사진이 없는 그룹은 카드에서 빼되,
# 순위 번호는 발췌 랭킹 그대로 유지하고 캡션에 전체 순위+제외 사실을 명기한다.
ROOKIE_PATH = ROOT / "data" / "rookie_girlgroup_brand_rep.json"
ROOKIE_MIN_CARDS = 6


def _group_attribution(groups) -> str:
    """그룹 단체사진 출처 표기 — 캐시된 그룹당 한 줄."""
    from warm_group_photo_cache import load_group_cache
    attr = load_group_cache()
    lines = []
    for g in groups:
        rec = attr.get(g, {})
        if not rec.get("path"):
            continue
        a = rec.get("artist") or "Wikimedia 기여자"
        lic = rec.get("license") or "CC"
        lines.append(f"사진 출처: {g} — {a} ({lic}, Wikimedia Commons)")
    return "\n".join(lines[:12])


def run_rookie(date, dry):
    from warm_group_photo_cache import group_cached_photo
    data = json.loads(ROOKIE_PATH.read_text(encoding="utf-8"))
    period = data["period"].replace(" ", "")
    topic_id = f"eng_rookie_brandrep_{period}"
    if not dry and _already_posted(topic_id):
        print(f"✅ {period} 신인 걸그룹 랭킹 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_group_rank_card, make_cta_card
    from make_video import make_slideshow_video

    ordered = sorted(data["rankings"], key=lambda r: r["gg_rank"])
    with_photo = [r for r in ordered if group_cached_photo(r["group"])]
    if len(with_photo) < ROOKIE_MIN_CARDS:
        raise PhotoCoverageError(
            f"[rookie] 단체 실사 확보 그룹이 {len(with_photo)}/{len(ordered)}개뿐 "
            f"(최소 {ROOKIE_MIN_CARDS}) — warm_group_photo_cache.py 로 캐시를 채우세요. "
            "미확보: " + ", ".join(r["group"] for r in ordered
                                  if not group_cached_photo(r["group"])))
    skipped = [r["group"] for r in ordered if not group_cached_photo(r["group"])]

    out = OUT / f"rookie_{period}"
    cover = make_text_cover([period.replace("년", "년 "), "신인 걸그룹", "브랜드평판 랭킹"],
                            "이번 달 대세 신인은? 끝까지 확인!",
                            out / "00_cover.jpg", kicker="공식 데이터", accent_line_idx=1)
    frames = [cover]
    for r in sorted(with_photo, key=lambda x: -x["gg_rank"]):  # 하위 → 1위
        rec = group_cached_photo(r["group"])
        chg = r.get("change_pct")
        chg_txt = ("" if chg is None else
                   f" · 전월 {'▲' if chg >= 0 else '▼'}{abs(chg):.1f}%")
        frames.append(make_group_rank_card(
            rec["path"], r["gg_rank"], r["group"], r.get("group_en", ""),
            (f"브랜드평판 지수 {r['score']:,}{chg_txt}" if r.get("score")
             else f"보이그룹 포함 통합 {r['overall_rank']}위{chg_txt}"),
            out / f"rank{r['gg_rank']:02d}.jpg"))
    frames.append(make_cta_card(
        ["출처: 한국기업평판연구소", f"{data.get('source_date', '')} 발표",
         "2023년 이후 데뷔 그룹 대상", "", "다음 달 1위 예측은?", "댓글로 남겨주세요"],
        out / "99_outro.jpg", emphasis="내 최애 신인 몇 위?"))
    durations = [1.8] + [2.2] * len(with_photo) + [2.5]
    mp4 = make_slideshow_video(frames, out / "rookie.mp4", durations=durations,
                               crossfade=0.25, bgm_path=_bgm(date), bgm_volume=0.35)

    listing = " · ".join(f"{r['gg_rank']}위 {r['group']}" for r in ordered)
    skip_note = (f"\n(영상은 자유 라이선스 단체 사진이 있는 그룹 기준 — "
                 f"{', '.join(skipped)}는 순위 텍스트로만 표기)" if skipped else "")
    attribution = _group_attribution([r["group"] for r in with_photo])
    caption = (f"{period} 신인 걸그룹 브랜드평판 랭킹 🌱\n"
               f"{listing}\n"
               f"출처: 한국기업평판연구소 ({data.get('source_date', '')} 발표, "
               f"2023년 이후 데뷔 보이+걸그룹 통합 TOP30 중 걸그룹 발췌){skip_note}\n\n"
               f"{_follow_loop(date)}\n\n{HASHTAGS} #신인걸그룹 #4세대걸그룹"
               + (f"\n\n{attribution}" if attribution else ""))
    return _post_reel(mp4, caption, "다음 달 신인 1위 예측 댓글로! 🌱",
                      topic_id, f"신인 걸그룹 랭킹 {period}", "eng_rookie", dry,
                      yt_title=f"{period} 신인 걸그룹 브랜드평판 랭킹 카운트다운")


# ─────────────────────────────── 7) 걸그룹 상식 등급전 (퀴즈 릴스) ──
# 스카우트 채택안 3번. 문항은 저장소에서 이미 검증된 데이터(group_rosters·
# 브랜드평판)에서만 프로그램으로 생성 — 날조 위험 0. 분쟁/활동중단 이슈가 있는
# 그룹(뉴진스·베이비몬스터)과 보이그룹은 문항에서 제외.
QUIZ_EXCLUDE_GROUPS = {"뉴진스", "BABYMONSTER", "RIIZE", "ATEEZ", "CORTIS",
                       "KickFlip", "NCT", "P1Harmony", "TWS", "TXT", "더보이즈",
                       "보이넥스트도어", "스트레이키즈", "엔하이픈", "제로베이스원", "트레저"}


def _quiz_pool():
    rosters = json.loads((ROOT / "data" / "group_rosters.json").read_text(encoding="utf-8"))["groups"]
    return {g: r for g, r in rosters.items()
            if g not in QUIZ_EXCLUDE_GROUPS and len(r.get("members", [])) >= 4}


def _build_quiz(date, n=5):
    """검증 데이터 기반 5문항 — (질문, 보기4, 정답 인덱스)."""
    rng = _seed_for(date, "quiz")
    pool = _quiz_pool()
    groups = sorted(pool)
    qs = []

    def member_of(g):
        return rng.choice(pool[g]["members"])

    # 유형1·2: "다음 중 ○○ 멤버는?" x2 — 정답 1 + 타 그룹 멤버 3
    for g in rng.sample(groups, 2):
        others = [x for x in groups if x != g]
        opts = [member_of(g)] + [member_of(o) for o in rng.sample(others, 3)]
        ans = opts[0]; rng.shuffle(opts)
        qs.append((f"다음 중 {g} 멤버는?", opts, opts.index(ans)))
    # 유형3: 역매칭 "'○○'가 속한 그룹은?"
    g = rng.choice(groups)
    m = member_of(g)
    opts = [g] + rng.sample([x for x in groups if x != g], 3)
    ans = opts[0]; rng.shuffle(opts)
    qs.append((f"'{m}' — 소속 그룹은?", opts, opts.index(ans)))
    # 유형4: 멤버 수
    g = rng.choice([x for x in groups if x not in ("소녀시대",)])  # 활동 형태 논쟁 여지 그룹 제외
    correct = len(pool[g]["members"])
    opts_n = sorted({correct, correct + 1, max(2, correct - 1), correct + 2})[:4]
    while len(opts_n) < 4:
        opts_n.append(max(opts_n) + 1)
    rng.shuffle(opts_n)
    qs.append((f"{g} — 현재 몇 인조? (2026년 기준)",
               [f"{x}인조" for x in opts_n], opts_n.index(correct)))
    # 유형5: 브랜드평판 (자체 데이터)
    br = json.loads(BRANDREP_PATH.read_text(encoding="utf-8"))
    top = sorted(br["rankings"], key=lambda r: r["rank"])
    first = top[0]
    distract = [r["member"] for r in top[1:4]]
    opts = [first["member"]] + distract
    ans = opts[0]; rng.shuffle(opts)
    qs.append((f"{br['period']} 걸그룹 개인 브랜드평판 1위는?", opts, opts.index(ans)))

    rng.shuffle(qs)
    return qs[:n]


def run_quiz(date, dry):
    topic_id = f"eng_quiz_{date.isoformat()}"
    if not dry and _already_posted(topic_id):
        print("✅ 오늘 상식 등급전 이미 게시 — skip")
        return 0
    from make_engagement_cards import make_text_cover, make_quiz_card, make_grade_card
    from make_video import make_slideshow_video

    qs = _build_quiz(date)
    out = OUT / f"quiz_{date.isoformat()}"
    cover = make_text_cover(["걸그룹 상식", "등급전"], "5문항 · 3초 안에 답하기",
                            out / "00_cover.jpg", kicker="너 얼마나 아는데?")
    paths, durations = [cover], [1.8]
    for i, (q, opts, ans) in enumerate(qs, 1):
        paths.append(make_quiz_card(i, len(qs), q, opts, out / f"q{i}_q.jpg",
                                    countdown="3초"))
        durations.append(3.5)
        paths.append(make_quiz_card(i, len(qs), q, opts, out / f"q{i}_a.jpg",
                                    answer_idx=ans))
        durations.append(1.2)
    paths.append(make_grade_card(out / "99_grade.jpg"))
    durations.append(3.0)

    mp4 = make_slideshow_video(paths, out / "quiz.mp4", durations=durations,
                               crossfade=0.0, bgm_path=_bgm(date), bgm_volume=0.35)
    caption = ("걸그룹 상식 등급전 🎓 5문항, 문항당 3초!\n"
               "몇 개 맞혔는지 댓글로 (0~5) — 5개면 고인물 인정 👑\n"
               "출처: 공식 프로필 · 한국기업평판연구소\n\n"
               f"{_follow_loop(date)}\n\n{HASHTAGS}")
    return _post_reel(mp4, caption, "몇 개 맞혔어요? 0~5 댓글로!",
                      topic_id, f"상식 등급전 {date.isoformat()}", "eng_quiz", dry,
                      yt_title=f"걸그룹 상식 등급전 — 너 얼마나 아는데? #{date.strftime('%m%d')}")


# ──────────────────────────────────────────────────────────── main ──
FORMATS = {
    "balance": run_balance, "pause": run_pause, "unit": run_unit,
    "chemi": run_chemi, "chemi_result": run_chemi_result, "brandrep": run_brandrep,
    "quiz": run_quiz, "calendar": run_calendar, "rookie": run_rookie,
}
# 2026-09 편성 축소 — 조회수 붕괴(계정 전체 20~30 조회) 대응.
# 인사이트 누적(8/22~9/2): pause 27·7·22·0 조회, unit/balance/chemi 캐러셀 좋아요 0~1,
# chemi_result 는 투표 0표로 매주 생략 → 5개 포맷이 매일 슬롯만 소모하며 계정 품질
# 신호(반응 0 게시물 누적)를 깎았다. 반응이 있던 quiz(1,225 조회)만 주 1회 유지.
# 나머지 포맷은 코드 유지(--format 으로 수동 호출 가능), 로테이션에서만 뺀다.
# 되돌리기: 아래 dict 에 요일 항목 추가.
ROTATION = {4: "quiz"}
_ROTATION_LEGACY = {0: "unit", 1: "balance", 2: "pause", 3: "chemi",
                    5: "pause", 6: "chemi_result"}  # 참고용 (미사용)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=sorted(FORMATS), default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    date = _today()
    fmt = args.format or ROTATION.get(date.weekday())
    wd = ['월', '화', '수', '목', '금', '토', '일'][date.weekday()]
    if fmt is None:
        print(f"📅 {date} ({wd}) → 정기 포맷 없음 (편성 축소) — 월간 추가 게시만 확인")
        rc = 0
    else:
        print(f"📅 {date} ({wd}) → 포맷: {fmt}")
    try:
        if fmt is not None:
            rc = FORMATS[fmt](date, args.dry_run)
    except PhotoCoverageError as e:
        # 실사가 하나라도 빠지면 폴백 카드로 나가지 않게 게시를 중단하고 실패로 끝낸다.
        # 워크플로우가 실패를 감지해 GitHub 이슈로 알린다.
        print(f"\n🛑 실사 미확보로 게시 중단\n   {e}")
        print("   조치: python scripts/warm_photo_cache.py 로 캐시를 채운 뒤 재실행하세요.")
        return 1

    # 매월 15일: 브랜드평판 추가 게시 (그 달 데이터 미게시분만)
    if args.format is None and date.day == 1:
        print("\n📅 1일 — 월간 컴백 캘린더 추가 시도")
        try:
            rc = max(rc, run_calendar(date, args.dry_run))
        except Exception as e:
            print(f"⚠️ 캘린더 게시 실패(비치명): {e}")
    # 매월 2일: 신인 걸그룹 랭킹 (전월 1일경 발표 데이터 — period 로 멱등)
    if args.format is None and date.day == 2:
        print("\n🌱 2일 — 신인 걸그룹 브랜드평판 추가 시도")
        try:
            rc = max(rc, run_rookie(date, args.dry_run))
        except PhotoCoverageError as e:
            print(f"🛑 신인 랭킹 단체 실사 미확보로 중단: {e}")
            rc = 1
    if args.format is None and date.day == 15:
        print("\n📊 15일 — 브랜드평판 카운트다운 추가 시도")
        try:
            rc = max(rc, run_brandrep(date, args.dry_run))
        except PhotoCoverageError as e:
            print(f"🛑 브랜드평판 실사 미확보로 중단: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
