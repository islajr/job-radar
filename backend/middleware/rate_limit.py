import time
import threading
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 15):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.history = defaultdict(list)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit requests targeting /api/*
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Bypass rate-limiting if the user is signed in (session cookie is present)
        if request.cookies.get("session"):
            return await call_next(request)

        # Identify client IP (using X-Forwarded-For header or fallback to request.client.host)
        ip = request.headers.get("X-Forwarded-For")
        if ip:
            # X-Forwarded-For can be a comma-separated list; get the client (first) IP
            ip = ip.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        now = time.time()
        cutoff = now - 60.0

        with self.lock:
            # Clean up old timestamps for this IP
            timestamps = [ts for ts in self.history[ip] if ts > cutoff]
            
            # Check limit
            if len(timestamps) >= self.requests_per_minute:
                self.history[ip] = timestamps
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests. Anonymous rate limit is 15 requests per minute."}
                )
            
            # Add current timestamp
            timestamps.append(now)
            self.history[ip] = timestamps

            # Simple periodic cleanup of other keys to prevent memory leaks when size grows
            if len(self.history) > 1000:
                keys_to_remove = []
                # Clean up a small batch of keys
                for k, v in list(self.history.items())[:10]:
                    v_clean = [ts for ts in v if ts > cutoff]
                    if not v_clean:
                        keys_to_remove.append(k)
                    else:
                        self.history[k] = v_clean
                for k in keys_to_remove:
                    self.history.pop(k, None)

        return await call_next(request)
