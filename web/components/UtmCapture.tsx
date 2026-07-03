"use client";

import { useEffect } from "react";
import { captureUtm } from "@/lib/utm";

/**
 * Invisible layout-level helper: records first-touch utm_source from the URL
 * into localStorage on page load. Renders nothing.
 */
export default function UtmCapture() {
  useEffect(() => {
    captureUtm();
  }, []);
  return null;
}
