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

from topic_registry import TOPICS, resolve_topic_cells, resolve_pick_pool
from make_emblem_matrix import SOFT_BG_ROTATION
from make_photo_matrix import make_photo_matrix
from make_premium_matrix import make_premium_matrix
from make_powerpick_matrix import make_powerpick_matrix
from make_soccer_squad_matrix import make_soccer_squad_matrix
from make_video import make_slideshow_video, make_motion_video
from post_instagram import InstagramPublisher, upload_image, upload_video
from notify import notify_discord
from coupang_affiliate import (
    caption_bio_cta, comment_affiliate_line, COUPANG_DISCLOSURE,
    get_topic_affiliate_url,
)
import post_youtube
import post_threads
import post_ledger
import music_credit
import random as _random


BRAND = "👥 친구 소환 → 조합 대결! · 📲 스토리 공유 · @daily_enter_kr"
OUTPUT_DIR = ROOT / "output_enter" / "publish"
BGM_DIR = ROOT / "assets" / "bgm"
INTER_POST_SLEEP = 90  # 초
REEL_SECONDS = 18.0    # 단일 카드 영상 길이.
                       # 6s 정적 → YouTube Shorts retention 즉사 → 0 view 였음.
                       # 18s + Ken Burns 모션이 YT/IG 양쪽 sweet spot
                       # (60s 미만 65% retention 임계 통과 + IG 도 충분 길이).

