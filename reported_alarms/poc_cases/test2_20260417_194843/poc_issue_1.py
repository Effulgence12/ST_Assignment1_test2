class Test:
    def __init__(self, items=[]):
        self.items = items
a = Test()
b = Test()
a.items.append(1)
print(b.items)  # Outputs [1], proving shared state
