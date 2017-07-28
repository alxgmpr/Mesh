# coding=utf-8
# Mesh ATC bot by Alex
# API technique from Luke Davis (@R8T3D)
# See https://github.com/R8T3D/MeshAPI
from classes.mesh import Mesh


def main():
    """ Main method keeps track of the execution process. Use to control poll times and how the product list builds"""
    m = Mesh('../config.json', 'thread-1')
    m.start()

if __name__ == '__main__':
    main()
