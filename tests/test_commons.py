import pytest
from core.commons import commons

def test_toCamelCase():
    """Test whether string gets correctly converted to camel case"""
    assert commons.toCamelCase('example string') == 'ExampleString'
    assert commons.toCamelCase('Example-string_2', replaceSepCharacters=True) == 'ExampleString2'
    assert commons.toCamelCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')) == 'ExampleString2'


def test_isSpelledWord():
    """Test whether string is spelled"""
    assert commons.isSpelledWord('e x a m p l e') == True
    assert commons.isSpelledWord('example') == False
    assert commons.isSpelledWord('e x am p l e') == False


def test_isInt():
    """Test whether string is spelled"""
    assert commons.isInt('1') == True
    assert commons.isInt(1) == True
    assert commons.isInt('1.1') == False
    assert commons.isInt('a') == False


def test_getDuration():
    """Test getDuration method"""

    class DialogSession():
        def __init__(self, retVal: dict):
            self.retVal = retVal
        @property
        def slotsAsObjects(self) -> dict:
            return self.retVal

    class TimeObject():
        def __init__(self, retVal: dict, entity: str = 'snips/duration'):
            self.retVal = retVal
            self._entity = entity
        @property
        def entity(self) -> str:
            return self._entity
        @property
        def value(self) -> dict:
            return self.retVal

    timeDict = {
        'seconds': 6,
		'minutes': 5,
		'hours': 4,
		'days': 3,
		'weeks': 2,
		'months': 1
    }
    assert commons.getDuration(DialogSession({'Duration': [TimeObject(timeDict)]})) == 3902706
    assert commons.getDuration(DialogSession({'Duration': [TimeObject(timeDict, 'customDurationIntent')]})) == 0
    assert commons.getDuration(DialogSession(dict())) == 0
