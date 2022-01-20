

# -*- coding: utf-8 -*-
import math

class PT1:
    """
    First order lag element (PT1).

    Can be used to simulate behavior e.g. temperature.
    """
    def __init__(self, k = 1, t = 1):
        self._k = k
        self._t = t
        self._time = 0.0
        self._v = 0
    
    @property
    def k(self):
        return self._k
    
    @k.setter
    def k(self, value):
        self._k = value
    
    @property
    def t(self):
        return self._t
    
    @t.setter
    def t(self, value):
        self._t = value
        
    @property
    def v(self):
        return self._v
    
    def reset(self):
        self._time = 0
        self._v = 0
        
    
    def tick(self, ticks):
        self._time += ticks
        
        if self.t <= 0:
            raise Exception("Division by zero - T = 0")
        
        self._v = self.k * (1 - math.exp(-self._time / self.t))
  
        return self._v
