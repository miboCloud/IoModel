


class Dispatcher:
    
    def __init__(self):
        self._listeners = {}
        
    def add_listener(self, event_name, listener):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
            
        event_listeners = self._listeners[event_name]
        
        event_listeners.append(listener)
        
    def fire(self, event_name, event = None, source = None):
        
        if event_name not in self._listeners:
            return
        
        if event is None:
            event = Callback()
            
        event_listeners = self._listeners[event_name]
        
        for listener in event_listeners:
            if callable(listener):
                listener(event, source)
        
class Callback:
    
    def __init__(self, name):
        self._name = name
        
    @property
    def name(self):
        return self._name
    
    
class CallbackValueChanged(Callback):
    
    def __init__(self, old = None, new = None):
        self._old_value = old
        self._new_value = new
        
    @property
    def old_value(self):
        return self._old_value
    
    @property
    def new_value(self):
        return self._new_value