#!/usr/bin/env python3
"""Sum up 18 November 2026's world news in one image (rev2: dense edition).

Renders a 1024x1024 newspaper front page (THE WORLD IN ONE DAY) with the
six verified stories of Wednesday 18 November 2026, plus an ALSO TODAY strip
and a sources footer. Country names get their flag, people get their cartoon
portrait, companies get a drawn ticker mark.

Rev2 changes (user feedback: the news content was too brief): every story
deck is expanded to a full multi-line article text built only from the
verified facts in NEWS_FACTS.md, the deck font auto-fits so no card
overflows, the numbers strip gains a 7th stat, and ALSO TODAY becomes a
proper three-item section with two lines per item.

Render path (Pillow available): draws the page with Pillow and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png.
Fallback path (no Pillow): copies the pre-rendered entry.png sitting next to
this file to $MAKEFUN_OUTPUT_DIR/entry.png, using only the standard library.
Both paths produce byte-identical output.
"""

import os
import shutil
import sys

W = 1024
H = 1024
MARGIN = 24
CONTENT_W = W - 2 * MARGIN

BG = (247, 242, 231)          # cream paper
INK = (26, 26, 26)            # near-black
MUTED = (90, 90, 90)          # grey text
CARD_BG = (255, 255, 255)     # white cards
CARD_BORDER = (216, 208, 192) # card outline
RULE = (26, 26, 26)           # rule lines
NAVY_BAND = (20, 33, 61)      # ALSO TODAY band
GOLD = (242, 193, 78)         # ALSO TODAY label

CAT_COLORS = {
    "gulf": (139, 26, 26),
    "apec": (26, 58, 107),
    "markets": (26, 92, 42),
    "cyber": (74, 42, 107),
    "space": (15, 31, 61),
    "business": (107, 74, 26),
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _font(name, size):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_w):
    """Wrap text to max_w. Avoid a final line holding a single short word."""
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for word in words[1:]:
        trial = cur + " " + word
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    # orphan control: a lone short word on the last line borrows the
    # previous line's last word.
    if len(lines) >= 2 and len(lines[-1].split()) == 1 and len(lines[-1]) <= 6:
        prev = lines[-2].split()
        if len(prev) >= 2:
            moved = prev[-1]
            lines[-2] = " ".join(prev[:-1])
            lines[-1] = moved + " " + lines[-1]
    return lines


def fit_deck(draw, deck, max_w, max_h):
    """Pick the largest deck font (13 down to 10.5) whose wrapped lines fit
    in max_h, so a long deck never overlaps the visual area below it."""
    for size in (13, 12.5, 12, 11.5, 11, 10.5):
        font = _font("DejaVuSans.ttf", size)
        line_h = int(size + 4)
        lines = wrap_text(draw, deck, font, max_w)
        if len(lines) * line_h <= max_h:
            return font, lines, line_h
    font = _font("DejaVuSans.ttf", 10.5)
    return font, wrap_text(draw, deck, font, max_w), int(10.5 + 4)


def draw_flag(draw, img, code, right, y, h):
    """Paste a flag PNG (assets/flags/<code>.png) so its right edge is at
    `right`, at height h, keeping its aspect ratio, with a thin grey border
    so white fields read. Returns the flag's left edge."""
    from PIL import Image
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "flags", code + ".png")
    flag = Image.open(path).convert("RGB")
    w = max(1, int(round(flag.width * h / flag.height)))
    flag = flag.resize((w, h))
    x = int(right - w)
    y = int(y)
    img.paste(flag, (x, y))
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=(120, 120, 120))
    return x


