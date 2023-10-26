from .BaseTest import BaseTest


def dba_pickupalert():
    files_path = "surelogix/dba/pickupalert"
    test = BaseTest(files_path)
    return test.res