"""Plot only sanitized, independently reviewed primary capture counts."""
import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt'] = 'esp-sdr-primary-capture-opportunity'
import matplotlib.pyplot as plt

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--input', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
d = json.loads(a.input.read_text())
keys = ('guarded_ON_1', 'guarded_ON_2', 'guarded_ON_3', 'OFF', 'boundary_or_guard')
counts = [d['phase_counts'][k] for k in keys]
if any(type(n) is not int or n < 0 for n in counts) or sum(counts) != d['captures']:
    raise ValueError('Complete, consistent capture accounting required')
fig, ax = plt.subplots(figsize=(9, 4.4), layout='constrained')
fig.patch.set_facecolor('#fbf8f1'); ax.set_facecolor('#fbf8f1')
bars = ax.barh(['Source 1 guarded ON', 'Source 2 guarded ON', 'Source 3 guarded ON', 'OFF', 'Boundary / guard'], counts, color=['#177f86'] * 3 + ['#8794a0', '#c38838'])
ax.bar_label(bars, padding=5, fontsize=12)
ax.invert_yaxis(); ax.set_xlim(0, max(counts) * 1.13)
ax.set_xlabel('Complete saved captures, not emitted events')
ax.set_title(f"{d['captures']} intact captures: only {sum(counts[:3])} wholly inside guarded source-on intervals", loc='left', fontsize=12, pad=16)
for side in ('top', 'right', 'left'): ax.spines[side].set_visible(False)
ax.tick_params(axis='y', length=0); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
fig.text(.01, -.025, f"Decoded owned primary PDUs: {d['decoder_counts']['valid_owned_primary']}. Air-emission count and reception rate remain unknown.", fontsize=10)
fig.savefig(a.output, format='svg', metadata={'Date': None}, bbox_inches='tight')
plt.close(fig)