# 주제별 niche 해시태그
TOPIC_TAGS = {
    "weekend_5man": ["#주말", "#한강", "#피크닉", "#영화관", "#호프", "#나혼산",
                     "#주말데이", "#일상"],
    "lunch_15k": ["#점심", "#먹스타", "#분식", "#카페", "#직장인점심",
                  "#밥스타그램", "#점심메뉴"],
    "girlgroup_real_10k": ["#케이팝", "#걸그룹", "#카리나", "#민지", "#채령",
                            "#윈터", "#유진", "#카즈하", "#kpop"],
    "idealtype_10k": ["#연애", "#이상형", "#썸", "#mbti", "#연애상담",
                       "#소개팅"],
    "idol_allstar_10k": ["#케이팝", "#아이돌", "#올스타", "#뉴진스",
                          "#에스파", "#아이브", "#민지", "#카리나",
                          "#장원영", "#kpop", "#kpopfan"],
    "spinner_food_man": ["#밸런스게임", "#일시정지챌린지", "#운동", "#치킨",
                          "#엽떡", "#닭발", "#소주", "#다이어트", "#헬창"],
    "spinner_lazy_woman": ["#밸런스게임", "#일시정지챌린지", "#운동", "#홈트",
                            "#넷플릭스", "#유튜브", "#쇼츠", "#침대요정",
                            "#운동복"],
    "girlgroup_4gen_10k": ["#케이팝", "#4세대걸그룹", "#NMIXX", "#엔믹스",
                            "#뉴진스", "#에스파", "#아이브", "#르세라핌",
                            "#있지", "#릴리", "#설윤", "#채령", "#카즈하",
                            "#kpop"],
    "boygroup_4gen_10k": ["#케이팝", "#4세대보이그룹", "#스트레이키즈",
                           "#스키즈", "#엔하이픈", "#투바투", "#TXT",
                           "#RIIZE", "#라이즈", "#ATEEZ", "#에이티즈",
                           "#필릭스", "#정원", "#성훈", "#kpop"],
    "travel_30man": ["#해외여행", "#여행스타그램", "#일본여행", "#오사카",
                      "#도쿄", "#발리", "#방콕", "#파리", "#유럽여행",
                      "#동남아여행", "#travel", "#tripstagram"],
    "trot_concert_10k": ["#트로트", "#임영웅", "#송가인", "#영탁",
                          "#김호중", "#장윤정", "#정동원", "#이찬원",
                          "#트로트라이브", "#미스터트롯", "#미스트롯"],
    "ballad_concert_10k": ["#발라드", "#성시경", "#박정현", "#김범수",
                            "#박효신", "#백지영", "#폴킴", "#케이시",
                            "#정인", "#정승환", "#감성발라드", "#한국발라드"],
    "child_pick_100man": ["#밸런스게임", "#육아", "#자녀", "#부모공감",
                           "#엄마스타그램", "#육아맘", "#육아일상",
                           "#mbti", "#일상공감"],
    "girlgroup_5gen_tier1_10k": ["#케이팝", "#5세대걸그룹", "#베이비몬스터",
                                   "#BABYMONSTER", "#일릿", "#ILLIT", "#키스오브라이프",
                                   "#KISSOFLIFE", "#루카", "#원희", "#벨", "#아현",
                                   "#나띠", "#kpop", "#kpopfan"],
    "girlgroup_4gen_tier1_10k": ["#케이팝", "#4세대걸그룹", "#뉴진스", "#에스파",
                                   "#아이브", "#르세라핌", "#카리나", "#장원영",
                                   "#민지", "#하니", "#카즈하", "#윈터", "#레이",
                                   "#kpop"],
    "girlgroup_4gen_tier2_10k": ["#케이팝", "#4세대걸그룹", "#NMIXX", "#엔믹스",
                                   "#ITZY", "#있지", "#여자아이들", "#GIDLE",
                                   "#릴리", "#설윤", "#채령", "#소연", "#kpop"],
    "girlgroup_4gen_tier3_10k": ["#케이팝", "#4세대걸그룹", "#STAYC", "#스테이씨",
                                   "#Kep1er", "#케플러", "#Billlie", "#빌리",
                                   "#fromis_9", "#프로미스나인", "#시은", "#수민",
                                   "#kpop"],
    "boygroup_4gen_tier1_10k": ["#케이팝", "#4세대보이그룹", "#스트레이키즈", "#스키즈",
                                  "#엔하이픈", "#투바투", "#TXT", "#RIIZE", "#라이즈",
                                  "#ATEEZ", "#에이티즈", "#제로베이스원", "#ZB1",
                                  "#필릭스", "#정원", "#kpop"],
    "boygroup_4gen_tier2_10k": ["#케이팝", "#4세대보이그룹", "#더보이즈", "#THEBOYZ",
                                  "#NCT", "#엔시티", "#트레저", "#TREASURE",
                                  "#P1Harmony", "#피원하모니", "#kpop"],
    "boygroup_5gen_tier1_10k": ["#케이팝", "#5세대보이그룹", "#CORTIS", "#코르티스",
                                  "#TWS", "#투어스", "#보이넥스트도어", "#BOYNEXTDOOR",
                                  "#KickFlip", "#킥플립", "#kpop", "#kpopfan"],
    "spinner_idol_pick": ["#밸런스게임", "#일시정지챌린지", "#최애", "#아이돌",
                           "#케이팝", "#장원영", "#카리나", "#윈터", "#민지",
                           "#최애뽑기", "#kpop"],
    "powerpick_office": ["#초능력", "#직장인", "#직장인공감", "#회사원",
                          "#밸런스게임", "#카드뉴스", "#월요일", "#퇴근",
                          "#회식", "#일상공감", "#밈", "#릴스", "#reels"],
    "powerpick_student": ["#초능력", "#학생", "#학생공감", "#고등학생",
                           "#중학생", "#대학생", "#수험생", "#시험",
                           "#밸런스게임", "#카드뉴스", "#학생일상", "#릴스"],
    "powerpick_teacher": ["#초능력", "#선생님", "#교사", "#교사공감",
                           "#스승의날", "#학교", "#교무실", "#방학",
                           "#밸런스게임", "#카드뉴스", "#일상공감", "#릴스"],
    "powerpick_neet": ["#초능력", "#백수", "#무직", "#백수일상",
                        "#취준", "#취준생", "#휴식", "#잠",
                        "#넷플릭스", "#밸런스게임", "#카드뉴스", "#릴스"],
    "powerpick_landlord": ["#초능력", "#건물주", "#임대", "#재테크",
                            "#부동산", "#임대료", "#건물", "#투자",
                            "#밸런스게임", "#카드뉴스", "#일상", "#릴스"],
    "powerpick_idol": ["#초능력", "#아이돌", "#아이돌일상", "#케이팝",
                        "#kpop", "#아이돌공감", "#무대", "#컴백",
                        "#밸런스게임", "#카드뉴스", "#릴스", "#reels"],
    "soccer_nationalteam_1000eok": ["#축구", "#국가대표", "#손흥민", "#이강인",
                                  "#김민재", "#황희찬", "#조규성", "#박지성",
                                  "#차범근", "#월드컵", "#축구국대",
                                  "#밸런스게임", "#football", "#soccer"],
    "job_pick_10k": ["#직장", "#취준", "#취준생", "#직장인", "#재택근무",
                      "#연봉", "#회사", "#출근", "#월급", "#야근",
                      "#밸런스게임", "#카드뉴스", "#일상공감"],
    "power_budget_10k": ["#초능력", "#밸런스게임", "#로또", "#순간이동",
                          "#기상예측", "#슈퍼파워", "#카드뉴스",
                          "#일상공감", "#밈", "#릴스"],
    "spot_diff_bear": ["#틀린그림찾기", "#곰돌이", "#숨은그림찾기", "#두뇌게임",
                        "#집중력테스트", "#관찰력", "#곰", "#귀여운",
                        "#밈", "#카드뉴스", "#릴스", "#reels"],
    "kpop_concept_love_hate": ["#케이팝", "#kpop", "#컨셉", "#걸크러쉬",
                                "#청순컨셉", "#큐트댄스", "#이지리스닝",
                                "#밸런스게임", "#호불호", "#카드뉴스",
                                "#아이돌컨셉", "#릴스"],
    "brand_rep_girlgroup": ["#브랜드평판", "#걸그룹", "#케이팝", "#kpop",
                             "#장원영", "#제니", "#카리나", "#로제",
                             "#리센느", "#원이", "#미나미", "#아이브",
                             "#블랙핑크", "#TOP30", "#한국기업평판연구소"],
    "slot_girlgroup_5x3": ["#슬롯머신", "#걸그룹조합", "#밸런스게임",
                            "#일시정지챌린지", "#케이팝", "#kpop", "#아이돌조합",
                            "#카리나", "#장원영", "#민지", "#카즈하", "#윈터",
                            "#안유진", "#릴스", "#reels"],
    "slot_boygroup_5x3": ["#슬롯머신", "#보이그룹조합", "#밸런스게임",
                           "#일시정지챌린지", "#케이팝", "#kpop", "#아이돌조합",
                           "#필릭스", "#정원", "#성훈", "#앤톤", "#TXT",
                           "#엔하이픈", "#RIIZE", "#릴스", "#reels"],
}

