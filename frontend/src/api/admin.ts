export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  alerts_paused: boolean;
  telegram_connected: boolean;
}

export interface ScraperRun {
  id: string;
  board: string;
  started_at: string;
  completed_at?: string;
  listings_found: number;
  new_listings: number;
  errors?: string;
  status: string;
}

export async function getAdminUsers(): Promise<AdminUser[]> {
  const res = await fetch("/api/admin/users");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getScraperRuns(): Promise<ScraperRun[]> {
  const res = await fetch("/api/admin/scraper-runs");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function triggerScraper() {
  const res = await fetch("/api/admin/trigger-scrape", {
    method: "POST",
  });
  if (!res.ok) throw await res.json();
  return res.json();
}
