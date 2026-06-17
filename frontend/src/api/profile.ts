export async function getProfile() {
  const res = await fetch("/api/profile");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function updateProfile(body: Record<string, any>) {
  const res = await fetch("/api/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getNotifications() {
  const res = await fetch("/api/notifications");
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function updateNotifications(body: Record<string, any>) {
  const res = await fetch("/api/notifications", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function sendTestEmail() {
  const res = await fetch("/api/profile/test-email", {
    method: "POST",
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

