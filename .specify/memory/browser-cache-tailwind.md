# Browser Cache & Tailwind CSS Gotchas

## Problem

After modifying Tailwind CSS classes in templates (e.g., adding `bg-red-600`, `bg-sky-950`, etc.) and rebuilding containers with `docker compose up -d --build`, the browser may still show old styles or broken buttons (e.g., white text on white background).

## Root Cause

The browser aggressively caches:
1. **`/static/css/app.css`** — the compiled Tailwind CSS output
2. **JavaScript files** — including inline JS in templates like `layout.html`

Even after a full container rebuild, the browser serves the cached CSS/JS from before the rebuild.

## How to Fix

### Immediate Fix (for developers)
- **Hard refresh**: `Ctrl + Shift + R` (Chrome/Edge/Firefox) or `Cmd + Shift + R` (Mac)
- **DevTools**: Open F12 → Network tab → check "Disable cache" → reload
- **Clear cache**: Browser settings → Clear browsing data → Cached images and files

### Verification Commands
```bash
# Check if a Tailwind class exists in the compiled CSS
docker compose exec web grep -c "bg-red-600" /app/app/static/css/app.css

# Check if the class is in the HTML response
docker compose exec web curl -s http://localhost:8000/dashboard | grep -o "bg-red-600"
```

## Project-Specific Context

- **Tailwind version**: v4.2.2 (standalone CLI, downloaded in Dockerfile)
- **Build step**: `./tailwindcss-linux-x64 -i ./app/src/input.css -o ./app/static/css/app.css`
- **CSS served from**: `/app/app/static/css/app.css` → mapped to `/static/css/app.css`
- **Template with inline JS**: `app/templates/dashboard/layout.html` (contains retry button logic)
- **Base template**: `app/templates/base.html` (links `/static/css/app.css`)

## Prevention Tips

1. Always hard refresh after `docker compose up -d --build`
2. During active CSS development, consider adding a cache-busting query param to the CSS link in `base.html`
3. If a button looks "invisible" (white on white), it's almost certainly a cache issue — the CSS class exists but the browser is serving old styles
