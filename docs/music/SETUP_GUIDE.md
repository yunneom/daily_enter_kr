# abc 송 → IG/YT 음원 노출 셋업 가이드 (Option A)

@sunnyandgigi 의 abc 송을 daily_enter_kr 자동 게시의 배경음악으로 쓰고,
음원 노출로 YT 풀버전 트래픽을 유도하는 전체 절차.

---

## ⚠️ 먼저 알아야 할 기술적 사실 (정직하게)

**IG Graph API 는 "오디오 라이브러리 음원 선택"을 지원하지 않는다.**
자동 게시(daily_enter_kr)는 mp4 에 **합성(embed)된 음원**만 쓸 수 있고,
"@sunnyandgigi 원본 오디오를 라이브러리에서 골라 붙이기"는 API 로 불가능하다.

→ 그래서 **2중 경로**로 노출한다:

| 경로 | 작동 | 확실성 |
|---|---|---|
| ① mp4 에 abc.mp3 합성 + 캡션/댓글/YT설명에 **풀버전 링크 텍스트** | 코드 자동 | ✅ 100% |
| ② IG 가 같은 오디오 fingerprint 를 @sunnyandgigi 원본오디오로 **자동 매칭** | IG 내부 | ⚠️ 불확실 — 게시 후 육안 확인 |

①이 메인(확실), ②는 보너스. ②가 매칭되면 음원 라벨까지 귀속되어 더 강력.
게시 1주 후 daily_enter_kr reel 의 음원 라벨이 @sunnyandgigi 로 뜨는지 직접 확인.

---

## 검토 결과 — 노출 / 저작권 / ContentID

| 항목 | 판정 | 근거 |
|---|---|---|
| **저작권** | ✅ 문제 0 | 본인 곡. IG ToS·YT 모두 OK |
| **ContentID** | ✅ 현재 0 | 미발매·미등록 → 클레임 없음. 단 **배급 발매하면** 그때부터 daily_enter_kr 가 자기 곡에 클레임 받음 → 배급사 대시보드에서 daily_enter_kr 채널 **화이트리스트** 필요 |
| **노출(트래픽)** | ✅ 경로 확보 | YT설명/IG캡션/댓글 풀버전 링크(확실) + 음원 라벨 매칭(보너스) |
| **아동용 태그** | ⚠️ 확인 | @sunnyandgigi YT 가 "아동용"이면 댓글·맞춤광고 차단. 음원 노출엔 무관하나, 곡 톤이 daily_enter_kr(K-연예) 와 맞는지 별도 판단 |

### 🔴 톤 적합성 — 결정 필요
daily_enter_kr 는 K-연예/밸런스게임 채널. abc 송이 동요/키즈 톤이면 **톤 미스매치** 위험
(케이팝 티어 매트릭스에 동요 BGM = 어색). 곡이 어떤 톤인지 알려주면:
- 잘 맞으면(칠/EDM/팝) → 전곡 전용 OK
- 안 맞으면 → instrumental 구간만 잘라 쓰거나, 특정 토픽(육아 `child_pick_100man` 등)에만 매칭

---

## 🏠 집(PC)에서 할 일 — 순서대로

### STEP 1. abc 송 파일 준비 (5분)
- 마스터 음원을 `.wav` 또는 `320kbps mp3` 로 준비
- daily_enter_kr BGM 용으로는 mp3 1곡 (A송 권장 — 가장 자신 있는 곡)

### STEP 2. YouTube(@sunnyandgigi) 풀버전 업로드 (10분)
1. studio.youtube.com → 만들기 → 동영상 업로드
2. 제목·설명·태그 = `docs/music/A_<곡명>.md` 의 **1) YouTube** 블록 복붙
   (이 파일은 곡 정보 채운 뒤 `python scripts/generate_music_metadata.py` 로 생성)
3. 업로드 후 **영상 URL 복사** (예: `https://youtu.be/abcd1234`) — STEP 5 에서 씀
4. (선택) "아동용" 설정 검토 — 음원 노출엔 무관

### STEP 3. Instagram(@sunnyandgigi.official) Reels 재업로드 + 원본오디오 부트스트랩 (10분)
1. STEP 2 영상(또는 짧은 버전)을 **폰 IG 앱**에서 Reels 게시
   - ⚠️ Graph API 아님 — 반드시 **앱에서 직접** (원본오디오 등록 위해)
2. 음원 = abc.mp3 (앱에서 "원본 오디오"로 인식됨)
3. 캡션 = `docs/music/A_<곡명>.md` 의 **2) Instagram** 블록 복붙
4. 게시 후 reel 의 🎵 아이콘 탭 → **"@sunnyandgigi · 원본 오디오"** 라벨 확인
5. **프로필 bio 갱신**: `🎵 풀버전 ▶ youtu.be/abcd1234`

### STEP 4. abc.mp3 를 저장소에 추가 (코드 — 채팅에 파일 주면 내가 함)
- 채팅에 mp3 첨부 → 내가 `assets/bgm/abc_song.mp3` 커밋
- 전용 모드: 기존 ambient 3종 → `assets/bgm/_backup/` 이동
- 음원 톤 보고 `BGM_VOLUME` 조정 (vocal 강하면 0.25)

### STEP 5. GitHub Secrets 3개 등록 (5분) — 음악 크레딧 자동 노출
github.com/yunneom/daily_enter_kr/settings/secrets/actions → New secret:

| Secret | 값 |
|---|---|
| `MUSIC_YT_URL` | STEP 2 의 YT 링크 (예: `https://youtu.be/abcd1234`) |
| `MUSIC_TITLE` | 곡명 (예: `ABC송`) |
| `MUSIC_HANDLE` | `@sunnyandgigi` |

→ 다음 cron 게시부터 daily_enter_kr 캡션·댓글·YT설명에 자동으로:
```
🎵 배경음악: ABC송 — @sunnyandgigi
   풀버전 ▶ https://youtu.be/abcd1234
```
(Secret 미설정 시 아무 변화 없음 — 안전)

### STEP 6. (1주 후) 매칭 확인
- daily_enter_kr 자동 게시 reel 의 🎵 라벨이 @sunnyandgigi 로 뜨는지 확인
- 뜨면 ②경로 성공 (보너스). 안 떠도 ①경로(텍스트 링크)는 작동 중
- `docs/digests/cross_platform.html` 에서 profile_views·website_clicks 추세 확인

---

## 메타데이터 생성 (곡 정보 채우면 자동)

```bash
cp data/music_tracks.example.json data/music_tracks.json
# data/music_tracks.json 에 A~O 15곡 정보 채우기 (제목/장르/무드/테마)
python scripts/generate_music_metadata.py
# → docs/music/A_*.md ~ O_*.md 생성 (YT/IG/배급사 메타 복붙용)
```

곡 정보를 채팅에 주면 내가 직접 작성해줄 수도 있음 (장르·분위기·가사·테마).

---

## 배급(발매) — 별도 세션

15곡 → 3곡 EP × 매월 5개월 전략은 유튜브 채널 세션 핸드오프 참고.
**발매 시점에 반드시**: 배급사 대시보드에서 daily_enter_kr YT 채널을 ContentID
화이트리스트에 추가 (안 하면 자기 곡에 클레임).
