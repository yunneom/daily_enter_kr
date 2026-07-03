"""
아이돌 사진 — 위키미디어 커먼즈 검증 파일(오버라이드) + ko.wikipedia 폴백 + 캐시.

[합법성]
한국어 위키백과/위키미디어 커먼즈 이미지는 대부분 CC BY-SA / CC BY / public domain.
출처·기여자·라이선스를 표기하면 합법 사용 가능. 소속사/홈마 사진 스크래핑 X.

[전략]
0. 게이트 2종 (리스크 리뷰 — 완화 금지):
   a. 성인 게이트 — data/member_birthdays.json 의 생년월일이 확인되고 만 18세
      이상인 멤버만 사진 허용. 생일 미확인(null/미등록) = 미성년 취급 → 사진 X.
   b. 검증 소스 allowlist — data/idol_photo_overrides.json 에 등록된
      (= 커먼즈 파일이 사람 눈으로 검증된) 멤버만 사진 허용. 미등록 멤버는
      자동 검색으로도 사진을 받지 않음 (오식별/비검증 소스 리스크 차단).
1. 오버라이드 커먼즈 파일 우선 해석 (Commons API imageinfo) — CC/PD 게이트 통과 필수
2. 오버라이드 실패 시 ko.wikipedia pageimages/검색 폴백 (기존 4단계)
3. 썸네일 다운로드 + author/license 수집 → 캐시
4. 어떤 단계든 실패하면 None → 호출부가 이모지 폴백

[캐시]
output_enter/idol_photos/{name}.jpg + _attribution.json (positive/negative 모두 캐시)
한 번 받으면 재실행 시 네트워크 0. negative(사진없음)도 캐시해 반복 조회 방지.
(성인 게이트는 날짜 의존이라 캐시하지 않고 매 호출 판정.)

[주의]
이 컨테이너(dev)는 wikipedia.org egress 차단 → 여기선 항상 None(이모지 폴백).
GitHub Actions 런타임에선 정상 작동.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List

import requests

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "output_enter" / "idol_photos"
ATTR_PATH = CACHE_DIR / "_attribution.json"
WIKI_API = "https://ko.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OVERRIDES_PATH = ROOT / "data" / "idol_photo_overrides.json"
BIRTHDAYS_PATH = ROOT / "data" / "member_birthdays.json"
UA = "daily_enter_kr-worldcup/1.0 (educational fan project; contact @daily_enter_kr)"
THUMB_SIZE = 600
KST = timezone(timedelta(hours=9))

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


def _api_get(params: dict, api: str = WIKI_API) -> Optional[dict]:
    try:
        r = requests.get(api, params={**params, "format": "json"},
                         headers={"User-Agent": UA}, timeout=12)
        if not r.ok:
            return None
        return r.json()
    except Exception:
        return None


# ─── 검증 소스 오버라이드 + 성인 게이트 (리스크 리뷰 결정사항) ───────────────

_FREE_LICENSE_KEYWORDS = ["cc", "public domain", "cc0", "pd", "공용",
                          "creative commons"]


def _is_free_license(lic_str: str) -> bool:
    return any(k in (lic_str or "").lower() for k in _FREE_LICENSE_KEYWORDS)


def _load_overrides() -> Dict[str, dict]:
    """data/idol_photo_overrides.json → {member: {file, rank, group}}.
    파일이 없으면 빈 dict (allowlist 미적용 — 기존 검색만)."""
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for rank, rec in raw.items():
        m = rec.get("member")
        if m and rec.get("file"):
            out[m] = {**rec, "rank": rank}
    return out


def _load_birthdays() -> Dict[str, Optional[str]]:
    """data/member_birthdays.json → {member: 'YYYY-MM-DD' | None}."""
    if not BIRTHDAYS_PATH.exists():
        return {}
    try:
        raw = json.loads(BIRTHDAYS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {rec.get("member"): rec.get("birth") for rec in raw.values()
            if rec.get("member")}


def _adult_gate(member_name: str, on_date: Optional[date] = None) -> bool:
    """만 18세 이상(생일 확인됨)만 True. 생일 미확인 = 미성년 취급 → False.
    날짜 의존 판정이므로 결과를 negative 캐시에 쓰지 않는다."""
    if on_date is None:
        on_date = datetime.now(KST).date()
    birth_s = _load_birthdays().get(member_name)
    if not birth_s:
        print(f"  🔞 사진 게이트: {member_name} — 생년월일 미확인 → 사진 제외")
        return False
    try:
        b = date.fromisoformat(birth_s)
    except ValueError:
        print(f"  🔞 사진 게이트: {member_name} — 생년월일 형식 오류({birth_s}) → 사진 제외")
        return False
    age = on_date.year - b.year - ((on_date.month, on_date.day) < (b.month, b.day))
    if age < 18:
        print(f"  🔞 사진 게이트: {member_name} — 만 {age}세 → 사진 제외")
        return False
    return True


def _resolve_override(member_name: str) -> Optional[Dict]:
    """오버라이드 커먼즈 파일 → {thumb_url, title, file} + 라이선스 메타.
    CC/PD 게이트 실패 또는 API 실패 시 None (호출부가 기존 검색으로 폴백)."""
    ov = _load_overrides().get(member_name)
    if not ov:
        return None
    file_name = ov["file"]
    data = _api_get({
        "action": "query", "titles": f"File:{file_name}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": THUMB_SIZE,
    }, api=COMMONS_API)
    if not data:
        return None
    for _, p in (data.get("query", {}).get("pages", {}) or {}).items():
        ii = (p.get("imageinfo") or [{}])[0]
        thumb = ii.get("thumburl") or ii.get("url")
        if not thumb:
            continue
        ext = ii.get("extmetadata", {})
        lic = ext.get("LicenseShortName", {}).get("value", "")
        if not _is_free_license(lic):
            print(f"  ⚠️ 오버라이드 {member_name}: 비CC 라이선스({lic[:30]}) → 폴백")
            return None
        return {
            "thumb_url": thumb,
            "title": p.get("title", f"File:{file_name}"),
            "file": file_name,
            "_license": {
                "artist": _strip_html(ext.get("Artist", {}).get("value", "")),
                "license": lic,
                "descurl": ii.get("descriptionurl", ""),
            },
        }
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


# pageimage 가 비어도 페이지 내 다른 이미지로 폴백.
# 인포박스 이미지는 prop=pageimages 가 자주 누락 → prop=images 로 모든 파일 후보 후
# CC + 인물사진(파일명 + 크기) 필터.
_EXCLUDE_FILENAME_KEYWORDS = (
    "logo", "signature", "서명", "map", "flag", "icon", "wikimedia", "commons",
    "ambox", "stub", "yes_check", "x_mark", "edit-icon", "question_mark",
    "음악_아이콘", "노래방", "장르", "텍스트", "글자", "_text_"
)


def _is_candidate_filename(filename: str) -> bool:
    """파일명으로 인물사진 후보 1차 필터."""
    fn = filename.lower()
    if not any(fn.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        return False
    if any(k in fn for k in _EXCLUDE_FILENAME_KEYWORDS):
        return False
    if fn.endswith(".svg"):
        return False
    return True


def _imageinfo_with_thumb(file_titles: List[str], width: int = THUMB_SIZE) -> List[dict]:
    """File:X|File:Y… 다중 imageinfo (URL/라이선스/크기). titles 50개 한도."""
    if not file_titles:
        return []
    data = _api_get({
        "action": "query", "titles": "|".join(file_titles[:50]),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": width,  # → thumburl 자동 생성 (width px)
    })
    if not data:
        return []
    out = []
    for _, p in data.get("query", {}).get("pages", {}).items():
        for ii in (p.get("imageinfo") or []):
            ii["_title"] = p.get("title", "")
            out.append(ii)
    return out


def _page_images_filter(title: str) -> Optional[dict]:
    """페이지의 모든 이미지에서 첫 CC 인물사진. pageimages 폴백."""
    # 1) 페이지의 image 파일명 모두
    data = _api_get({
        "action": "query", "titles": title, "redirects": 1,
        "prop": "images", "imlimit": 30,
    })
    if not data:
        return None
    file_titles = []
    for _, p in data.get("query", {}).get("pages", {}).items():
        for img in p.get("images", []):
            t = img.get("title", "")  # "파일:..." or "File:..."
            fname = t.split(":", 1)[-1] if ":" in t else t
            if _is_candidate_filename(fname):
                file_titles.append(t)
    if not file_titles:
        return None
    # 2) 모든 후보 imageinfo 일괄 조회
    infos = _imageinfo_with_thumb(file_titles, width=THUMB_SIZE)
    # 3) CC + 인물크기 후보 첫 1개
    for ii in infos:
        if not ii.get("thumburl") and not ii.get("url"):
            continue
        if (ii.get("width") or 0) < 200:  # 너무 작으면 아이콘
            continue
        ext = ii.get("extmetadata", {})
        lic = (ext.get("LicenseShortName", {}).get("value") or "").lower()
        if not any(k in lic for k in ["cc", "public domain", "cc0", "pd",
                                       "공용", "creative commons"]):
            continue
        # extmetadata 의 ObjectName/ImageDescription 으로 추가 필터 (선택)
        return {
            "thumb_url": ii.get("thumburl") or ii.get("url"),
            "title": title,
            "file": (ii.get("_title", "") or "").split(":", 1)[-1],
        }
    return None


def _page_images_via_search(name: str) -> Optional[dict]:
    """검색으로 인물 페이지 추정 → page_images_filter."""
    data = _api_get({
        "action": "query", "list": "search",
        "srsearch": f"{name} 가수 아이돌", "srlimit": 3,
    })
    if not data:
        return None
    for hit in (data.get("query") or {}).get("search") or []:
        title = hit.get("title", "")
        if name not in title:
            continue  # 이름-제목 일치 가드 (검색 결과도)
        r = _page_images_filter(title)
        if r:
            return r
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

    게이트 (완화 금지):
    - 성인 게이트: 생년월일 확인 + 만 18세 이상만. 미확인 = 미성년 취급 → None.
    - 검증 소스 allowlist: overrides 파일이 있으면 등록 멤버만 사진 허용.
    캐시 우선. 네트워크 실패/사진없음도 캐시(negative)해 반복 호출 방지.
    """
    # ── 게이트1: 성인 (날짜 의존 → 캐시 앞에서, negative 캐시에 안 씀) ──
    if not _adult_gate(member_name):
        return None

    # ── 게이트2: 검증 소스 allowlist ── overrides 미등록 멤버는 자동 검색으로도
    # 사진을 받지 않음 (gstatic/비검증 소스 랭크는 이모지 폴백 확정).
    overrides = _load_overrides()
    if overrides and member_name not in overrides:
        print(f"  🚫 사진 게이트: {member_name} — 검증된 커먼즈 소스 없음 → 이모지 폴백")
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    attr = _load_attr()
    if member_name in attr:
        rec = attr[member_name]
        if rec.get("path") and (CACHE_DIR / rec["path"]).exists():
            return {**rec, "path": str(CACHE_DIR / rec["path"])}
        if rec.get("none"):
            return None  # negative 캐시

    # ── 0단계: 검증된 커먼즈 오버라이드 파일 우선 (CC/PD 게이트 포함) ──
    lic: dict = {}
    hit = _resolve_override(member_name)
    if hit:
        lic = hit.pop("_license", {})

    if not hit:
        # 후보 제목
        titles = WIKI_TITLE_OVERRIDES.get(member_name, [member_name, f"{member_name} (가수)"])
        # 4단계 폴백: pageimages → page_images_filter → pageimages 검색 → page_images 검색
        hit = _pageimage_for_titles(titles)
        if not hit:
            for t in titles:
                hit = _page_images_filter(t)
                if hit:
                    break
        if not hit:
            hit = _pageimage_via_search(member_name)
        if not hit:
            hit = _page_images_via_search(member_name)
        if not hit:
            attr[member_name] = {"none": True}
            _save_attr(attr)
            return None

        # ── 가드1: 이름-제목 일치 ── 그룹 페이지/동명이인 회피.
        # 설윤→"NMIXX"(그룹 단체사진), 잘못된 인물 등 차단. 멤버명이 제목에 없으면 거부.
        # (오버라이드 파일은 사람이 검증한 파일명이라 이 가드 대상 아님.)
        resolved = hit.get("title") or ""
        if member_name not in resolved:
            attr[member_name] = {"none": True, "reason": f"제목불일치({resolved})"}
            _save_attr(attr)
            return None

        # ── 가드2: CC/PD 라이선스만 ── 비자유(fair-use) 이미지 차단 (저작권 안전).
        lic = _fetch_license(hit.get("file"))
        if not _is_free_license(lic.get("license") or ""):
            attr[member_name] = {"none": True,
                                 "reason": f"비CC라이선스({(lic.get('license') or '')[:30]})"}
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

    # lic 은 가드2에서 이미 조회됨 (재사용)
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
    """게시 캡션용 출처 표기 — 실제 사진이 캐시된 멤버당 한 줄, 중복 제거.
    형식: '사진 출처: {멤버} — {저작자} ({라이선스}, Wikimedia Commons)'
    사진 사용 멤버가 없으면 빈 문자열."""
    attr = _load_attr()
    lines, seen = [], set()
    for m in members:
        if m in seen:
            continue
        seen.add(m)
        rec = attr.get(m, {})
        if not rec.get("path"):
            continue
        a = rec.get("artist") or "Wikimedia 기여자"
        lic = rec.get("license") or "CC"
        lines.append(f"사진 출처: {m} — {a} ({lic}, Wikimedia Commons)")
    return "\n".join(lines[:8])


if __name__ == "__main__":
    # 로컬 점검 — 컨테이너 차단이면 전부 None (이모지 폴백)
    for name in ["장원영", "카리나", "리즈"]:
        r = fetch_photo(name)
        print(f"{name}: {'사진 ' + r['path'] + ' (' + r.get('license','') + ')' if r else 'None (이모지 폴백)'}")
