"""HTML pages outside /api: the admin review of a day (`/admin/review/{date}`)
and the two legal pages App Store Connect links to (`/legal/*.html`).

Readable in any browser. Without an admin session it shows a login form
that posts to /api/auth/login (same cookie as the app), then reloads.
"""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import markdown as md
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user_optional
from ..db import get_session
from .admin import review_data

router = APIRouter(include_in_schema=False)

LEGAL_DIR = Path(__file__).resolve().parent.parent / "content" / "legal"
LEGAL_PAGES = {"privacy.html", "about.html"}


@router.get("/legal/{name}")
async def legal(name: str) -> Response:
    if name not in LEGAL_PAGES:
        return Response(status_code=404)
    return HTMLResponse((LEGAL_DIR / name).read_text(encoding="utf-8"))


STYLE = """
:root { color-scheme: light dark; --bg:#fff; --fg:#1d1d1f; --muted:#6e6e73; --card:#f5f5f7;
  --line:#d2d2d7; --accent:#e8590c; --ok:#2f9e44; --warn:#e67700; }
@media (prefers-color-scheme: dark) { :root { --bg:#111; --fg:#f5f5f7; --muted:#a1a1a6;
  --card:#1c1c1e; --line:#38383a; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.5 -apple-system, system-ui, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 16px; }
nav { display:flex; gap:12px; align-items:center; justify-content:space-between; margin-bottom:16px; }
a { color: var(--accent); }
article { background:var(--card); border-radius:14px; padding:16px; margin:16px 0; }
article.flagged { outline: 2px solid var(--warn); }
h1 { font-size: 22px; } h2 { font-size: 19px; margin:4px 0 8px; } h3 { font-size:16px; margin-top:18px; }
.meta { color:var(--muted); font-size:14px; }
.chip { display:inline-block; padding:2px 8px; border-radius:99px; background:var(--line); font-size:12px; margin-right:4px; }
.ok { color: var(--ok); } .warn { color: var(--warn); }
table { border-collapse: collapse; width:100%; font-size:14px; }
td, th { border-top:1px solid var(--line); padding:6px; text-align:left; vertical-align:top; }
details { margin-top: 8px; }
button { font:inherit; padding:8px 14px; border-radius:99px; border:1px solid var(--line);
  background:var(--bg); color:var(--fg); cursor:pointer; }
form.login { display:grid; gap:8px; max-width:320px; }
input { font:inherit; padding:8px; border-radius:8px; border:1px solid var(--line); background:var(--bg); color:var(--fg); }
pre { white-space: pre-wrap; }
"""

LOGIN = """
<form class="login" onsubmit="login(event)">
  <h1>Relecture CaseDuo</h1>
  <p class="meta">Connexion administrateur.</p>
  <input name="username" type="email" placeholder="e-mail" required autocomplete="username">
  <input name="password" type="password" placeholder="mot de passe" required autocomplete="current-password">
  <button type="submit">Se connecter</button>
  <p id="err" class="warn"></p>
</form>
<script>
async function login(e) {
  e.preventDefault();
  const r = await fetch('/api/auth/login', {method: 'POST', body: new URLSearchParams(new FormData(e.target)), credentials: 'same-origin'});
  if (r.ok) location.reload(); else document.getElementById('err').textContent = 'Identifiants refusés.';
}
</script>
"""

SCRIPT = """
<script>
async function flag(id, on) {
  const note = on ? prompt('Qu’est-ce qui ne va pas dans ce corrigé ?') : null;
  if (on && note === null) return;
  const r = await fetch(`/api/admin/exercises/${id}/flag`, {method:'POST', credentials:'same-origin',
    headers: {'Content-Type':'application/json'}, body: JSON.stringify({flagged: on, note})});
  if (r.ok) location.reload(); else alert('Échec : ' + r.status);
}
</script>
"""


def _md(text: str | None) -> str:
    return md.markdown(html.escape(text or ""), extensions=["tables", "sane_lists"])


def _e(text: Any) -> str:
    return html.escape(str(text if text is not None else ""))


