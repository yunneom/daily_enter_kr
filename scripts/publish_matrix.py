"""
매트릭스 IG 게시 — topic_registry 의 토픽을 빌드 → Cloudinary 업로드 → IG 단일 이미지 게시.

[모드]
- TOPIC=<id>     단일 토픽 게시
- TOPIC=all      전체 토픽 순차 게시 (90s 간격, 봇 패턴 회피)

[캡션]
주제별 niche 해시태그 + 공통 medium/broad + 댓글 유도 CTA.
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from topic_registry import TOPICS
from make_photo_matrix import make_photo_matrix
from make_premium_matrix import make_premium_matrix
from post_instagram import InstagramPublisher, upload_image
from notify import notify_discord


BRAND = "@daily_enter_kr · 당신의 조합은? 댓글로 ⬇️"
OUTPUT_DIR = ROOT / "output_enter" / "publish"
INTER_POST_SLEEP = 90  # 초

# 주제별 niche 해시태그
TOPIC_TAGS = {
    "weekend_5man": ["#주말", "#한강", "#피크닉", "#영화관", "#호프", "#나혼산",
                     "#주말데이", "#일상"],
    "lunch_15k": ["#점심", "#먹스타", "#분식", "#카페", "#직장인점심",
                  "#밥스타그램", "#점심메뉴"],
    "girlgroup_10k": ["#케이팝", "#걸그룹", "#덕질", "#포지션", "#메인보컬",
                       "#메인댄서", "#비주얼"],
    "idealtype_10k": ["#연애", "#이상형", "#썸", "#mbti", "#연애상담",
                       "#소개팅"],
}

COMMON_TAGS = ["#밸런스게임", "#카드뉴스", "#일상공감", "#밈", "#콘텐츠",
               "#릴스", "#reels", "#korea"]


def build_caption(topic_id: str, topic: dict) -> str:
    title = topic["title"]
    rule = topic["rule_hint"]
    niche = TOPIC_TAGS.get(topic_id, [])
    tags = niche + COMMON_TAGS
    # 30개 한도, 케이스 정규화
    seen, uniq = set(), []
    for t in tags:
        k = t.lower()
        if k in seen:
            continue
        seen.add(k); uniq.append(t)
        if len(uniq) >= 30:
            break

    lines = [
        title,
        "",
        rule,
        "",
        "💬 당신의 조합은? 댓글로 알려주세요 ⬇️",
        "📩 친구 태그하고 같이 골라보세요 / 🔖 저장해두면 다음 시리즈도 챙겨보기 좋아요",
        "",
        "⌁ 매일 새로운 밸런스 시리즈. 팔로우하고 받아보세요.",
        "",
        " ".join(uniq),
    ]
    return "\n".join(lines)


def build_and_upload(topic_id: str, topic: dict) -> str:
    """매트릭스 빌드 → Cloudinary 업로드 → URL 반환."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    local = OUTPUT_DIR / f"{topic_id}.jpg"
    args = dict(
        title=topic["title"], highlight=topic["highlight"],
        rule_hint=topic["rule_hint"],
        col_headers=topic["col_headers"], row_prices=topic["row_prices"],
        cells=topic["cells"], output_path=local, brand=BRAND,
    )
    if topic["style"] == "photo":
        make_photo_matrix(**args)
    else:
        make_premium_matrix(**args)
    return upload_image(local)


def publish_one(topic_id: str, topic: dict, publisher: InstagramPublisher) -> dict:
    print(f"\n=== {topic_id}: {topic['title']} ({topic['style']}) ===")
    try:
        url = build_and_upload(topic_id, topic)
        print(f"  ✓ Cloudinary: {url}")
    except Exception as e:
        print(f"  ❌ 빌드/업로드 실패: {e}")
        return {"topic_id": topic_id, "ok": False, "error": str(e)}

    caption = build_caption(topic_id, topic)
    try:
        media_id = publisher.post_single_image(url, caption)
        return {"topic_id": topic_id, "ok": True, "media_id": media_id, "url": url}
    except Exception as e:
        print(f"  ❌ IG 게시 실패: {e}")
        return {"topic_id": topic_id, "ok": False, "error": str(e), "url": url}


def main() -> int:
    target = os.environ.get("TOPIC", "all").strip().lower()
    ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not (ig_user_id and ig_token):
        print("❌ INSTAGRAM_USER_ID / INSTAGRAM_ACCESS_TOKEN 미설정")
        return 1
    if not (os.environ.get("CLOUDINARY_CLOUD_NAME") and
            os.environ.get("CLOUDINARY_UPLOAD_PRESET")):
        print("❌ Cloudinary 미설정")
        return 1

    publisher = InstagramPublisher(ig_user_id, ig_token)
    health = publisher.health_check()
    if not health.get("ok"):
        print(f"❌ IG 토큰 무효: {health.get('error_message')}")
        return 1
    print(f"✓ IG 토큰 OK: @{health.get('username')}")

    topic_ids = list(TOPICS.keys())  # 등록 순서 = 회전 순서
    if target == "all":
        topics_to_post = list(TOPICS.items())
    elif target in ("auto", ""):
        # cron 호출 시 사용 — 요일 기준 회전 (월=0 → 첫 번째 토픽, ...)
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        weekday = datetime.now(kst).weekday()  # 0-6
        picked = topic_ids[weekday % len(topic_ids)]
        print(f"🤖 auto 회전 — KST weekday={weekday} → {picked}")
        topics_to_post = [(picked, TOPICS[picked])]
    else:
        if target not in TOPICS:
            print(f"❌ 알 수 없는 토픽: {target}. 사용 가능: {topic_ids + ['all', 'auto']}")
            return 1
        topics_to_post = [(target, TOPICS[target])]

    print(f"\n📣 게시 대상: {len(topics_to_post)}개 ({[t[0] for t in topics_to_post]})")

    results = []
    for i, (tid, topic) in enumerate(topics_to_post):
        if i > 0:
            print(f"\n⏱  {INTER_POST_SLEEP}s 대기 (봇 패턴 회피)...")
            time.sleep(INTER_POST_SLEEP)
        results.append(publish_one(tid, topic, publisher))

    # 요약
    print("\n" + "=" * 50)
    ok = [r for r in results if r.get("ok")]
    fail = [r for r in results if not r.get("ok")]
    print(f"✅ 성공: {len(ok)} / 전체 {len(results)}")
    for r in ok:
        print(f"  • {r['topic_id']}: {r['media_id']}")
    for r in fail:
        print(f"  ❌ {r['topic_id']}: {r.get('error', '?')}")

    # Discord 알림
    lines = [f"📣 **매트릭스 시리즈 게시 결과** ({len(ok)}/{len(results)} 성공)"]
    for r in results:
        if r.get("ok"):
            lines.append(f"✅ `{r['topic_id']}` — Media: `{r['media_id']}`")
        else:
            lines.append(f"❌ `{r['topic_id']}` — {r.get('error', '?')[:80]}")
    notify_discord("\n".join(lines), username="daily_enter_kr matrix")

    # Step Summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(f"# 매트릭스 시리즈 게시\n\n")
            f.write(f"성공 {len(ok)} / 전체 {len(results)}\n\n")
            f.write("| 토픽 | 결과 | Media ID |\n|---|---|---|\n")
            for r in results:
                status = "✅" if r.get("ok") else "❌"
                mid = r.get("media_id", "-")
                f.write(f"| `{r['topic_id']}` | {status} | `{mid}` |\n")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
