# -*- coding: utf-8 -*-

"""

name = "abc/def/container"

names = name.split(sep="/")
name.splitlines()
print(names)
print(names[-1])
print("/".join(names[0:-1]))
name = "container"

names = name.split(sep="/")

print(names)



def test(x):
    
    if isinstance(x, Auto):
        print("Ist ein einzelnes object")
    elif isinstance(x, list):
        print("ist eien Liste")
        
        
        
class Auto:
    def __init__(self):
        self.drive = True
        
        
a = Auto()
b = Auto()

mylist = [a, b]

test(mylist)

"""

"""

import threading
import time
from IPython import embed

class Auto():
    
    def __init__(self):
        
        self.stop = False
        
        self._thread = None
        self._thread_stop = False
    
    
    def loop_start(self):
        self._thread = threading.Thread(target=self.forever)
        self._thread.daemon = True
        self._thread.start()
    
    def forever(self):
        
        for i in range(8):
            print("Thread")
            time.sleep(1)
        
if __name__ == "__main__":        
    a = Auto()
    a.loop_start()
    
    #embed()

    time.sleep(2)
    
    print("done")


"""


class Animal:
    
    def drive(self):
        self.drive = True
        
    def isdrive(self):
        return self.drive
    
a = Animal()
b = Animal()
a.drive()

print("a",a.isdrive())

print("b",b.isdrive())




