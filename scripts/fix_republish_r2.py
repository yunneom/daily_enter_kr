"""
R2(결승/3·4위전) 오게시 정리 — ledger 에서 잘못 게시된 항목 제거.

배경: 7/4 결승 라운드가 콤보(2매치 4지선다) 렌더러/캡션으로 잘못 게시됨
(솔로 post 구조인데 같은 매치를 매치1/매치2 로 두 번 + "윈터+윈터" 식 4지선다).
R4 발표 카드도 2명 진출 레이아웃 깨짐 + 낡은 "7/3(금) 21:00" 일정 표기.

이 스크립트는 post_ledger.json 에서 아래 topic_id 항목만 제거한다 (멱등):
  - worldcup_r2_1, worldcup_r2_2  (결승/3·4위전 매치 게시)
  - worldcup_announce_r4          (R4 결과 발표)
(worldcup_hf_r2_bracket 은 정상 → 유지)

제거 후엔 오케스트레이터의 catch-up 이 r4_finalize(발표 재게시) →
publish R2(수정판 재게시) 순서로 자동 복구한다. 여기서 직접 게시하지 않음.
IG 의 기존 오게시물 삭제는 운영자가 수동으로 진행.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LEDGER_PATH = ROOT / "post_ledger.json"

REMOVE_TOPIC_IDS = {"worldcup_r2_1", "worldcup_r2_2", "worldcup_announce_r4"}


def main() -> int:
    if not LEDGER_PATH.exists():
        print(f"❌ {LEDGER_PATH} 없음")
        return 1
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ ledger 파싱 실패: {e}")
        return 1

    entries = data.get("entries", [])
    keep, removed = [], []
    for e in entries:
        if (e.get("topic_id") or "") in REMOVE_TOPIC_IDS:
            removed.append(e)
        else:
            keep.append(e)

    if not removed:
        print("✅ 제거할 항목 없음 — 이미 정리됨 (멱등 skip)")
        return 0

    data["entries"] = keep
    LEDGER_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"✅ ledger 정리 완료 — {len(removed)}개 제거 (잔여 {len(keep)}개):")
    for e in removed:
        print(f"  - {e.get('topic_id')} (posted_at={e.get('posted_at')}, "
              f"ig_media_id={e.get('ig_media_id')})")
    print("→ 이후 orchestrator catch-up 이 r4_finalize → publish R2 순서로 재게시")
    return 0


if __name__ == "__main__":
    sys.exit(main())
