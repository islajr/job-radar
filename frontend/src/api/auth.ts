export async function registerUser(body: Record<string, any>) {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function loginUser(body: Record<string, any>) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function logoutUser() {
  const res = await fetch("/api/auth/logout", { method: "POST" });
  if (!res.ok) throw await res.json();
  return res.json();
}
