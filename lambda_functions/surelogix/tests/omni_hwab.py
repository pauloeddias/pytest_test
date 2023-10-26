from .BaseTest import BaseTest


def test_omni_hwab():
    files_path = "surelogix/omni_hwab"
    test = BaseTest(files_path)
    return test.res
