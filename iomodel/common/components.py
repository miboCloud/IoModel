# -*- coding: utf-8 -*-

from iomodel.common.base import ModelValue, ModelDataSet, ValueDataType
from iomodel.common.util_math import PT1
import logging



class Command(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, 
                 on_update_request = None, condition = None, external_write = False):
        super().__init__(name, parent, ValueDataType.Boolean, initial, external_write)
        self.logger = logging.getLogger(__name__)
        self._condition = condition
        self._on_update_request = on_update_request
        
    @property
    def on_update_request(self, value):
        return self._on_update_request
        
    @on_update_request.setter    
    def on_updat_request(self, value):
        self._on_update_request = value
    
    def update_request(self, value):

        if self._on_update_request and callable(self._on_update_request):
            self._on_update_request()
        else:
            if self._condition:
                if callable(self._condition):
                    if self._condition():
                        self.value = value
                else:
                    if self._condition:
                        self.value = value
            else:
                self.value = value
        return 0     


class CommandToggle(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, 
                 value_toggled = None, condition = None):
        super().__init__(name, parent, ValueDataType.Boolean, initial, True)
        self.logger = logging.getLogger(__name__)
        self._condition = condition
        self._value_toggled = value_toggled
        
    def update_value(self, value):
        if self._condition:
            if callable(self._condition):
                if self._condition():
                    self.value = value
            else:
                if self._condition:
                    self.value = value
        else:
            self.value = value
            
        if self._value_toggled and callable(self._value_toggled):
            self._value_toggled(value)
        return 0

class CommandTap(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, 
                 value_tapped = None):
        super().__init__(name, parent, ValueDataType.Boolean, initial, True)
        
        self.logger = logging.getLogger(__name__)
        self._value_tapped = value_tapped
    
    def update_value(self, value):
        try:
            if self._value_tapped and callable(self._value_tapped):
                self._value_tapped(value)
        except Exception as e:
            print("EEE:", e)
        return 0     


class Variant(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, datatype = ValueDataType.Int, external_write = False):
        super().__init__(name, parent, datatype, initial, external_write)
        self.logger = logging.getLogger(__name__)



class VariantDataSet(ModelDataSet):
    
    def __init__(self, name = "defaultModel", parent = None, columns = [("Column1", ValueDataType.Int), ("Column2", ValueDataType.String)]):
        super().__init__(name, parent, columns)
        self.logger = logging.getLogger(__name__)
        
    def append_data(self, dataset = ("Value1", "Values2"), suppress_event = False):
        if isinstance(self.value, list):
            if isinstance(dataset, list):
                self.value.extend(dataset)
            else:
                self.value.append(dataset)
            
        if not suppress_event:
            self.fire_has_changed_event()
        
class VariantDataMap(ModelDataSet):
    
    def __init__(self, name = "defaultModel", parent = None, columns = [("Column1", ValueDataType.Int), ("Column2", ValueDataType.String)]):
        super().__init__(name, parent, columns)
        self.logger = logging.getLogger(__name__)
        self._map = {}
        
    def set_entry(self, key, data = ("key", "data1", "data2"), suppress_event = False):
        self._map[key] = data
        self.value = list(self._map.values())
        
        if not suppress_event:
            self.fire_has_changed_event()
       
    def del_entry(self, key, suppress_event = False):
        if key in self._map:
            del self._map[key]
            self.value = list(self._map.values())
            
            if not suppress_event:
                self.fire_has_changed_event()
    @property       
    def map_count(self):
        return len(self._map)
            
        

class Switch(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, external_write = False):
        super().__init__(name, parent, ValueDataType.Boolean, initial, external_write)
        self.logger = logging.getLogger(__name__)
        
        self._method = None
        
    def set_callback(self, method):
        self._method = method
    
    @property
    def unit(self):
        return ""
        
    def loop(self, ticks):
        
        if self._method is not None:
            if callable(self._method):
                self.value = self._method()

class LevelSensor(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = False, external_write = False):
        super().__init__(name, parent, ValueDataType.Float, initial, external_write)
        self.logger = logging.getLogger(__name__)
        
class TemperatureSensor(ModelValue):
    
    def __init__(self, name = "defaultModel", parent = None, initial = 0.0, range_max = 1, t = 1, external_write = False):
        super().__init__(name, parent, ValueDataType.Float, initial, external_write)
        self.logger = logging.getLogger(__name__)
        
        self._range_max = range_max
        self._t = t
        
        self._pt1 = None
        
        self.reset()
        self._heat = False
        self.value = 0.0
        self._pt1_last = 0.0
    
    def heat(self, value = True):
        self.logger.debug("Heat : %r", value)
        
        if self._heat != value:
            self.logger.debug("Reset PT1")
            self._pt1_last = 0
            self._pt1.reset()
        
        self._heat = value
        
    def reset(self):
        self._pt1 = PT1(self._range_max, self._t)
    
    @property
    def t(self):
        return self._t
    
    @t.setter
    def t(self, value):
        self._t(value)
        
    @property
    def range_max(self):
        return self._range_max
    
    @range_max.setter
    def range_max(self, value):
        self._range_max(value)
    
    
    @property
    def unit(self):
        return "°C"
        
    def loop(self, tick):
        if self._heat:
            self.value = self._pt1.tick(tick)
        else:

            value = self._pt1.tick(tick)
            
            self.value = self.value - (value - self._pt1_last)
            self._pt1_last = value
            
            if self.value <= 0:
                self.value = 0
                    
        self.logger.debug("Temperature: %f Heat: %r", self.value, self._heat)
        
        
        

            
            