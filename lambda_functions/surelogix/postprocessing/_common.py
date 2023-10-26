
class UnintendedFileException(Exception):
    def __init__(self):
        self.message = 'File type not supported'
        super().__init__(self.message)
