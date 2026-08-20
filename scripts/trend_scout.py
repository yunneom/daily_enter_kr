"""
주간 트렌드 스카우트 — 걸그룹 숏폼 트렌드 리서치 → 신규 콘텐츠 큐 제안.

[무엇]
유튜브가 크리에이터에게 아이디어를 추천해주듯, 매주 Claude 가 웹서치로
IG Reels / YT Shorts / TikTok 의 걸그룹·K팝 콘텐츠 트렌드를 조사하고,
우리 채널의 실제 성과 데이터(저장·공유 상위)와 기존 포맷 목록을 대조해
"겹치지 않는 새 큐 후보"를 마크다운 제안서로 생성한다.

[어디로]
stdout + output_enter/trend_scout/YYYY-WNN.md. 워크플로우(trend_scout.yml)가
이 파일을 GitHub 이슈로 올린다 — 운영자가 골라 컨펌하면 그때 구현·게시.
자동 게시는 절대 하지 않는다 (새 포맷은 사람 승인 필수).

[스코프 규칙]
이 계정은 걸그룹 전문 채널(2026-07 전환)이다. 제안은 걸그룹/K팝 참여형으로
한정하고, 비걸그룹이지만 강력한 아이디어는 '별도 채널 후보' 섹션에만 격리한다.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

KST = timezone(timedelta(hours=9))
OUT_DIR = ROOT / "output_enter" / "trend_scout"

# 주 1회 실행이라 호출량이 미미해 품질 우선 — Opus 5.
# (일간 대량 호출인 summarize 는 비용 결정으로 Haiku 유지 — CLAUDE.md 참조)
MODEL = "claude-opus-5"
MAX_WEB_SEARCHES = 8


def _current_formats() -> str:
    """현재 운영 중인 포맷 요약 — 제안 중복 방지용 컨텍스트."""
    lines = [
        "- 걸그룹 이상형 월드컵 (32강 토너먼트: IG 라운드 투표 + 웹 완주형, dailyenterkr.com)",
        "- 걸그룹 뉴스 카드 캐러셀 (매일 08:00, 걸그룹/여성 아이돌 스코프)",
        "- 드림 유닛 빌더 (4x3 실사 그리드, 댓글 1-3-2-1 조합) — 월",
        "- 밸런스게임 2문항 (덕질/상황 취향, 1/2 투표) — 화·금",
        "- 멈춰라 챌린지 (실사 고속 순환 릴스, 일시정지 뽑기) — 수·토",
        "- 케미 듀오 4팀 투표 (같은 그룹 2인 조합, 1~4 투표 → 일요일 결과) — 목",
        "- 만원으로 걸그룹 조합 (올스타 실사판 / 4·5세대 티어편, 포지션별 예산 조합) — 매일 09:00",
        "- 슬롯머신 걸그룹 조합 (3릴 스크롤 영상, 일시정지 픽) — 로테이션",
        "- 브랜드평판 TOP10 카운트다운 릴스 — 월 1회",
    ]
    return "\n".join(lines)


def _performance_summary() -> str:
    """insights.json 최신 스냅샷에서 성과 요약 — 데이터 기반 제안 유도."""
    try:
        d = json.loads((ROOT / "insights.json").read_text(encoding="utf-8"))
        snap = d["snapshots"][-1]
        acct = snap.get("account", {})
        posts = snap.get("posts", [])
        ranked = sorted(
            posts,
            key=lambda p: ((p.get("saved") or 0) + (p.get("shares") or 0),
                           p.get("like_count") or 0),
            reverse=True,
        )[:5]
        lines = [f"계정: 도달 {acct.get('reach', '?')}, 팔로워 {acct.get('followers_count', '미추적')}"]
        for p in ranked:
            cap = (p.get("caption_excerpt") or "").split("\n")[0][:40]
            lines.append(
                f"- {cap} | 저장 {p.get('saved') or 0} · 공유 {p.get('shares') or 0}"
                f" · 좋아요 {p.get('like_count') or 0} · 댓글 {p.get('comments_count') or 0}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"(인사이트 로드 실패: {e})"


PROMPT = """당신은 K-팝 걸그룹 전문 인스타그램 채널(@daily_enter_kr)의 콘텐츠 전략가다.
웹서치로 **최신(최근 1~2개월) 걸그룹/K팝 숏폼 콘텐츠 트렌드**를 조사하고,
아래 우리 채널 상황과 대조해 **새로운 콘텐츠 큐 후보 3~5개**를 제안하라.