COMMON_TAGS = ["#밸런스게임", "#카드뉴스", "#일상공감", "#밈", "#콘텐츠",
               "#릴스", "#reels", "#korea"]


def build_caption(topic_id: str, topic: dict) -> str:
    title = topic["title"]
    # spinner 는 rule_hint 대신 hint 필드 사용
    rule = topic.get("rule_hint") or topic.get("hint", "")
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

    # 쿠팡 파트너스 CTA — 단축링크 설정된 카테고리만 (가짜 링크 X)
    bio_cta = caption_bio_cta(topic_id)
    has_affiliate = bool(get_topic_affiliate_url(topic_id))

    lines = [
        title,
        "",
        rule,
        "",
        "💬 내 조합 댓글로 남기기 ⬇️",
        "👥 친구 소환해서 누구 조합이 이겼나 대결!",
        "📲 스토리에 공유하고 친구 조합이랑 비교해보세요",
        "🔖 저장해두면 다음 시리즈도 챙겨보기 좋아요",
    ]
    if bio_cta:
        lines += ["", bio_cta]
    # abc 송 음악 크레딧 — MUSIC_YT_URL 설정 시에만 (미설정 silent skip)
    music_block = music_credit.caption_music_block()
    if music_block:
        lines += ["", music_block]
    lines += ["", "⌁ 매일 새로운 밸런스 시리즈. 팔로우하고 받아보세요."]
    # 디스클로저는 어필리에이트 링크 노출 시에만 (공정위 표시 의무 해당)
    if has_affiliate:
        lines.append(f"({COUPANG_DISCLOSURE})")
    lines += ["", " ".join(uniq)]
    return "\n".join(lines)


