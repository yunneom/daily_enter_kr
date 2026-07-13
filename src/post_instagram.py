"""
Instagram 업로드 모듈
Instagram Graph API 로 카드뉴스를 **Reels** (mp4 슬라이드쇼) 로 업로드합니다.

[2026-05 변경]
- 캐러셀 이미지 게시 → Reels (mp4) 게시로 전환. IG 알고리즘이 캐러셀에 거의 도달을 안 줘서 폐기.
- 카드 이미지(9:16)는 make_video.py 에서 mp4 슬라이드쇼로 합쳐진 뒤 이 모듈로 들어옴.

[사전 준비 - 필수]
1. Facebook 페이지 + IG 비즈니스/크리에이터 계정 + 두 계정 연결
2. https://developers.facebook.com 앱 생성 + Instagram Graph API 추가
3. 필요 권한: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
4. 장기 액세스 토큰 (60일, 자동 갱신 필요)
5. Instagram Business Account ID 확보

[Reels 제약]
- 비디오가 공개 URL 로 호스팅돼 있어야 함 (Cloudinary 비디오 업로드 권장)
- 길이: 3 ~ 90초
- 비율: 9:16 (1080x1920) 권장 — 다른 비율은 letterbox 됨
- 24시간 내 100건 게시 제한 (이미지/Reels 공통 풀)
"""

import os
import time
import requests
from pathlib import Path
from typing import List, Optional


GRAPH_API_VERSION = "v22.0"
# Instagram API for Business 사용 (IGAA 토큰).
# Meta가 권장하는 신버전 API. graph.facebook.com이 아닌 graph.instagram.com 사용.
GRAPH_API_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"


