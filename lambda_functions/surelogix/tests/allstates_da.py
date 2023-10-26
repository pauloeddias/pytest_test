from .BaseTest import BaseTest


def test_allstates_da():
    files_path = "surelogix/allstates_da"
    test = BaseTest(files_path)
    return test.res