## 우리 채널 상황

### 현재 운영 중인 포맷 (제안이 이것들과 겹치면 안 됨)
{formats}

### 최근 성과 데이터 (무엇이 통하는지)
{performance}

### 제작 파이프라인 제약 (자동화 가능해야 함)
- Python PIL 정적 카드(1080x1920) + FFmpeg 슬라이드쇼 mp4 + 자체 BGM
- 실사 사진은 위키미디어 커먼즈 검증분 30명만 사용 가능 (그 외 멤버는 사진 불가)
- 실사 촬영/편집자 없음, GitHub Actions 완전 자동
- 댓글 수집·집계 가능 (숫자 투표 파싱)

### 안전 가드레일 (완화 불가)
- 실존 인물 존중: 외모 비교/서열, 사생활, 열애 추측 금지
- 클릭베이트 어휘 금지, 커플링(이성 셀럽 페어링) 금지
- 저작권: MV 캡처/음원 사용 불가, 커먼즈 사진과 자체 생성물만

## 조사할 것 (웹서치 활용, 최소 5회 검색 — 한국어+영어)
1. 인스타 릴스/유튜브 쇼츠/틱톡에서 지금 뜨는 K팝 걸그룹 콘텐츠 포맷
2. 참여형(투표/게임/챌린지) 포맷 중 새로 부상하는 것
3. 팬덤 문화 트렌드 (포카/최애/덕질 관련 신조어·놀이)

## 출력 형식 (마크다운, 한국어)
각 제안마다:
### N. [제안 이름]
- **근거 트렌드**: 뭐가 뜨고 있어서 이걸 제안하는지 (출처 URL 포함)
- **포맷**: 카드 몇 장/영상 구조, 각 장에 뭐가 들어가는지 구체적으로
- **참여 루프**: 댓글/저장/공유를 어떻게 유발하는지
- **팔로우 이유**: 왜 다음 편을 기다리게 되는지 (시리즈성)
- **자동화 난이도**: S(기존 렌더러 재사용)/M(신규 렌더러)/L(신규 시스템)
- **리스크**: 가드레일 관점 주의점
- **추천도**: 1~10점 + 한 줄 이유

마지막에:
### 별도 채널 후보 (이 계정엔 게시 금지)
걸그룹과 무관하지만 강력한 트렌드가 보이면 1~2개만 간단히 (예: 재테크/절약 챌린지
계열은 준비된 daily_money_kr 채널 소재).

### 이번 주 한 줄 요약
운영자가 3초 안에 읽을 핵심.

주의: 기존 포맷의 사소한 변형(문항만 다른 밸런스게임 등)은 제안이 아니다.
새 참여 메커니즘이나 새 소재 축이 있어야 한다. 확신 없는 트렌드를 지어내지 마라 —
검색에서 실제로 확인한 것만 근거로 써라."""


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 미설정")
        return 1

    now = datetime.now(KST)
    week_label = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    out_path = OUT_DIR / f"{week_label}.md"
    if out_path.exists():
        print(f"✅ 이번 주({week_label}) 제안서 이미 생성됨 — skip")
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    prompt = PROMPT.format(formats=_current_formats(),
                           performance=_performance_summary())

    print(f"🔎 트렌드 스카우트 실행 ({MODEL}, 웹서치 최대 {MAX_WEB_SEARCHES}회)…")
    # Opus 5 는 thinking 기본 on(adaptive) — thinking 파라미터 생략.
    # 웹서치가 길어질 수 있어 스트리밍으로 타임아웃 회피.
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        tools=[{
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": MAX_WEB_SEARCHES,
        }],
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        print("❌ 모델이 요청을 거절함 — 프롬프트 확인 필요")
        return 1

    report = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if len(report) < 500:
        print(f"❌ 제안서가 비정상적으로 짧음({len(report)}자) — 게시 스킵")
        print(report)
        return 1

    searches = sum(1 for b in response.content
                   if getattr(b, "type", "") == "server_tool_use")
    header = (f"# 💡 주간 신규 콘텐츠 큐 제안 — {week_label}\n\n"
              f"> 자동 생성: {now.strftime('%Y-%m-%d %H:%M KST')} · {MODEL}"
              f" · 웹서치 {searches}회 · 채택 전까지 게시되지 않음\n\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + report + "\n", encoding="utf-8")
    print(f"✅ 제안서 생성: {out_path.relative_to(ROOT)} ({len(report)}자)")
    print()
    print(report[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
