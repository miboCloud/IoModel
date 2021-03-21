# -*- coding: utf-8 -*-

import sys
import getopt
import logging
sys.path.insert(0, "..")

from common.base import ModelDevice, ValueDataType
from common.components import Switch, TemperatureSensor, ModelValue, LevelSensor, CommandToggle, CommandTap, Variant
from sparkplug.connector import NodeConnector
from common.runner import ModelRunner
from enum import Enum
from timeit import default_timer as timer


class Plant(ModelDevice):
    

    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._system = System("0_System", self)
        
        self._area1 = AreaA01("1_A01", self)

        self._area2 = Area("1_A02", self)
        self._area3 = Area("1_A03", self)
        #self._area_a1 = Area("A_10", self)
    
    def loop(self, tick):
        super().loop(tick)
        
        


class System(ModelDevice):
    
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._on = CommandToggle("1_Command/SystemOn", self, False, lambda v: self._switch_on_request(v))
        self._error_src = Variant("2_State/ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("2_State/ErrorActive", self, False, ValueDataType.Boolean)


    def _switch_on_request(self, value):
        pass
    

    
    def loop(self, tick):
        super().loop(tick)


class Area(ModelDevice):
    
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._conv_list = []
 
        self._area_on = CommandToggle("1_Command/AreaOn", self, False, lambda v: self._area_state_changed(v) )
        self._automatic = CommandToggle("1_Command/ModeAutomatic", self, False, lambda v: self._area_state_changed(v))
        
        self._state_on = Variant("2_State/On", self, False, ValueDataType.Boolean)
        self._state_off = Variant("2_State/Off", self, False, ValueDataType.Boolean)
        self._state_automatic = Variant("2_State/Automatic", self, False, ValueDataType.Boolean)
        self._state_manual = Variant("2_State/Manual", self, False, ValueDataType.Boolean)
        self._error_src = Variant("2_State/ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("2_State/ErrorActive", self, False, ValueDataType.Boolean)
    
    def add_sim_box(self, conv):
        CommandTap("3_Sim/AddBox_" + conv.name, self, False, lambda v: conv.add_box())
    
    def _area_state_changed(self, value):
        for c in self._conv_list:
            c.area_state_changed(self.auto, self.on)

    @property
    def on(self):
        return self._area_on.value        
 
    @property
    def auto(self):
        return self._automatic.value
    
    @property
    def conv_list(self):
        return self._conv_list
    
    def loop(self, tick):
        super().loop(tick)

class AreaA01(Area):
    
    def __init__(self, name, parent = None):
        super().__init__(name, parent)
        
        c111 = Conveyor("C_111", self, prev_c = None)
        c112 = Conveyor("C_112", self, prev_c = c111)
        c113 = Conveyor("C_113", self, prev_c = c112)
        c114 = Conveyor("C_114", self, prev_c = c113)
        c115 = Conveyor("C_115", self, prev_c = None)
        c116 = Conveyor("C_116", self, prev_c = c115)
        c117 = Conveyor("C_117", self, prev_c = c116)
        c118 = Conveyor("C_118", self, prev_c = c117)
        c121 = Conveyor("C_121", self, prev_c = None)
        c122 = Conveyor("C_122", self, prev_c = c121)
        c123 = Conveyor("C_123", self, prev_c = c122)
        c124 = Conveyor("C_124", self, prev_c = c123)
        
        conv_list = [c111, c112, c113, c114, c115, c116, c117, c118, c121, c122, c123, c124]
        self.conv_list.extend(conv_list)
        self.add_sim_box(c111)
        self.add_sim_box(c121)
        
        
        
class Transport:
    
    def __init__(self):
        pass
    
    @property
    def ready(self):
        return False
    

class Box():
    def __init__(self, length = 1000):
        self._length = length


class Conveyor(Transport):
        
    LENGTH = 1000
    SPEED = 1000
    
    def __init__(self, name, parent = None, prev_c = []):
        self._name = name
        self._area = parent
        
        self._interrupt = CommandToggle(name + "/1_Command/Interrupt", parent, False)
        self._manual_on = CommandToggle(name + "/1_Command/ManualOn", parent, False, None, condition = lambda: not self._area.auto)
        
    
        self._error_active = Variant(name + "/2_State/ErrorActive", parent, False, ValueDataType.Boolean)
        self._error_src = Variant(name + "/2_State/ErrorSource", parent, "", ValueDataType.String)
        self._error_msg = Variant(name + "/2_State/ErrorMessage", parent, "", ValueDataType.String)
        self._drive_on = Switch(name + "/2_State/DriveOn", parent, False, True)
        self._drive_speed = Variant(name + "/2_State/DriveSpeed", parent, False, ValueDataType.Float)
        self._drive_current = Variant(name + "/2_State/DriveCurrent", parent, False, ValueDataType.Float)
        self._drive_encoder = Variant(name + "/2_State/DriveEncoder", parent, False, ValueDataType.Float)
        self._box_pos = Variant(name + "/2_State/BoxPosition", parent, False, ValueDataType.Float)
        self._occupied = Switch(name + "/2_State/Occupied", parent, False, True)
        self._photoeye = Switch(name + "/2_State/Photoeye", parent, False, False)
        self._ready_give = Switch(name + "/2_State/ReadyGive", parent, False, False)
        
        
        self._prev = prev_c
        
        
    @property
    def name(self):
        return self._name
    
    def area_state_changed(self, mode_auto, switched_on):
        if mode_auto:
            self._manual_on.value = False
            
        if switched_on:
            pass
        
    def add_box(self):
        pass
        
    def interrupt(self):
        pass

    def manual_on(self):
        pass
    
    def manual_off(self):
        pass
    
    def loop(self, tick):
        pass
    
    @property
    def released(self):
        if not self._area.auto:
            return False
        
        if not self._area.on:
            return False
        
        if self._interrupt.value:
            return False
        
        if self._error_active.value:
            return False
        
        return True
        
    @property
    def ready(self):
        
        
        return False
        
        

class Drive:
    
    def __init__(self):
        pass



if __name__ == "__main__":

    print("Start Application, Arguments({}): {}".format(len(sys.argv)-1, sys.argv[1:]))
    
    options, args = getopt.getopt(sys.argv[1:], "g:h:p:l:n:",
                               ["group =","host =","port =", "node =", "log ="])
    
    group = "CaseStudy"
    node = "DefaultPlant"
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