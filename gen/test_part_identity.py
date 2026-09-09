import unittest

from part_identity import decode, engineering_value, identity_errors


class PartIdentity(unittest.TestCase):
    def test_vishay_precision_order_codes_include_tcr(self):
        part = decode("TNPU060355K6HZEN00")
        self.assertEqual((part.value, part.size, part.tolerance, part.tcr_ppm),
                         (55600, "0603", .02, 5))
        part = decode("TNPW0603102KBYEA")
        self.assertEqual((part.value, part.tolerance, part.tcr_ppm), (102000, .1, 10))
        self.assertEqual(decode("TNPU060310K2HWEN00").tcr_ppm, 2)
        self.assertTrue(identity_errors("102k 0.1% 5ppm", "Resistor_SMD:R_0603_1608Metric",
                                        "TNPW0603102KBYEA"))

    def test_vishay_unpublished_grade_and_range_combinations_remain_unknown(self):
        for mpn in ("TNPU0603102KHZEN00", "TNPU060355K6HWEN00", "TNPU060355K6HYEN00",
                    "TNPU040210K0HZEN00", "TNPW06031M00BYEA", "TNPW060310K0FYEA",
                    "TNPU060310K0HZEA", "TNPU060310K0HZEI00", "TNPW060310K0BYEC"):
            with self.subTest(mpn=mpn):
                self.assertIsNone(decode(mpn))

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
