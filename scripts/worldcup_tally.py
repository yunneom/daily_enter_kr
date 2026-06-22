"""
월드컵 라운드 댓글 집계 봇 — 게시글별 IG 댓글 파싱 → 매치별 winner 결정 → 다음 라운드 페어링.

[흐름]
1. worldcup_bracket.json 의 현재 라운드 매치별 ig_media_id 조회
2. 각 media_id 의 댓글 IG Graph API 로 pagination 수집
3. 첫 등장 1·2·3·4 (또는 1️⃣~4️⃣) 파싱 → 사용자별 1표
4. 4지선다 → 매치별 winner 추출:
   - 매치1.A votes = count(1) + count(2)  /  매치1.B votes = count(3) + count(4)
   - 매치2.A votes = count(1) + count(3)  /  매치2.B votes = count(2) + count(4)
5. winner 결정 → bracket json 의 round.matches[].winner 채움
6. 다음 라운드 페어링 자동 생성 (build_next_round)

[입력]
  ROUND=R32 (집계할 라운드)
  INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID (Actions secret)

[출력]
  worldcup_bracket.json 업데이트:
    - 현재 라운드 matches[i].votes = {raw: {"1":N,"2":N,"3":N,"4":N}, m1_a/b: ..., m2_a/b: ...}
    - 현재 라운드 matches[i].winner = {"member": ..., "group": ..., "rank": ...}
    - 다음 라운드 (R16/R8/R4/R2/R1) posts/matches 자동 생성

[댓글 파싱 룰 — 봇/스팸 방어 약하지만 명확]
- 첫 등장 숫자 1·2·3·4 만 카운트 (또는 1️⃣·2️⃣·3️⃣·4️⃣)
- 사용자별 1표 (마지막 댓글 채택)
- 50자 초과 = 스킵
- 동률 시 tiebreak = 좋아요 수 보조 (raw counts 동률 시 좋아요 합산)
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

BRACKET_PATH = ROOT / "data" / "worldcup_bracket.json"
LEDGER_PATH = ROOT / "post_ledger.json"
GRAPH = "https://graph.instagram.com/v22.0"
KST = timezone(timedelta(hours=9))

# 1·2·3·4 또는 emoji 1️⃣~4️⃣ — 댓글 첫 등장 매칭
EMOJI_TO_NUM = {"1️⃣": "1", "2️⃣": "2", "3️⃣": "3", "4️⃣": "4"}
VOTE_RE = re.compile(r"(?:^|\s)([1-4])(?:번|픽|\D|$)")


def parse_vote(text: str) -> Optional[str]:
    """댓글 텍스트 → '1'·'2'·'3'·'4' 중 하나, 또는 None.
    너무 긴 텍스트(50자+) = invalid."""
    if not text:
        return None
    if len(text) > 50:
        return None
    # 이모지 우선
    for em, n in EMOJI_TO_NUM.items():
        if em in text:
            return n
    # 텍스트 첫 등장 1·2·3·4
    s = text.strip()
    if s and s[0] in "1234":
        return s[0]
    # boundary 매칭
    m = VOTE_RE.search(" " + s)
    if m:
        return m.group(1)
    return None


def fetch_all_comments(media_id: str, token: str) -> List[Dict]:
    """IG /{media_id}/comments — pagination 모두 수집."""
    out = []
    url = f"{GRAPH}/{media_id}/comments"
    params = {
        "fields": "id,text,username,like_count,timestamp",
        "limit": 100,
        "access_token": token,
    }
    while True:
        resp = requests.get(url, params=params, timeout=20)
        if not resp.ok:
            print(f"  ⚠️  comments fetch fail {media_id}: HTTP {resp.status_code}")
            break
        data = resp.json()
        out.extend(data.get("data", []))
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        url = nxt
        params = {}  # next URL 에 이미 모든 파라미터 포함
        time.sleep(0.3)
    return out


def tally_post(media_id: str, token: str) -> Dict:
    """게시글 1개 → 1·2·3·4 카운트 + 사용자 dedup."""
    comments = fetch_all_comments(media_id, token)
    user_vote = {}        # username → '1'·'2'·'3'·'4' (마지막 댓글 채택)
    user_like_weight = {} # username → sum of likes on their voting comments (tiebreak 용)
    raw_comments = len(comments)

    # IG 가 최신순으로 줘서 그대로 순회하면서 사용자별 마지막 표 == 가장 처음 본 표
    # 안정성 위해 timestamp 오름차순(=오래된→최신) 재정렬 후 덮어쓰기
    def _ts(c):
        return c.get("timestamp", "")
    for c in sorted(comments, key=_ts):
        user = c.get("username", "anon")
        text = c.get("text") or ""
        v = parse_vote(text)
        if not v:
            continue
        user_vote[user] = v
        user_like_weight[user] = user_like_weight.get(user, 0) + (c.get("like_count") or 0)

    counts = {"1": 0, "2": 0, "3": 0, "4": 0}
    like_w = {"1": 0, "2": 0, "3": 0, "4": 0}
    for user, v in user_vote.items():
        counts[v] += 1
        like_w[v] += user_like_weight.get(user, 0)
    return {
        "raw_comments": raw_comments,
        "valid_votes": len(user_vote),
        "counts": counts,
        "like_w": like_w,
    }


def decide_winners(match1: Dict, match2: Dict, counts: Dict, like_w: Dict) -> Tuple[Dict, Dict, Dict]:
    """4지선다 → 매치1·2 winner. 동률시 like_w 로 tiebreak.

    Returns: (m1_votes, m2_votes, winners) — winners = {"m1": Dict, "m2": Dict}
    """
    # 매치1: A(1+2) vs B(3+4)
    m1_a_votes = counts["1"] + counts["2"]
    m1_b_votes = counts["3"] + counts["4"]
    # 매치2: A(1+3) vs B(2+4)
    m2_a_votes = counts["1"] + counts["3"]
    m2_b_votes = counts["2"] + counts["4"]

    def pick(a, b, lw_a, lw_b, m):
        if a > b: return m["a"]
        if b > a: return m["b"]
        # tiebreak — like_w
        if lw_a >= lw_b: return m["a"]
        return m["b"]

    m1_winner = pick(m1_a_votes, m1_b_votes,
                     like_w["1"] + like_w["2"], like_w["3"] + like_w["4"], match1)
    m2_winner = pick(m2_a_votes, m2_b_votes,
                     like_w["1"] + like_w["3"], like_w["2"] + like_w["4"], match2)

    m1_votes = {"a": m1_a_votes, "b": m1_b_votes}
    m2_votes = {"a": m2_a_votes, "b": m2_b_votes}
    return m1_votes, m2_votes, {"m1": m1_winner, "m2": m2_winner}


def load_ledger() -> Dict[str, str]:
    """post_ledger.json → topic_id (또는 worldcup_post_key) → ig_media_id 매핑.
    월드컵 게시는 topic_id 가 worldcup_{round}_{post_idx} 형태로 기록되어 있어야."""
    if not LEDGER_PATH.exists():
        return {}
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for e in data.get("entries", []):
        tid = e.get("topic_id", "")
        mid = e.get("ig_media_id")
        if tid and mid:
            out[tid] = mid
    return out


def round_seq(rnd: str) -> List[str]:
    """라운드 순서. 다음 라운드 키 자동 결정."""
    seq = ["R32", "R16", "R8", "R4", "R2", "R1"]
    return seq


def next_round_key(cur: str) -> Optional[str]:
    seq = round_seq(cur)
    if cur not in seq:
        return None
    i = seq.index(cur)
    if i + 1 >= len(seq):
        return None
    return seq[i + 1]


def build_next_round(bracket: Dict, cur_round: str) -> bool:
    """현재 라운드 winners → 다음 라운드 페어링 자동 생성.
    매치 페어링 룰: 같은 quarter 안에서 slot 0vs1, 2vs3 (월드컵 표준).
    """
    cur = bracket["rounds"][cur_round]
    matches = cur.get("matches", [])
    if any(m.get("winner") is None for m in matches):
        print(f"⚠️  {cur_round} 일부 매치 winner 미정 — 다음 라운드 빌드 보류")
        return False
    nxt_key = next_round_key(cur_round)
    if not nxt_key:
        print(f"🏆 {cur_round} 가 마지막 라운드 — 토너먼트 완료")
        bracket["winner"] = matches[0]["winner"]
        return True

    # 다음 라운드 매치 = 같은 quarter 안 인접 매치 winner 끼리 페어
    # cur 의 matches 는 quarter (0..3) × slot (0..3) 순회로 16개 (R32) → 다음 R16 은 8매치
    # 또는 quarter 0..3 × slot (0..1) for R16 → 4매치 (R8) ...
    # 일반화: 두 매치 winner 가 1 새 매치 → 매치 수 절반
    new_matches = []
    for i in range(0, len(matches), 2):
        m_a = matches[i]
        m_b = matches[i + 1]
        new_matches.append({
            "quarter": m_a["quarter"],
            "slot": i // 2,
            "round": nxt_key,
            "a": m_a["winner"],
            "b": m_b["winner"],
            "winner": None,
        })
    # 게시글 페어링 — 매트릭스처럼 (다른 quarter 끼리) 또는 같은 brackets 끼리
    # 단순화: 라운드별 게시글 수 표준
    # R16 → 4 게시(2매치 콤비), R8 → 2 게시, R4 → 1 게시 (4매치는 X — 2매치만 남음)
    # R2(결승+3위전) → 2 게시 (1:1 단순), R1(우승발표) → 결과 카드
    posts = []
    if nxt_key in ("R16", "R8", "R4"):
        # 2매치 콤비 패턴. 같은 quarter 의 매치는 같은 게시 X (결승까지 안 만나야 한다는 원칙은
        # R32 에서만 의미 — 이후 라운드는 자유. 다만 동일 1/4 매치는 한 게시에 묶지 않도록 분산)
        n_matches = len(new_matches)
        # 단순: 매치 0+(n/2), 1+(n/2+1), ... 페어
        half = n_matches // 2
        if half == 0:
            # R4 는 매치 2개 — 1 게시에 콤비
            posts.append({"post_idx": 0, "match1": new_matches[0], "match2": new_matches[1]})
        else:
            for i in range(half):
                posts.append({"post_idx": i, "match1": new_matches[i], "match2": new_matches[i + half]})
    elif nxt_key == "R2":
        # 결승전 + 3·4위전 — 1:1 단순 매치 2 게시. 콤비 패턴 X.
        # 4강 winner 2명 → 결승, 4강 loser 2명 → 3·4위전
        # 단 cur(R4) 는 매치 2개에 winner 만 들어있음 (loser 정보 없음).
        # → R4 matches 에 loser 도 채워 둠 (build_next_round 가 호출 전에 채워야)
        # 간단화: R4 → R2 빌드는 별도 처리 함수에서.
        return _build_finals(bracket, cur_round, nxt_key, new_matches)
    elif nxt_key == "R1":
        # 우승 발표 카드 — 매치 없음
        bracket["winner"] = new_matches[0]["winner"]
        bracket["rounds"][nxt_key] = {"matches": [], "posts": [], "winner": new_matches[0]["winner"]}
        return True

    bracket["rounds"][nxt_key] = {"matches": new_matches, "posts": posts}
    bracket["current_round"] = nxt_key
    return True


def _build_finals(bracket, cur_round, nxt_key, new_finals):
    """R4 winners → 결승 1매치, R4 losers → 3·4위전 1매치. 2 게시 (1:1 단순)."""
    r4 = bracket["rounds"][cur_round]
    matches_r4 = r4.get("matches", [])
    if len(matches_r4) != 2:
        print(f"⚠️  R4 matches 가 2개여야 함 (현재 {len(matches_r4)})")
        return False
    # 결승 = new_finals (R4 winners)
    final_match = {
        "round": "R2", "type": "final",
        "a": new_finals[0]["a"], "b": new_finals[1]["a"],
        "winner": None,
    }
    # 3·4위전 = R4 losers
    losers = []
    for m in matches_r4:
        w = m.get("winner")
        loser = m["b"] if w == m["a"] else m["a"]
        losers.append(loser)
    third_match = {
        "round": "R2", "type": "third_place",
        "a": losers[0], "b": losers[1],
        "winner": None,
    }
    posts = [
        {"post_idx": 0, "match1": third_match, "match2": third_match, "type": "third_place_solo"},
        {"post_idx": 1, "match1": final_match, "match2": final_match, "type": "final_solo"},
    ]
    bracket["rounds"][nxt_key] = {
        "matches": [third_match, final_match],
        "posts": posts,
    }
    bracket["current_round"] = nxt_key
    return True


def main():
    if len(sys.argv) > 1:
        round_key = sys.argv[1]
    else:
        round_key = os.environ.get("ROUND", "R32")

    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("❌ INSTAGRAM_ACCESS_TOKEN 미설정")
        return 1

    bracket = json.loads(BRACKET_PATH.read_text(encoding="utf-8"))
    if round_key not in bracket["rounds"]:
        print(f"❌ {round_key} 라운드 없음")
        return 1
    rnd = bracket["rounds"][round_key]
    posts = rnd.get("posts", [])
    matches = rnd.get("matches", [])

    ledger = load_ledger()

    print(f"=== {round_key} 댓글 집계 시작 ({len(posts)} 게시글, {len(matches)} 매치) ===")
    # 게시글 단위로 댓글 수집 + 매치 1·2 winner 결정
    for post in posts:
        idx = post["post_idx"]
        # ledger 에서 ig_media_id 조회 (topic_id = worldcup_{round}_{idx})
        tid = f"worldcup_{round_key.lower()}_{idx + 1}"
        media_id = ledger.get(tid)
        if not media_id:
            print(f"  ⚠️  post #{idx+1} ({tid}) ig_media_id 미상 — 스킵")
            continue
        tally = tally_post(media_id, token)
        m1 = post["match1"]; m2 = post["match2"]
        m1_v, m2_v, winners = decide_winners(m1, m2, tally["counts"], tally["like_w"])
        # matches 안의 해당 매치 객체에 winner 기록
        m1["winner"] = winners["m1"]
        m2["winner"] = winners["m2"]
        m1["votes"] = m1_v
        m2["votes"] = m2_v
        post["tally"] = {
            "raw_comments": tally["raw_comments"],
            "valid_votes": tally["valid_votes"],
            "counts": tally["counts"],
        }
        print(f"  post #{idx+1}: 댓글 {tally['raw_comments']} (유효 {tally['valid_votes']}) "
              f"1={tally['counts']['1']} 2={tally['counts']['2']} "
              f"3={tally['counts']['3']} 4={tally['counts']['4']}")
        print(f"    매치1: {m1['a']['member']}({m1_v['a']}) vs {m1['b']['member']}({m1_v['b']}) → "
              f"승: {winners['m1']['member']}")
        print(f"    매치2: {m2['a']['member']}({m2_v['a']}) vs {m2['b']['member']}({m2_v['b']}) → "
              f"승: {winners['m2']['member']}")

    # 다음 라운드 자동 빌드
    print(f"\n=== 다음 라운드 페어링 생성 ===")
    build_next_round(bracket, round_key)

    # 저장
    BRACKET_PATH.write_text(json.dumps(bracket, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print(f"✅ {BRACKET_PATH.relative_to(ROOT)} 갱신")
    if bracket.get("winner"):
        w = bracket["winner"]
        print(f"\n🏆 토너먼트 우승: {w['member']} ({w['group']})!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
