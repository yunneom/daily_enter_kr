"""
TTS (Text-to-Speech) 프레임워크 — Korean 보이스오버 합성.

[설계]
- Provider 추상화: OpenAI / Google Cloud TTS / 무 (off)
- 환경변수 TTS_PROVIDER 로 선택. 미설정 시 off (BGM-only 동작 유지)
- 각 카드 제목 → mp3 → 카드 노출 시간에 맞춰 mix

[비용 (대략 2026 기준)]
- OpenAI tts-1: $15 / 1M chars (~ 200 카드/일 × 30자 = 6000자/일 → $0.09/일)
- Google Cloud TTS Standard: $4 / 1M chars
- Google Cloud TTS WaveNet: $16 / 1M chars (고품질)

[환경변수]
- TTS_PROVIDER = "openai" | "google" | "off"
- OPENAI_API_KEY (openai 시)
- GOOGLE_APPLICATION_CREDENTIALS (google 시; JSON 파일 경로) — 또는 GOOGLE_TTS_API_KEY

[OFF 기본값]
TTS 미사용 시 호출자는 None 반환 받고 BGM-only mp4 생성. 호환성 유지.
"""

import os
from pathlib import Path
from typing import Optional, List
import requests


def is_enabled() -> bool:
    return os.environ.get("TTS_PROVIDER", "off").lower() in ("openai", "google")


def synthesize_korean(text: str, output_path: Path, voice: Optional[str] = None) -> Optional[Path]:
    """텍스트 → mp3. 실패/미설정 시 None.

    Args:
        text: 합성 대상 (한글)
        output_path: 저장 경로 (.mp3)
        voice: provider 별 voice id (옵션)
    Returns: output_path 또는 None
    """
    provider = os.environ.get("TTS_PROVIDER", "off").lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if provider == "openai":
        return _synthesize_openai(text, output_path, voice or "nova")
    if provider == "google":
        return _synthesize_google(text, output_path, voice or "ko-KR-Wavenet-A")
    return None


def _synthesize_openai(text: str, output_path: Path, voice: str) -> Optional[Path]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    url = "https://api.openai.com/v1/audio/speech"
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,  # nova / shimmer / alloy / echo / fable / onyx
        "response_format": "mp3",
    }
    try:
        resp = requests.post(url,
                             headers={"Authorization": f"Bearer {api_key}",
                                      "Content-Type": "application/json"},
                             json=payload, timeout=30)
        if not resp.ok:
            print(f"⚠️  OpenAI TTS HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        output_path.write_bytes(resp.content)
        return output_path
    except Exception as e:
        print(f"⚠️  OpenAI TTS 오류: {e}")
        return None


def _synthesize_google(text: str, output_path: Path, voice: str) -> Optional[Path]:
    """Google Cloud TTS — API key 또는 service account 둘 다 지원."""
    api_key = os.environ.get("GOOGLE_TTS_API_KEY")
    if not api_key:
        return None
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "ko-KR", "name": voice},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if not resp.ok:
            print(f"⚠️  Google TTS HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        import base64
        audio_b64 = resp.json().get("audioContent", "")
        output_path.write_bytes(base64.b64decode(audio_b64))
        return output_path
    except Exception as e:
        print(f"⚠️  Google TTS 오류: {e}")
        return None


def synthesize_card_titles(titles: List[str], output_dir: Path,
                           prefix: str = "tts") -> List[Optional[Path]]:
    """N개 제목을 N개 mp3 로. None 항목은 합성 실패/스킵."""
    paths = []
    for i, t in enumerate(titles):
        out = output_dir / f"{prefix}_{i+1:02d}.mp3"
        result = synthesize_korean(t, out)
        paths.append(result)
    return paths
