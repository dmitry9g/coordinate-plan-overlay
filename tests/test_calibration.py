import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from geometry import calibrate


def points(world, transform):
    return [dict(name=str(i), world=[x, y], pixel=transform(x, y))
            for i, (x, y) in enumerate(world)]


def affine(x, y):
    x, y = x-500000, y-1300000
    return [100+9*x+2*y, 200+x-11*y]


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        controls = points([(500000, 1300000), (500010, 1300000),
                           (500000, 1300010), (500010, 1300010)], affine)
        checks = points([(500002, 1300004)], affine)
        checks[0]['name'] = 'independent'
        self.request = dict(controls=controls, checkpoints=checks, tolerance_world_units=0.05)

    def test_good_affine_with_large_world_coordinates(self):
        result = calibrate(self.request)
        self.assertEqual(result['status'], 'passes_numerical_checks')
        self.assertLess(result['checkpoints'][0]['residual_world_units'], 1e-10)

    def test_missing_holdout_and_tolerance(self):
        del self.request['checkpoints'], self.request['tolerance_world_units']
        result = calibrate(self.request)
        self.assertEqual(result['status'], 'provisional')
        self.assertCountEqual(result['reasons'], ['no_independent_checkpoint', 'missing_world_tolerance'])

    def test_relabelled_control_not_independent(self):
        self.request['checkpoints'] = [dict(self.request['controls'][0], name='new label')]
        result = calibrate(self.request)
        self.assertFalse(result['checkpoints'][0]['independent'])
        self.assertIn('checkpoint_reuses_control', result['reasons'])

    def test_wrong_holdout_blocks_verification(self):
        self.request['checkpoints'][0]['pixel'][1] += 2
        result = calibrate(self.request)
        self.assertEqual(result['status'], 'provisional')
        self.assertIn('checkpoint_residual_exceeds_tolerance', result['reasons'])

    def test_nearly_collapsed_transform_rejected(self):
        self.request['controls'] = points(
            [p['world'] for p in self.request['controls']],
            lambda x, y: [(x-500000)*100, (y-1300000)*1e-8])
        with self.assertRaisesRegex(ValueError, 'ill-conditioned'):
            calibrate(self.request)

    def test_nearly_collinear_controls_rejected(self):
        self.request['controls'] = points(
            [(0, 0), (1, 1e-9), (2, 0), (3, 1e-9)], lambda x, y: [x, y])
        with self.assertRaisesRegex(ValueError, 'nearly collinear'):
            calibrate(self.request)

    def test_duplicate_controls_rejected(self):
        self.request['controls'].append(dict(self.request['controls'][0], name='duplicate'))
        with self.assertRaisesRegex(ValueError, 'distinct'):
            calibrate(self.request)


if __name__ == '__main__':
    unittest.main()
