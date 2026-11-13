class TracingIterator:
    def __init__(self, values):
        self.source = iter(values)
        self.consumed = 0

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.source)
        self.consumed += 1
        return value