class InstagramPublisher:
    def __init__(self, ig_user_id: str, access_token: str):
        """
        Args:
            ig_user_id: Instagram Business Account ID
            access_token: 장기 액세스 토큰
        """
        self.ig_user_id = ig_user_id
        self.access_token = access_token

    def health_check(self) -> dict:
        """토큰 유효성 + 연결된 IG 계정 정보 확인.

        Returns: dict {ok: bool, username, account_type, error_message}
        토큰이 만료됐거나 잘못된 경우 ok=False와 함께 error_message 반환.
        """
        try:
            resp = requests.get(
                f"{GRAPH_API_BASE}/me",
                params={
                    "fields": "user_id,username,account_type",
                    "access_token": self.access_token,
                },
                timeout=15,
            )
            if not resp.ok:
                err = resp.json().get("error", {}).get("message", resp.text[:200])
                return {"ok": False, "error_message": f"HTTP {resp.status_code}: {err}"}
            data = resp.json()
            return {
                "ok": True,
                "username": data.get("username"),
                "account_type": data.get("account_type"),
                "user_id": data.get("user_id") or data.get("id"),
            }
        except Exception as e:
            return {"ok": False, "error_message": f"{type(e).__name__}: {e}"}
    
    @staticmethod
    def _post_ig(url: str, params: dict, step: str, timeout: int = 30):
        """IG Graph API POST 래퍼. 실패 시 응답 본문의 error.message/code/subcode를 메시지에 포함시켜
        re-raise. raise_for_status만 호출하면 'HTTPError: 400 Client Error'만 남아 진단이 어렵다."""
        resp = requests.post(url, params=params, timeout=timeout)
        if not resp.ok:
            try:
                err = resp.json().get("error", {}) or {}
                detail = (
                    f"code={err.get('code')} subcode={err.get('error_subcode')} "
                    f"type={err.get('type')} msg={err.get('message', '')[:240]}"
                )
            except Exception:
                detail = resp.text[:300]
            # publish 단계 403은 토큰/스코프는 살아있는데 계정 레벨에서 게시만 거부되는 패턴.
            # 응답 본문 없이 raise 만 하면 사용자가 다음에 뭘 해야 할지 모르므로 가이드 출력.
            if resp.status_code == 403 and step == "publish":
                print("\n💡 IG /media_publish 403 — 흔한 원인 4가지:")
                print("   1. 계정 일시 게시 제한 (IG 봇 패턴 탐지) → IG 앱에서 알림/배너 확인, 본인 확인")
                print("   2. instagram_content_publish 스코프 누락 → 'python exchange_token.py --refresh'")
                print("   3. 일일 게시 한도(50건) 초과 → 시간 두고 재시도")
                print("   4. Meta App 정책 플래그 → developers.facebook.com → App Review/Alerts 확인\n")
            raise requests.HTTPError(
                f"IG {step} HTTP {resp.status_code} — {detail}",
                response=resp,
            )
        return resp

    def _create_reel_container(self, video_url: str, caption: str,
                               cover_url: Optional[str] = None,
                               share_to_feed: bool = True) -> str:
        """Reels 컨테이너 생성. video_url 은 mp4 공개 URL."""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token,
        }
        if cover_url:
            # 커버는 IG가 첫 프레임을 자동 추출하므로 미지정 시 자동. 명시 시 정사각/9:16 권장.
            params["cover_url"] = cover_url
        resp = self._post_ig(url, params, step="create_reel")
        return resp.json()["id"]

    def _publish_container(self, container_id: str) -> str:
        """컨테이너 게시"""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        resp = self._post_ig(url, params, step="publish")
        return resp.json()["id"]

    def _wait_container_ready(self, container_id: str, timeout: int = 300):
        """컨테이너가 FINISHED 상태가 될 때까지 대기.

        Reels 는 비디오 트랜스코딩 때문에 이미지 컨테이너보다 훨씬 오래 걸림 (수십초 ~ 수분).
        default timeout 을 60s → 300s 로 늘렸다.

        ERROR 상태이면 status 필드(IG가 사람-가독한 reason)를 같이 메시지에 포함.
        """
        url = f"{GRAPH_API_BASE}/{container_id}"
        params = {"fields": "status_code,status", "access_token": self.access_token}
        elapsed = 0
        while elapsed < timeout:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json() if resp.ok else {}
            status_code = data.get("status_code")
            if status_code == "FINISHED":
                return
            if status_code in ("ERROR", "EXPIRED"):
                reason = data.get("status") or resp.text[:200]
                raise requests.HTTPError(
                    f"IG container {container_id} {status_code}: {reason}"
                )
            time.sleep(5)
            elapsed += 5
        raise TimeoutError(f"Container {container_id} not ready in {timeout}s")

    def _create_story_container(self, video_url: str) -> str:
        """Stories 컨테이너 생성 (mp4)."""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": self.access_token,
        }
        resp = self._post_ig(url, params, step="create_story")
        return resp.json()["id"]

    def _create_single_image_container(self, image_url: str, caption: str) -> str:
        """단일 피드 이미지 컨테이너 (캐러셀 아님)."""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        resp = self._post_ig(url, params, step="create_image")
        return resp.json()["id"]

    def post_single_image(self, image_url: str, caption: str) -> str:
        """단일 이미지 피드 게시 (캐러셀 아닌 일반 이미지 포스트).

        Args:
            image_url: 공개 접근 가능한 이미지 URL (Cloudinary)
            caption: 캡션 (해시태그 포함)
        Returns: published media id
        """
        print(f"[1/3] 단일 이미지 컨테이너 생성...")
        cid = self._create_single_image_container(image_url, caption)
        print(f"  ✓ container_id: {cid}")

        print("[2/3] 컨테이너 준비 대기...")
        self._wait_container_ready(cid, timeout=120)
        print("  ✓ FINISHED")

        print("[3/3] 게시...")
        media_id = self._publish_container(cid)
        print(f"  ✅ 단일 이미지 게시 완료! Media ID: {media_id}")
        return media_id

    def _create_carousel_child(self, image_url: str) -> str:
        """캐러셀 자식 이미지 컨테이너 (is_carousel_item=true)."""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self.access_token,
        }
        resp = self._post_ig(url, params, step="carousel_child")
        return resp.json()["id"]

    def post_carousel(self, image_urls: list, caption: str) -> str:
        """캐러셀(스와이프 다중 이미지) 피드 게시. 2-20장 (IG 2024 확장).

        Args:
            image_urls: 공개 이미지 URL 리스트 (Cloudinary). 순서 = 스와이프 순서.
            caption: 캡션 (해시태그 포함)
        Returns: published media id
        """
        if not (2 <= len(image_urls) <= 20):
            raise ValueError(f"캐러셀은 2-20장 — 현재 {len(image_urls)}")
        print(f"[1/4] 자식 이미지 {len(image_urls)}장 컨테이너 생성...")
        child_ids = []
        for i, u in enumerate(image_urls, 1):
            cid = self._create_carousel_child(u)
            child_ids.append(cid)
            print(f"  ✓ child {i}: {cid}")

        print("[2/4] 캐러셀 컨테이너 생성...")
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": self.access_token,
        }
        resp = self._post_ig(url, params, step="create_carousel")
        carousel_id = resp.json()["id"]
        print(f"  ✓ carousel_id: {carousel_id}")

        print("[3/4] 컨테이너 준비 대기...")
        self._wait_container_ready(carousel_id, timeout=120)
        print("  ✓ FINISHED")

        print("[4/4] 게시...")
        media_id = self._publish_container(carousel_id)
        print(f"  ✅ 캐러셀 게시 완료! Media ID: {media_id}")
        return media_id

    def post_comment(self, media_id: str, text: str) -> str:
        """게시물에 댓글 추가 (게시 직후 호출하면 첫 댓글로 노출).

        필요 권한: instagram_manage_comments (Business API 기본 포함).
        IG rate limit ~25-30 comments/h per account — 일 24회 안쪽이면 안전.

        Args:
            media_id: 게시된 미디어 ID
            text: 댓글 본문 (이모지 OK, 2200자 한도)
        Returns: comment id
        """
        url = f"{GRAPH_API_BASE}/{media_id}/comments"
        params = {"message": text[:2190], "access_token": self.access_token}
        resp = self._post_ig(url, params, step="comment")
        return resp.json()["id"]

    def post_story_video(self, video_url: str) -> str:
        """Stories 에 mp4 게시. 캡션 / 해시태그 미지원 (Stories 자체 제약).

        주의: IG Stories 는 24h 후 자동 삭제됨. 도달 증폭 + 팔로워 노출 강화 목적.
        Returns: 게시된 story media id.
        """
        print(f"[Stories 1/3] 컨테이너 생성...")
        container_id = self._create_story_container(video_url)
        print(f"  ✓ container_id: {container_id}")

        print("[Stories 2/3] 트랜스코딩 대기...")
        self._wait_container_ready(container_id, timeout=180)
        print("  ✓ FINISHED")

        print("[Stories 3/3] 게시...")
        media_id = self._publish_container(container_id)
        print(f"  ✅ Stories 게시 완료! Media ID: {media_id}")
        return media_id

    def post_reel(self, video_url: str, caption: str,
                  cover_url: Optional[str] = None,
                  share_to_feed: bool = True) -> str:
        """Reels 게시 — 비디오 업로드 → 컨테이너 → 트랜스코딩 대기 → publish.

        Args:
            video_url: 공개 접근 가능한 mp4 URL (Cloudinary 등)
            caption: 게시물 캡션 (해시태그 포함)
            cover_url: 커버 이미지(URL). 미지정 시 IG가 첫 프레임 자동 사용
            share_to_feed: True 면 피드에도 같이 표시 (도달 +)

        Returns: published media id
        """
        print(f"[1/3] Reels 컨테이너 생성 (video_url 길이: {len(video_url)})...")
        container_id = self._create_reel_container(
            video_url=video_url, caption=caption,
            cover_url=cover_url, share_to_feed=share_to_feed,
        )
        print(f"  ✓ container_id: {container_id}")

        print("[2/3] 비디오 트랜스코딩 대기 (보통 30-90초)...")
        self._wait_container_ready(container_id)
        print("  ✓ FINISHED")

        print("[3/3] 게시...")
        media_id = self._publish_container(container_id)
        print(f"  ✅ Reels 게시 완료! Media ID: {media_id}")
        return media_id


