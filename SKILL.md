---
name: coordinate-plan-overlay
description: Calibrate a survey, cadastral, engineering or site plan against known coordinates and construct verifiable scaled lines, points, setbacks and grids. Use for coordinate-based diagrams or overlays on existing plans, especially when precise distances, alignment or intersections must be shown and checked.
---

# Coordinate Plan Overlay

Create a coordinate-based drawing that can be checked against the supplied plan. Follow user instructions and the platform's image, file and tool rules. Keep the user's original unmodified. Generative image editing does not guarantee geometric accuracy; never present generated or visually guessed lines as a calibrated result.

## Establish the geometry

1. Identify every source, coordinate system, unit, point label and date. Explicitly distinguish historical from modern labels, survey points from annotation leader ends, surveyed objects from cadastral boundaries, and straight-line distances from lengths along a polyline. Extract the numbers into a compact table, and check ambiguity against the source. Do not infer an unprovided coordinate conversion or historical/legal boundary.
2. Express each requested construction mathematically. Specify the origin, direction, units, distance, whether parallelism refers to a segment or infinite line, and how an endpoint is selected. If an offset must remain constant along a straight wall, use the direction between the correct wall vertices and its perpendicular distance. The closest point on the finite wall segment can differ from the closest point on its extended line.
3. Use full-precision computations and independently recompute constraints. For two-circle intersections examine both solutions, show the branch-selection basis, and handle zero, tangent and coincident cases. Never silently force incompatible constraints: quantify differences and identify viable alternatives. Separate uncertainty of the source survey from numerical rounding and image calibration.

## Calibrate the plan

Work in a single verified coordinate reference system. Prefer an original georeferenced vector plan. For an image, match at least four well-spread, noncollinear, clearly identified surveyed points with their *actual image pixel locations*, not the labels. Reserve at least one independently located check point, preferably near the intended drawing; use more when available. Record identities, coordinates, pixel locations and confidence. Flag ambiguous or obscured points rather than silently including them.

Fit a world-to-pixel affine transformation using centered coordinates. Check rank, singularity, fitted residuals and residuals on held-out points in pixels and ground units. Inspect whether residuals are systematic, whether points span the target, and whether axes have different scale, shear, rotation, mirroring or nonlinear distortion. Compare a simpler similarity transform where appropriate. Do not assert a threshold means survey accuracy: manually selected pixels and a single check point understate uncertainty. If the fit is inadequate for the requested use, investigate control selection and distortion, request a better scan or original plan as needed, and mark the result provisional. Extrapolated target areas deserve independent local checks.

The included `scripts/geometry.py` reads a JSON request from stdin and emits JSON. Set `operation`:
- `distance`: `a`, `b`.
- `along`: `start`, `through`, `length`, `domain` (`segment`, `ray`, or `line`). Always set the domain explicitly in new requests; older requests default to a ray.
- `line_circle_intersections`: `start`, `through`, `domain`, `center`, `radius`. Use this to meet an existing straight segment, ray or line at a fixed distance from an origin. For a polyline, test its segments separately and deduplicate shared-vertex hits.
- `circle_intersections`: `center1`, `radius1`, `center2`, `radius2`. Use this when the endpoint must satisfy two distances, not when it must lie on a pre-existing line. Check all returned candidates; do not assume an ordering conveys intent.
- `calibrate`: `controls` and `checkpoints`, each containing `name`, `world: [X,Y]`, and `pixel: [horizontal,vertical]`; supply positive `tolerance_world_units` appropriate to the use. Missing or reused holdouts, missing tolerance, or residuals above tolerance make the result `provisional`. Reject singular or ill-conditioned fits; don't substitute a visual guess. `passes_numerical_checks` is necessary, not sufficient: verify actual point identity, local coverage and visible alignment before calling it verified. A duplicated feature annotated under a different position/name in the source is still not independent.

NumPy is required. Preserve the transform, point list, tolerance and output for reproducibility. See [the runnable synthetic example](examples/README.md).

## Draw and verify

Choose and state a useful metric grid size. Derive the coordinate grid and all line endpoints from the same recorded transform; preserve X/Y orientation, aspect ratio and original plan features. For exact technical diagrams use a coordinate-based vector/CAD approach when permitted by the governing image-editing rules; when those rules require a different editor, comply and disclose precision limits. Draw selected points and requested lines in distinct colors with labels, include a scale bar or grid size, coordinate table, and distinguish proposed from existing lines. If multiple valid solutions exist, choose only when the user's intended geometry or source evidence supports a branch; otherwise present alternatives.

Check lengths, offsets, parallelism, all points and constraints independently in coordinate space. Compare the overlay with calibration and withheld controls on the original image and inspect the full output and enlarged detail for line placement, clipping, label overlap and legibility. Distinguish computed distances from measurements made on the raster. Report measured fit residuals, independent-check errors, visual identification limits and any unverified assumptions. Provide viewable and, where useful, scalable output; save deliverables according to workspace storage rules. Do not say legally established, geodetically certified or court-ready without appropriate evidence.

## Reuse and privacy

Keep the workflow general; do not include personal coordinates, private case documents or source images in a public skill. Treat a successful drawing as validation of that instance, not proof of accuracy on every plan. For a new case, repeat the fit and checks with that case's own points.
