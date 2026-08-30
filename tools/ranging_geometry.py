from matplotlib.patches import Polygon, FancyArrowPatch, Circle
import matplotlib.pyplot as plt
import os
import matplotlib
matplotlib.use("Agg")

FIG = "figures"
os.makedirs(FIG, exist_ok=True)

INK = "#1a1a1a"
BLUE = "#1f4e79"
RED = "#c1666b"
GREY = "#8a8a8a"

plt.rcParams.update({"figure.dpi": 200, "font.size": 9})

PX = 0.75
IX = 3.10
SX = 9.20
SC = 0.72
SR = 0.62
scale = (IX - PX) / (SX - PX)
top_i, bot_i = (SC + SR) * scale, (SC - SR) * scale

fig, ax = plt.subplots(figsize=(8.4, 3.6))
ax.set_xlim(-0.8, 11.6)
ax.set_ylim(-1.9, 3.4)
ax.axis("off")

ax.plot([-0.2, 10.8], [0, 0], color=GREY, linewidth=0.9,
        linestyle=(0, (6, 4)), zorder=0)
ax.text(10.9, -0.22, "optical axis", fontsize=7.5, color=GREY, va="center")

for ys in (SC + SR, SC - SR):
    ax.plot([PX, SX], [0, ys], color=GREY, linewidth=0.8, alpha=0.6,
            zorder=1)

ax.add_patch(Polygon([[-0.35, -0.42], [0.35, -0.42], [0.35, 0.42],
                      [-0.35, 0.42]], closed=True,
                     facecolor="white", edgecolor=INK, linewidth=1.3,
                     zorder=3))
ax.add_patch(Polygon([[0.35, -0.26], [PX, -0.46], [PX, 0.46],
                      [0.35, 0.26]], closed=True,
                     facecolor=INK, edgecolor=INK, linewidth=1, zorder=3))
ax.text(0.1, -0.82, "camera", fontsize=8.5, ha="center", color=INK)
ax.text(0.1, -1.62, "calibrated:\n$f_y$ known", fontsize=7.5, ha="center",
        color=GREY, style="italic")

ax.plot([IX, IX], [-0.95, 1.35], color=BLUE, linewidth=1.6, zorder=2)
ax.text(IX, 1.55, "image plane", fontsize=8, ha="center", color=BLUE)

ax.add_patch(Polygon([[IX - 0.06, bot_i], [IX + 0.06, bot_i],
                      [IX + 0.06, top_i], [IX - 0.06, top_i]],
                     closed=True, facecolor=RED, edgecolor=RED, zorder=4))

bx = IX - 0.34
ax.plot([bx, bx], [bot_i, top_i], color=RED, linewidth=1.2, zorder=4)
for yy in (bot_i, top_i):
    ax.plot([bx, bx + 0.11], [yy, yy], color=RED, linewidth=1.2, zorder=4)
ax.text(bx - 0.12, (bot_i + top_i) / 2, "$h_{px}$", fontsize=11, color=RED,
        ha="right", va="center")

ax.plot([SX, SX], [-1.35, SC - SR + 0.04], color=GREY, linewidth=2.4,
        solid_capstyle="butt", zorder=2)
ax.add_patch(Circle((SX, SC), SR, facecolor="white", edgecolor=RED,
                    linewidth=3.4, zorder=4))
ax.plot([SX - 0.34, SX + 0.34], [SC, SC], color=RED, linewidth=3.4,
        zorder=5)
ax.text(SX, -1.68, "traffic sign", fontsize=8.5, ha="center", color=INK)

hx = SX + 0.95
ax.plot([hx, hx], [SC - SR, SC + SR], color=RED, linewidth=1.2)
for yy in (SC - SR, SC + SR):
    ax.plot([hx - 0.11, hx], [yy, yy], color=RED, linewidth=1.2)
ax.text(hx + 0.14, SC, "$H$", fontsize=11, color=RED, va="center")
ax.text(hx + 0.14, SC + 0.34, "standardised\nby VwV-StVO", fontsize=7,
        color=GREY, va="bottom", style="italic")

zy = -1.05
ax.add_patch(FancyArrowPatch((PX, zy), (SX, zy), arrowstyle="<->",
                             mutation_scale=11, color=BLUE, linewidth=1.3))
ax.text((PX + SX) / 2, zy - 0.34, "$Z$   the quantity being estimated",
        fontsize=9, ha="center", color=BLUE)

ax.text(5.6, 2.85, r"$Z \;=\; \dfrac{f_y \, H}{h_{px}}$", fontsize=17,
        ha="center", va="center", color=INK)
ax.text(5.6, 2.05,
        "one image, one calibrated camera, one known physical size",
        fontsize=8, ha="center", color=GREY, style="italic")

fig.tight_layout()
fig.savefig(f"{FIG}/ranging_geometry.png", bbox_inches="tight",
            facecolor="white")
plt.close(fig)
print("wrote figures/ranging_geometry.png")
