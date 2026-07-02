export const dynamic = "force-dynamic";

/**
 * AdSense requires /ads.txt at the domain root. Served dynamically from
 * NEXT_PUBLIC_ADSENSE_CLIENT so the publisher id lives in one env var.
 * When the env is unset (ads off) we return 404 — AdSense treats a missing
 * ads.txt as "not configured", which is correct until approval.
 */
export async function GET() {
  const client = process.env.NEXT_PUBLIC_ADSENSE_CLIENT;
  if (!client) {
    return new Response("Not Found", { status: 404 });
  }
  const pubId = client.replace(/^ca-pub-/, "");
  return new Response(`google.com, pub-${pubId}, DIRECT, f08c47fec0942fa0\n`, {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=86400",
    },
  });
}
