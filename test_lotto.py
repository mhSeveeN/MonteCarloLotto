"""Testy jednostkowe generatora liczb. Uruchomienie: python -m unittest -v"""

import math
import unittest

import lotto
from lotto import GAMES, LCG, METHODS, PRNGS


class DrawTests(unittest.TestCase):
    def test_numbers_unique_and_in_range(self):
        """Warunek zadania: liczby się nie powtarzają i mieszczą się w zakresie."""
        for game in GAMES.values():
            for method in METHODS:
                for prng in PRNGS:
                    rng = lotto.make_rng(prng, 123)
                    for _ in range(500):
                        numbers = lotto.draw(game, rng, method).numbers
                        self.assertEqual(len(numbers), game.picks)
                        self.assertEqual(len(set(numbers)), game.picks)
                        self.assertTrue(all(1 <= n <= game.pool for n in numbers))
                        self.assertEqual(numbers, sorted(numbers))

    def test_seed_gives_reproducible_results(self):
        for prng in ("mt", "lcg"):
            a = lotto.draw(GAMES["lotto"], lotto.make_rng(prng, 7)).numbers
            b = lotto.draw(GAMES["lotto"], lotto.make_rng(prng, 7)).numbers
            self.assertEqual(a, b)

    def test_validate_rejects_bad_draws(self):
        game = GAMES["lotto"]
        with self.assertRaises(ValueError):
            lotto.validate_draw(game, [1, 2, 3, 4, 5])  # za mało liczb
        with self.assertRaises(ValueError):
            lotto.validate_draw(game, [1, 1, 2, 3, 4, 5])  # powtórzenie
        with self.assertRaises(ValueError):
            lotto.validate_draw(game, [1, 2, 3, 4, 5, 50])  # poza zakresem


class LCGTests(unittest.TestCase):
    def test_first_values(self):
        gen = LCG(0)
        first = gen.next_int()
        self.assertEqual(first, LCG.C)
        self.assertEqual(gen.next_int(), (LCG.A * first + LCG.C) % LCG.M)

    def test_random_in_unit_interval(self):
        gen = LCG(99)
        self.assertTrue(all(0.0 <= gen.random() < 1.0 for _ in range(10_000)))


class StatisticsTests(unittest.TestCase):
    def test_hypergeometric_sums_to_one(self):
        for game in GAMES.values():
            total = sum(lotto.hypergeometric_pmf(game, m) for m in range(game.picks + 1))
            self.assertAlmostEqual(total, 1.0, places=9)

    def test_lotto_jackpot_probability(self):
        self.assertEqual(math.comb(49, 6), 13_983_816)
        self.assertAlmostEqual(lotto.hypergeometric_pmf(GAMES["lotto"], 6), 1 / 13_983_816)

    def test_chi2_critical_value(self):
        self.assertAlmostEqual(lotto.chi2_critical_005(48), 65.17, delta=0.1)

    def test_simulation_is_uniform(self):
        report = lotto.simulate(GAMES["lotto"], "reject", "mt", 20_000, seed=42)
        self.assertTrue(report.uniform_ok)
        self.assertEqual(sum(report.counts.values()), 20_000 * 6)


if __name__ == "__main__":
    unittest.main()
