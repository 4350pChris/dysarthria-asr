import unittest

from prepare_combined_training_data import split_name


class SplitNameTest(unittest.TestCase):
    def test_groups_are_stable_and_text_based(self) -> None:
        self.assertEqual(split_name("Hallo, Welt!"), split_name("hallo welt"))
        self.assertEqual({split_name(str(number)) for number in range(100)}, {"train", "validation", "test"})


if __name__ == "__main__":
    unittest.main()