# ============================================================
# 이미지 호스팅 - Imgur API (무료, 익명 업로드 가능)
# ============================================================
def upload_to_imgur(image_path: Path, client_id: str) -> str:
    """
    Imgur에 이미지 업로드하고 공개 URL 반환
    https://api.imgur.com/oauth2/addclient 에서 클라이언트 ID 발급
    """
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://api.imgur.com/3/image",
            headers={"Authorization": f"Client-ID {client_id}"},
            files={"image": f},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()["data"]["link"]


# ============================================================
# 이미지 호스팅 - Cloudinary (Imgur 대안, 더 안정적)
# ============================================================
def upload_to_cloudinary(image_path: Path, cloud_name: str, upload_preset: str) -> str:
    """
    Cloudinary에 이미지 업로드하고 공개 URL 반환 (Unsigned upload preset 사용).
    https://cloudinary.com 에서 무료 가입 후 Unsigned preset 만들기.

    Args:
        cloud_name: Cloudinary 대시보드 상단의 Cloud name
        upload_preset: Settings → Upload → Unsigned preset 이름
    """
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            files={"file": f},
            data={"upload_preset": upload_preset},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()["secure_url"]


def upload_to_cloudinary_video(video_path: Path, cloud_name: str,
                               upload_preset: str) -> str:
    """Cloudinary 비디오 업로드. 이미지 endpoint 와 분리된 /video/upload 사용.

    주의: upload preset 이 'Video' resource 를 허용해야 함. Cloudinary 대시보드 →
    Settings → Upload → 해당 preset → Resource type: Auto 또는 Video.
    이미지 전용 preset 이면 400 떨어지므로 그때 'Resource type: Auto' 로 변경.
    """
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/video/upload"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            files={"file": f},
            data={"upload_preset": upload_preset, "resource_type": "video"},
            timeout=180,  # 비디오라 업로드 시간 김 (~30MB 가량 가능)
        )
    if not resp.ok:
        try:
            err = resp.json().get("error", {}).get("message", "")
        except Exception:
            err = resp.text[:300]
        raise requests.HTTPError(f"Cloudinary video upload {resp.status_code}: {err}")
    return resp.json()["secure_url"]


