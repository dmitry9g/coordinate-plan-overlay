# Synthetic plan overlay

No real survey or private inputs are used. The example includes four affine controls,
one withheld check near the construction, and a 0.05 m tolerance for this synthetic
case only. With Python and NumPy installed, run from the skill directory:

```sh
python examples/synthetic_overlay.py /tmp/coordinate-overlay-example
python -m unittest discover -s tests -v
```

Open `plan.svg` and `overlay.svg` from the output directory. The teal line starts
2.5 m along one finite segment and meets another finite segment at a distance of
4.5 m. An intersection with the infinite extension is discarded. The script checks
both the distance and membership on the target segment. It also shifts the withheld
point by five pixels and verifies that this second calibration is **provisional**;
`verification.json` records both results. Hand-picked control points on a real
scan still require visual and source checks.
