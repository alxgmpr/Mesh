# coding=utf-8
# Mesh ATC bot by Alex
# API technique from Luke Davis (@R8T3D)
# See https://github.com/R8T3D/MeshAPI
from random import randrange
from time import time, sleep
from classes.logger import Logger
from classes.mesh import Mesh


def main():
    """ Main method keeps track of the execution process. Use to control poll times and how the product list builds"""
    log = Logger().log
    m = Mesh()
    if m.settings['product']['preset_sku'] is not None:
        log("[short] predefined pid {}".format(m.settings['product']['preset_sku']))
    else:
        while len(m.matches) < 1:
            m.build_product_list()
            m.check_product_list()
            if len(m.matches) < 1:
                log("[sleep] no matches, waiting and refreshing")
                m.products = []  # Clear product list
                sleep(5)
    if (len(m.matches) is 1) or (m.settings['product']['preset_sku'] is not None):
        log("[exec] single match found. executing atc")
        if m.settings['product']['preset_sku'] is None:
            m.get_product_info()
            if m.sel_product_sku():
                if m.add_to_cart():
                    m.checkout()
        elif m.settings['product']['preset_sku'] is not None:
            while not m.add_to_cart():
                log("[sleep] unable to add to cart, waiting and refreshing")
                sleep(randrange(1, 2))
            m.checkout()
        else:
            log("[exec] failed to find a good size")
    else:
        log("[exec] multiple matches found")

    log("[time] {} seconds to finish".format(abs(m.start-time())))

if __name__ == '__main__':
    main()
