import unittest

from part_identity import decode, engineering_value, identity_errors


class PartIdentity(unittest.TestCase):
    def test_reel_digits_are_not_resistance_digits(self):
        self.assertEqual(decode("RT0603BRD075KL").value, 5000)
        self.assertEqual(decode("RT0603BRD0775KL").value, 75000)
        self.assertEqual(decode("RT0603BRD0743KL").value, 43000)
        self.assertEqual(decode("RC0603FR-0736K1L").value, 36100)

    def test_original_regulator_errors_fail(self):
        for value, mpn in [("75.0k 0.1%", "RT0603BRD075KL"),
                           ("74.3k 0.1%", "RT0603BRD0743KL"),
                           ("100k 1%", "RC0603FR-07169KL"),
                           ("100k 1%", "RC0603FR-0736K1L")]:
            with self.subTest(mpn=mpn):
                self.assertTrue(identity_errors(value, "Resistor_SMD:R_0603_1608Metric", mpn))

    def test_embossed_tape_resistor_keeps_value_size_and_tolerance(self):
        part = decode("RC2010FK-071KL")
        self.assertEqual((part.value, part.size, part.tolerance), (1000, "2010", 1))
        self.assertEqual(identity_errors("1k 1% 0.75W", "Resistor_SMD:R_2010_5025Metric",
                                         "RC2010FK-071KL"), [])
        self.assertTrue(identity_errors("1k 1%", "Resistor_SMD:R_1206_3216Metric",
                                        "RC2010FK-071KL"))

    def test_capacitance_and_package_are_independent_checks(self):
        self.assertTrue(identity_errors("100n", "Capacitor_SMD:C_0402_1005Metric",
                                        "GRM1555C1H101JA01D"))
        errors = identity_errors("47u 6.3V", "Capacitor_SMD:C_1206_3216Metric",
                                 "GRM32ER60J476ME20L")
        self.assertEqual(len(errors), 1)
        self.assertIn("1210", errors[0])
        self.assertEqual(identity_errors("47u 6.3V", "Capacitor_SMD:C_1210_3225Metric",
                                         "GRM32ER60J476ME20L"), [])

    def test_insufficient_voltage_and_tolerance_fail(self):
        self.assertTrue(identity_errors("1u 25V", "Capacitor_SMD:C_0603_1608Metric",
                                        "GRM188R60J105KA01D"))
        self.assertTrue(identity_errors("100k 0.1%", "Resistor_SMD:R_0603_1608Metric",
                                        "RC0603FR-07100KL"))

    def test_unknown_parts_are_not_claimed_as_decoded(self):
        self.assertIsNone(decode("unverified-part"))
        self.assertEqual(engineering_value("4k7"), 4700)
        self.assertAlmostEqual(engineering_value("100nF"), 1e-7)


if __name__ == "__main__":
    unittest.main()
