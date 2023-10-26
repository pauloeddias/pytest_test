from .BaseTest import BaseTest


def test_pegasus_pickupalert():
    files_path = "surelogix/pegasus_pickupalert"
    test = BaseTest(files_path)
    return test.res
