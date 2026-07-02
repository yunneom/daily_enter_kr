import { adsPubId } from "@/lib/adsense";

export const dynamic = "force-dynamic";

/**
 * AdSense requires /ads.txt at the domain root. Served dynamically from
 * NEXT_PUBLIC_ADSENSE_CLIENT so the publisher id lives in one env var.
 * When the env is unset/unparseable (ads off) we return 404 — AdSense treats
 * a missing ads.txt as "not configured", which is correct until approval.
 */
export async function GET() {
  const pubId = adsPubId(process.env.NEXT_PUBLIC_ADSENSE_CLIENT);
  if (!pubId) {
    return new Response("Not Found", { status: 404 });
  }
  return new Response(`google.com, pub-${pubId}, DIRECT, f08c47fec0942fa0\n`, {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      // Short cache — this route is derived from an env var that gets tuned
      // during AdSense setup; a long max-age here previously caused a stale
      // pre-fix response (pub-pub-XXXX) to stick in the browser/CDN for a
      // full day after the bug was already fixed and redeployed.
      "cache-control": "public, max-age=300, s-maxage=300",
    },
  });
}