def upload_image(image_path: Path) -> str:
    """
    이미지 호스팅 라우터 — Cloudinary 우선, 없으면 Imgur 폴백.
    Reels 본 게시 경로엔 더 이상 쓰이지 않지만 (커버 이미지·디버그용으로 남김).
    """
    cloudinary_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    cloudinary_preset = os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    if cloudinary_name and cloudinary_preset:
        return upload_to_cloudinary(image_path, cloudinary_name, cloudinary_preset)

    imgur_id = os.environ.get("IMGUR_CLIENT_ID")
    if imgur_id:
        return upload_to_imgur(image_path, imgur_id)

    raise RuntimeError(
        "이미지 호스팅 환경변수가 설정되지 않았습니다. "
        "CLOUDINARY_CLOUD_NAME + CLOUDINARY_UPLOAD_PRESET, "
        "또는 IMGUR_CLIENT_ID 중 하나를 설정하세요."
    )


def upload_video(video_path: Path) -> str:
    """비디오 호스팅 라우터 — 현재는 Cloudinary 만 지원 (Imgur 는 mp4 불가)."""
    cloudinary_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    cloudinary_preset = os.environ.get("CLOUDINARY_UPLOAD_PRESET")
    if cloudinary_name and cloudinary_preset:
        return upload_to_cloudinary_video(video_path, cloudinary_name, cloudinary_preset)
    raise RuntimeError(
        "비디오 호스팅 환경변수가 설정되지 않았습니다. "
        "CLOUDINARY_CLOUD_NAME + CLOUDINARY_UPLOAD_PRESET 가 필요합니다 "
        "(preset 의 Resource type 이 'Auto' 또는 'Video' 여야 함)."
    )


