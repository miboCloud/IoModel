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
        
        self._system = System("0_System", "S1-00-000-000", self)
        self._area1 = AreaA0x("1_A1","S1-A1-000-000", self, ident = 1)
        self._area2 = AreaA0x("2_A2","S1-A2-000-000", self, ident = 2)
        #self._area3 = AreaA03("3_A03", self)
        
        self._system.areas.extend([self._area1, self._area2])
        
        #self._area3.link_infeed_331(self._area1.outfeed_cx18)
        #self._area3.link_infeed_336(self._area2.outfeed_cx18)
    
    def loop(self, tick):
        super().loop(tick)
        
        
class System(ModelDevice):
    """ 
    System component.
    
    A system consits of areas and represents the top hierarchy
    
    """
    def __init__(self, name, reference_designation, parent = None, areas = []):
        super().__init__(name, parent) 
        
        self._on = CommandTap("1_Cmd/SystemOn", self, False, lambda v: self._switch_on_request(v))
        self._ref_des = Variant("ReferenceDesignation", self, reference_designation, ValueDataType.String)
        self._type = Variant("Type", self, "System", ValueDataType.String)
        self._error_src = Variant("ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("ErrorActive", self, False, ValueDataType.Boolean)
        self._areas = areas

    def _switch_on_request(self, value):
        for a in self._areas:
            a.switch_on()
    
    @property
    def reference_designation(self):
        return self._ref_des.value

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
    def __init__(self, name, reference_designation, parent = None):
        super().__init__(name, parent) 
        
        self._conv_list = []


        self._area_on = CommandToggle("1_Cmd/AreaOn", self, False, lambda v: self._area_state_changed(v) )
        self._auto = CommandToggle("1_Cmd/ModeAuto", self, True, lambda v: self._area_state_changed(v))
        self._ref_des = Variant("ReferenceDesignation", self, reference_designation, ValueDataType.String)
        self._type = Variant("Type", self, "Area", ValueDataType.String)
        self._error_src = Variant("ErrorSource", self, "", ValueDataType.String)
        self._error_active = Variant("ErrorActive", self, False, ValueDataType.Boolean)
    
    def add_sim_box(self, conv):
        CommandTap("3_Sim/AddBox_" + conv.name, self, False, lambda v: conv.transport_handler.insert_new_box())
    
    def _area_state_changed(self, value):
        """
        Notify all related conveyors about any change in the area

        """
        for c in self._conv_list:
            c.area_state_changed(self.auto, self.on)

    def switch_on(self):
        self._area_on.value = True

    @property
    def reference_designation(self):
        return self._ref_des.value

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
    
    def __init__(self, name, reference_designation, parent = None, ident = 1):
        super().__init__(name, reference_designation, parent)
        
        cx11 = Conveyor(str(ident) + "11", "S1-A" + str(1) + "-" + str(1) + "11-000", self)
        cx12 = Conveyor(str(ident) + "12", "S1-A" + str(1) + "-" + str(1) + "12-000", self)
        cx13 = Conveyor(str(ident) + "13", "S1-A" + str(1) + "-" + str(1) + "13-000", self)
        cx14 = Conveyor(str(ident) + "14", "S1-A" + str(1) + "-" + str(1) + "14-000", self)
        cx21 = Conveyor(str(ident) + "21", "S1-A" + str(1) + "-" + str(1) + "21-000", self)
        cx22 = Conveyor(str(ident) + "22", "S1-A" + str(1) + "-" + str(1) + "22-000", self)
        cx23 = Conveyor(str(ident) + "23", "S1-A" + str(1) + "-" + str(1) + "23-000", self)
        cx24 = Conveyor(str(ident) + "24", "S1-A" + str(1) + "-" + str(1) + "24-000", self)
        cx15 = Conveyor(str(ident) + "15", "S1-A" + str(1) + "-" + str(1) + "15-000", self)
        cx16 = Conveyor(str(ident) + "16", "S1-A" + str(1) + "-" + str(1) + "16-000", self)
        cx17 = Conveyor(str(ident) + "17", "S1-A" + str(1) + "-" + str(1) + "17-000", self)
        self.cx18 = Conveyor(str(ident) + "18", "S1-A" + str(1) + "-" + str(1) + "18-000", self)
        
        cx11.set_adjacent(None, cx12)
        cx12.set_adjacent(cx11, cx13)
        cx13.set_adjacent(cx12, cx14)
        cx14.set_adjacent(cx13, cx15)
        cx15.set_adjacent([cx14,cx24], cx16)
        cx16.set_adjacent(cx15, cx17)
        cx17.set_adjacent(cx16, self.cx18)
        self.cx18.set_adjacent(cx17, None)
        cx21.set_adjacent(None, cx22)
        cx22.set_adjacent(cx21, cx23)
        cx23.set_adjacent(cx22, cx24)
        cx24.set_adjacent(cx23, cx15)
       
        conv_list = [cx11, cx12, cx13, cx14, cx15, cx16, cx17, self.cx18, cx21, cx22, cx23, cx24]
        self.conv_list.extend(conv_list)
        self.add_sim_box(cx11)
        self.add_sim_box(cx21)
        
        self._area_state_changed(False)
        
    @property
    def outfeed_cx18(self):
        return self.cx18
    """
# Area Definitions
class AreaA03(Area):
    
    def __init__(self, name, reference_designation, parent = None):
        super().__init__(name, reference_designation, parent)
        
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
        """
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
     
    
       
class TransportHandler:
    
    def __init__(self, parent_name, parent, length = 1000):
        self._box = None
        self._parent_name = parent_name
        self._target = None
        self._source = None
        self._run_drive = False
        
        # data points
        self._cmd_interrupt = CommandToggle(parent_name + "/Cmd_InterruptToggle", parent, False)
        self._length = Variant(parent_name + "/Length", parent, length, ValueDataType.Int)
        self._box_position = Variant(parent_name + "/BoxPosition", parent, False, ValueDataType.Float)
        self._box_id = Variant(parent_name + "/BoxId", parent, "", ValueDataType.String)
        self._occupied = Switch(parent_name + "/Occupied", parent, False, True)
        self._transport_allowed = Switch(parent_name + "/TransportAllowed", parent, False, False)
        self._ready_handover = Switch(parent_name + "/ReadyHandover", parent, False, False)
        self._ready_takeover = Switch(parent_name + "/ReadyTakeover", parent, True, False)
        self._source_name = Variant(parent_name + "/SourceName", parent, "", ValueDataType.String)
        self._target_name = Variant(parent_name + "/TagetName", parent, "", ValueDataType.String)
     
    @property
    def parent_name(self):
        return self._parent_name
   
    @property
    def box(self):
        return self._box
    
    @property
    def interrupted(self):
        return self._cmd_interrupt.value

    @property
    def box_position(self):
        return self._box_position.value
    
    @box_position.setter
    def box_position(self, value):
        self._box_position.value = value

    @property
    def occupied(self):
        return self._occupied.value
    
    @occupied.setter
    def occupied(self, value):
        self._occupied.value = value

    @property
    def length(self):
        return self._length.value
    
    @property
    def source(self):
        return self._source
    
    @property
    def target(self):
        return self._target
    
    @property
    def transport_allowed(self):
        return self._transport_allowed.value
    
    @property
    def run_drive(self):
        return self._run_drive
    
    @property
    def ready_takeover(self):
        return self._ready_takeover.value
    
    @ready_takeover.setter
    def ready_takeover(self, value):
        self._ready_takeover.value = value
    
    @property
    def ready_handover(self):
        """
        Ready handover to next conveyor

        Returns
        -------
        bool
            DESCRIPTION.

        """

        if not self._transport_allowed.value:
            return False
        
        if self.interrupted:
            return False
        
        if self.box_at_border:
            return True
    
        return False
    
    @property
    def box_at_border(self):
        if not self.box:
            return False
        
        if self.box_position >= self.length:
            return True
        return False
    
    def takeover_box(self):
        if self.box:
            box = self.box
            pos = self.box_position
            box_left = (self.box_position - self.length) >= self.box.length
            self.occupied = False
            if box_left:
                self._box = None
                self.box_position = 0
            
            return (box, pos - self.length)
        else:
            return None
    
    def request_transport(self, source):
        if self.box:
            return False
        
        if not self.ready_takeover:
            return False
        
        if source.takeover_box():
            self.occupied = True
            return True
        return False
    
    def insert_new_box(self):
        if self.box:
            raise Exception("Already Box present")
            
        self._box = Box()
        self.box_position = self.length / 2
        self.occupied = True
    
    def remove_box(self):
        self._box = None
        self.box_position = 0
        
        self.clear_links()
    
    def box_found_at(self, pos):
        if not self._box:
            return False
        
        if (self.box_position >= pos and
            (self.box_position - self.box.length) <= pos):
            return True
     
        return False  
    
    def clear_links(self):
        self._target = None
        self._source = None
        self._source_name.value = ""
        self._target_name.value = ""
        
    def on_request_source(self):
        return None
    
    def on_request_target(self):
        return None 
    
    def get_source(self):
        source_th = self.on_request_source()

        if source_th:
            self._source_name.value = source_th.parent_name
            self._source = source_th
        
    def get_target(self):
        target_th = self.on_request_target()

        if target_th:
            self._target_name.value = target_th.parent_name
            self._target = target_th

    def loop(self, tick, enable, current_speed):
        """
        Handles all transport operations
        """
        self._transport_allowed.value = enable

        step = tick * current_speed
        
        if self.box:
            self._run_drive = self.transport_allowed and ((self.box_at_border and not self.occupied) or (not self.box_at_border))
        else:
            self._run_drive = False
            
        # Only transport if box available
        if self.box:
            if not self.target:
                self.get_target()         
            
            next_position = self.box_position + step
            
            if next_position >= self.length:
                # When next target is unknown, move to the border
                if (self.target is None) or (self.interrupted and self.occupied) or not enable:
                    self.box_position = self.length
                else:
                    
                    if self.occupied:
                        if self.target.request_transport(self):
                            self.box_position = next_position
                        else:
                            self.box_position = self.length
                    else:
                        self.box_position = next_position
            else:
                self.box_position = next_position
                
            if self.box_position > (self.length + self.box.length):
                self.remove_box()
                
            
        # when no box is available        
        else:
            if not self.source:
                self.get_source()    
            
            if self.source:
                if self.source.ready_handover:
                    box_values = self.source.takeover_box()
                    if box_values:
                        self.occupied = True
                        self._box = box_values[0]
                        self.box_position = box_values[1]
                        self.clear_links()
                        
        # update cyclic data
        if self.box:
            self._box_id.value = self.box.box_id
        else:
            self._box_id.value = ""
            
        self._ready_handover.value = self.ready_handover
  


            
class Drive:

    def __init__(self, parent_name, name,reference_designation, speed = 100, parent = None):
        
        self._manual_on = CommandToggle(parent_name + "/" + name + "/Cmd_ManualOnToggle", parent, False, None, condition = lambda: self.manual_mode)
        self._speed = speed
        self._manual_mode = Switch(parent_name + "/" + name + "/ManualMode", parent, False, False)
        self._drive_on = Switch(parent_name + "/" + name + "/DriveOn", parent, False, False)
        self._error = Switch(parent_name + "/" + name + "/Error", parent, False, False)
        self._ref_des = Variant(parent_name + "/" + name + "/ReferenceDesignation", parent, reference_designation, ValueDataType.String)
        self._drive_speed = Variant(parent_name + "/" + name + "/DriveSpeed", parent, 0, ValueDataType.Int)
        self._drive_current = Variant(parent_name + "/" + name + "/DriveCurrent", parent, 0.0, ValueDataType.Float)
        self._drive_encoder = Variant(parent_name + "/" + name + "/DriveEncoder", parent, 0.0, ValueDataType.Float)
    
    @property
    def current_speed(self):
        return self._drive_speed.value

    @property
    def manual_mode(self):
        return self._manual_mode.value
    
    @property
    def error(self):
        return self._error.value
    
    @manual_mode.setter
    def manual_mode(self, value):
        self._manual_mode.value = value
        
    def reset_manual(self):
        self.manual_mode = False
        self._manual_on.value = False
        
    def reset_error(self):
        self._error.value = False
        
    def sim_error(self):
        self._error.value = True
        return (True, "Overcurrent", self._ref_des.value)

    def loop(self, tick, run_auto):
        
        if self.manual_mode:
            self._drive_on.value = self._manual_on.value and not self.error
        else:
            self._drive_on.value = run_auto and not self.error
        
        
        if self._drive_on.value:
            self._drive_speed.value = self._speed
            self._drive_current.value = 3.5
            self._drive_encoder.value = self._drive_encoder.value + self._speed
        else:
            self._drive_speed.value = 0
            self._drive_current.value = 0
            
            
class Conveyor:
        
    def __init__(self, name, reference_designation, parent = None, length = 1000, speed = 100):
        
        self._name = name
        self._area = parent

        self._length = length        
        self._speed = speed
        self._source = None
        self._target = None
        self._transport_handler = TransportHandler(name, parent, length)
        self._transport_handler.on_request_source = self._on_request_source
        self._transport_handler.on_request_target = self._on_request_target
        # data points
        self._reset_error = CommandTap(name + "/Cmd_ResetErrorTap", parent, False, lambda v: self._reset_error_request())
        self._error_active = Variant(name + "/ErrorActive", parent, False, ValueDataType.Boolean)
        self._error_src = Variant(name + "/ErrorSource", parent, "", ValueDataType.String)
        self._error_msg = Variant(name + "/ErrorMessage", parent, "", ValueDataType.String)
        self._ref_des = Variant(name + "/ReferenceDesignation", parent, reference_designation, ValueDataType.String)
        self._type = Variant(name + "/Type", parent, "Conveyor", ValueDataType.String)
        self._drive = Drive(name, "Drive", reference_designation[0:-3] + "D01", speed, parent)
        self._photoeye = Switch(name + "/Photoeye", parent, False, False)
        
        CommandTap(name + "/Sim/DriveErrorTap", parent, False, lambda v: self.sim_drive_error())
    
    def sim_drive_error(self):
        error = self._drive.sim_error()
    
        self._error_active.value = error[0]
        self._error_msg.value = error[1]
        self._error_src.value = error[2]
    
    
    @property
    def reference_designation(self):
        return self._ref_des.value

    
    @property
    def name(self):
        return self._name
    
    @property
    def source(self):
        return self._source
    
    @property
    def target(self):
        return self._target
 
    @property
    def transport_handler(self):
        return self._transport_handler
    
    def set_adjacent(self, source = None, target=None):
        self._source = source
        self._target = target
    
    def _reset_error_request(self):
        self._drive.reset_error()
        
    def _on_request_target(self):
        if self.target:
            return self.target.transport_handler
        return None
    
    def _on_request_source(self):
        if self.source:
            if isinstance(self.source,list):
                for s in self.source:
                    if s.transport_handler.ready_handover:
                        return s.transport_handler
            else:
                return self.source.transport_handler
        return None
    
    def area_state_changed(self, mode_auto, switched_on):
        if mode_auto:
            self._drive.reset_manual()
        else:
            self._drive.manual_mode = True
            
        if switched_on:
            pass
    
    def loop(self, tick):

        self.transport_handler.loop(tick, self.released, self._drive.current_speed)
        self._drive.loop(tick, self.transport_handler.run_drive)

        # update signals
        self._photoeye.value = self.transport_handler.box_found_at(self._length / 2)
  
    
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
        
        if self._error_active.value:
            return False
        
        return True
        



            
class Conveyorx(Transport):
        
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
        
        self._drive = Drive("Drive", parent)
        
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