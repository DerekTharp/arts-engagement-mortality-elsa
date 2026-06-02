"""
Generate the directed acyclic graph (DAG) for the arts engagement MSM analysis.
Output: output/figures/figure1_dag.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(8, 4.5))
ax.set_xlim(-0.5, 10.5)
ax.set_ylim(-1.5, 4.0)
ax.set_aspect('equal')
ax.axis('off')

# Node positions (x, y)
nodes = {
    'A_{t-1}': (1.0, 1.5),
    'L_t':     (4.0, 1.5),
    'A_t':     (7.0, 1.5),
    'Y':       (9.5, 1.5),
    'V':       (4.0, 3.0),
    'U':       (4.0, 0.0),
}

labels = {
    'A_{t-1}': '$A_{t-1}$\nArts\nengagement',
    'L_t':     '$L_t$\nTime-varying\nhealth',
    'A_t':     '$A_t$\nArts\nengagement',
    'Y':       '$Y$\nMortality',
    'V':       '$V$\nBaseline\ncovariates',
    'U':       '$U$\nUnmeasured\nsocial factors',
}

box_w = 1.6
box_h = 1.1

for name, (x, y) in nodes.items():
    fc = 'white'
    ls = '-'
    lw = 1.5
    if name == 'U':
        ls = '--'
        lw = 1.0
    rect = mpatches.FancyBboxPatch(
        (x - box_w/2, y - box_h/2), box_w, box_h,
        boxstyle="round,pad=0.1",
        facecolor=fc, edgecolor='black',
        linewidth=lw, linestyle=ls
    )
    ax.add_patch(rect)
    ax.text(x, y, labels[name], ha='center', va='center',
            fontsize=7.5, fontfamily='serif', linespacing=1.15)

def draw_arrow(start_name, end_name, color='black', style='->', ls='-', lw=1.2,
               connectionstyle='arc3,rad=0'):
    sx, sy = nodes[start_name]
    ex, ey = nodes[end_name]
    # Offset from box edges
    dx = ex - sx
    dy = ey - sy
    dist = (dx**2 + dy**2)**0.5
    # Shorten by half box dimension in the direction of travel
    frac_start = (box_w/2 * abs(dx/dist) + box_h/2 * abs(dy/dist)) / dist if dist > 0 else 0
    frac_end = frac_start
    sx2 = sx + dx * frac_start
    sy2 = sy + dy * frac_start
    ex2 = ex - dx * frac_end
    ey2 = ey - dy * frac_end

    arrow = FancyArrowPatch(
        (sx2, sy2), (ex2, ey2),
        arrowstyle=style,
        color=color,
        linewidth=lw,
        linestyle=ls,
        connectionstyle=connectionstyle,
        mutation_scale=12,
        shrinkA=0, shrinkB=0,
    )
    ax.add_patch(arrow)

# Solid arrows — observed causal paths
draw_arrow('A_{t-1}', 'L_t')         # prior engagement -> health
draw_arrow('L_t', 'A_t')              # health -> current engagement
draw_arrow('A_t', 'Y')                # engagement -> mortality
draw_arrow('L_t', 'Y', connectionstyle='arc3,rad=-0.15')  # health -> mortality
draw_arrow('A_{t-1}', 'A_t', connectionstyle='arc3,rad=-0.35')  # persistence
draw_arrow('V', 'A_{t-1}', connectionstyle='arc3,rad=0.15')
draw_arrow('V', 'A_t', connectionstyle='arc3,rad=-0.15')
draw_arrow('V', 'L_t')
draw_arrow('V', 'Y', connectionstyle='arc3,rad=-0.25')

# Dashed arrows — unmeasured
draw_arrow('U', 'A_{t-1}', ls='--', color='grey', connectionstyle='arc3,rad=-0.15')
draw_arrow('U', 'A_t', ls='--', color='grey', connectionstyle='arc3,rad=0.15')
draw_arrow('U', 'Y', ls='--', color='grey', connectionstyle='arc3,rad=0.25')

fig.tight_layout()
fig.savefig(
    'output/figures/figure1_dag.png',
    dpi=300, bbox_inches='tight', facecolor='white'
)
print("DAG saved to output/figures/figure1_dag.png")
