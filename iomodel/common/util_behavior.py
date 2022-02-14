from iomodel.common.base import ModelObject


class LatchIntervall(ModelObject):
    
    def __init__(self, time, value_list):
        self._list = value_list
        self._time = time
        self._t = 0
        
        self._index = 0
        self._list_max = len(value_list)
        
        if self._list_max <= 0:
            raise Exception("List empty")
            
        self._value = self._list[0]
        
    @property
    def value(self):
        return self._value
        
    def loop(self, tick):
        self._t += tick
        
        if self._t >= self._time:
            self._t = 0
            
            self._index += 1
            if (self._index) >= self._list_max:
                self._index = 0
                
         
            if callable(self._list[self._index]):

                self._list[self._index]()
                self._value = None
            else:
                self._value = self._list[self._index]