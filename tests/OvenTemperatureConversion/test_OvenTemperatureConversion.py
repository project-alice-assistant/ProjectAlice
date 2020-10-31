import unittest
from unittest import TestCase
from unittest import mock
from unittest.mock import MagicMock
from skills.OvenTemperatureConversion.OvenTemperatureConversion import OvenTemperatureConversion


class TestOvenTemperatureConversion(TestCase):

    def test_convertingToCelciusIntent(self):
        pass  # To be implemented or nothing to test()


    def test_convertingToFahrenheitIntent(self):
        pass  # To be implemented or nothing to test()


    def test_readyToConvert(self):
        pass  # To be implemented or nothing to test()


    def test_askToRepeatWithNumber(self):
        pass  # To be implemented or nothing to test()


    # todo Psycho please attempt this one so i can see how to do methods with dialog session etc
    def test_gasMarkIntent(self):
        pass  # To be implemented or nothing to test()


    def test_convertToFahrenheit(self):
        result = OvenTemperatureConversion.convertToFahrenheit(temperature=0)
        self.assertEquals(first=result, second=32)


    def test_convertToCelsius(self):
        result = OvenTemperatureConversion.convertToCelsius(temperature=32)
        self.assertEquals(first=result, second=0)


if __name__ == '__main__':
    unittest.main()
