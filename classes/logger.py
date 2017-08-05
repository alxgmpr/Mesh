from datetime import datetime

class Logger(object):
    def __init__(self):
        self.format = "%H:%M:%S.%f"

    def log(self, text):
        now = datetime.now()
        t = now.strftime(self.format)
        print "[{}] :: {}".format(t, text)

    def logt(self, tid, text):
        now = datetime.now()
        t = now.strftime(self.format)
        print '[{}] :: [{}] :: {}'.format(tid, t, text)

    def space(self, char):
        print char*50
