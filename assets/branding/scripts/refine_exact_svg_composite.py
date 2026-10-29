from playwright.sync_api import sync_playwright
from PIL import Image
import numpy as np

# Load original Image 2
img2_path = "/Users/contabilidad/.gemini/antigravity-ide/brain/fa5fa454-ce6d-4e6f-9a30-77dc642032c3/.user_uploaded/media_1793225948907.png"
base_img = Image.open(img2_path).convert("RGBA")
W, H = base_img.size

# We want an SVG overlay of width W=1024, height H=206
# Center of Y in Image 2 is at x = 522.5
# In Image 2, the letters sit from y = 35 to y = 163 (Height = 128px)
# In jayaj_mirror_variants.svg, coordinates were:
# y goes from -40 to +40 (Height = 80px)
# Scale factor s = 128.0 / 80.0 = 1.6!
# Center Y translation: y_mid = (35 + 163) / 2 = 99.0
# Translation in Y: 99.0

# Center X of J in Image 2 was 114
# In SVG, J center:
# The stem was at x in [-160, -142], capitel at [-206, -142].
# Width of J = 64px.
# Middle of J in SVG = -174.
# If we translate by dx: dx + (-174)*1.6 = 114 -> dx = 114 + 278.4 = 392.4
# Then the right mirrored J will be at:
# Center = 522.5 + (522.5 - 114) = 931.0
# Perfect symmetry!

svg_overlay = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <!-- Filter for subtle matching glow -->
    <filter id="softGlow" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="0.8" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Left J (Original) -->
  <g transform="translate(393, 99) scale(1.6)" filter="url(#softGlow)">
    <!-- Top Capitel -->
    <rect x="-206" y="-40" width="64" height="10" rx="2" fill="#FFFFFF"/>
    <!-- Stem and Hook -->
    <path d="M -160,-40 L -142,-40 L -142,15 C -142,32 -158,40 -178,40 C -195,40 -206,30 -206,16 L -190,16 C -190,22 -185,26 -178,26 C -166,26 -160,20 -160,15 Z" fill="#FFFFFF"/>
  </g>

  <!-- Right Mirrored J (Ⴑ) - Exact Mirror relative to x=522.5 -->
  <g transform="translate(522.5, 0) scale(-1, 1) translate(-522.5, 0)">
    <g transform="translate(393, 99) scale(1.6)" filter="url(#softGlow)">
      <!-- Top Capitel -->
      <rect x="-206" y="-40" width="64" height="10" rx="2" fill="#FFFFFF"/>
      <!-- Stem and Hook -->
      <path d="M -160,-40 L -142,-40 L -142,15 C -142,32 -158,40 -178,40 C -195,40 -206,30 -206,16 L -190,16 C -190,22 -185,26 -178,26 C -166,26 -160,20 -160,15 Z" fill="#FFFFFF"/>
    </g>
  </g>
</svg>
"""

svg_file = "/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/j_overlay.svg"
with open(svg_file, "w") as f:
    f.write(svg_overlay)

# Render SVG overlay to transparent PNG with Playwright
overlay_png = "/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/j_overlay.png"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H})
    page.set_content(f"""<!DOCTYPE html><html><body style="margin:0; background:transparent; overflow:hidden;">{svg_overlay}</body></html>""")
    page.screenshot(path=overlay_png, omit_background=True)
    browser.close()

# Now combine with Image 2 (keeping A Y A and the real background)
base_arr = np.array(base_img)
col_slice = base_arr[:, 200, :].copy()
clean_bg = np.tile(col_slice[:, np.newaxis, :], (1, W, 1))
final_img = Image.fromarray(clean_bg.astype(np.uint8), "RGBA")

# Paste A Y A (from x=210 to x=835)
aya_crop = base_img.crop((210, 0, 835, H))
final_img.paste(aya_crop, (210, 0), aya_crop)

# Paste the new vector J overlay
overlay_img = Image.open(overlay_png).convert("RGBA")
final_img.paste(overlay_img, (0, 0), overlay_img)

out_path = "/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/assets/branding/jayaj_master_hybrid_official.png"
final_img.save(out_path, "PNG")
print("Saved master hybrid official image to:", out_path)