# 마지막으로 선택된 BGM 파일명 — 원장(post_ledger) 음원 A/B 추적용.
# build_and_upload 가 _pick_bgm() 호출 시 갱신, publish_one 이 읽어 결과에 주입.
_LAST_BGM = None

# 시그니처 BGM 분기 — 컨텍스트별 톤 매치 (A: 밝은 K-pop / C: 게임 톤)
# 미존재 시 같은 폴더 내 다른 mp3 폴백.
# topic_id 매핑이 우선 (특정 토픽만 다른 톤), style 매핑이 폴백.
_BGM_BY_TOPIC = {
    "slot_girlgroup_5x3": "daily_enter_theme_a.mp3",  # 걸그룹 슬롯 — A 톤 (밝게)
    "slot_boygroup_5x3":  "daily_enter_theme_c.mp3",  # 보이그룹 슬롯 — C 톤 (다크)
}
_BGM_BY_STYLE = {
    "spinner":         "daily_enter_theme_c.mp3",   # 일시정지 챌린지 — 긴장감
    "brand_chart":     "daily_enter_theme_c.mp3",   # TOP30 차트 — 에픽
    "worldcup_match":  "daily_enter_theme_c.mp3",   # 월드컵 매치 — 게임 톤
    # 기본 (matrix/emblem/photo/drawing/powerpick) → A
}
_BGM_DEFAULT = "daily_enter_theme_a.mp3"


def _pick_bgm(style: str = None, topic_id: str = None):
    """토픽 id/style 에 맞는 시그니처 BGM 선택. 없으면 폴더 내 fallback.

    Priority: topic_id 매핑 > style 매핑 > default(A) > 폴더 랜덤.
    """
    global _LAST_BGM
    if not BGM_DIR.exists():
        _LAST_BGM = None
        return None
    # topic_id 명시 매핑 우선
    target = None
    if topic_id and topic_id in _BGM_BY_TOPIC:
        target = _BGM_BY_TOPIC[topic_id]
    elif style and style in _BGM_BY_STYLE:
        target = _BGM_BY_STYLE[style]
    else:
        target = _BGM_DEFAULT

    p = BGM_DIR / target
    if p.exists():
        _LAST_BGM = p.name
        return p
    # 폴백: 같은 폴더 어떤 mp3 든
    candidates = sorted(BGM_DIR.glob("*.mp3"))
    chosen = _random.choice(candidates) if candidates else None
    _LAST_BGM = chosen.name if chosen else None
    return chosen


