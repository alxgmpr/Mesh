from time import strftime


class Logger(object):
    def __init__(self):
        self.format = '%H:%M:%S'

    def log(self, text):
        t = strftime(self.format)
        print '[{}] :: {}'.format(t, text)

    def logt(self, tid, text):
        t = strftime(self.format)
        print '[Thread-{}] :: [{}] :: {}'.format(tid, t, text)

    def space(self, char):
        print char*50
