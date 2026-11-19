#!/usr/bin/env python3
"""Compute survey-plan geometry and affine calibration from a JSON request on stdin."""
import json
import math
import sys
import numpy as np

def point(value):
    arr = np.asarray(value, dtype=float)
    if arr.shape != (2,) or not np.all(np.isfinite(arr)):
        raise ValueError('Each point must have exactly two finite coordinates')
    return arr

def distance(a, b):
    return math.hypot(*(a - b))

def direction(a, b, domain):
    if domain not in ('line', 'ray', 'segment'):
        raise ValueError('Domain must be line, ray, or segment')
    span = distance(a, b)
    if span == 0 or not math.isfinite(span):
        raise ValueError('Direction points must be distinct with finite separation')
    return (b - a) / span, span

def along(a, b, length, domain='ray'):
    unit, span = direction(a, b, domain)
    length = float(length)
    if not math.isfinite(length):
        raise ValueError('Length must be finite')
    if domain != 'line' and length < 0:
        raise ValueError('Length must be non-negative on rays and segments')
    if domain == 'segment' and length > span:
        raise ValueError('Length exceeds the finite segment')
    return b.copy() if length == span else a + unit * length

def radius(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Radius must be finite and non-negative')
    return value

def roundoff(*values):
    # Floating-point slack only; never use plan/survey tolerances to snap geometry.
    return 8 * math.ulp(max(map(abs, values)))

def line_circle(a, b, center, r, domain):
    unit, span = direction(a, b, domain)
    r = radius(r)
    relative = center - a
    foot = float(relative @ unit)
    normal = np.array([-unit[1], unit[0]])
    offset = abs(float(relative @ normal))
    margin = r - offset
    if margin < -roundoff(r, offset):
        return []
    if margin <= 0:
        parameters = [foot]
    else:
        half_chord = math.sqrt(margin) * math.sqrt(r + offset)
        parameters = [foot - half_chord, foot + half_chord]
    points = []
    for t in parameters:
        if domain != 'line' and t < 0:
            if t < -roundoff(foot, r):
                continue
            t = 0.0
        if domain == 'segment' and t > span:
            if t - span > roundoff(span, foot, r):
                continue
            t = span
        p = (b if t == span else a + t * unit).tolist()
        if not points or p != points[-1]:
            points.append(p)
    return points

def circles(c1, r1, c2, r2):
    r1, r2 = radius(r1), radius(r2)
    delta = c2-c1
    d = distance(c1, c2)
    if d == 0:
        if r1 != r2:
            return []
        if r1 == 0:
            return [c1.tolist()]
        raise ValueError('Coincident nonzero circles have infinitely many intersections')
    if not math.isfinite(d):
        raise ValueError('Circle centers must have finite separation')
    scale = max(d, r1, r2)
    D, R1, R2 = d / scale, r1 / scale, r2 / scale
    if D == 0:
        raise ValueError('Circle dimensions exceed supported numerical range')
    external_gap, internal_gap = (R1 + R2) - D, D - abs(R1 - R2)
    if min(external_gap, internal_gap) < -roundoff(D, R1, R2):
        return []
    x = (((R1 - R2) / D) * (R1 + R2) + D) * (scale / 2)
    if min(external_gap, internal_gap) <= 0 or d == r1 + r2 or d == abs(r1 - r2):
        h = 0.0
    else:
        # Factorized form avoids subtracting nearly equal squares at tangency.
        h = (math.sqrt(external_gap * (R1 + R2 + D))
             * math.sqrt((internal_gap / D) * (1 + abs(R1 - R2) / D))
             * (scale / 2))
    u = delta/d
    mid = c1+x*u
    perpendicular = np.array([-u[1],u[0]])
    first = mid+h*perpendicular
    second = mid-h*perpendicular
    return [first.tolist()] if np.array_equal(first, second) else [first.tolist(),second.tolist()]

def calibrate(data):
    controls = data['controls']
    if len(controls) < 4:
        raise ValueError('Provide at least four well-distributed control points')
    xy = np.array([point(p['world']) for p in controls])
    pixels = np.array([point(p['pixel']) for p in controls])
    if len(np.unique(xy, axis=0)) != len(xy) or len(np.unique(pixels, axis=0)) != len(pixels):
        raise ValueError('Control points must have distinct world and image locations')
    origin = xy.mean(axis=0)
    centered = xy - origin
    # Reject gross numerical instability, not merely zero determinants. This
    # conservative numerical guard is separate from a plan's accuracy tolerance.
    max_condition = 1e6
    if np.linalg.matrix_rank(centered) < 2 or np.linalg.cond(centered) > max_condition:
        raise ValueError('Control points are collinear or nearly collinear')
    matrix = np.column_stack((np.ones(len(xy)), centered))
    coefficients = np.linalg.lstsq(matrix, pixels, rcond=None)[0]
    linear = coefficients[1:, :]
    condition = float(np.linalg.cond(linear))
    if not math.isfinite(condition) or condition > max_condition:
        raise ValueError('Calibration transform is singular or ill-conditioned')
    inverse = np.linalg.inv(linear)

    def metrics(p, world, pixel):
        q = np.r_[1, world-origin] @ coefficients
        error_px = pixel-q
        error_world = error_px @ inverse
        return {
            'name': p.get('name'),
            'predicted_pixel': q.tolist(),
            'residual_px': float(np.linalg.norm(error_px)),
            'residual_world_units': float(np.linalg.norm(error_world)),
        }

    names = {p['name'] for p in controls if p.get('name')}
    check_results = []
    for p in data.get('checkpoints', []):
        world, pixel = point(p['world']), point(p['pixel'])
        overlaps = (
            p.get('name') in names
            or np.any(np.linalg.norm(xy-world, axis=1) <= 1e-9)
            or np.any(np.linalg.norm(pixels-pixel, axis=1) <= 1e-9)
        )
        check_results.append(dict(metrics(p, world, pixel), independent=not overlaps))
    control_results = [metrics(p, w, u) for p, w, u in zip(controls, xy, pixels)]
    tolerance = data.get('tolerance_world_units')
    reasons = []
    if tolerance is None:
        reasons.append('missing_world_tolerance')
    else:
        tolerance = float(tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError('tolerance_world_units must be finite and positive')
        if any(p['residual_world_units'] > tolerance for p in control_results):
            reasons.append('control_residual_exceeds_tolerance')
        if any(p['independent'] and p['residual_world_units'] > tolerance for p in check_results):
            reasons.append('checkpoint_residual_exceeds_tolerance')
    if not any(p['independent'] for p in check_results):
        reasons.append('no_independent_checkpoint')
    if any(not p['independent'] for p in check_results):
        reasons.append('checkpoint_reuses_control')
    return {
        'status': 'provisional' if reasons else 'passes_numerical_checks',
        'reasons': reasons,
        'tolerance_world_units': tolerance,
        'transform_condition': condition,
        'origin': origin.tolist(),
        'coefficients': coefficients.tolist(),
        'controls': control_results,
        'checkpoints': check_results,
    }


def main(req):
    operation=req['operation']
    if operation=='calibrate': return calibrate(req)
    if operation=='distance': return {'distance':distance(point(req['a']),point(req['b']))}
    if operation=='along': return {'point':along(point(req['start']),point(req['through']),req['length'],req.get('domain','ray')).tolist()}
    if operation=='circle_intersections': return {'points':circles(point(req['center1']),req['radius1'],point(req['center2']),req['radius2'])}
    if operation=='line_circle_intersections':
        return {'points':line_circle(point(req['start']),point(req['through']),point(req['center']),req['radius'],req['domain'])}
    raise ValueError('Unknown operation')

if __name__ == '__main__':
    try:
        print(json.dumps(main(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
    except (ValueError, KeyError, TypeError, np.linalg.LinAlgError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