def build_and_upload(topic_id: str, topic: dict, seed: int = 0) -> tuple:
    """주제 빌드 → mp4(Reels) + jpg(cover) Cloudinary 업로드 → (video_url, cover_url).

    seed: 게시 회전 시드. col_pools 멤버 라인업 + 배경 회전에 사용 →
          같은 토픽이라도 게시마다 다른 멤버/배경 (새 콘텐츠로 인지).
    style="spinner" 는 mp4 를 바로 생성 (정적 jpg → mp4 변환 단계 없음).
    cover_url 은 None — IG 가 첫 프레임 자동 추출.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    local_jpg = OUTPUT_DIR / f"{topic_id}.jpg"
    local_mp4 = OUTPUT_DIR / f"{topic_id}.mp4"
    style = topic["style"]

    # ─── spinner: 정적 이미지 없이 바로 mp4 생성 ───
    if style == "spinner":
        from make_spinner_video import make_pause_challenge_video
        kwargs = dict(
            options=topic["options"],
            output_path=local_mp4,
            title=topic["title"],
            hint=topic.get("hint", "⏸ 일시정지로 골라봐!"),
            character_style=topic.get("character_style", "muscle_man"),
            pointer_offset_deg=topic.get("pointer_offset_deg", 0.0),
            bend_deg=topic.get("bend_deg", 0.0),
        )
        if topic.get("deg_per_frame"):
            kwargs["deg_per_frame"] = topic["deg_per_frame"]
        if topic.get("option_fill"):
            kwargs["option_fill"] = tuple(topic["option_fill"])
        make_pause_challenge_video(**kwargs)
        video_url = upload_video(local_mp4)
        return video_url, None

    # ─── spot_difference: 틀린 곰 찾기 퍼즐 (seed 로 정답/차이 회전) ───
    if style == "spot_difference":
        from make_spot_difference import make_spot_difference
        _, ans, _typ = make_spot_difference(
            output_path=local_jpg, seed=seed,
            title=topic["title"], subtitle=topic.get("subtitle", "어디 있을까?"),
            brand=BRAND,
        )
        print(f"  🐻 정답: {ans}번째 ({_typ})")
        bgm = _pick_bgm(style, topic_id)
        make_motion_video(
            image_path=local_jpg, output_path=local_mp4,
            duration=REEL_SECONDS, bgm_path=bgm,
            motion='kenburns_in',
        )
        video_url = upload_video(local_mp4)
        cover_url = upload_image(local_jpg)
        return video_url, cover_url

    # ─── soccer_squad: 5컬럼 × 3로우 + 절차적 캐릭터 헤드 + 미니 포메이션 ───
    if style == "soccer_squad":
        make_soccer_squad_matrix(
            title=topic["title"], highlight=topic["highlight"],
            rule_hint=topic["rule_hint"],
            col_headers=topic["col_headers"], row_headers=topic["row_headers"],
            cells=topic["cells"], output_path=local_jpg, brand=BRAND,
            precondition_lines=topic.get("precondition_lines"),
            source_note=topic.get("source_note", ""),
            cta_text=topic.get("cta_text", "💬 당신의 영입 조합은? 댓글로 ⬇️"),
        )
        bgm = _pick_bgm(style, topic_id)
        make_motion_video(
            image_path=local_jpg, output_path=local_mp4,
            duration=REEL_SECONDS, bgm_path=bgm,
            motion='kenburns_in',
        )
        video_url = upload_video(local_mp4)
        cover_url = upload_image(local_jpg)
        return video_url, cover_url

    # ─── brand_chart: 외부 출처(한국기업평판연구소) JSON → TOP30 차트 ───
    if style == "brand_chart":
        from make_brand_reputation_chart import make_brand_reputation_chart
        data_path = ROOT / topic["data_path"]
        if not data_path.exists():
            raise FileNotFoundError(f"브랜드평판 데이터 파일 없음: {data_path}")
        make_brand_reputation_chart(data_path=data_path, output_path=local_jpg)
        bgm = _pick_bgm(style, topic_id)
        make_slideshow_video(
            image_paths=[local_jpg], output_path=local_mp4,
            durations=[REEL_SECONDS], bgm_path=bgm,
        )
        video_url = upload_video(local_mp4)
        cover_url = upload_image(local_jpg)
        return video_url, cover_url

    # ─── slot_machine: 3열 다른 방향 스크롤 mp4 + 빨강 PICK zone ───
    if style == "slot_machine":
        from make_slot_machine_video import make_slot_machine_video
        bgm = _pick_bgm(style, topic_id)
        make_slot_machine_video(
            title=topic["title"],
            rule_hint=topic.get("rule_hint", "멈춰서 본인 픽 만들기!"),
            col_headers=topic["col_headers"],
            col_pools=topic["col_pools"],
            output_path=local_mp4,
            chances_text=topic.get("chances_text", "🎰 기회 3번"),
            duration=topic.get("duration", 10.0),
            cta=topic.get("cta", "⏸ 일시정지로 멈춰서 조합 댓글 ⬇️"),
            brand=BRAND,
            bgm_path=bgm,
        )
        video_url = upload_video(local_mp4)
        return video_url, None  # cover_url 없음 — IG 자동 추출

    # ─── powerpick: 9-셀 단일 픽 grid (가격/매트릭스 X) ───
    if style == "powerpick":
        picks = resolve_pick_pool(topic, seed=seed, n=9)
        make_powerpick_matrix(
            title=topic["title"], rule_hint=topic["rule_hint"],
            picks=picks, output_path=local_jpg, brand=BRAND,
            source_note=topic.get("source_note", ""),
        )
        bgm = _pick_bgm(style, topic_id)
        make_motion_video(
            image_path=local_jpg, output_path=local_mp4,
            duration=REEL_SECONDS, bgm_path=bgm,
            motion='kenburns_in',
        )
        video_url = upload_video(local_mp4)
        cover_url = upload_image(local_jpg)
        return video_url, cover_url

    # col_pools 있으면 seed 로 멤버 라인업 회전, 없으면 고정 cells.
    cells = resolve_topic_cells(topic, seed=seed)

    # ─── 매트릭스 계열: 정적 jpg → mp4 (단일 프레임 × REEL_SECONDS + BGM) ───
    args = dict(
        title=topic["title"], highlight=topic["highlight"],
        rule_hint=topic["rule_hint"],
        col_headers=topic["col_headers"], row_prices=topic["row_prices"],
        cells=cells, output_path=local_jpg, brand=BRAND,
    )
    if style == "photo":
        make_photo_matrix(**args)
    elif style == "emblem":
        from make_emblem_matrix import make_emblem_matrix
        base_bg = topic.get("background_style", "soccer")
        # 흰 배경(아이돌 기본) 토픽은 게시마다 라이트 배경 회전 — "새 글" 인지.
        # soccer 등 컨셉 배경은 그대로 유지.
        if base_bg == "white":
            base_bg = SOFT_BG_ROTATION[seed % len(SOFT_BG_ROTATION)]
        args["background_style"] = base_bg
        args["source_note"] = topic.get("source_note", "")
        args["precondition"] = topic.get("precondition", "")
        if topic.get("budget_label"):
            args["budget_label"] = topic["budget_label"]
        make_emblem_matrix(**args)
    else:
        make_premium_matrix(**args)

    bgm = _pick_bgm(style, topic_id)
    make_motion_video(
            image_path=local_jpg, output_path=local_mp4,
            duration=REEL_SECONDS, bgm_path=bgm,
            motion='kenburns_in',
        )
    video_url = upload_video(local_mp4)
    cover_url = upload_image(local_jpg)
    return video_url, cover_url


def publish_one(topic_id: str, topic: dict, publisher: InstagramPublisher,
                seed: int = 0) -> dict:
    print(f"\n=== {topic_id}: {topic['title']} ({topic['style']}) [seed={seed}] ===")
    try:
        video_url, cover_url = build_and_upload(topic_id, topic, seed=seed)
        print(f"  ✓ video: {video_url}")
        print(f"  ✓ cover: {cover_url}")
    except Exception as e:
        print(f"  ❌ 빌드/업로드 실패: {e}")
        return {"topic_id": topic_id, "ok": False, "error": str(e)}

    caption = build_caption(topic_id, topic)
    local_mp4 = OUTPUT_DIR / f"{topic_id}.mp4"

    # ─── YouTube Shorts 먼저 업로드 (cold-start 개선) ───
    # [왜] YouTube 가 IG 보다 먼저 인덱싱하게 해서 "원본 vs 재가공" 판정에서
    # 우리 채널이 원본 측으로 분류되게. IG 먼저 → YT 시간차 30-90s 면 YT가
    # reused/inauthentic 으로 의심 → 도달 0. 순서 뒤집어서 해결.
    yt_id = None
    if post_youtube.is_configured() and local_mp4.exists():
        try:
            hint = topic.get("rule_hint") or topic.get("hint", "")
            tags = TOPIC_TAGS.get(topic_id, []) + COMMON_TAGS
            yt_title, yt_desc = post_youtube.build_youtube_meta(
                title=topic["title"], hint=hint, hashtags=tags,
                disclosure=COUPANG_DISCLOSURE if get_topic_affiliate_url(topic_id) else "",
                music_block=music_credit.youtube_music_block(),
            )
            category_id = post_youtube.youtube_category_for(topic_id, topic.get("style"))
            yt_id = post_youtube.upload_short(
                local_mp4, yt_title, yt_desc, tags=tags,
                category_id=category_id)
        except Exception as e:
            print(f"  ⚠️  YouTube 업로드 실패 (비치명): {e}")

    # ─── IG Reels 게시 (YouTube 인덱싱 시작 후) ───
    try:
        media_id = publisher.post_reel(
            video_url=video_url, caption=caption,
            cover_url=cover_url, share_to_feed=True,
        )
    except Exception as e:
        print(f"  ❌ IG 게시 실패: {e}")
        return {"topic_id": topic_id, "ok": False, "error": str(e),
                "video_url": video_url, "cover_url": cover_url,
                "youtube_id": yt_id}

    # 자동 첫 댓글 — 첫 노출 댓글로 엔게이지먼트 시동 + 쿠팡 단축링크 시드.
    # 게시 직후 너무 빠른 댓글은 봇 패턴 우려 → 30초 대기.
    comment_text = topic.get("auto_comment") or _default_comment(topic.get("style"))
    aff_line = comment_affiliate_line(topic_id)
    if comment_text and aff_line:
        comment_text = f"{comment_text}\n\n{aff_line}\n({COUPANG_DISCLOSURE})"
    # abc 송 음악 크레딧 한 줄 — 댓글로도 노출 (MUSIC_YT_URL 설정 시)
    music_line = music_credit.comment_music_line()
    if comment_text and music_line:
        comment_text = f"{comment_text}\n\n{music_line}"
    if comment_text:
        time.sleep(30)
        try:
            comment_id = publisher.post_comment(media_id, comment_text)
            print(f"  💬 자동 댓글: {comment_id}" + (" + 쿠팡링크" if aff_line else ""))
        except Exception as e:
            print(f"  ⚠️  자동 댓글 실패 (비치명): {e}")

    threads_id = None

    if post_threads.is_configured():
        try:
            reel_link = f"https://www.instagram.com/reel/{media_id}/" if media_id else None
            threads_id = post_threads.post_thread(
                top_titles=[topic["title"], topic.get("rule_hint", "")],
                date_str="", label_short="밸런스게임", reel_link=reel_link)
        except Exception as e:
            print(f"  ⚠️  Threads 게시 실패 (비치명): {e}")

    return {"topic_id": topic_id, "ok": True, "media_id": media_id,
            "video_url": video_url, "cover_url": cover_url,
            "youtube_id": yt_id, "threads_id": threads_id,
            "title": topic.get("title", ""), "style": topic.get("style", ""),
            "seed": seed, "bgm": _LAST_BGM}


def _default_comment(style: str) -> str:
    """auto_comment 미지정 토픽의 폴백."""
    return {
        "spinner": "⏸ 결과 댓글로 알려주세요!",
        "emblem":  "🤔 본인 픽 댓글로 ⬇️",
        "photo":   "🤔 당신의 조합은? 댓글로 ⬇️",
        "drawing": "💭 당신의 답은? 댓글로 ⬇️",
    }.get(style or "", "🤔 댓글로 알려주세요 ⬇️")


def main() -> int:
    # 🏆 걸그룹 월드컵 캠페인 (6/23 ~ 7/5, 연장) 기간 동안 매트릭스 자동 게시 일시정지 —
    # 시청자 어텐션을 월드컵에 집중. cron 자체는 유지 (캠페인 후 자연 재개).
    from datetime import date as _date
    _today = _date.today()
    if _date(2026, 6, 23) <= _today <= _date(2026, 7, 5):
        print("🏆 걸그룹 월드컵 캠페인 기간(6/23~7/5) — 매트릭스 자동 게시 일시정지")
        return 0
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
    spinner_ids = [t for t in topic_ids if TOPICS[t]["style"] == "spinner"]
    matrix_ids = [t for t in topic_ids if TOPICS[t]["style"] != "spinner"]

    # 멤버/배경 회전 시드 — KST yday*7+hour. col_pools 라인업 + 배경이 매번 달라짐.
    from datetime import datetime, timezone, timedelta
    _kst_now = datetime.now(timezone(timedelta(hours=9)))
    run_seed = _kst_now.timetuple().tm_yday * 11 + _kst_now.hour

    if target == "all":
        topics_to_post = list(TOPICS.items())
    elif target in ("auto", "auto_matrix", "auto_spinner", ""):
        # cron 호출 — 시간대별 다른 토픽 풀에서 회전
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        if target == "auto_spinner":
            pool = spinner_ids
            # 하루 1슬롯이라 day-of-year 만으로 충분 (2 토픽 격일)
            seed = now_kst.timetuple().tm_yday
        elif target == "auto_matrix":
            pool = matrix_ids
            # 시드 = yday*11 + hour. 11은 22/33 외 모든 풀 크기와 코프라임 →
            # 풀이 6~30 사이 어떤 값이든 모든 토픽이 cron 슬롯에 노출됨.
            seed = now_kst.timetuple().tm_yday * 11 + now_kst.hour
        else:  # 하위 호환 (기존 'auto')
            pool = topic_ids
            seed = now_kst.weekday()
        if not pool:
            print(f"❌ {target} 풀이 비어있음")
            return 1
        picked = pool[seed % len(pool)]
        print(f"🤖 {target} 회전 — KST {now_kst.strftime('%a %H시')} → {picked}")
        topics_to_post = [(picked, TOPICS[picked])]
    else:
        if target not in TOPICS:
            print(f"❌ 알 수 없는 토픽: {target}. "
                  f"사용 가능: {topic_ids + ['all', 'auto', 'auto_matrix', 'auto_spinner']}")
            return 1
        topics_to_post = [(target, TOPICS[target])]

    print(f"\n📣 게시 대상: {len(topics_to_post)}개 ({[t[0] for t in topics_to_post]})")

    results = []
    for i, (tid, topic) in enumerate(topics_to_post):
        if i > 0:
            print(f"\n⏱  {INTER_POST_SLEEP}s 대기 (봇 패턴 회피)...")
            time.sleep(INTER_POST_SLEEP)
        # 'all' 모드는 토픽마다 시드를 약간 어긋나게 (i 더함) → 라인업 다양화
        results.append(publish_one(tid, topic, publisher, seed=run_seed + i))

    # 게시 원장 기록 — IG↔YT↔topic 조인 키 + 음원 추적 (크로스플랫폼 분석 기반)
    try:
        n_ledger = post_ledger.record_results(
            [r for r in results if r.get("ok")],
            bgm=results[0].get("bgm") if results else None,
        )
        if n_ledger:
            print(f"📒 게시 원장 기록: {n_ledger}건 (post_ledger.json)")
    except Exception as e:
        print(f"  ⚠️  원장 기록 실패 (비치명): {e}")

    # 요약
    print("\n" + "=" * 50)
    ok = [r for r in results if r.get("ok")]
    fail = [r for r in results if not r.get("ok")]
    print(f"✅ 성공: {len(ok)} / 전체 {len(results)}")
    yt_ok = sum(1 for r in ok if r.get("youtube_id"))
    th_ok = sum(1 for r in ok if r.get("threads_id"))
    print(f"   ↳ YouTube Shorts: {yt_ok} · Threads: {th_ok} 동시 게시")
    for r in ok:
        extra = []
        if r.get("youtube_id"):
            extra.append(f"YT:{r['youtube_id']}")
        if r.get("threads_id"):
            extra.append("TH✓")
        suffix = (" [" + " ".join(extra) + "]") if extra else ""
        print(f"  • {r['topic_id']}: {r['media_id']}{suffix}")
    for r in fail:
        print(f"  ❌ {r['topic_id']}: {r.get('error', '?')}")

    # 쿠팡 파트너스 랜딩 + 협찬 미디어 키트 재생성 (게시 1건이라도 성공한 경우)
    if ok:
        try:
            import generate_landing
            generate_landing.main()
        except Exception as e:
            print(f"  ⚠️  랜딩 페이지 생성 실패 (비치명): {e}")
        try:
            import generate_mediakit
            generate_mediakit.main()
        except Exception as e:
            print(f"  ⚠️  미디어 키트 생성 실패 (비치명): {e}")

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
