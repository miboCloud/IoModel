# -*- coding: utf-8 -*-
"""
Example: Logistics Plant for use sparkplug B MQTT
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import getopt
import logging

from iomodel.common.base import ModelDevice, ValueDataType
from iomodel.common.components import Switch, CommandToggle, CommandTap, Variant, VariantDataMap, TemperatureSensorBA
from iomodel.sparkplug.connector import NodeConnector
from iomodel.common.runner import ModelRunner


__version__ = "3.0.0"

from random import randint, choice
class Box():

    articles = ['Coca Cola', 'USB-Sticks', 'Apples', 'Pens', 'Coffee', 'Webcam', 'Mouse', 'Keyboard', 'Laptop', 'IPhone', 'Fanta',
                'Peanuts', 'Back to the Future', 'ESP32', 'Camera', 'Headset', 'Book: Answer to the universe', 'Plane', 'Playcar',
                'Beer', 'Wine', 'Milk', 'Chocolate' , 'Dress', 'Software', 'Banana', 'Tickets']

    def __init__(self,length = 500):
        self._length = length
        self._box_id = str(self.random_with_N_digits(8))
        self._weight = randint(1,16)
        self._article = choice(self.articles)
        
    @property
    def box_id(self):
        return self._box_id
    
    @property
    def length(self):
        return self._length

    @property
    def weight(self):
        return self._weight

    @property
    def article(self):
        return self._article

    def random_with_N_digits(self, n):
        range_start = 10**(n-1)
        range_end = (10**n)-1
        return randint(range_start, range_end)


class BoxManager:

    def __init__(self, number_of_boxes = 25):

        self._boxes = []
        self._index = 0
        self._number_of_boxes = number_of_boxes

        for i in range(self._number_of_boxes):
            self._boxes.append(Box())

    def next_box(self):

        if self._index >= self._number_of_boxes:
            self._index = 0

        box = self._boxes[self._index]
        self._index += 1
        return box

    @property
    def boxes(self):
        return self._boxes



box_manager = BoxManager(30)

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
        
        self._mes = MES("PLC_A0_K1_System", "S1-00-000-000", self)
        self._network = Network("Switch_K9_Network",self)
        self._area2_logistics = AreaA0x("PLC_A2_K3_Logistics","S1-A2-000-000", self, ident = 2)
        self._area2_building_automation = BuildingAutomation("PLC_A2_K7_Building",self)
        self._mes.add_area( self._area2_logistics)
        
    def loop(self, tick):
        super().loop(tick)

class ErrorHandler:
    """
    ErrorHandler 
    """
    def __init__(self, parent, prefix = None):
        self._prefix = ""
        if prefix:
            self._prefix = prefix + "/"
        
        self._error_list = []
        self._error_src = Variant(self._prefix + "ErrorSource", parent, "", ValueDataType.String)
        self._error_active = Variant(self._prefix + "ErrorActive", parent, False, ValueDataType.Boolean)
        self._error_msg = Variant(self._prefix +"ErrorMessage", parent, "", ValueDataType.String)
        self._child_error_active = Variant(self._prefix + "ChildErrorActive", parent, False, ValueDataType.Boolean)
        self._child_errors = VariantDataMap(self._prefix +"ChildErrors", parent, [("Reference Designation", ValueDataType.String),("Error MSG", ValueDataType.String)])
        self._parent_error_handler = None
    
    def _add_child_error(self, error_msg, error_src):
        """
        Report an error to the parent

        Parameters
        ----------
        error_msg : Error message (e.g. Overcurrent)
        error_src : Error source (e.g. reference designation)

        """
        self._child_errors.set_entry(error_src, (error_src, error_msg))
        
        if self._parent_error_handler:
            self._parent_error_handler._add_child_error(error_msg, error_src)
            
        self._child_error_active.value = self._child_errors.map_count > 0
    
    def _remove_child_error(self, error_src):
        """
        Remove an reported child error on parent

        Parameters
        ----------
        error_src : Identifier to remove
        

        """
        self._child_errors.del_entry(error_src)
        
        if self._parent_error_handler:
            self._parent_error_handler._remove_child_error(error_src)
            
        self._child_error_active.value = self._child_errors.map_count > 0
    
    def set_error(self, error_msg, error_src):
        """
        Set error for the owner of this module

        Parameters
        ----------
        error_msg : Error message
        error_src : Reporting source

        """
        self._error_active.value = True
        self._error_src.value = error_src
        self._error_msg.value = error_msg
        
        if self._parent_error_handler:
            self._parent_error_handler._add_child_error(error_msg, error_src)
        
    def clear_error(self):
        """
        Reset error

        """
        if self._parent_error_handler:
            self._parent_error_handler._remove_child_error(self._error_src.value)
            
        self._error_active.value = False
        self._error_src.value = ""
        self._error_msg.value = ""
    
    @property
    def error_pending(self):
        return self._error_active.value
    
    def link_to_parent(self, parent_error_handler):
        """
        Link a parent error handler
        Allows building of error hierarchy chains.

        Parameters
        ----------
        parent_error_handler : Parent error handler
        """
        self._parent_error_handler = parent_error_handler
             
class MES(ModelDevice):
    """ 
    System component.
    
    A system consits of areas and represents the top hierarchy
    
    """
    def __init__(self, name, reference_designation, parent = None):
        super().__init__(name, parent)
        
        self._error_handler = ErrorHandler(self)
        self._reference_designation = Variant("ReferenceDesignation", self, reference_designation, ValueDataType.String)
        self._type = Variant("Type", self, "System", ValueDataType.String)
        
        self._on = CommandTap("Cmd_SystemOn_Tap", self, False, lambda v: self._switch_on_request(v))
        self._off = CommandTap("Cmd_SystemOff_Tap", self, False, lambda v: self._switch_off_request(v))

        self._orders = VariantDataMap("TransportOrders", self, [("id", ValueDataType.String), ("article", ValueDataType.String), ("length", ValueDataType.Int),  ("weight", ValueDataType.Int)])
        self._initialize_orders()

        self._performance = CommandToggle("Performance_Suggestion_A2", self, True)

        self._areas = []

    def _initialize_orders(self):
        global box_manager

        for e in box_manager.boxes:
            self._orders.set_entry(e.box_id, data=(e.box_id, e.article, e.length, e.weight))


    @property
    def reference_designation(self):
        return self._reference_designation.value
     
    @property
    def error_handler(self):
        return self._error_handler

    def _switch_on_request(self, value):
        """
        Request to switch on all areas

        """
        for a in self._areas:
            a.switch_on()
            
    def _switch_off_request(self, value):
        """
        Request to switch off all areas
        """
        for a in self._areas:
            a.switch_off()
    
    def add_area(self, *args):
        """
        Register area to system
        """
        for area in args:
            area.error_handler.link_to_parent(self.error_handler)
            self._areas.append(area)
    
    @property
    def areas(self):
        return self._areas
    
    def loop(self, tick):
        super().loop(tick)


class BuildingAutomation(ModelDevice):
    """ 
    Base class of an Building Automation Setup
    
    """
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._type = Variant("Type", self, "BA", ValueDataType.String)
        self._t1 = TemperatureSensorBA("T1", self, initial=21.5, range = 0.5, delay = 5)
        self._t2 = TemperatureSensorBA("T2", self, initial=21.2, range = 0.2, delay = 5)
        self._t3 = TemperatureSensorBA("T3", self, initial=21.3, range = 0.3, delay = 5)
        self._t4 = TemperatureSensorBA("T4", self, initial=21.9, range = 0.1, delay = 5)

    def loop(self, tick):
        super().loop(tick)


class Network(ModelDevice):
    """ 
    Base class of the network infrastructure
    
    """
    def __init__(self, name, parent = None):
        super().__init__(name, parent) 
        
        self._type = Variant("Type", self, "Network", ValueDataType.String)
        self._switch_online = CommandToggle("SwitchOnline", self, True)

    def loop(self, tick):
        super().loop(tick)
        

class Area(ModelDevice):
    """ 
    Base class of an Area
    
    Setup of conveyor can be added by inheritance of this class
    
    """
    def __init__(self, name, reference_designation, parent = None):
        super().__init__(name, parent) 
        
        self._error_handler = ErrorHandler(self)
        self._reference_designation = Variant("ReferenceDesignation", self, reference_designation, ValueDataType.String)
        self._type = Variant("Type", self, "Area", ValueDataType.String)
 
        self._conv_list = []

        self._area_on = CommandToggle("Cmd_AreaOn_Toggle", self, False, lambda v: self._area_state_changed(v) )
        self._auto = CommandToggle("Cmd_ModeAuto_Toggle", self, True, lambda v: self._area_state_changed(v))
        self._performance = CommandToggle("Cmd_PerformanceMode", self, True)
        
    @property
    def error_handler(self):
        return self._error_handler
    
    @property
    def reference_designation(self):
        return self._reference_designation.value
    
    def switch_on(self):
        self._area_on.value = True
        
    def switch_off(self):
        self._area_on.value = False

    def _area_state_changed(self, value):
        """
        Notify all related conveyors about any change in the area

        """
        for c in self._conv_list:
            c.area_state_changed(self.auto, self.on)

    @property
    def on(self):
        return self._area_on.value        
 
    @property
    def auto(self):
        return self._auto.value
    
    def add_conveyor(self, *args):
        for a in args:
            self._conv_list.append(a)
        
    def loop(self, tick):
        super().loop(tick)
        
        for c in self._conv_list:
            c.loop(tick)


# Area Definitions
class AreaA0x(Area):
    
    def __init__(self, name, reference_designation, parent = None, ident = 1):
        super().__init__(name, reference_designation, parent)
        
        cx11 = Conveyor(str(ident) + "11", "S1-A" + str(ident) + "-" + str(ident) + "11-000", self)
        cx12 = Conveyor(str(ident) + "12", "S1-A" + str(ident) + "-" + str(ident) + "12-000", self)
        cx13 = Conveyor(str(ident) + "13", "S1-A" + str(ident) + "-" + str(ident) + "13-000", self)
        cx14 = Conveyor(str(ident) + "14", "S1-A" + str(ident) + "-" + str(ident) + "14-000", self)
        cx21 = Conveyor(str(ident) + "21", "S1-A" + str(ident) + "-" + str(ident) + "21-000", self)
        cx22 = Conveyor(str(ident) + "22", "S1-A" + str(ident) + "-" + str(ident) + "22-000", self)
        cx23 = Conveyor(str(ident) + "23", "S1-A" + str(ident) + "-" + str(ident) + "23-000", self)
        cx24 = Conveyor(str(ident) + "24", "S1-A" + str(ident) + "-" + str(ident) + "24-000", self)
        
        cx16 = Conveyor(str(ident) + "16", "S1-A" + str(ident) + "-" + str(ident) + "16-000", self)
        cx17 = Conveyor(str(ident) + "17", "S1-A" + str(ident) + "-" + str(ident) + "17-000", self)
        self.cx18 = Conveyor(str(ident) + "18", "S1-A" + str(ident) + "-" + str(ident) + "18-000", self)
        
        cx15 = Lift(str(ident) + "15", "S1-A" + str(ident) + "-" + str(ident) + "15-000", self )
        
        cx11.set_adjacent(None, cx12)
        cx12.set_adjacent(cx11, cx13)
        cx13.set_adjacent(cx12, cx14)
        cx14.set_adjacent(cx13, cx15.conveyor)
        cx15.set_adjacent([(cx14, 5000),(cx24,4000)], (cx16,100))
        cx16.set_adjacent(cx15.conveyor, cx17)
        cx17.set_adjacent(cx16, self.cx18)
        self.cx18.set_adjacent(cx17, None)
        cx21.set_adjacent(None, cx22)
        cx22.set_adjacent(cx21, cx23)
        cx23.set_adjacent(cx22, cx24)
        cx24.set_adjacent(cx23, cx15.conveyor)
       
        self.add_conveyor(cx11, cx12, cx13, cx14, cx15, cx16, cx17, self.cx18, cx21, cx22, cx23, cx24)

        cx11.auto_add_boxes = True
        cx21.auto_add_boxes = True
        self.cx18.auto_clear = True

        self._area_state_changed(False)
        
    @property
    def outfeed_cx18(self):
        return self.cx18


class Lift:
    """
    A Lift module with a single drive
    """
    def __init__(self, name, reference_designation, area = None, height = 5000):
        self._name = name
        self._speed_fast = 1000
        self._speed_slow = 500
        self._area = area
        
        self._error_handler = ErrorHandler(area, name)
        self._error_handler.link_to_parent(area.error_handler)
        self._reference_designation = Variant(name + "/ReferenceDesignation", area, reference_designation, ValueDataType.String)
        
        self._move_fast = CommandToggle(name + "/Cmd_MoveFast_Toggle", area, True, lambda v: self._change_speed_request())
        self._reset_error = CommandTap(name + "/Cmd_ResetError_Tap", area, False, lambda v: self._reset_error_request())
        self._lift_position = Variant(name + "/LiftPosition", area, height / 2, ValueDataType.Float)
        
        self._conveyor = Conveyor(name + "/Conv", reference_designation, area, 1000, 200)
        self._conveyor.transport_handler.on_request_source = self._on_request_source
        self._conveyor.transport_handler.on_request_target = self._on_request_target
        
        self._drive = DrivePos(name, "LiftDrive", reference_designation[0:-3] + "D02", self._speed_fast, area)
        self._drive.error_handler.link_to_parent(self.error_handler)
        self._drive.encoder = height / 2
        
        Switch(name + "/GapCheck_1", area, False, False)
        Switch(name + "/GapCheck_2", area, False, False)
        self._in_motion = Switch(name + "/InPosition", area, False, False)
        self._in_position = Switch(name + "/InMotion", area, False, False)
        
        self._next_source = None
        self._next_target = None 
        self._lift_source = None
        self._lift_target = None  
        
    def area_state_changed(self, mode_auto, switched_on):
        self._conveyor.area_state_changed(mode_auto, switched_on)
        
        if mode_auto:
            self._drive.manual_mode = False
        else:
            self._drive.manual_mode = True
            
        if switched_on:
            pass
    
    def _reset_error_request(self):
        self._drive.reset_error()
        self._conveyor.error_handler.clear_error()
        
    def _change_speed_request(self):
        if self._move_fast.value:
            self._drive.set_speed(self._speed_fast)
        else:
            self._drive.set_speed(self._speed_slow)
        
    @property
    def current_position(self):
        return self._lift_position.value
    
    @current_position.setter
    def current_position(self, value):
        self._lift_position = value
        
    @property
    def conveyor(self):
        return self._conveyor
    
    @property
    def error_handler(self):
        return self._error_handler
    
    def set_adjacent(self, source = [(None, 0)], target=(None, 0)):
        self._lift_source = source
        self._lift_target = target    
    
    def _on_request_target(self):
        if self._next_target:
                return self._next_target.transport_handler
        return None
    
    def _on_request_source(self):
        if self._next_source:
            return self._next_source.transport_handler
        return None
    
    def _lift_logic(self, tick):
        
        self._conveyor.transport_handler.ready_takeover = self._next_source is not None
        
        if self._drive.busy:
            return
        
        if self._conveyor.empty:
            self._next_target = None
            if not self._lift_source:
                return
            
            for s in self._lift_source:
                if s[0].transport_handler.ready_handover:
                    self._drive.move_to(s[1])
                    if self.current_position == s[1]:
                        self._next_source = s[0]
 
                    break
        else:
            self._next_source = None
            
            if not self._lift_target:
                return
            
            self._drive.move_to(self._lift_target[1])
            if self.current_position == self._lift_target[1]:
                self._next_target = self._lift_target[0]

    
    def loop(self, tick):
        self._lift_position.value = self._drive.encoder

        self._conveyor.loop(tick)
        self._lift_logic(tick)
        
        self._drive.run(tick, self.released)
        
        self._in_motion.value = self._drive.busy
        self._in_position.value = not self._drive.busy
    
    @property
    def released(self):
        """
        Describes whenever the conveyor is released for transportation

        """
        if not self._area.auto:
            return False
        
        if not self._area.on:
            return False
        
        if self.error_handler.error_pending:
            return False
        
        if self._conveyor.error_handler.error_pending:
            return False
        
        return True

             
class Conveyor:
        
    def __init__(self, name, reference_designation, area = None, length = 1000, speed = 200):
        
        self._name = name
        self._area = area
        self._length = length        
        self._speed = speed
        self._source = None
        self._target = None
        
        self._error_handler = ErrorHandler(area, name)
        self._error_handler.link_to_parent(area.error_handler)
        self._reference_designation = Variant(name + "/ReferenceDesignation", area, reference_designation, ValueDataType.String)
        self._type = Variant(name + "/Type", area, "Conveyor", ValueDataType.String)
        
        self._transport_handler = TransportHandler(name, area, length)
        self._transport_handler.on_request_source = self._on_request_source
        self._transport_handler.on_request_target = self._on_request_target

        # data points
        self._reset_error = CommandTap(name + "/Cmd_ResetError_Tap", area, False, lambda v: self._reset_error_request())
        self._photoeye = Switch(name + "/Photoeye", area, False, False)
        
        self._drive = Drive(name, "Drive", reference_designation[0:-3] + "D01", speed, area)
        self._drive.error_handler.link_to_parent(self.error_handler)
        
        self._auto_clear = CommandToggle(name + "/Sim/AutoClear_Toggle", area, False)
        self._counter = 0
        
   
        self._auto_add_boxes = CommandToggle(name + "/Sim/AutoAddBoxes_Toggle", area, False, lambda v: self._change_speed_request())
        self._auto_add_boxes_interval = Variant(name + "/Sim/AutoAddBoxes_Interval", area, 5, ValueDataType.Int)
        self._auto_add_boxes_current = 0;

        CommandTap(name + "/Sim/AddBox_Tap", area, False, lambda v: self.transport_handler.insert_new_box())
        CommandTap(name + "/Sim/DriveErrorTap", area, False, lambda v: self._drive.sim_error())
        CommandTap(name + "/Sim/JamErrorTap", area, False, lambda v: self.sim_jam_error())
        
    @property
    def auto_add_boxes(self):
        return self._auto_add_boxes.value

    @auto_add_boxes.setter
    def auto_add_boxes(self, value):
        self._auto_add_boxes.value = value


    @property
    def reference_designation(self):
        return self._reference_designation.value

    @property
    def error_handler(self):
        return self._error_handler

    @property
    def name(self):
        return self._name
    
    @property
    def auto_clear(self):
        return self._auto_clear.value
    
    @auto_clear.setter
    def auto_clear(self, value):
        self._auto_clear.value = value
    
    @property
    def source(self):
        return self._source
    
    @property
    def target(self):
        return self._target
 
    @property
    def transport_handler(self):
        return self._transport_handler
    
    @transport_handler.setter
    def transport_handler(self, value):
        self._transport_handler = value
    
    @property
    def empty(self):
        return not self._transport_handler.box 
    
    def sim_jam_error(self):
        self._error_handler.set_error("Jam", self._reference_designation.value)
        
    def set_source(self, source):
        self.set_adjacent(source, self._target)
        
    def set_target(self, target):
        self.set_adjacent(self._source, target)
    
    def _reset_error_request(self):
        self._drive.error_handler.clear_error()
        self.error_handler.clear_error()
    
    def set_adjacent(self, source = None, target=None):
        self._source = source
        self._target = target   
        if ((self._source != source) or
            (self._target != target)):
            self.transport_handler.clear_links()
    
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
            self._drive.manual_mode = False
        else:
            self._drive.manual_mode = True
            
        if switched_on:
            pass
    
    def loop(self, tick):


        if self._auto_add_boxes.value and not self.transport_handler.box:
            self._auto_add_boxes_current += tick
        else:
            self._auto_add_boxes_current = 0

        if self._auto_add_boxes_current >= self._auto_add_boxes_interval.value:
            self.transport_handler.insert_new_box()
            self._auto_add_boxes_current = 0


        self.transport_handler.loop(tick, self.released, self._drive.current_speed)
        self._drive.run(tick, self.transport_handler.run_drive)

        # update signals
        self._photoeye.value = self.transport_handler.box_found_at(self._length / 2)
        
        if self.auto_clear:
            if self.transport_handler.ready_handover:
                self._counter = self._counter + tick
                elapsed = self._counter >= 3
                
                if elapsed:
                    self._counter = 0
                    self.transport_handler.remove_box()
  
    
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
        
        if self.error_handler.error_pending:
            return False
        
        return True
        

class Drive:

    def __init__(self, parent_name, name,reference_designation, speed = 100, parent = None):
        
        self._manual_on = CommandToggle(parent_name + "/" + name + "/Cmd_ManualOn_Toggle", parent, False, None, condition = lambda: self.manual_mode)
 
        self._manual_mode = Switch(parent_name + "/" + name + "/ManualMode", parent, False, False)
        self._drive_on = Switch(parent_name + "/" + name + "/DriveOn", parent, False, False)
        self._drive_speed = Variant(parent_name + "/" + name + "/CurrentSpeed", parent, 0, ValueDataType.Int)
        self._drive_speed_setpoint = Variant(parent_name + "/" + name + "/SetpointSpeed", parent, speed, ValueDataType.Int)
        self._drive_current = Variant(parent_name + "/" + name + "/Current", parent, 0.0, ValueDataType.Float)
        self._drive_encoder = Variant(parent_name + "/" + name + "/Encoder", parent, 0.0, ValueDataType.Float)
        
        self._error_handler = ErrorHandler(parent, parent_name + "/" + name)
        self._reference_designation = Variant(parent_name + "/" + name + "/ReferenceDesignation", parent, reference_designation, ValueDataType.String)
        self._type = Variant(parent_name + "/" + name + "/Type", parent, "Drive", ValueDataType.String)

    @property
    def reference_designation(self):
        return self._ref_des.value

    @property
    def error_handler(self):
        return self._error_handler
    
    @property
    def current_speed(self):
        return self._drive_speed.value

    @property
    def manual_mode(self):
        return self._manual_mode.value
    
    @manual_mode.setter
    def manual_mode(self, value):
        if not value:
            self._manual_on.value = False
            self._drive_speed.value = 0
            self._drive_current.value = 0
            self._drive_on.value = False
            
        self._manual_mode.value = value
    
    @property
    def encoder(self):
        return self._drive_encoder.value
    
    @encoder.setter
    def encoder(self, value):
        self._drive_encoder.value = value
    
    def set_speed(self, speed):
        self._drive_speed_setpoint.value = speed
        
    def sim_error(self):
        self._error_handler.set_error("Overcurrent", self._reference_designation.value)

    def run(self, tick, run, speed = None):
        if speed:
            self._drive_speed_setpoint.value = speed
            
        move_allowed = (((run and not self.manual_mode) or
                                 (self._manual_on.value and self.manual_mode)) and
                                 not self._error_handler.error_pending)
        
        self._run_process(move_allowed, tick)
        
    def _run_process(self, run, tick):
        
        if run:
            self._drive_speed.value = self._drive_speed_setpoint.value
            self._drive_current.value = 3.5
            self._drive_encoder.value = self._drive_encoder.value + self._drive_speed_setpoint.value
        else:
            self._drive_speed.value = 0
            self._drive_current.value = 0
            
        self._drive_on.value = run


class DrivePos(Drive):
    
    def __init__(self, parent_name, name,reference_designation, speed = 1000, parent = None):
        super().__init__(parent_name, name,reference_designation, speed, parent)
        
        self._busy = Switch(parent_name + "/" + name + "/Busy", parent, False, False)
        self._target = Variant(parent_name + "/" + name + "/Target", parent, 0, ValueDataType.Int)
        
    def move_to(self, target):
        if not self._busy.value:
            self.target = target
            self._busy.value = self._drive_encoder.value != target
          
    @property
    def target(self):
        return self._target.value
    
    @target.setter
    def target(self, value):
        self._target.value = value
    
    @property
    def busy(self):
        return self._busy.value
            
    def _run_process(self, run, tick):
        
        if self.manual_mode:
            if self._manual_on.value:
                self._drive_speed.value = 100
                self._drive_current.value = 5.5
                self._drive_encoder.value = self._drive_encoder.value + 100
                self._drive_on.value = True
            else:
                self._drive_speed.value = 0
                self._drive_current.value = 0
                self._drive_on.value = False
            return
        
        self._drive_on.value = self.busy and run
        
        if self.busy and run:
            self._drive_speed.value = self._drive_speed_setpoint.value
            self._drive_current.value = 10.5
            
            if self.target > self._drive_encoder.value:
                pos_step = self._drive_speed_setpoint.value * tick
                
                if pos_step + self._drive_encoder.value > self.target:
                    self._drive_encoder.value = self.target
                    self._busy.value = False
                else:
                    self._drive_encoder.value = self._drive_encoder.value + pos_step
                    
            elif self.target < self._drive_encoder.value:
                pos_step = self._drive_speed_setpoint.value * tick * (-1)
                
                if pos_step + self._drive_encoder.value < self.target:
                    self._drive_encoder.value = self.target
                    self._busy.value = False
                else:
                    self._drive_encoder.value = self._drive_encoder.value + pos_step
            else:
                pos_step = 0
                self._busy.value = False
        else:
            self._drive_speed.value = 0
            self._drive_current.value = 0.0
            
  




             
class TransportHandler:
    
    def __init__(self, parent_name, parent, length = 1000):
        self._box = None
        self._parent_name = parent_name
        self._target = None
        self._source = None
        self._run_drive = False
        
        # data points
        self._cmd_interrupt = CommandToggle(parent_name + "/Cmd_Interrupt_Toggle", parent, False)
        self._length = Variant(parent_name + "/Length", parent, length, ValueDataType.Int)
        self._box_position = Variant(parent_name + "/BoxPosition", parent, False, ValueDataType.Float)
        self._box_id = Variant(parent_name + "/BoxId", parent, "", ValueDataType.String)
        self._occupied = Switch(parent_name + "/Occupied", parent, False, True)
        self._transport_allowed = Switch(parent_name + "/TransportAllowed", parent, False, False)
        self._ready_handover = Switch(parent_name + "/ReadyHandover", parent, False, False)
        self._ready_takeover = Switch(parent_name + "/ReadyTakeover", parent, True, False)
        self._source_name = Variant(parent_name + "/SourceName", parent, "", ValueDataType.String)
        self._target_name = Variant(parent_name + "/TargetName", parent, "", ValueDataType.String)
     
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
        
    def takeover_process(self):
        box_values = self.source.takeover_box()
        if box_values:
            self.occupied = True
            self._box = box_values[0]
            self.box_position = box_values[1]
            self.clear_links()
    
    def request_transport(self, source):
        if self.box:
            return False
        
        if not self.ready_takeover:
            return False
        
        if self.source != source:
            return False
        
        if source.takeover_box():
            self.occupied = True
            return True
        return False
    
    def insert_new_box(self):
        global box_manager

        if self.box:
            raise Exception("Already Box present")
            
        self._box = box_manager.next_box()

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
                if self.ready_takeover:
                    if self.source.ready_handover:
                        self.takeover_process()
                        
        # update cyclic data
        if self.box:
            self._box_id.value = self.box.box_id
        else:
            self._box_id.value = ""
            
        self._ready_handover.value = self.ready_handover


if __name__ == "__main__":
    
    print("Start Application, Arguments({}): {}".format(len(sys.argv)-1, sys.argv[1:]))
    
    print("#####################################################")
    print(" ")
    print("Simulation: Smart Delivery, Version: " + __version__)
    print(" ")
    print("Press Ctrl + C to close the application properly. ")
    print(" ")
    print("#####################################################")
    
    options, args = getopt.getopt(sys.argv[1:], "g:h:p:n:l:",
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
    
    logger = logging.getLogger("iomodel.common.runner")
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