def _exercise(ex: dict[str, Any]) -> str:
    facts = ex["context_data"].get("facts") or []
    fact_rows = "".join(
        f"<tr><td>{_e(f.get('label'))}</td><td>{_e(f.get('value'))}</td><td>"
        + (
            f'<a href="{_e(f["source_url"])}" target="_blank" rel="noopener">source</a>'
            if f.get("source_url")
            else '<span class="warn">hypothèse</span>'
        )
        + "</td></tr>"
        for f in facts
    )
    sources = "".join(
        f'<li><a href="{_e(s.get("url"))}" target="_blank" rel="noopener">{_e(s.get("title"))}</a> '
        + (
            '<span class="ok">✓ vue par la recherche</span>'
            if s.get("verified")
            else '<span class="warn">non vérifiée</span>'
        )
        + "</li>"
        for s in ex["sources"]
    )
    rubric = "".join(
        f"<tr><td><b>{_e(c['label'])}</b> ({_e(c['weight'])})</td>"
        f"<td>0 : {_e(c['levels'].get('0'))}<br>1 : {_e(c['levels'].get('1'))}<br>2 : {_e(c['levels'].get('2'))}</td></tr>"
        for c in ex["rubric"]
    )
    parts = "".join(
        f"<li>{_e(p.get('question'))}"
        + (f" <span class='meta'>— {_e(p.get('data'))}</span>" if p.get("data") else "")
        + "</li>"
        for p in (ex["parts"] or [])
    )
    flag_button = (
        f"<button onclick=\"flag('{ex['id']}', false)\">Retirer le signalement</button>"
        if ex["flagged"]
        else f"<button onclick=\"flag('{ex['id']}', true)\">Marquer « mauvais »</button>"
    )
    return f"""
<article class="{"flagged" if ex["flagged"] else ""}">
  <div class="meta"><span class="chip">{_e(ex["type_label"])}</span><span class="chip">{_e(ex["style"])}</span>
  <span class="chip">{_e(ex["language"])}</span><span class="chip">difficulté {_e(ex["difficulty"])}</span>
  <span class="chip">{_e(ex["sector"])}</span><span class="chip">{_e(ex["generation_mode"])}</span>
  {('<span class="chip">cible : ' + _e(", ".join(ex["targets_weakness"])) + "</span>") if ex["targets_weakness"] else ""}</div>
  <h2>{_e(ex["title"])}</h2>
  {('<p class="warn">Signalé : ' + _e(ex["flag_note"]) + "</p>") if ex["flagged"] else ""}
  {_md(ex["prompt"])}
  {("<ol>" + parts + "</ol>") if parts else ""}
  <h3>Données (context_data)</h3>
  {("<table>" + fact_rows + "</table>") if fact_rows else '<p class="meta">Aucune.</p>'}
  <details><summary>Corrigé (model_answer)</summary>{_md(ex["model_answer"])}</details>
  <details><summary>Rubric</summary><table>{rubric}</table></details>
  <h3>Sources</h3>{("<ul>" + sources + "</ul>") if sources else '<p class="meta">Aucune.</p>'}
  <p>{flag_button}</p>
</article>"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{_e(title)}</title><style>{STYLE}</style></head><body><main>{body}</main></body></html>"
    )


@router.get("/admin/review/{day}", response_class=HTMLResponse)
async def review_page(
    day: date,
    user: User | None = Depends(current_active_user_optional),
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    if user is None or not user.is_superuser:
        return page("Relecture CaseDuo", LOGIN)
    data = await review_data(session, day)
    prev_day, next_day = day - timedelta(days=1), day + timedelta(days=1)
    runs = "".join(
        f"<tr><td>{_e(r['job'])}</td><td>{_e(r['status'])}</td><td>{r['n_succeeded']}/{r['n_requests']}</td>"
        f"<td>{r['input_tokens'] + r['cache_read_tokens']:,} / {r['output_tokens']:,}</td><td>{r['web_searches']}</td>"
        f"<td>${r['cost_usd']:.4f}</td><td>{len(r['errors'])}</td></tr>"
        for r in data["cron_runs"]
    )
    body = f"""
<nav><a href="/admin/review/{prev_day.isoformat()}">← {prev_day.isoformat()}</a>
<h1>{day.isoformat()}</h1><a href="/admin/review/{next_day.isoformat()}">{next_day.isoformat()} →</a></nav>
<p class="meta">{len(data["exercises"])} exercices · coût de génération ${data["cost_usd"]:.4f}</p>
{("<table><tr><th>job</th><th>statut</th><th>ok</th><th>tokens in/out</th><th>recherches</th><th>coût</th><th>erreurs</th></tr>" + runs + "</table>") if runs else ""}
{"".join(_exercise(e) for e in data["exercises"]) or "<p>Rien pour cette date.</p>"}
{SCRIPT}"""
    return page(f"Relecture {day.isoformat()}", body)