CAPTION_VARIANT_NAMES = ["headlines_dotted", "question_hook", "list_count",
                         "tease_one", "you_wont_believe"]


def _variant_index_for(date_str: str) -> int:
    """date 기반 결정적 회전 — 같은 날에 같은 변형, 5일 주기."""
    # 단순 날짜 hash 의 mod
    s = date_str.replace("-", "").replace(":", "")
    h = sum(ord(c) for c in s)
    return h % len(CAPTION_VARIANT_NAMES)


def caption_hook_variant(summaries, date_str: str, label_short: str, n: int) -> dict:
    """date 기반으로 5종 hook 변형 중 하나 선택.

    Returns: {"name": str, "hook": str, "body_lead": str}
    """
    top_titles = [s.card_title for s in summaries[:3]]
    idx = _variant_index_for(date_str)
    name = CAPTION_VARIANT_NAMES[idx]

    if name == "headlines_dotted":
        hook = " · ".join(top_titles)
        if len(hook) > 120:
            hook = " · ".join(top_titles[:2])
        body_lead = f"오늘 {label_short} 핫이슈 {n}건 — 영상으로 한눈에 보세요 ▶"
    elif name == "question_hook":
        first = top_titles[0] if top_titles else ""
        hook = f"오늘 K연예에서 가장 핫한 건? {first[:60]}"
        body_lead = f"외 {n-1}건. 전체 영상 보기 ▶"
    elif name == "list_count":
        hook = f"📌 오늘 {label_short} TOP {n} | {top_titles[0][:50] if top_titles else ''}..."
        body_lead = "전체 목록은 본 영상에서 → ▶"
    elif name == "tease_one":
        first = top_titles[0] if top_titles else ""
        hook = f"잠깐, {first[:80]} ?"
        body_lead = f"오늘 {n}건 중 가장 화제된 이슈 + 나머지 ▶"
    else:  # you_wont_believe
        hook = f"오늘 {label_short} 핫이슈, 다 알고 있나요? {n}건 — 1분 안에 확인"
        body_lead = "영상으로 한눈에 ▶"

    return {"name": name, "hook": hook, "body_lead": body_lead}


# 댓글 유도 라인 (C 자동화 — 5종 회전, hook variant 와 독립).
# IG 알고리즘 2026 에서 comments_count 가 토론 신호 → 게시별로 다양한 question 던지면
# "어떤 질문이 댓글 잘 받나" A/B 측정 가능 (다음 사이클부터).
COMMENT_CTA_VARIANTS = [
    "💬 오늘의 픽은? 댓글로 알려주세요",
    "💬 가장 궁금한 이슈는 몇 번? 댓글로 ⬇️",
    "💬 이 중 본 적 있나요? 댓글로 공유 부탁",
    "💬 가장 응원하는 픽은? 댓글로 알려주세요 ⬇️",
    "💬 어떤 게 가장 인상적이었나요? 솔직한 감상 부탁",
]


def comment_cta_for(date_str: str) -> str:
    """date 기반 결정적 회전 — 같은 날 같은 라인, 5일 주기."""
    digits = "".join(ch for ch in date_str if ch.isdigit())
    return COMMENT_CTA_VARIANTS[int(digits or "0") % len(COMMENT_CTA_VARIANTS)]


def build_caption_with_variant(summaries, date_str: str, label_short: str = "K-연예",
                                default_hashtags=None) -> tuple:
    """build_caption 의 튜플 버전 — A/B 분석용 variant 이름도 반환."""
    caption = build_caption(summaries, date_str, label_short, default_hashtags)
    variant_idx = _variant_index_for(date_str)
    return caption, CAPTION_VARIANT_NAMES[variant_idx]


