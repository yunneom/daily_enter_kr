"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { memberImageUrl } from "@/lib/memberImages";
import { groupColor, shade } from "@/lib/colors";

/**
 * 완주 공유 카드 — client-side canvas render (1080x1920, 9:16 for IG story).
 *
 * Photo path mirrors MemberImage's source chain, loaded with
 * crossOrigin="anonymous" (upload.wikimedia.org sends CORS headers). If no
 * source loads clean — or the canvas would be tainted — we fall back to an
 * initial-in-circle rendering so export always works.
 */

interface Props {
  rank: number;
  group: string;
  member: string;
  /** live share-of-champions pct for this member, or null when unknown */
  pct: number | null;
  onClose: () => void;
}

const W = 1080;
const H = 1920;
const SHARE_URL = "https://dailyenterkr.com/play?utm_source=share";

function photoSources(rank: number): string[] {
  const list: string[] = [];
  const explicit = memberImageUrl(rank);
  if (explicit) list.push(explicit);
  list.push(`/members/${rank}.jpg`, `/members/${rank}.png`, `/members/${rank}.webp`);
  return list;
}

function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

async function loadFirstImage(rank: number): Promise<HTMLImageElement | null> {
  for (const src of photoSources(rank)) {
    const img = await loadImage(src);
    if (img && img.naturalWidth > 0) return img;
  }
  return null;
}

function isTainted(canvas: HTMLCanvasElement): boolean {
  try {
    canvas.getContext("2d")?.getImageData(0, 0, 1, 1);
    return false;
  } catch {
    return true;
  }
}

function toBlob(canvas: HTMLCanvasElement): Promise<Blob | null> {
  return new Promise((resolve) => {
    try {
      canvas.toBlob((b) => resolve(b), "image/png");
    } catch {
      resolve(null);
    }
  });
}

