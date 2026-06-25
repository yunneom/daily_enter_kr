"""
아이돌 사진 — 한국어 위키백과(CC 라이선스) pageimage 자동 수집 + 캐시.

[합법성]
한국어 위키백과/위키미디어 커먼즈 이미지는 대부분 CC BY-SA / CC BY / public domain.
출처·기여자·라이선스를 표기하면 합법 사용 가능. 소속사/홈마 사진 스크래핑 X.

[전략]
1. 멤버 한글 이름으로 ko.wikipedia pageimages 조회 (오버라이드 disambiguation 우선)
2. 없으면 ko.wikipedia 검색(generator=search) 으로 인물 페이지 추정 → pageimage
3. 썸네일 다운로드 + imageinfo 로 author/license 수집 → 캐시
4. 어떤 단계든 실패하면 None → 호출부가 이모지 폴백

[캐시]
output_enter/idol_photos/{name}.jpg + _attribution.json (positive/negative 모두 캐시)
한 번 받으면 재실행 시 네트워크 0. negative(사진없음)도 캐시해 반복 조회 방지.

[주의]
이 컨테이너(dev)는 wikipedia.org egress 차단 → 여기선 항상 None(이모지 폴백).
GitHub Actions 런타임에선 정상 작동.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List

import requests

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "output_enter" / "idol_photos"
ATTR_PATH = CACHE_DIR / "_attribution.json"
WIKI_API = "https://ko.wikipedia.org/w/api.php"
UA = "daily_enter_kr-worldcup/1.0 (educational fan project; contact @daily_enter_kr)"
THUMB_SIZE = 600

# disambiguation 오버라이드 — 정확한 ko.wikipedia 문서 제목.
# 동명이인/일반명사 충돌 멤버만. 나머지는 [이름, 이름+" (가수)"] 자동 시도.
WIKI_TITLE_OVERRIDES: Dict[str, List[str]] = {
    "장원영": ["장원영"],
    "제니": ["제니 (가수)", "제니 (1996년)"],
    "카리나": ["카리나 (가수)"],
    "로제": ["로제 (가수)"],
    "리사": ["리사 (1997년)", "리사 (가수)"],
    "지수": ["지수 (1995년)", "지수 (가수)"],
    "윈터": ["윈터 (가수)"],
    "카즈하": ["카즈하"],
    "김채원": ["김채원 (2000년)", "김채원 (가수)"],
    "안유진": ["안유진"],
    "닝닝": ["닝닝"],
    "지젤": ["지젤 (가수)"],
    "리즈": ["리즈 (가수)"],
    "설윤": ["설윤"],
    "태연": ["태연"],
    "나연": ["나연"],
    "정연": ["정연 (가수)", "정연"],
    "원희": ["원희 (가수)"],
    "원이": ["원이 (가수)", "원이"],
    "미나미": ["미나미 (가수)", "미나미"],
    "모카": ["모카 (가수)"],
    "조이": ["조이 (가수)"],
    "슬기": ["슬기 (가수)"],
    "아이린": ["아이린 (가수)"],
    "여름": ["여름 (가수)", "엑시"],  # 우주소녀 여름
    "이채영": ["이채영 (2000년)", "이채영 (가수)"],
    "윤아": ["윤아"],
    "지원": ["지원 (시그니처)", "이지원 (2003년)"],
    "레이": ["레이 (2004년)", "이레이"],
    "정채연": ["정채연"],
    "최유정": ["최유정 (가수)"],
}


def _load_attr() -> dict:
    if ATTR_PATH.exists():
        try:
            return json.loads(ATTR_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_attr(d: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ATTR_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _api_get(params: dict) -> Optional[dict]:
    try:
        r = requests.get(WIKI_API, params={**params, "format": "json"},
                         headers={"User-Agent": UA}, timeout=12)
        if not r.ok:
            return None
        return r.json()
    except Exception:
        return None


def _pageimage_for_titles(titles: List[str]) -> Optional[dict]:
    """주어진 후보 제목들에서 첫 pageimage(thumbnail) 반환. {thumb_url, pageid, title, file}."""
    for title in titles:
        data = _api_get({
            "action": "query", "titles": title, "redirects": 1,
            "prop": "pageimages|pageprops", "piprop": "thumbnail|name",
            "pithumbsize": THUMB_SIZE,
        })
        if not data:
            continue
        pages = data.get("query", {}).get("pages", {})
        for _, p in pages.items():
            if p.get("thumbnail", {}).get("source"):
                # 인물 disambiguation 페이지 회피 (pageprops.disambiguation)
                if "disambiguation" in (p.get("pageprops") or {}):
                    continue
                return {
                    "thumb_url": p["thumbnail"]["source"],
                    "pageid": p.get("pageid"),
                    "title": p.get("title"),
                    "file": p.get("pageimage"),
                }
    return None


def _pageimage_via_search(name: str) -> Optional[dict]:
    """검색으로 인물 페이지 추정 → pageimage."""
    data = _api_get({
        "action": "query", "generator": "search",
        "gsrsearch": f"{name} 가수 아이돌", "gsrlimit": 3,
        "prop": "pageimages", "piprop": "thumbnail|name",
        "pithumbsize": THUMB_SIZE, "redirects": 1,
    })
    if not data:
        return None
    pages = list(data.get("query", {}).get("pages", {}).values())
    # index 순 정렬 (검색 랭킹)
    pages.sort(key=lambda p: p.get("index", 99))
    for p in pages:
        if p.get("thumbnail", {}).get("source"):
            return {
                "thumb_url": p["thumbnail"]["source"],
                "pageid": p.get("pageid"),
                "title": p.get("title"),
                "file": p.get("pageimage"),
            }
    return None


def _fetch_license(file_name: Optional[str]) -> dict:
    """File:xxx 의 라이선스/저작자 메타 (출처 표기용). 실패 시 빈 dict."""
    if not file_name:
        return {}
    data = _api_get({
        "action": "query", "titles": f"File:{file_name}",
        "prop": "imageinfo", "iiprop": "extmetadata|url",
    })
    if not data:
        return {}
    for _, p in data.get("query", {}).get("pages", {}).items():
        ii = (p.get("imageinfo") or [{}])[0]
        ext = ii.get("extmetadata", {})
        return {
            "artist": _strip_html(ext.get("Artist", {}).get("value", "")),
            "license": ext.get("LicenseShortName", {}).get("value", ""),
            "descurl": ii.get("descriptionurl", ""),
        }
    return {}


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s or "").strip()[:80]


def fetch_photo(member_name: str) -> Optional[Dict]:
    """멤버 한글 이름 → {path, artist, license, title} 또는 None.

    캐시 우선. 네트워크 실패/사진없음도 캐시(negative)해 반복 호출 방지.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    attr = _load_attr()
    if member_name in attr:
        rec = attr[member_name]
        if rec.get("path") and (CACHE_DIR / rec["path"]).exists():
            return {**rec, "path": str(CACHE_DIR / rec["path"])}
        if rec.get("none"):
            return None  # negative 캐시

    # 후보 제목
    titles = WIKI_TITLE_OVERRIDES.get(member_name, [member_name, f"{member_name} (가수)"])
    hit = _pageimage_for_titles(titles) or _pageimage_via_search(member_name)
    if not hit:
        attr[member_name] = {"none": True}
        _save_attr(attr)
        return None

    # 다운로드
    try:
        r = requests.get(hit["thumb_url"], headers={"User-Agent": UA}, timeout=15)
        if not r.ok:
            attr[member_name] = {"none": True}
            _save_attr(attr)
            return None
        fname = f"{member_name}.jpg"
        (CACHE_DIR / fname).write_bytes(r.content)
    except Exception:
        attr[member_name] = {"none": True}
        _save_attr(attr)
        return None

    lic = _fetch_license(hit.get("file"))
    rec = {
        "path": fname,
        "artist": lic.get("artist", ""),
        "license": lic.get("license", ""),
        "title": hit.get("title", ""),
        "descurl": lic.get("descurl", ""),
    }
    attr[member_name] = rec
    _save_attr(attr)
    return {**rec, "path": str(CACHE_DIR / fname)}


def attribution_line(members: List[str]) -> str:
    """게시 캡션용 출처 표기 — 사진 받은 멤버들의 저작자/라이선스 묶음."""
    attr = _load_attr()
    used = [(m, attr.get(m, {})) for m in members
            if attr.get(m, {}).get("path")]
    if not used:
        return ""
    # 라이선스 종류 묶음
    parts = []
    for m, rec in used:
        a = rec.get("artist") or "Wikimedia 기여자"
        parts.append(f"{m}={a}")
    return "📷 사진: 위키미디어 커먼즈 (CC) · " + ", ".join(parts[:8])


if __name__ == "__main__":
    # 로컬 점검 — 컨테이너 차단이면 전부 None (이모지 폴백)
    for name in ["장원영", "카리나", "리즈"]:
        r = fetch_photo(name)
        print(f"{name}: {'사진 ' + r['path'] + ' (' + r.get('license','') + ')' if r else 'None (이모지 폴백)'}")
