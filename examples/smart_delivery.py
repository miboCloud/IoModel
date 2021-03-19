# -*- coding: utf-8 -*-

import sys
import getopt
import logging
sys.path.insert(0, "..")

from common.base import ModelDevice, ValueDataType
from common.components import Switch, TemperatureSensor, ModelValue, LevelSensor, Command, Variant
from sparkplug.connector import NodeConnector
from common.runner import ModelRunner
from enum import Enum
from timeit import default_timer as timer


class Plant(ModelDevice):
    

    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        self._area_10 = Area("A_10", self)
    
    def loop(self, tick):
        super().loop(tick)

class Area(ModelDevice):
    
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 

        c_a10_001 = Conveyor("001", self)
        c_a10_002 = Conveyor("002", self)
        c_a10_003 = Conveyor("003", self)
        
        


class ConveyorMode(Enum):
    Undefined = 0,
    Manual = 1,
    Auto = 2

class Conveyor:
        
    def __init__(self, name, parent = None):
        
        self._photo_eye = Switch(name + "/Occupied", parent, False, True)
        self._drive_on = Switch(name + "/DriveOn", parent, False, True)
        
        
        self._mode = ConveyorMode.Auto



class Drive:
    
    def __init__(self):
        pass



if __name__ == "__main__":

    print("Start Application, Arguments({}): {}".format(len(sys.argv)-1, sys.argv[1:]))
    
    options, args = getopt.getopt(sys.argv[1:], "g:h:p:l:n:",
                               ["group =","host =","port =", "node =", "log ="])
    
    group = "FastDelivery"
    node = "DefaultNode"
    host = "127.0.0.1"
    port = 1883
    log_level = logging.WARN
    
    for name, value in options:
        if name in ['-g', '--group']:
            group = value
        elif name in ['-n', '--node']:
            node = value
        elif name in ['-h', '--host']:
            host = value
        elif name in ['-p', '--port']:
            port = int(value)
        elif name in ['-l', '--log']:
            log_level = logging.DEBUG
            
    # Setup logger
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', 
                        level=log_level)
    
    logger = logging.getLogger("common.runner")
    logger.setLevel(logging.DEBUG)
    
    # Setup Model
    runner = ModelRunner(1)
    
    plant = Plant(node)
    runner.add_model_object(plant)
    
    # Setup Sparkplug connection
    broker_args = (host, port, 60)
    plantNode = NodeConnector(plant, group, broker_args)
    plantNode.start_loop()

    try:
        runner.loop_forever()
    except (KeyboardInterrupt, SystemExit):
        
        plantNode.stop_loop()
        print("Application stopped")