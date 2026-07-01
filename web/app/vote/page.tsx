import { redirect } from "next/navigation";

// Old per-round voting flow is gone. Keep the /vote URL alive → send to /play.
export default function VoteRedirect() {
  redirect("/play");
}
