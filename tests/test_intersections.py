import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from geometry import main


class GeometryTests(unittest.TestCase):
    def along(self, length, **kwargs):
        return main(dict(operation='along', start=[0, 0], through=[3, 0],
                         length=length, **kwargs))['point']

    def intersect(self, start, through, center, radius, domain):
        return main(dict(operation='line_circle_intersections', start=start,
                         through=through, center=center, radius=radius,
                         domain=domain))['points']

    def circle_pair(self, c1, r1, c2, r2):
        return main(dict(operation='circle_intersections', center1=c1,
                         radius1=r1, center2=c2, radius2=r2))['points']

    def test_along_domains_and_boundaries(self):
        self.assertEqual(self.along(5), [5, 0])
        self.assertEqual(self.along(-2, domain='line'), [-2, 0])
        self.assertEqual(self.along(3, domain='segment'), [3, 0])
        for length, domain in [(5, 'segment'), (-2, 'ray'), (-2, 'segment'), (2, 'arc')]:
            with self.subTest(length=length, domain=domain), self.assertRaises(ValueError):
                self.along(length, domain=domain)

    def test_domains_filter_geometric_roots(self):
        for domain, expected in [('line', [[-2, 0], [2, 0]]),
                                 ('ray', [[2, 0]]), ('segment', [])]:
            with self.subTest(domain=domain):
                pts = self.intersect([0, 0], [1, 0], [0, 0], 2, domain)
                np.testing.assert_allclose(pts, expected, rtol=0, atol=1e-12)

    def test_both_endpoints_returned_in_direction_order(self):
        self.assertEqual(self.intersect([2, 0], [-2, 0], [0, 0], 2, 'segment'),
                         [[2, 0], [-2, 0]])

    def test_tangency_miss_and_point_circle(self):
        self.assertEqual(self.intersect([0, 0], [5, 0], [3, 2], 2, 'segment'), [[3, 0]])
        self.assertEqual(self.intersect([0, 0], [5, 0], [3, 2.01], 2, 'segment'), [])
        self.assertEqual(self.intersect([0, 0], [5, 0], [3, 0], 0, 'segment'), [[3, 0]])

    def test_bad_direction_and_radius_rejected(self):
        with self.assertRaises(ValueError):
            self.intersect([0, 0], [0, 0], [2, 0], 1, 'line')
        with self.assertRaises(ValueError):
            self.intersect([0, 0], [2, 0], [2, 0], -1, 'line')

    def test_large_coordinate_offsets(self):
        start = [800000, 3000000]
        pts = self.intersect(start, [800019, 3000000], [800003, 3000004], 5, 'segment')
        np.testing.assert_allclose(pts, [start, [800006, 3000000]], rtol=0, atol=1e-9)

    def test_circle_pair_degeneracies(self):
        self.assertEqual(self.circle_pair([2, 1], 0, [2, 1], 0), [[2, 1]])
        self.assertEqual(self.circle_pair([2, 1], 1, [2, 1], 2), [])
        with self.assertRaisesRegex(ValueError, 'infinitely many'):
            self.circle_pair([2, 1], 1, [2, 1], 1)
        self.assertEqual(self.circle_pair([0, 0], 3, [7, 0], 4), [[3, 0]])
        self.assertEqual(self.circle_pair([0, 0], 3, [2, 0], 1), [[3, 0]])
        self.assertEqual(self.circle_pair([0, 0], 3, [0, 1], 1), [])
        self.assertEqual(self.circle_pair([0, 0], 3, [5, 0], 1), [])

    def test_circle_pair_both_solutions(self):
        np.testing.assert_allclose(self.circle_pair([0, 0], 5, [6, 0], 5),
                                   [[3, 4], [3, -4]], rtol=0, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
