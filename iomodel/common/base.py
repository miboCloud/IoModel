from enum import Enum
from common.util_callback import Dispatcher, CallbackValueChanged

    
    
class ValueAccess(Enum):
    OK = 0,
    DENIED = 1


class ValueDataType(Enum):
    Unknown = 0,
    Int = 1,
    Float = 2,
    Boolean = 3,
    String = 4,
    Bytes = 5,
    DataSet = 9


class ModelObject:
    
    def __init__(self, name = "defaultModel"):
        
        name_parts = name.split(sep = "/")
        
        self._qualified_name = name
        self._name = name_parts[-1]
        self._path_list = name_parts[0:-1]
        self._path_str = "/".join(name_parts[0:-1]) + "/"
        
    
    def loop(self, tick):
        pass
    
    @property
    def name(self):
        return self._name
    
    @property
    def path_string(self):
        return self._path_str
    
    @property
    def path_list(self):
        return self._path_list
    
    @property
    def qualified_name(self):
        return self._qualified_name
    

    

class ModelDevice(ModelObject):

    def __init__(self, name = "defaultModel", parent = None):
        super().__init__(name)
        
        self._children = []
        self._parent = parent
        
        if self._parent is not None:
            self._parent.add_child(self)

    @property
    def parent(self):
        return self._parent
    
    @property
    def children(self):
        return self._children
    
    def add_child(self, child):
        self._children.append(child)
    
    def loop(self, tick):
        super().loop(tick)
        for child in self._children:
            child.loop(tick) 
    



   # TODO ModelValue?
class ModelValue(ModelObject):
    
    def __init__(self, name = "defaultModel", parent = None, datatype = ValueDataType.Unknown, initial = None, external_write = False):
        super().__init__(name)
        self._dispatcher = Dispatcher()
        self._initial = initial
        self._datatype = datatype
        self._parent = parent
        self._external_write = external_write
        self._value = initial
        
        if self._parent is not None:
            self._parent.add_child(self)
    
    def update_request(self, value):

        if self._external_write:
            self.update_value(value)
            return ValueAccess.OK 
            
        return ValueAccess.DENIED 
    
    def update_value(self, value):
        self.value = value
    
    def add_value_changed_listener(self, listener):
        self._dispatcher.add_listener("value_changed", listener)
    
    @property
    def external_write(self):
        return self._external_write
    
    @external_write.setter
    def external_write(self, value):
        self._external_write = value
        
    @property
    def dispatcher(self):
        return self._dispatcher
    
    @property
    def datatype(self):
        return self._datatype
    
    @property
    def initial(self):
        return self._initial
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):

        if self._value != value:
            old_value = self._value
            self._value = value
            self.fire_has_changed_event(old_value, value)

    @property
    def unit(self):
        return ""
    
    @property
    def max(self):
        return None
    
    @property
    def min(self):
        return None
    
    def fire_has_changed_event(self, old_value = None, new_value = None):
        callback = CallbackValueChanged(old_value, new_value)
        self._dispatcher.fire("value_changed", callback, self)



class ModelDataSet(ModelValue):
    
    def __init__(self, name, parent, columns = [("Column1", ValueDataType.Int), ("Column2", ValueDataType.String)]):
        super().__init__(name, parent, ValueDataType.DataSet, [], False)
        
        self._columns_count = len(columns)
        self._columns = columns
    
    @property
    def columns(self):
        return self._columns    

    @property
    def columns_count(self):
        return self._columns_count      
        
    
    def clear_data(self, suppress_event = False):
        if isinstance(self.value, list):
            self.value.clear()

        if not suppress_event:
            self.fire_has_changed_event()    