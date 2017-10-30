# coding=utf-8
# Mesh ATC bot by Alex
# API technique from Luke Davis (@R8T3D)
# See https://github.com/R8T3D/MeshAPI
from classes.mesh import Mesh
import os

def main():
    """ Main method keeps track of the execution process. Use to control poll times and how the product list builds"""
    threads=[]
    i=0
    for config in os.listdir('configs'):
        print config
        if config != "config.example.json":
            threads.append(Mesh("configs/"+config, 'thread-'+str(i)))
            threads[i].start()
            i += 1
        else:
            print ("Change the default config filename")

if __name__ == '__main__':
    main()