export default function ShareCard({ rank, group, member, pct, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const draw = useCallback(
    (photo: HTMLImageElement | null) => {
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;

      const base = groupColor(group);

      // background — group color gradient with a dark floor for text contrast
      const grad = ctx.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, shade(base, 8));
      grad.addColorStop(0.55, shade(base, -30));
      grad.addColorStop(1, "#0b0b12");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // top label
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      ctx.font = "700 46px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
      ctx.fillText("나의 우승 픽", W / 2, 300);

      // photo circle
      const cx = W / 2;
      const cy = 770;
      const r = 310;
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.closePath();
      ctx.clip();
      if (photo) {
        // cover-fit the image into the circle's bounding square
        const d = r * 2;
        const scale = Math.max(d / photo.naturalWidth, d / photo.naturalHeight);
        const dw = photo.naturalWidth * scale;
        const dh = photo.naturalHeight * scale;
        ctx.drawImage(photo, cx - dw / 2, cy - dh / 2, dw, dh);
      } else {
        // initial-in-circle fallback
        ctx.fillStyle = shade(base, -18);
        ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
        ctx.fillStyle = "rgba(255,255,255,0.92)";
        ctx.font = "900 300px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
        ctx.textBaseline = "middle";
        ctx.fillText(member.slice(0, 1), cx, cy + 16);
        ctx.textBaseline = "alphabetic";
      }
      ctx.restore();

      // ring around the photo
      ctx.beginPath();
      ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
      ctx.lineWidth = 10;
      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.stroke();

      // champion name (huge)
      ctx.fillStyle = "#ffffff";
      const nameSize = member.length > 4 ? 128 : 156;
      ctx.font = `900 ${nameSize}px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif`;
      ctx.fillText(member, W / 2, 1290);

      // group tag (pill)
      ctx.font = "700 52px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
      const tagW = ctx.measureText(group).width + 88;
      const tagH = 96;
      const tagY = 1360;
      ctx.fillStyle = "rgba(255,255,255,0.16)";
      if (typeof ctx.roundRect === "function") {
        ctx.beginPath();
        ctx.roundRect(W / 2 - tagW / 2, tagY, tagW, tagH, 48);
        ctx.fill();
      } else {
        ctx.fillRect(W / 2 - tagW / 2, tagY, tagW, tagH);
      }
      ctx.fillStyle = "rgba(255,255,255,0.95)";
      ctx.fillText(group, W / 2, tagY + 66);

      // live stat line
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.font = "700 54px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
      const statLine =
        pct != null ? `전체 참여자 중 ${pct}%가 같은 픽` : "지금 실시간 집계 확인";
      ctx.fillText(statLine, W / 2, 1610);

      // footer
      ctx.fillStyle = "rgba(255,255,255,0.6)";
      ctx.font = "600 42px 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
      ctx.fillText("dailyenterkr.com · @daily_enter_kr", W / 2, 1800);
    },
    [group, member, pct],
  );

  // Render on mount: try the photo chain, then verify the canvas is still
  // exportable; if tainted, redraw with the initial fallback.
  useEffect(() => {
    let alive = true;
    (async () => {
      const photo = await loadFirstImage(rank);
      if (!alive) return;
      draw(photo);
      const canvas = canvasRef.current;
      if (photo && canvas && isTainted(canvas)) {
        draw(null);
      }
      setReady(true);
    })();
    return () => {
      alive = false;
    };
  }, [rank, draw]);

  const exportBlob = useCallback(async (): Promise<Blob | null> => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    let blob = await toBlob(canvas);
    if (!blob) {
      // last-resort: taint slipped through — redraw without the photo and retry
      draw(null);
      blob = await toBlob(canvas);
    }
    return blob;
  }, [draw]);

  const save = useCallback(async () => {
    setMsg(null);
    const blob = await exportBlob();
    if (!blob) {
      setMsg("이미지 생성에 실패했습니다. 다시 시도해 주세요.");
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `worldcup-pick-${member}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 4000);
    setMsg("이미지를 저장했습니다.");
  }, [exportBlob, member]);

  const share = useCallback(async () => {
    setMsg(null);
    const text = `나의 우승 픽은 ${member}. 걸그룹 이상형 월드컵 ${SHARE_URL}`;
    try {
      const blob = await exportBlob();
      if (blob && typeof navigator.canShare === "function") {
        const file = new File([blob], `worldcup-pick-${member}.png`, { type: "image/png" });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file], text });
          return;
        }
      }
      if (typeof navigator.share === "function") {
        await navigator.share({ text, url: SHARE_URL });
        return;
      }
      await navigator.clipboard.writeText(SHARE_URL);
      setMsg("링크를 복사했습니다. 원하는 곳에 붙여넣어 주세요.");
    } catch (e) {
      // user cancelled the share sheet — not an error
      if (e instanceof Error && e.name === "AbortError") return;
      try {
        await navigator.clipboard.writeText(SHARE_URL);
        setMsg("링크를 복사했습니다. 원하는 곳에 붙여넣어 주세요.");
      } catch {
        setMsg("공유에 실패했습니다. 이미지 저장을 이용해 주세요.");
      }
    }
  }, [exportBlob, member]);

  return (
    <div className="share-overlay" role="dialog" aria-modal="true" aria-label="공유 카드">
      <div className="share-panel">
        <canvas ref={canvasRef} width={W} height={H} className="share-canvas" />
        {!ready ? <p className="share-msg">카드 만드는 중…</p> : null}
        <div className="share-actions">
          <button className="btn-vs share-btn" onClick={save} disabled={!ready}>
            이미지 저장
          </button>
          <button className="btn-vs ghost share-btn" onClick={share} disabled={!ready}>
            공유
          </button>
          <button className="btn-vs ghost share-btn" onClick={onClose}>
            닫기
          </button>
        </div>
        {msg ? <p className="share-msg">{msg}</p> : null}
      </div>
    </div>
  );
}