def build_caption(summaries, date_str: str, label_short: str = "K-연예",
                  default_hashtags=None) -> str:
    """인스타 캡션 생성 — 첫 줄 훅 + 본문 + 해시태그 mix.

    [캡션 첫 줄 = 훅]
    IG 피드는 첫 줄만 미리 보이고 나머지는 'see more' 뒤에 숨음. 첫 줄이 약하면
    클릭 안 함 → engagement velocity 떨어짐. '오늘의 K-연예 TOP N' 식의 정형 문구는
    훅으로 약함 → 상위 3개 헤드라인을 ' · ' 로 연결해 티저로 사용.

    [해시태그 mix 전략 — 3-tier]
    1. niche : 각 뉴스에서 추출한 인물/작품/이벤트별 태그 (#뉴진스컴백 같은) — summary.hashtags
    2. medium: 채널 카테고리 태그 (#K연예, #연예뉴스 등) — default_hashtags
    3. broad : 글로벌 영문 태그 (#kpop, #korea, #koreantrend) — 채널 무관 도달 확장

    IG 한도 30개. niche → medium → broad 순으로 우선 채우고 dedup.
    """
    if default_hashtags is None:
        default_hashtags = [
            "#K연예", "#연예뉴스", "#오늘의연예", "#연예소식",
            "#카드뉴스", "#kpop", "#kdrama", "#한국연예",
        ]
    n = len(summaries)

    # === 첫 줄 훅 (A/B 변형) ===
    # 5종 hook 템플릿을 매일 회전 (date_str 기반 결정 → 같은 날 호출은 동일).
    # state.json에 caption_variant 도 같이 저장하면 weekly_digest 가 변형별 성과 비교 가능.
    variant = caption_hook_variant(summaries, date_str, label_short, n)
    hook = variant["hook"]
    body_lead = variant["body_lead"]
    lines = [
        hook,
        "",
        body_lead,
        "",
    ]

    # === 본문 — 번호 매긴 헤드라인 목록 ===
    for i, s in enumerate(summaries, 1):
        lines.append(f"{i}. {s.card_title}")

    # === 댓글 유도 (C 자동화 — 매일 다른 질문 회전) ===
    lines.append("")
    lines.append(comment_cta_for(date_str))
    lines.append("")
    lines.append("⌁ 매일 아침 8시 K-연예 핫이슈 큐레이션. 팔로우하고 받아보세요.")
    lines.append("📩 친구에게 공유 / 🔖 북마크해두면 매일 다시 확인하기 좋아요.")
    lines.append("")
    lines.append("본 게시물은 공개 보도를 자동 큐레이션한 카드뉴스로,")
    lines.append("정확한 내용은 원문을 함께 확인해 주세요.")
    lines.append("")

    # === 해시태그 mix (niche → medium → broad) ===
    # broad 에 IG Reels 자체 discoverability 태그 (#릴스, #reels) 합류 — 탐색 페이지 노출 ↑
    broad_global = ["#kpop", "#korea", "#koreantrend", "#kculture",
                    "#asianentertainment", "#dailynews", "#newsupdate",
                    "#릴스", "#reels", "#instareels", "#dailyreels"]
    niche = []
    for s in summaries:
        niche.extend(s.hashtags or [])
    # 우선순위: niche 가 가장 강한 시그널 (구체적 검색어 매칭). 그다음 medium, 마지막 broad.
    ordered = list(niche) + list(default_hashtags) + broad_global
    seen = set()
    unique_tags = []
    for tag in ordered:
        # 정규화: 소문자, # 없으면 추가, 공백 제거
        normalized = tag.strip().lower()
        if not normalized.startswith("#"):
            normalized = "#" + normalized
        if normalized in seen or " " in normalized:
            continue
        seen.add(normalized)
        unique_tags.append(tag.strip())
        if len(unique_tags) >= 30:
            break
    lines.append(" ".join(unique_tags))

    return "\n".join(lines)


if __name__ == "__main__":
    print("이 모듈은 main.py에서 호출됩니다.")
    print("필요 환경변수:")
    print("  - INSTAGRAM_USER_ID")
    print("  - INSTAGRAM_ACCESS_TOKEN")
    print("  - CLOUDINARY_CLOUD_NAME + CLOUDINARY_UPLOAD_PRESET (또는 IMGUR_CLIENT_ID)")
