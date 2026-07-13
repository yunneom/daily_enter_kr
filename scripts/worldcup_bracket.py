"""
걸그룹 월드컵 — 32강 시드 배정 + 페어링 생성.

[시드 룰 — FIFA 월드컵식]
- TOP1-4: 절대 같은 1/4 브라켓 불가 (결승전까지 못 만남)
- TOP5-8: 4개 1/4 브라켓에 분산 (8강까지 안 만남)
- TOP9-16: 각 1/8 브라켓에 분산 (16강까지 안 만남)
- TOP17-32: 시드 + 랜덤

[페어링]
32강 = 16매치. 게시글당 2매치 콤비네이션 4지선다 = 8게시글.
같은 게시글의 두 매치는 결승까지 만나지 않는 다른 1/4 브라켓에서 추출
(시청자가 두 매치 모두 응원해도 OK = 토론·재시도 ↑).

[출력]
data/worldcup_bracket.json — 브라켓 + 페어링 + 라운드별 진행 상태
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TOP100_PATH = ROOT / "data" / "girlgroup_brand_rep_top100.json"
BRACKET_PATH = ROOT / "data" / "worldcup_bracket.json"

SEED_RANDOM = 20260714  # 시즌2 — 이전과 다른 대진(결정론적 재현)


def build_32_seeds():
    """32명 시드 배정 — 1-32위.
    32강 브라켓을 4개 1/4 (각 8명) 으로 나눔.
    1/4 = [Q1, Q2, Q3, Q4].
    """
    data = json.loads(TOP100_PATH.read_text(encoding="utf-8"))
    ranks = data["rankings"][:32]
    rng = random.Random(SEED_RANDOM)

    # 4개 1/4 브라켓
    quarters = [[], [], [], []]

    # POT1: TOP1-4 → 각 1/4 에 1명씩 (1 → Q1, 2 → Q4 — 결승에서 만남)
    # 월드컵 룰: TOP1 vs TOP2 가 결승, TOP3 vs TOP4 가 3·4위전
    # 즉 Q1=TOP1, Q4=TOP2, Q2=TOP3, Q3=TOP4 (의도된 cross)
    pot1_order = [0, 3, 2, 1]  # 1→Q1, 4→Q2, 3→Q3, 2→Q4 — TOP1↔TOP2 결승
    for i in range(4):
        quarters[pot1_order[i]].append(ranks[i])

    # POT2: TOP5-8 → 각 1/4 에 1명씩 분배 (랜덤 셔플 후 1:1)
    pot2 = ranks[4:8]
    rng.shuffle(pot2)
    for i in range(4):
        quarters[i].append(pot2[i])

    # POT3: TOP9-16 → 각 1/4 에 2명씩 (8명 ÷ 4 = 2)
    pot3 = ranks[8:16]
    rng.shuffle(pot3)
    for i, p in enumerate(pot3):
        quarters[i % 4].append(p)

    # POT4: TOP17-32 → 각 1/4 에 4명씩 (16명 ÷ 4 = 4)
    pot4 = ranks[16:32]
    rng.shuffle(pot4)
    for i, p in enumerate(pot4):
        quarters[i % 4].append(p)

    return quarters  # 각 1/4 에 정확히 8명


def build_32_matches(quarters):
    """각 1/4 (8명) → 1라운드 매치 4개. 시드 1번 vs 시드 8번 (가장 약한)
    형식이 아니라, 1/4 안에서도 POT 간 매칭 = 시드 1번 vs 마지막 POT4 1명.

    1/4 의 8명 = [P1, P2, P3, P4_a, P4_b, P4_c, P4_d, P3_b]
    실제 quarters[i] = [pot1_1명, pot2_1명, pot3_2명, pot4_4명]
    = 8명. 매치 = (idx0 vs idx7), (idx1 vs idx6), (idx2 vs idx5), (idx3 vs idx4).
    """
    all_matches = []
    for qi, q in enumerate(quarters):
        assert len(q) == 8, f"1/4 브라켓 {qi} 크기 {len(q)} (8 필요)"
        # 4 매치 — 양 끝 매칭 = pot1 vs pot4 첫번째, pot2 vs pot4 마지막 ...
        for i in range(4):
            a = q[i]
            b = q[7 - i]
            all_matches.append({
                "quarter": qi,         # 0-3, 같은 quarter 는 같은 1/4 = 결승까지 안 만남
                "slot": i,             # 1/4 안 매치 위치 (다음 라운드 진행용)
                "round": "R32",
                "a": a, "b": b,
                "winner": None,        # 라운드 종료 후 댓글 집계로 채움
            })
    return all_matches  # 16 매치


def pair_posts(matches):
    """게시글당 2매치 콤비. 같은 게시글의 두 매치는 다른 1/4 브라켓에서.

    16매치 → 8게시글. 게시글 = quarter 0 매치 + quarter 2 매치 / quarter 1 + 3 …
    즉 서로 결승까지 만나지 않는 1/4 끼리 묶음.
    """
    by_q = {0: [], 1: [], 2: [], 3: []}
    for m in matches:
        by_q[m["quarter"]].append(m)

    posts = []
    # Q0-Q2 페어 4건, Q1-Q3 페어 4건
    for i in range(4):
        posts.append({"post_idx": i,     "match1": by_q[0][i], "match2": by_q[2][i]})
        posts.append({"post_idx": i + 4, "match1": by_q[1][i], "match2": by_q[3][i]})
    return posts


def build():
    quarters = build_32_seeds()
    matches = build_32_matches(quarters)
    posts = pair_posts(matches)

    bracket = {
        "tournament": "걸그룹 월드컵 (32강)",
        "source": "한국기업평판연구소 2026.6.21",
        "seed_method": "TOP1-4 분산 → 5-8 분산 → 9-16 분산 → 17-32 시드+랜덤",
        "deterministic_seed": SEED_RANDOM,
        "quarters": [
            [{"rank": p["rank"], "group": p["group"], "member": p["member"]}
             for p in q] for q in quarters
        ],
        "rounds": {
            "R32": {
                "matches": matches,
                "posts": posts,  # 8개 게시글 — 매트릭스 자동화에 사용
            },
            # R16, R8, R4, R2, R1 은 R32 결과 들어오면 build_next_round() 가 채움
        },
        "current_round": "R32",
        "winner": None,
    }
    BRACKET_PATH.write_text(json.dumps(bracket, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return bracket


def print_summary(bracket):
    print(f"=== {bracket['tournament']} ===")
    print(f"출처: {bracket['source']}")
    print(f"시드: {bracket['seed_method']}")
    print()
    print("📋 1/4 브라켓 (각 8명):")
    for qi, q in enumerate(bracket["quarters"]):
        print(f"\n  Q{qi+1}:")
        for p in q:
            print(f"    #{p['rank']:>3} {p['group']} {p['member']}")
    print()
    print("🎯 32강 16매치 (게시글 8개 × 2매치 콤비):")
    for post in bracket["rounds"]["R32"]["posts"]:
        m1 = post["match1"]; m2 = post["match2"]
        print(f"\n  📱 게시글 #{post['post_idx']+1}")
        print(f"     매치1 [Q{m1['quarter']+1}]: "
              f"#{m1['a']['rank']} {m1['a']['member']}({m1['a']['group']}) "
              f"vs #{m1['b']['rank']} {m1['b']['member']}({m1['b']['group']})")
        print(f"     매치2 [Q{m2['quarter']+1}]: "
              f"#{m2['a']['rank']} {m2['a']['member']}({m2['a']['group']}) "
              f"vs #{m2['b']['rank']} {m2['b']['member']}({m2['b']['group']})")


if __name__ == "__main__":
    bracket = build()
    print_summary(bracket)
    print(f"\n✅ {BRACKET_PATH.relative_to(ROOT)} 저장 완료")
