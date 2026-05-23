"""
Instagram 업로드 모듈
Instagram Graph API를 사용하여 카드뉴스를 캐러셀 포스트로 업로드합니다.

[사전 준비 - 필수]
1. Facebook 페이지 생성
2. 인스타그램 계정을 비즈니스/크리에이터로 전환
3. Facebook 페이지와 인스타 계정 연결
4. https://developers.facebook.com 에서 앱 생성
5. Instagram Graph API 추가, 권한 요청:
   - instagram_basic
   - instagram_content_publish
   - pages_show_list
   - pages_read_engagement
6. 장기 액세스 토큰 발급 (60일짜리, 자동 갱신 필요)
7. Instagram Business Account ID 확인

[중요한 제약]
- 이미지가 공개 URL로 호스팅되어 있어야 함 (S3, Cloudinary, Imgur 등)
- 캐러셀은 최대 10장
- 첫 이미지의 비율에 맞춰 모두 크롭됨 → 모두 1:1로 통일 권장
- 24시간 내 100건 게시 제한
"""

import os
import time
import requests
from pathlib import Path
from typing import List


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
    
    def _create_image_container(self, image_url: str, is_carousel_item: bool = True) -> str:
        """캐러셀 자식 컨테이너 생성"""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "is_carousel_item": str(is_carousel_item).lower(),
            "access_token": self.access_token,
        }
        resp = requests.post(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]
    
    def _create_carousel_container(self, child_ids: List[str], caption: str) -> str:
        """캐러셀 메인 컨테이너 생성"""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media"
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": self.access_token,
        }
        resp = requests.post(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]
    
    def _publish_container(self, container_id: str) -> str:
        """컨테이너 게시"""
        url = f"{GRAPH_API_BASE}/{self.ig_user_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        resp = requests.post(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()["id"]
    
    def _wait_container_ready(self, container_id: str, timeout: int = 60):
        """컨테이너가 FINISHED 상태가 될 때까지 대기"""
        url = f"{GRAPH_API_BASE}/{container_id}"
        params = {"fields": "status_code", "access_token": self.access_token}
        elapsed = 0
        while elapsed < timeout:
            resp = requests.get(url, params=params, timeout=10)
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise Exception(f"Container {container_id} failed")
            time.sleep(3)
            elapsed += 3
        raise TimeoutError(f"Container {container_id} not ready in {timeout}s")
    
    def post_carousel(self, image_urls: List[str], caption: str) -> str:
        """
        캐러셀 포스트 게시
        
        Args:
            image_urls: 공개 접근 가능한 이미지 URL 리스트 (최대 10개)
            caption: 게시물 캡션 (해시태그 포함)
        Returns:
            published media id
        """
        if len(image_urls) > 10:
            raise ValueError("캐러셀은 최대 10장까지만 가능합니다")
        
        print(f"[1/4] {len(image_urls)}개 자식 컨테이너 생성...")
        child_ids = []
        for i, url in enumerate(image_urls, 1):
            child_id = self._create_image_container(url, is_carousel_item=True)
            child_ids.append(child_id)
            print(f"  ✓ ({i}/{len(image_urls)}) {child_id}")
        
        print("[2/4] 자식 컨테이너 처리 대기...")
        for cid in child_ids:
            self._wait_container_ready(cid)
        
        print("[3/4] 캐러셀 메인 컨테이너 생성...")
        carousel_id = self._create_carousel_container(child_ids, caption)
        self._wait_container_ready(carousel_id)
        print(f"  ✓ {carousel_id}")
        
        print("[4/4] 게시...")
        media_id = self._publish_container(carousel_id)
        print(f"  ✅ 게시 완료! Media ID: {media_id}")
        
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


def upload_image(image_path: Path) -> str:
    """
    설정된 환경변수에 따라 자동으로 적합한 호스팅 서비스 선택.
    Cloudinary가 설정되어 있으면 우선 사용, 없으면 Imgur 폴백.
    """
    import os

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


def build_caption(summaries, date_str: str) -> str:
    """인스타 캡션 생성 (K-연예 톤)"""
    lines = [
        f"오늘의 K-연예 TOP 10 ({date_str})",
        "",
        "오늘 안 보면 손해. 슬라이드 →",
        "",
    ]

    # 본문에 각 뉴스 한 줄씩 (제목만 노출 = 슬라이드 안 보면 모름 → 클릭 유도)
    for i, s in enumerate(summaries, 1):
        lines.append(f"{i}. {s.card_title}")

    lines.append("")
    lines.append("자세한 내용은 슬라이드를 넘겨주세요.")
    lines.append("본 게시물은 자동 큐레이션이며 원문 기사를 함께 확인해주세요.")
    lines.append("")

    # 해시태그 수집 + 중복 제거 (K-연예 우선 태그를 앞에 배치)
    all_hashtags = [
        "#K연예", "#연예뉴스", "#오늘의연예", "#연예핫이슈",
        "#카드뉴스", "#연예TOP10", "#kpop", "#kdrama", "#한국연예",
    ]
    for s in summaries:
        all_hashtags.extend(s.hashtags)
    unique_tags = list(dict.fromkeys(all_hashtags))[:30]  # 인스타 해시태그 최대 30개
    lines.append(" ".join(unique_tags))

    return "\n".join(lines)


if __name__ == "__main__":
    print("이 모듈은 main.py에서 호출됩니다.")
    print("필요 환경변수:")
    print("  - INSTAGRAM_USER_ID")
    print("  - INSTAGRAM_ACCESS_TOKEN")
    print("  - IMGUR_CLIENT_ID")
