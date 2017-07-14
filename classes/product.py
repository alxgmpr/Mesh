class Product:
    def __init__(self, sku, name, stock):
        self.sku = sku
        self.name = name.lower().split(' ')
        self.stock = stock