def circle_portrait(img, path, diameter):
    """Circular-crop a portrait (face-centred square crop, circular mask)."""
    from PIL import Image, ImageDraw
    src = Image.open(path).convert("RGB")
    w, h = src.size
    side = min(w, h)
    cx = w // 2
    cy = int(h * 0.35)
    top = max(0, min(h - side, cy - side // 2))
    left = max(0, min(w - side, cx - side // 2))
    sq = src.crop((left, top, left + side, top + side)).resize(
        (diameter, diameter))
    mask = Image.new("L", (diameter, diameter), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([0, 0, diameter - 1, diameter - 1], fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(sq, (0, 0), mask)
    return out


def _chip(draw, x, y, w, h, fill, text, font, text_fill=(255, 255, 255)):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=fill)
    tw = draw.textlength(text, font=font)
    draw.text((x + (w - tw) / 2, y + (h - font.size) / 2 - 1),
              text, font=font, fill=text_fill)


def draw_radar(draw, x, y, w, h):
    """Gulf: a radar dish with a burst and signal waves."""
    # dish
    draw.pieslice([x + 8, y + 22, x + w - 8, y + h + 6], 180, 360,
                  fill=(31, 120, 110))
    draw.rectangle([x + w // 2 - 2, y + h - 14, x + w // 2 + 2, y + h - 2],
                   fill=(31, 120, 110))
    draw.rectangle([x + w // 2 - 14, y + h - 4, x + w // 2 + 14, y + h - 1],
                   fill=(31, 120, 110))
    # burst (orange star)
    bx, by = x + w - 18, y + 12
    draw.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=(232, 130, 30))
    for ang in range(0, 360, 45):
        import math
        r1, r2 = 10, 16
        a = math.radians(ang)
        draw.line([bx + r1 * math.cos(a), by + r1 * math.sin(a),
                   bx + r2 * math.cos(a), by + r2 * math.sin(a)],
                  fill=(232, 130, 30), width=3)
    # waves
    for i, ww in enumerate((34, 52, 70)):
        draw.arc([x + 6, y + h - 8 - ww // 2, x + 6 + ww, y + h - 8 + ww // 2],
                 200, 340, fill=(60, 110, 180), width=2)


def draw_chart(draw, x, y, w, h):
    """Markets: an NVDA chip and a rising chart line with an arrow."""
    f_small = _font("DejaVuSans-Bold.ttf", 13)
    _chip(draw, x, y + 6, 62, 26, (20, 20, 20), "NVDA", f_small)
    pts = [(x + 74, y + h - 14), (x + 96, y + h - 26), (x + 114, y + h - 20),
           (x + 134, y + h - 34), (x + 156, y + h - 44), (x + 176, y + h - 52)]
    draw.line(pts, fill=(26, 140, 60), width=4, joint="curve")
    # arrowhead
    draw.polygon([(x + 176, y + h - 52), (x + 164, y + h - 50),
                  (x + 172, y + h - 40)], fill=(26, 140, 60))


def draw_laptop(draw, x, y, w, h):
    """Cyber: a laptop with a warning triangle."""
    draw.rounded_rectangle([x + 6, y + 8, x + w - 6, y + h - 22], radius=4,
                           fill=(30, 30, 46))
    draw.rectangle([x + 14, y + 16, x + w - 14, y + h - 30], fill=(240, 238, 225))
    # warning triangle
    cx, cy = x + w // 2, y + h // 2 - 2
    draw.polygon([(cx, cy - 20), (cx - 20, cy + 14), (cx + 20, cy + 14)],
                 fill=(242, 193, 40), outline=(26, 26, 26))
    f_b = _font("DejaVuSans-Bold.ttf", 20)
    draw.text((cx - 3, cy - 8), "!", font=f_b, fill=(26, 26, 26))
    draw.polygon([(x, y + h - 20), (x + w, y + h - 20),
                  (x + w - 8, y + h - 8), (x + 8, y + h - 8)],
                 fill=(90, 90, 110))
    # coffee cup
    draw.rectangle([x + w - 26, y + h - 26, x + w - 10, y + h - 10],
                   outline=(90, 90, 90), width=2)


def draw_space(draw, x, y, w, h):
    """Space: a dark sky panel, stars, a dish, Earth, and signal arcs."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=(15, 31, 61))
    for sx, sy in [(12, 10), (30, 26), (52, 8), (78, 20), (96, 34),
                   (118, 12), (140, 28), (162, 10), (180, 24)]:
        draw.ellipse([x + sx, y + sy, x + sx + 2, y + sy + 2],
                     fill=(255, 255, 255))
    # Earth
    draw.ellipse([x + 10, y + h - 34, x + 34, y + h - 10], fill=(60, 130, 200))
    draw.arc([x + 10, y + h - 34, x + 34, y + h - 10], 40, 200,
             fill=(120, 200, 120), width=2)
    # dish
    draw.polygon([(x + w // 2 - 6, y + h - 22), (x + w // 2 + 34, y + 16),
                  (x + w // 2 + 46, y + 24), (x + w // 2 + 6, y + h - 14)],
                 fill=(220, 220, 220))
    draw.rectangle([x + w // 2 - 2, y + h - 22, x + w // 2 + 2, y + h - 6],
                   fill=(220, 220, 220))
    draw.rectangle([x + w // 2 - 12, y + h - 8, x + w // 2 + 12, y + h - 4],
                   fill=(220, 220, 220))
    # signal arcs
    for r in (18, 30):
        draw.arc([x + w // 2 + 34 - r, y + 10 - r, x + w // 2 + 34 + r,
                  y + 10 + r], 300, 60, fill=(242, 193, 78), width=2)


def draw_store(draw, x, y, w, h):
    """Business: a storefront with a CLOSING sign and a striped awning."""
    draw.rectangle([x + 8, y + 18, x + w - 8, y + h - 6], fill=(238, 228, 205),
                   outline=(26, 26, 26))
    # awning stripes
    for i in range(6):
        col = (200, 40, 40) if i % 2 == 0 else (255, 255, 255)
        draw.rectangle([x + 8 + i * (w - 16) // 6, y + 18,
                        x + 8 + (i + 1) * (w - 16) // 6, y + 34], fill=col,
                       outline=(26, 26, 26))
    # windows and door
    draw.rectangle([x + 18, y + 46, x + 62, y + h - 14], fill=(120, 170, 210),
                   outline=(26, 26, 26))
    draw.rectangle([x + w - 62, y + 46, x + w - 18, y + h - 14],
                   fill=(120, 170, 210), outline=(26, 26, 26))
    draw.rectangle([x + w // 2 - 16, y + 46, x + w // 2 + 16, y + h - 14],
                   fill=(70, 70, 70), outline=(26, 26, 26))
    f_s = _font("DejaVuSans-Bold.ttf", 13)
    _chip(draw, x + w // 2 - 38, y + 2, 76, 20, (200, 40, 40), "CLOSING", f_s)


def draw_card(img, draw, x, y, w, h, cat, cat_key, flags, headline, deck,
              visual, portraits=()):
    """One story card: white rounded card, category + flags on top,
    headline, a long auto-fitted deck, and a compact visual anchored to
    the bottom. Portraits get a taller visual slot (76px); the drawn
    visuals get 64px, so the deck has room for 7-9 lines of text."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=CARD_BG,
                           outline=CARD_BORDER)
    pad = 14
    cx = x + pad
    cw = w - 2 * pad
    # header: category left, flags right
    f_cat = _font("DejaVuSans-Bold.ttf", 13)
    draw.text((cx, y + 12), cat, font=f_cat, fill=CAT_COLORS[cat_key])
    fx = x + w - pad
    for code in flags:
        fx = draw_flag(draw, img, code, fx, y + 12, 16)
        fx -= 6
    # headline
    f_head = _font("DejaVuSerif-Bold.ttf", 25)
    hy = y + 38
    for line in wrap_text(draw, headline, f_head, cw):
        draw.text((cx, hy), line, font=f_head, fill=INK)
        hy += 30
    # deck: auto-fit so it never reaches the visual area
    vh = 76 if visual == "portraits" else 64
    vy = y + h - pad - vh
    dy = hy + 6
    max_deck_h = vy - 6 - dy
    f_deck, deck_lines, line_h = fit_deck(draw, deck, cw, max_deck_h)
    for line in deck_lines:
        draw.text((cx, dy), line, font=f_deck, fill=(51, 51, 51))
        dy += line_h
    # visual area anchored to the bottom
    vw = cw
    if visual == "portraits":
        d = 64
        total = d * len(portraits) + 16 * (len(portraits) - 1)
        px = cx + (cw - total) // 2
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets")
        for name in portraits:
            circ = circle_portrait(img, os.path.join(base, name + ".png"), d)
            img.paste(circ, (px, vy + 6), circ)
            draw.ellipse([px, vy + 6, px + d - 1, vy + 6 + d - 1],
                         outline=(26, 26, 26), width=2)
            px += d + 16
    elif visual == "radar":
        draw_radar(draw, cx + 40, vy + 4, vw - 80, vh - 8)
    elif visual == "chart":
        draw_chart(draw, cx + 40, vy + 6, vw - 80, vh - 12)
    elif visual == "laptop":
        draw_laptop(draw, cx + 40, vy + 4, vw - 80, vh - 8)
    elif visual == "space":
        draw_space(draw, cx + 10, vy + 2, vw - 20, vh - 4)
    elif visual == "store":
        draw_store(draw, cx + 10, vy + 2, vw - 20, vh - 4)


def render():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ---- masthead ----
    f_mast = _font("DejaVuSerif-Bold.ttf", 56)
    mast = "THE WORLD IN ONE DAY"
    mw = draw.textlength(mast, font=f_mast)
    draw.text(((W - mw) / 2, 20), mast, font=f_mast, fill=INK)
    draw.line([(MARGIN, 92), (W - MARGIN, 92)], fill=RULE, width=2)
    f_sub = _font("DejaVuSans-Bold.ttf", 15)
    f_sub2 = _font("DejaVuSans.ttf", 15)
    draw.text((MARGIN, 100), "WEDNESDAY, 18 NOVEMBER 2026", font=f_sub,
              fill=INK)
    mid = "THE DAY IN WORLD NEWS"
    draw.text(((W - draw.textlength(mid, font=f_sub2)) / 2, 100), mid,
              font=f_sub2, fill=MUTED)
    right = "6 STORIES"
    draw.text((W - MARGIN - draw.textlength(right, font=f_sub), 100), right,
              font=f_sub, fill=INK)
    draw.line([(MARGIN, 126), (W - MARGIN, 126)], fill=RULE, width=3)

    # ---- numbers strip (7 stats) ----
    f_numlabel = _font("DejaVuSans-Bold.ttf", 12)
    draw.text((MARGIN, 138), "THE DAY IN", font=f_numlabel, fill=MUTED)
    draw.text((MARGIN, 154), "NUMBERS", font=f_numlabel, fill=MUTED)
    stats = [
        ("+4.7%", "NVDA AFTER HOURS"),
        ("3.3%", "KOSPI GAIN"),
        ("1", "LIGHT-DAY"),
        ("1,500", "JOBS CUT"),
        ("14", "EXPORT MONTHS"),
        ("19", "STORES CLOSING"),
        ("$116bn", "NVDA Q3 REV"),
    ]
    f_num = _font("DejaVuSans-Bold.ttf", 26)
    f_numsub = _font("DejaVuSans.ttf", 11)
    sx0 = MARGIN + 118
    scol = (CONTENT_W - 118) // 7
    for i, (num, lab) in enumerate(stats):
        sx = sx0 + i * scol
        draw.text((sx, 138), num, font=f_num, fill=INK)
        draw.text((sx, 168), lab, font=f_numsub, fill=MUTED)
    draw.line([(MARGIN, 188), (W - MARGIN, 188)], fill=RULE, width=1)

    # ---- story cards: 3 columns x 2 rows ----
    cw = (CONTENT_W - 2 * 12) // 3
    ch = 342
    xs = [MARGIN, MARGIN + cw + 12, MARGIN + 2 * (cw + 12)]
    ys = [198, 198 + ch + 12]
    cards = [
        dict(cat="THE GULF", key="gulf", flags=["bh", "kw", "ir"],
             headline="Bahrain stops Iranian air attack",
             deck="Bahrain's defence force said its air defences intercepted "
             "Iranian aerial attacks, accusing Tehran of a 'systematic "
             "hostile approach'. The Interior Ministry issued two threat "
             "alerts, urging residents to move to safety, then gave the "
             "all-clear after each. Kuwait's army said its defences were "
             "countering hostile drones early on Wednesday; it named no "
             "origin and reported no casualties or damage. On Tuesday, "
             "Iran's Guards fired drones at a US radar at Sheikh Isa Air "
             "Base, and the US struck a missile site on Qeshm Island.",
             visual="radar"),
        dict(cat="APEC — SHENZHEN", key="apec",
             flags=["ru", "cn", "us", "ph"],
             headline="Putin lands for APEC summit",
             deck="Russian President Vladimir Putin arrived in Shenzhen on "
             "Wednesday for the 33rd APEC Economic Leaders' Meeting, "
             "running 18-19 Nov. US President Donald Trump was due to meet "
             "Philippine President Ferdinand Marcos Jr. in Manila on "
             "Wednesday, then fly to Shenzhen. The first-ever trilateral "
             "meeting of Trump, Xi Jinping and Putin is scheduled for "
             "Thursday 19 Nov, with nuclear arms control expected to top "
             "the agenda.",
             visual="portraits", portraits=("putin", "trump")),
        dict(cat="MARKETS — AI", key="markets", flags=["kr", "jp"],
             headline="Nvidia beat lifts Asia stocks",
             deck="Asian stocks rose on Wednesday after Nvidia reported "
             "quarterly revenue above forecasts, its first earnings since "
             "Jensen Huang's abrupt departure as CEO. Nvidia shares rose "
             "4.7% in after-hours trading. MSCI's Asia-Pacific index "
             "outside Japan rose 0.9%; South Korea's KOSPI gained as much "
             "as 3.3% and Japan's Nikkei rose 0.6%. Reuters reports Q3 "
             "revenue of $116 billion, up 103% year on year.",
             visual="chart"),
        dict(cat="CYBER — JAVA", key="cyber", flags=["kr"],
             headline="Seoul in emergency Java talks",
             deck="South Korea's presidential office held an emergency "
             "meeting with government agencies on Wednesday on "
             "pre-emptive measures against possible security flaws in the "
             "Java programming language, Yonhap reported. Officials from "
             "the military, the Ministry of Science and ICT and financial "
             "supervisory agencies attended. A cybersecurity researcher "
             "has said some of the world's most visited websites were "
             "compromised, according to the report.",
             visual="laptop"),
        dict(cat="SPACE", key="space", flags=[],
             headline="Voyager 1 hits one light-day",
             deck="On Wednesday 18 Nov at 5:16 a.m. ET (10:16 UTC), NASA's "
             "Voyager 1 reached one light-day from Earth, more than 16 "
             "billion miles (25.9 billion km) away, becoming the first "
             "human-made object ever to reach that distance. Light, or a "
             "radio signal, now takes a full 24 hours to reach it. "
             "Launched in 1977, it is already the most distant "
             "human-made object; Voyager 2 is not expected to reach one "
             "light-day until about November 2035.",
             visual="space"),
        dict(cat="BUSINESS", key="business", flags=["au"],
             headline="David Jones to cut 1,500 jobs",
             deck="Troubled Australian department store chain David Jones "
             "will cut about 1,500 jobs across 19 stores slated for "
             "closure after collapsing into administration, a union said "
             "on Wednesday. Only 170 of the 1,689 affected store workers "
             "had been offered redeployment. The chain entered "
             "administration on 5 Nov, owing at least A$459 million "
             "(about $310 million) to creditors, administrators said at a "
             "creditors' meeting on Tuesday.",
             visual="store"),
    ]
    for i, c in enumerate(cards):
        draw_card(img, draw, xs[i % 3], ys[i // 3], cw, ch,
                  c["cat"], c["key"], c["flags"], c["headline"], c["deck"],
                  c["visual"], portraits=c.get("portraits", ()))

    # ---- ALSO TODAY strip: three items, two lines each ----
    by = ys[1] + ch + 14
    bh = 72
    draw.rounded_rectangle([MARGIN, by, W - MARGIN, by + bh], radius=6,
                           fill=NAVY_BAND)
    f_al = _font("DejaVuSans-Bold.ttf", 13)
    f_lead = _font("DejaVuSans-Bold.ttf", 12)
    f_det = _font("DejaVuSans.ttf", 11)
    label = "ALSO TODAY:"
    lx = MARGIN + 14
    draw.text((lx, by + (bh - 13) // 2 - 1), label, font=f_al, fill=GOLD)
    col0 = lx + draw.textlength(label, font=f_al) + 16
    col_w = (W - MARGIN - 14 - col0) // 3
    items = [
        dict(lead="Japan exports", flag="jp",
             detail="Up a 14th successive month in October."),
        dict(lead="Oil eases", flag=None,
             detail="US crude stocks +5.28m barrels; Brent $92.98, WTI $85.45"),
        dict(lead="Anthropic IPO", flag=None, chart=True,
             detail="Due to price Wed; Nasdaq debut Thu as ANT, $70-78 a share"),
    ]
    for j, it in enumerate(items):
        cx = col0 + j * col_w
        tx = cx
        if it.get("flag"):
            # flag at the lead line, then the lead text after it
            draw_flag(draw, img, it["flag"], cx + 22, by + 10, 14)
            tx = cx + 28
        draw.text((tx, by + 10), it["lead"], font=f_lead,
                  fill=(255, 255, 255))
        if it.get("chart"):
            lw = draw.textlength(it["lead"], font=f_lead)
            gx = tx + lw + 8
            draw.line([(gx, by + 24), (gx + 8, by + 18), (gx + 16, by + 21),
                       (gx + 24, by + 12)], fill=(110, 220, 130), width=3)
        dy = by + 30
        for line in wrap_text(draw, it["detail"], f_det, col_w - 8):
            draw.text((cx, dy), line, font=f_det, fill=(215, 222, 235))
            dy += 15

    # ---- footer ----
    f_foot = _font("DejaVuSans.ttf", 11)
    f_foot_i = _font("DejaVuSerif.ttf", 11)
    fy = by + bh + 10
    s1 = "Sources: Reuters · Xinhua · France 24 · NASA · Yonhap · AP"
    draw.text(((W - draw.textlength(s1, font=f_foot)) / 2, fy), s1,
              font=f_foot, fill=MUTED)
    s2 = "Every story above was reported on Wednesday 18 November 2026."
    draw.text(((W - draw.textlength(s2, font=f_foot_i)) / 2, fy + 15), s2,
              font=f_foot_i, fill=MUTED)
    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    try:
        from PIL import Image  # noqa: F401  (render path needs Pillow)
    except ImportError:
        shutil.copyfile(os.path.join(here, "entry.png"), out_path)
        return 0
    img = render()
    img.save(out_path, "PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
