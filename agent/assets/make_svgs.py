"""Generates the animated README SVGs (pure SVG/SMIL, no scripts - GitHub renders these).

Usage: python agent/assets/make_svgs.py agent/assets
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape as esc

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
EMOJI = "'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',sans-serif"


def fade(t_in, t_out, total, e=0.35, start_visible=False):
    """SMIL opacity animate: invisible -> visible at t_in -> invisible at t_out (seconds), looping."""
    f = lambda t: max(0.0, min(1.0, t / total))
    kt = [0, f(t_in), f(t_in + e), f(t_out), f(t_out + e), 1]
    for i in range(1, len(kt)):  # keyTimes must be non-decreasing
        kt[i] = max(kt[i], kt[i - 1])
    vals = "0;0;1;1;0;0"
    return (f'<animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(f"{k:.4f}" for k in kt)}" values="{vals}"/>')


# ---------------------------------------------------------------- hero banner
def hero():
    W, H = 900, 250
    lines = ["> searching Delhi & Noida for small AI startups...",
             "> reading their websites, finding the HR email...",
             "> writing an email that fits what each one builds...",
             "> screened, queued by deadline - sending 40 a day"]
    cw, fs, y = 12.2, 20, 182
    parts, per = [], 4.0
    total = per * len(lines)
    for i, text in enumerate(lines):
        w = len(text) * cw
        x = W / 2 - w / 2
        t0 = i * per
        type_dur = 1.9
        parts.append(f'''
  <clipPath id="clip{i}"><rect x="{x - 2:.1f}" y="{y - 24}" height="34" width="0">
    <animate attributeName="width" dur="{total}s" repeatCount="indefinite"
      keyTimes="0;{t0 / total:.4f};{(t0 + type_dur) / total:.4f};1" values="0;0;{w + 4:.1f};{w + 4:.1f}" calcMode="linear"/>
  </rect></clipPath>
  <g opacity="0">{fade(t0, t0 + per - 0.35, total, e=0.01)}
    <text x="{x:.1f}" y="{y}" font-family="{MONO}" font-size="{fs}" fill="#7ee787" textLength="{w:.1f}"
      lengthAdjust="spacingAndGlyphs" clip-path="url(#clip{i})">{esc(text)}</text>
    <rect y="{y - 18}" width="10" height="22" fill="#7ee787">
      <animate attributeName="x" dur="{total}s" repeatCount="indefinite"
        keyTimes="0;{t0 / total:.4f};{(t0 + type_dur) / total:.4f};1" values="{x:.1f};{x:.1f};{x + w + 4:.1f};{x + w + 4:.1f}"/>
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="0.9s" repeatCount="indefinite"/>
    </rect>
  </g>''')
    dots = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#58a6ff" opacity="0.0">'
        f'<animate attributeName="opacity" values="0;0.5;0" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cy" values="{cy};{cy - 25}" dur="{d}s" begin="{b}s" repeatCount="indefinite"/></circle>'
        for cx, cy, r, d, b in [(60, 200, 2, 5, 0), (140, 90, 1.5, 6, 1), (790, 70, 2, 5.5, 2), (850, 190, 1.5, 4.5, .5),
                                (230, 40, 1.2, 6.5, 3), (700, 215, 1.8, 5, 1.5), (520, 30, 1.2, 7, 2.5), (330, 225, 1.5, 6, 4)])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="AI Job-Hunt Agent">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#161b2e"/>
    </linearGradient>
    <linearGradient id="title" x1="0" y1="0" x2="1" y2="0" gradientUnits="objectBoundingBox">
      <stop offset="0" stop-color="#58a6ff"/><stop offset="0.5" stop-color="#bc8cff"/><stop offset="1" stop-color="#58a6ff"/>
      <animateTransform attributeName="gradientTransform" type="translate" values="-1 0;1 0" dur="6s" repeatCount="indefinite"/>
    </linearGradient>
    <linearGradient id="title-spread" href="#title" spreadMethod="repeat"/>
  </defs>
  <rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#30363d"/>
  {dots}
  <text x="{W / 2}" y="86" text-anchor="middle" font-family="{SANS}" font-size="46" font-weight="800" fill="url(#title-spread)">AI Job-Hunt Agent</text>
  <text x="{W / 2}" y="122" text-anchor="middle" font-family="{SANS}" font-size="17" fill="#8b949e">Finds AI/ML openings · screens out senior &amp; fake posts · sends 40 tailored emails a day</text>
  <rect x="120" y="150" width="660" height="48" rx="10" fill="#010409" stroke="#30363d"/>
  {"".join(parts)}
</svg>'''
    (OUT / "hero.svg").write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------- pipeline
def pipeline():
    W, H = 900, 210
    nodes = [("⏰", "Every 3 h", "sleeps when full"), ("🔎", "Web search", "jobs · LinkedIn posts"),
             ("🧠", "AI filter", "AI/ML · Delhi NCR"), ("🛡️", "Screened", "0–2 yrs · no scams"),
             ("🌐", "Company site", "real HR email"), ("✍️", "Tailored draft", "fits their domain"),
             ("📧", "Paced send", "40/day + resume")]
    x0, x1, y, total, travel = 70, 830, 78, 8.0, 0.85
    step = (x1 - x0) / (len(nodes) - 1)
    out = []
    for i, (emo, title, sub) in enumerate(nodes):
        x = x0 + i * step
        f = travel * i / (len(nodes) - 1)
        color = "#3fb950" if i == len(nodes) - 1 else "#d29922" if i == 5 else "#58a6ff"
        kt = sorted({0, max(0, f - 0.02), f, min(1, f + 0.10), 1})
        vals = {0: 0, max(0, f - 0.02): 0, f: 1, min(1, f + 0.10): 0.35, 1: 0.35 if i == len(nodes) - 1 else 0}
        if i == 0:
            kt, vals = [0, 0.1, 0.9, 1], {0: 1, 0.1: 0.35, 0.9: 0, 1: 1}
        out.append(f'''
  <g>
    <circle cx="{x:.1f}" cy="{y}" r="31" fill="#161b22" stroke="#30363d" stroke-width="2"/>
    <circle cx="{x:.1f}" cy="{y}" r="31" fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="2.5" opacity="0">
      <animate attributeName="opacity" dur="{total}s" repeatCount="indefinite"
        keyTimes="{";".join(f"{k:.4f}" for k in kt)}" values="{";".join(str(vals[k]) for k in kt)}"/>
      <animate attributeName="r" dur="{total}s" repeatCount="indefinite"
        keyTimes="{";".join(f"{k:.4f}" for k in kt)}" values="{";".join('35' if vals[k] == 1 else '31' for k in kt)}"/>
    </circle>
    <text x="{x:.1f}" y="{y + 9}" text-anchor="middle" font-family="{EMOJI}" font-size="26">{emo}</text>
    <text x="{x:.1f}" y="{y + 58}" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="700" fill="#e6edf3">{esc(title)}</text>
    <text x="{x:.1f}" y="{y + 77}" text-anchor="middle" font-family="{SANS}" font-size="11.5" fill="#8b949e">{esc(sub)}</text>
  </g>''')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="How the agent works">
  <defs>
    <radialGradient id="glow"><stop offset="0" stop-color="#fff"/><stop offset="0.35" stop-color="#79c0ff"/><stop offset="1" stop-color="#58a6ff" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="16" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="#30363d"/>
  <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#30363d" stroke-width="3"/>
  <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#58a6ff" stroke-width="3" stroke-dasharray="6 10" opacity="0.6">
    <animate attributeName="stroke-dashoffset" values="32;0" dur="1s" repeatCount="indefinite"/>
  </line>
  {"".join(out)}
  <circle r="11" fill="url(#glow)">
    <animateMotion dur="{total}s" repeatCount="indefinite" path="M{x0},{y} H{x1}" keyPoints="0;1;1" keyTimes="0;{travel};1" calcMode="linear"/>
    <animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" keyTimes="0;{travel};{travel + 0.02};1" values="1;1;0;0"/>
  </circle>
  <text x="{W / 2}" y="{H - 14}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#6e7681">deadline-first queue · 09:30–19:30 IST · ~13 min apart · Telegram ping after each email</text>
</svg>'''
    (OUT / "pipeline.svg").write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------- telegram card
def card():
    W, H, total = 480, 530, 11.0
    bx, by, bw = 24, 70, 432
    rows = [  # (text, y, size, color, weight, delay)
        ("Acme Vision AI · Noida", 104, 17, "#e6edf3", 700, 0.9),
        ("🔵 AI company — writing to HR", 130, 14, "#79c0ff", 400, 1.2),
        ("🏢 Document-understanding APIs for banks", 154, 14, "#c9d1d9", 400, 1.5),
        ("✉️ To: careers@acmevision.example", 184, 14, "#e6edf3", 600, 1.8),
        ("     found on: acmevision.example/careers", 204, 12.5, "#8b949e", 400, 1.8),
        ("Subject: GenAI engineer – RAG & search", 238, 14, "#e6edf3", 700, 2.2),
        ("Hi Hiring Team,", 268, 14, "#c9d1d9", 400, 2.5),
        ("Your OCR pipeline for bank statements is a", 290, 14, "#c9d1d9", 400, 2.7),
        ("problem I've worked close to: at NIC I built a", 310, 14, "#c9d1d9", 400, 2.8),
        ("RAG document-intelligence system with", 330, 14, "#c9d1d9", 400, 2.9),
        ("LangChain, ChromaDB and FastAPI…", 350, 14, "#c9d1d9", 400, 3.0),
        ("📎 Sandeep_Kumar_Resume.pdf", 382, 13, "#79c0ff", 400, 3.2),
    ]
    end = total - 0.8
    text = "".join(
        f'<text x="{bx + 18}" y="{y}" font-family="{SANS},{EMOJI}" font-size="{s}" font-weight="{w}" fill="{c}" opacity="0">'
        f'{esc(t)}{fade(d, end, total)}</text>' for t, y, s, c, w, d in rows)
    tap, sent = 5.2, 5.8
    btn_y, btn_h, gap = 410, 40, 8
    bwid = (bw - 2 * gap) / 3
    buttons = ""
    for j, label in enumerate(["✅ Send", "🔁 Rewrite", "❌ Skip"]):
        x = bx + j * (bwid + gap)
        flash = (f'<animate attributeName="fill" dur="{total}s" repeatCount="indefinite" '
                 f'keyTimes="0;{tap / total:.4f};{(tap + 0.05) / total:.4f};{(tap + 0.5) / total:.4f};1" '
                 f'values="#2b5278;#2b5278;#4a8fd6;#2b5278;#2b5278"/>') if j == 0 else ""
        buttons += (f'<rect x="{x:.1f}" y="{btn_y}" width="{bwid:.1f}" height="{btn_h}" rx="9" fill="#2b5278">{flash}</rect>'
                    f'<text x="{x + bwid / 2:.1f}" y="{btn_y + 26}" text-anchor="middle" font-family="{SANS},{EMOJI}" '
                    f'font-size="14" font-weight="600" fill="#e6edf3">{label}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Telegram approval card demo">
  <rect width="{W}" height="{H}" rx="22" fill="#0e1621"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="#30363d"/>
  <rect width="{W}" height="56" rx="22" fill="#17212b"/><rect y="34" width="{W}" height="22" fill="#17212b"/>
  <circle cx="40" cy="28" r="16" fill="#2b5278"/><text x="40" y="34" text-anchor="middle" font-family="{EMOJI}" font-size="16">🤖</text>
  <text x="66" y="25" font-family="{SANS}" font-size="15" font-weight="700" fill="#e6edf3">Job Agent</text>
  <text x="66" y="43" font-family="{SANS}" font-size="12" fill="#6ab3f3">bot</text>
  <g opacity="0">{fade(0.3, end, total)}
    <animateTransform attributeName="transform" type="translate" dur="{total}s" repeatCount="indefinite"
      keyTimes="0;{0.3 / total:.4f};{0.9 / total:.4f};1" values="0 24;0 24;0 0;0 0"/>
    <rect x="{bx}" y="{by + 8}" width="{bw}" height="{332}" rx="14" fill="#182533"/>
    {text}
    <g opacity="0">{fade(3.4, sent, total, e=0.25)}{buttons}</g>
    <g opacity="0">{fade(sent, end, total)}
      <rect x="{bx}" y="{btn_y}" width="{bw}" height="{btn_h}" rx="9" fill="#1f3b2a" stroke="#3fb950"/>
      <text x="{bx + bw / 2}" y="{btn_y + 26}" text-anchor="middle" font-family="{SANS},{EMOJI}" font-size="14" font-weight="600" fill="#7ee787">✅ Sent from your Gmail · 1/20 today</text>
    </g>
    <circle cx="{bx + bwid / 2 + 10:.1f}" cy="{btn_y + 24}" r="18" fill="#ffffff" opacity="0">
      <animate attributeName="opacity" dur="{total}s" repeatCount="indefinite"
        keyTimes="0;{(tap - 0.4) / total:.4f};{tap / total:.4f};{(tap + 0.35) / total:.4f};1" values="0;0;0.45;0;0"/>
      <animate attributeName="r" dur="{total}s" repeatCount="indefinite"
        keyTimes="0;{(tap - 0.4) / total:.4f};{tap / total:.4f};{(tap + 0.35) / total:.4f};1" values="26;26;14;30;30"/>
    </circle>
  </g>
  <rect x="24" y="{H - 66}" width="{W - 48}" height="42" rx="21" fill="#17212b"/>
  <text x="46" y="{H - 39}" font-family="{SANS}" font-size="14" fill="#6e7681">Reply "shorter" to rewrite, or "to: hr@…"</text>
</svg>'''
    (OUT / "telegram-card.svg").write_text(svg, encoding="utf-8")


hero()
pipeline()
card()
print("wrote", *sorted(p.name for p in OUT.glob("*.svg")))
