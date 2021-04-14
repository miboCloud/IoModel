# -*- coding: utf-8 -*-
"""
Example: Logistics Plant for use with Ignition 8.1 over sparkplug B MQTT
"""

import sys
import getopt
import logging
sys.path.insert(0, "..")

from common.base import ModelDevice, ValueDataType
from common.components import Switch, CommandToggle, CommandTap, Variant
from sparkplug.connector import NodeConnector
from common.runner import ModelRunner


class Plant(ModelDevice):
    """
    Main Container of smart delivery factory plant
    """

    def __init__(self, name):
        """
        Parameters
        ----------
        name : Name of the plant

        """
        super().__init__(name, None) 
        
        self._system = System("0_System", self)
        self._area1 = AreaA0x("1_A01", self, ident = 1)
        self._area2 = AreaA0x("2_A02", self, ident = 2)
        self._area3 = AreaA03("3_A03", self)
        
        self._system.areas.extend([self._area1, self._area2, self._area3])
        
        self._area3.link_infeed_331(self._area1.outfeed_cx18)
        self._area3.link_infeed_336(self._area2.outfeed_cx18)
    
    def loop(self, tick):
        super().loop(tick)
        
        
class System(ModelDevice):
    """ 
    System component.
    
    A system consits of areas and represents the top hierarchy
    
    """
    def __init__(self, name, parent = None, areas = []):
        super().__init__(name, parent) 
        
        self._on = CommandTap("1_Cmd/SystemOn", self, False, lambda v: self._switch_on_request(v))
        self._error_src = Variant("ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("ErrorActive", self, False, ValueDataType.Boolean)
        self._areas = areas

    def _switch_on_request(self, value):
        for a in self._areas:
            a.switch_on()
    
    @property
    def areas(self):
        return self._areas
    
    def loop(self, tick):
        super().loop(tick)


class Area(ModelDevice):
    """ 
    Base class of an Area
    
    Setup of conveyor can be added by inheritance of this class
    
    """
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._conv_list = []

        self._area_on = CommandToggle("1_Cmd/AreaOn", self, False, lambda v: self._area_state_changed(v) )
        self._auto = CommandToggle("1_Cmd/ModeAuto", self, True, lambda v: self._area_state_changed(v))
        
        self._error_src = Variant("ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("ErrorActive", self, False, ValueDataType.Boolean)
    
    def add_sim_box(self, conv):
        CommandTap("3_Sim/AddBox_" + conv.name, self, False, lambda v: conv.add_new_box())
    
    def _area_state_changed(self, value):
        """
        Notify all related conveyors about any change in the area

        """
        for c in self._conv_list:
            c.area_state_changed(self.auto, self.on)

    def switch_on(self):
        self._area_on.value = True

    @property
    def on(self):
        return self._area_on.value        
 
    @property
    def auto(self):
        return self._auto.value
    
    @property
    def conv_list(self):
        return self._conv_list
    
    def loop(self, tick):
        super().loop(tick)
        
        for c in self._conv_list:
            c.loop(tick)

# Area Definitions
class AreaA0x(Area):
    
    def __init__(self, name, parent = None, ident = 1):
        super().__init__(name, parent)
        
        cx11 = Conveyor("C_" + str(ident) + "11", self, prev_c = None)
        cx12 = Conveyor("C_" + str(ident) + "12", self, prev_c = cx11)
        cx13 = Conveyor("C_" + str(ident) + "13", self, prev_c = cx12)
        cx14 = Conveyor("C_" + str(ident) + "14", self, prev_c = cx13)
        cx21 = Conveyor("C_" + str(ident) + "21", self, prev_c = None)
        cx22 = Conveyor("C_" + str(ident) + "22", self, prev_c = cx21)
        cx23 = Conveyor("C_" + str(ident) + "23", self, prev_c = cx22)
        cx24 = Conveyor("C_" + str(ident) + "24", self, prev_c = cx23)
        cx15 = Conveyor("C_" + str(ident) + "15", self, prev_c = [cx14, cx24])
        cx16 = Conveyor("C_" + str(ident) + "16", self, prev_c = cx15)
        cx17 = Conveyor("C_" + str(ident) + "17", self, prev_c = cx16)
        self.cx18 = Conveyor("C_" + str(ident) + "18", self, prev_c = cx17)
       
        conv_list = [cx11, cx12, cx13, cx14, cx15, cx16, cx17, self.cx18, cx21, cx22, cx23, cx24]
        self.conv_list.extend(conv_list)
        self.add_sim_box(cx11)
        self.add_sim_box(cx21)
        
    @property
    def outfeed_cx18(self):
        return self.cx18
    
# Area Definitions
class AreaA03(Area):
    
    def __init__(self, name, parent = None):
        super().__init__(name, parent)
        
        self.c331 = Conveyor("C_331", self, prev_c = None)
        c332 = Conveyor("C_332", self, prev_c = self.c331)
        
        self.c336 = Conveyor("C_336", self, prev_c = None)
        c335 = Conveyor("C_335", self, prev_c = self.c336)
        c334 = Conveyor("C_334", self, prev_c = c335)
        
        c333 = Conveyor("C_333", self, prev_c = [c332,c334])
        c337 = Conveyor("C_337", self, prev_c = c333)
        c338 = Conveyor("C_338", self, prev_c = c337)
        

        conv_list = [self.c331, c332, c333, c334, c335, self.c336, c337, c338]
        self.conv_list.extend(conv_list)
        self.add_sim_box(self.c331)
        self.add_sim_box(self.c336)
        
    def link_infeed_331(self, conv):
        self.c331.prev_c = conv
        
    def link_infeed_336(self, conv):
        self.c336.prev_c = conv
        
from random import randint
class Box():
    def __init__(self,length = 500):
        self._length = length
        self._box_id = str(self.random_with_N_digits(8))
        
        
    @property
    def box_id(self):
        return self._box_id
    
    @property
    def length(self):
        return self._length

    def random_with_N_digits(self, n):
        range_start = 10**(n-1)
        range_end = (10**n)-1
        return randint(range_start, range_end)
            
        
class Transport:
    
    def __init__(self, prev_c = None, conveyor_length = 1000):
        self._box = None
        self._box_position = 0
        self._conveyor_length = conveyor_length
        self._last_box_id = 0
        self._next = None
        self._prev = prev_c
        
    @property
    def prev_c(self):
        return self._prev
    
    @prev_c.setter
    def prev_c(self, value):
        self._prev = value
    
    @property
    def next_c(self):
        return self._next
    
    @property
    def ready(self):
        return False
        
    @property
    def box_position(self):
        return self._box_position
    
    @box_position.setter
    def box_position(self, value):
        self._box_position = value
    
    @property
    def box(self):
        return self._box

    @box.setter
    def box(self, value):
        self._box = value
    
    def take_box(self):
        if self.box:
            box = self.box
            pos = self.box_position
            box_left = (self.box_position - self._conveyor_length) >= self.box.length
            
            if box_left:
                self.box = None
                self.box_position = 0
            
            return (box, pos - self._conveyor_length)
        else:
            raise Exception("No Box Found")
    
    def notifyNext(self, prev):
        if self.box:
            return
        
        self.take_from_prev(prev)
            
    def take_from_prev(self, prev):
        prev.link_next(self)
        box_args = prev.take_box()
        self.box = box_args[0]
        self.box_position = box_args[1]
     
    def box_is_at(self, pos):
        if not self._box:
            return False
        
        if (self.box_position >= pos and
            (self.box_position - self.box.length) <= pos):
            return True
     
        return False  
    
    def delete_box(self):
        self.box_position = 0
        self.box = None
    
    def link_next(self, conv):
        self._next = conv
     
    def transport(self, step):
        if self.box:
            temp_pos = self.box_position + step
            
            if temp_pos >= self._conveyor_length:
                if self._next is None:
                    self.box_position = self._conveyor_length
                    
                else:
                    self.box_position = temp_pos
                    if self._last_box_id != self.box.box_id:
                        self._last_box_id = self.box.box_id
                        self._next.notifyNext(self)
            else:
                self.box_position = temp_pos
                
            if self.box_position > (self._conveyor_length + self.box.length):
                self.delete_box()
                self.link_next(None)
                
        else:
            self.link_next(None)
            if self._prev:
                if isinstance(self._prev, list):
                    for p in self._prev:
                        if p.ready:
                            self.take_from_prev(p)
                            return
                else:
                    if self._prev.ready:
                        self.take_from_prev(self._prev)
                        return
                
                
class Conveyor(Transport):
        
    LENGTH = 1000
    SPEED = 100
    
    def __init__(self, name, parent = None, prev_c = [], service = None):
        super().__init__(prev_c, Conveyor.LENGTH)
        
        self._name = name
        self._area = parent
        self._service = service
        self._box = None
        self._interrupt = CommandToggle(name + "/1_Command/Interrupt", parent, False)
        self._manual_on = CommandToggle(name + "/1_Command/ManualOn", parent, False, None, condition = lambda: not self._area.auto)
        
        self._error_active = Variant(name + "/9_Error/ErrorActive", parent, False, ValueDataType.Boolean)
        self._error_src = Variant(name + "/9_Error/ErrorSource", parent, "", ValueDataType.String)
        self._error_msg = Variant(name + "/9_Error/ErrorMessage", parent, "", ValueDataType.String)
        self._drive_on = Switch(name + "/2_State/DriveOn", parent, False, True)
        self._drive_speed = Variant(name + "/2_State/DriveSpeed", parent, False, ValueDataType.Float)
        self._drive_current = Variant(name + "/2_State/DriveCurrent", parent, False, ValueDataType.Float)
        self._drive_encoder = Variant(name + "/2_State/DriveEncoder", parent, False, ValueDataType.Float)
        self._box_pos = Variant(name + "/2_State/BoxPosition", parent, False, ValueDataType.Float)
        self._box_id = Variant(name + "/2_State/BoxId", parent, "", ValueDataType.String)
        self._occupied = Switch(name + "/2_State/Occupied", parent, False, True)
        self._photoeye = Switch(name + "/2_State/Photoeye", parent, False, False)
        self._ready_give = Switch(name + "/2_State/ReadyGive", parent, False, False)
        
    @property
    def name(self):
        return self._name
 
    @property
    def box_position(self):
        return self._box_pos.value
    
    @box_position.setter
    def box_position(self, value):
        self._box_pos.value = value
        
    @property
    def box(self):
        return self._box    
        
    @box.setter
    def box(self, value):
        self._occupied.value = value is not None
        self._box = value

    def area_state_changed(self, mode_auto, switched_on):
        if mode_auto:
            self._manual_on.value = False
            
        if switched_on:
            pass
        
    def add_new_box(self):
        if self.box:
            raise Exception("Already Box present")
            
        self.box = Box()
        self.box_position = Conveyor.LENGTH / 2
    
    
    def loop(self, tick):
        if self.released:
            step = tick * Conveyor.SPEED
            self.transport(step)
        
        self._photoeye.value = self.box_is_at(Conveyor.LENGTH / 2)
        self._ready_give.value = self.ready
        
        if self.box:
            self._box_id.value = self.box.box_id
        else:
            self._box_id.value = ""
    
    @property
    def released(self):
        """
        Describes whenever the conveyor is released for transportation

        Returns
        -------
        bool
            DESCRIPTION.

        """
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
        """
        Ready handover to next conveyor

        Returns
        -------
        bool
            DESCRIPTION.

        """
        if not self.released:
            return False
        
        if not self.box:
            return False
        
        if self.box_position >= Conveyor.LENGTH:
            return True

        return False
        
        

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
    plantNode = NodeConnector(plant, group, broker_args, node)
    plantNode.start_loop()

    try:
        runner.loop_forever()
    except (KeyboardInterrupt, SystemExit):
        
        plantNode.stop_loop()
        print("Application stopped")