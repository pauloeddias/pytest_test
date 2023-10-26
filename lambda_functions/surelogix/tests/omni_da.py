from .BaseTest import BaseTest


def test_omni_da():
    files_path = "surelogix/omni_da"
    test = BaseTest(files_path)
    return test.res
