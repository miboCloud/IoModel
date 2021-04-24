# -*- coding: utf-8 -*-

class A:
    def __init__(self):
        self._b = B()
        self._b.invoke = self.invoke
        
        
    def invoke(self):
        print("Call in A")
        
    
    @property
    def b(self):
        return self._b
 
class B:
    
    def invoke(self):
        print("Call in B")

    def mach(self):
        self.invoke()
        
def invoke():
    print("Call in CCCC")
    
x = A()
print(x._b.__dict__)
x.b.invoke = invoke

print(x._b.__dict__)
x.b.invoke()