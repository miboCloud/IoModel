# -*- coding: utf-8 -*-
import threading
import logging
import time

class ModelRunner:
    
    def __init__(self, ticks = 0.5):
        self.logger = logging.getLogger(__name__)
        
        self._models = []
        self._ticks = ticks
        
        self._thread = None
        self._thread_terminate = False

        
    @property
    def models(self):
        return self._models
    
    @property
    def ticks(self):
        return self._ticks
    
    @ticks.setter
    def ticks(self, value):
        self._ticks = value
    
    def add_model_object(self, model):
        self.logger.debug("Add model object")
        self._models.append(model)
    
        
    def start_loop(self):
        """
        Start the runner

        """
        self._thread_terminate = False
        
        if self._thread is not None:
            raise Exception("Thread already started")
        
        self._thread = threading.Thread(target = self.loop_forever)
        self._thread.daemon = True
        self._thread.start()
        self.logger.debug("Thread started: %s", self._thread)
    
    def stop_loop(self):
        """
        Stops the runner

        """
        if self._thread is None:
            raise Exception("No running thread.")
        
        self._thread_terminate = True
        
        if threading.current_thread() != self._thread:
            self._thread.join()
            self.logger.debug("Thread stopped: %s", self._thread)
            self._thread = None

    def loop_forever(self):
        self.logger.debug("Start loop")
        
        while not self._thread_terminate:
            time.sleep(self.ticks)
            
            for model in self._models:
                model.loop(self.ticks)
                
        for model in self._models:
                model.loop(self.ticks)
                
        self.logger.debug("Stop loop")