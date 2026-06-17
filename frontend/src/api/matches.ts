export interface Match {
  id: string;
  listing_id: string;
  title: string;
  company?: string;
  location?: string;
  url: string;
  salary_text?: string;
  board: string;
  created_at: string;
}

export async function getMatches(): Promise<Match[]> {
  const res = await fetch("/api/matches");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function toggleAlertPause(paused: boolean) {
  const res = await fetch("/api/alerts/pause", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paused }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}
