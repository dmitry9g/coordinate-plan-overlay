"""Run from the skill root: python examples/synthetic_overlay.py OUTPUT_DIRECTORY."""
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from geometry import main

ROOT = Path(__file__).resolve().parent
out = Path(sys.argv[1]) if len(sys.argv) == 2 else None
if out is None:
    sys.exit(__doc__)
out.mkdir(parents=True, exist_ok=True)
request = json.loads((ROOT / 'synthetic_calibration.json').read_text())
fit = main(request)
assert fit['status'] == 'passes_numerical_checks', fit
bad_request = json.loads(json.dumps(request))
bad_request['checkpoints'][0]['pixel'][0] += 5
bad_fit = main(bad_request)
assert bad_fit['status'] == 'provisional', bad_fit

start = [2, 3]
origin = main(dict(operation='along', start=start, through=[6, 3],
                   length=2.5, domain='segment'))['point']
# Target is an existing finite segment, not a radial distance from its start.
target = ([2, 6], [8, 6])
candidates = main(dict(operation='line_circle_intersections', start=target[0],
                       through=target[1], center=origin, radius=4.5,
                       domain='segment'))['points']
assert len(candidates) == 1, candidates
end = candidates[0]
assert abs(np.linalg.norm(np.subtract(origin, end)) - 4.5) < 1e-9
assert abs(end[1]-6) < 1e-9 and 2 <= end[0] <= 8

def px(world):
    return np.r_[1, np.subtract(world, fit['origin'])] @ fit['coefficients']

def xy(world):
    return ' '.join(f'{x:.3f}' for x in px(world))

def line(a, b, color, width):
    return f'<path d="M {xy(a)} L {xy(b)}" stroke="{color}" stroke-width="{width}"/>'

def marker(world, name, color):
    x, y = px(world)
    return (f'<circle cx="{x:.3f}" cy="{y:.3f}" r="4" fill="{color}"/>'
            f'<text x="{x+8:.3f}" y="{y-8:.3f}">{name}</text>')

plan = [line([x, 0], [x, 10], '#d5dfe7', 1) for x in range(11)]
plan += [line([0, y], [10, y], '#d5dfe7', 1) for y in range(11)]
plan += [line(start, [6, 3], '#334155', 3), line(*target, '#334155', 3)]
plan += [marker(p['world'], p['name'], '#64748b')
         for p in request['controls'] + request['checkpoints']]
overlay = [line(origin, end, '#087e8b', 4),
           marker(origin, 'A', '#087e8b'), marker(end, 'B', '#087e8b')]

def svg(shapes):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 420" '
            'width="500" height="420" font-family="sans-serif" font-size="13">'
            '<rect width="500" height="420" fill="#f8fafc"/>'
            '<text x="25" y="395" fill="#334155">Synthetic plan · grid: 1 m</text>'
            + ''.join(shapes) + '</svg>\n')

(out / 'plan.svg').write_text(svg(plan))
(out / 'overlay.svg').write_text(svg(plan + overlay))
(out / 'verification.json').write_text(json.dumps(
    dict(calibration=fit, deliberately_bad_calibration=bad_fit, constructed=dict(
        start=origin, end=end, end_pixel=px(end).tolist(), distance_m=4.5)), indent=2)+'\n')
print('Wrote plan.svg, overlay.svg and verification.json')
