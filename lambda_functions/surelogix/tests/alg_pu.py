from .BaseTest import BaseTest


def test_alg_pu():
    files_path = "surelogix/alg_pu"
    test = BaseTest(files_path)
    return test.res
