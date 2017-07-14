# coding=utf-8
# Mesh ATC bot by Alex
# API technique from Luke Davis (@R8T3D)
# See https://github.com/R8T3D/MeshAPI
from time import strftime, time, sleep
from classes.logger import Logger
from classes.mesh import Mesh
log = Logger().log


def main():
    """ Main method keeps track of the execution process. Use to control poll times and how the product list builds"""
    pick = raw_input("[{}] :: pick mesh site (FP, JD, SZ) \n>".format(strftime("%H:%M:%S")))
    m = Mesh(pick)
    if m.skupid is not None:
        log("[short] predefined pid {}".format(m.skupid))
    else:
        while len(m.matches) < 1:
            m.build_product_list()
            m.check_product_list()
            if len(m.matches) < 1:
                log("[sleep] no matches, waiting and refreshing")
                m.products = []  # Clear product list
                sleep(5)
    if (len(m.matches) is 1) or (m.skupid is not None):
        log("[exec] single match found. executing atc")
        if m.skupid is None:
            m.get_product_info()
            if m.sel_product_sku():
                if m.add_to_cart():
                    m.checkout()
        elif m.skupid is not None:
            if m.add_to_cart():
                m.checkout()
        else:
            log("[exec] failed to find a good size")
    else:
        log("[exec] multiple matches found")

    log("[time] {} seconds to finish".format(abs(m.start-time())))

if __name__ == '__main__':
    main()
