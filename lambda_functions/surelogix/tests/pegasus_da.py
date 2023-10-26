from .BaseTest import BaseTest

def test_pegasus_da():
    files_path = "surelogix/pegasus/delivery_alert"
    test = BaseTest(files_path)
    return test.res
