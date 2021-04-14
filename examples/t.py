# -*- coding: utf-8 -*-



def funcA(a, b):
    print("Do something with", a, b)
    
    
def funcB():
    print("I can do better")
    
    

def action(fun, **args):
    fun(*args)
    print("it worked")
    



action(funcA, b =1, a= 2, x=5)