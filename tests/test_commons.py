from core.commons.CommonsManager import CommonsManager

def test_getFunctionCaller():
    assert CommonsManager.getFunctionCaller(1) == 'test_commons'

def test_toPascalCase():
    """Test whether string gets correctly converted to pascal case"""
    assert CommonsManager.toPascalCase('example string') == 'ExampleString'
    assert CommonsManager.toPascalCase('Example-string_2', replaceSepCharacters=True) == 'ExampleString2'
    assert CommonsManager.toPascalCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')) == 'ExampleString2'

def test_toCamelCase():
    """Test whether string gets correctly converted to camel case"""
    assert CommonsManager.toCamelCase('example string') == 'exampleString'
    assert CommonsManager.toCamelCase('Example-string_2', replaceSepCharacters=True) == 'exampleString2'
    assert CommonsManager.toCamelCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')) == 'exampleString2'


def test_isSpelledWord():
    """Test whether string is spelled"""
    assert CommonsManager.isSpelledWord('e x a m p l e') == True
    assert CommonsManager.isSpelledWord('example') == False
    assert CommonsManager.isSpelledWord('e x am p l e') == False


def test_getDuration():
    """Test getDuration method"""

    class DialogSession:
        def __init__(self, retVal: dict):
            self.retVal = retVal
        @property
        def slotsAsObjects(self) -> dict:
            return self.retVal

    class TimeObject:
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
    assert CommonsManager.getDuration(DialogSession({'Duration': [TimeObject(timeDict)]})) == 3902706
    assert CommonsManager.getDuration(DialogSession({'Duration': [TimeObject(timeDict, 'customDurationIntent')]})) == 0
    assert CommonsManager.getDuration(DialogSession(dict())) == 0
