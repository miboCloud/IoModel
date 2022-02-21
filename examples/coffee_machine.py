# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import getopt
import logging
import json

from iomodel.common.base import ModelDevice, ValueDataType
from iomodel.common.components import Switch, TemperatureSensor, ModelValue, LevelSensor, CommandTap, Variant
from iomodel.sparkplug.connector import NodeConnector
from iomodel.common.runner import ModelRunner
from enum import Enum
from timeit import default_timer as timer


__version__ = "1.1.1"

class OperationState(Enum):
    """
    Operationstates
    """
    Off = 0,
    ServiceRequired = 1,
    Ready = 2,
    HeatUp_Grind = 3,
    Output = 4,
    Cleaning = 5
        
     
class CoffeeMachine(ModelDevice):
    """
    Simulated coffee machine
    
    Uses MQTT with SparkplugB Specification
    """
    COFFEE_COUNTER = 0

    def __init__(self, name, parent = None):
        super().__init__(name, parent)
        
        # states
        self._state_on = Variant("1_State/SwitchedOn", self, False, ValueDataType.Boolean)
        
        self._state_str = Variant("1_State/State", self, "Idle", ValueDataType.String)
        self._state_ready = Variant("1_State/Ready", self, False, ValueDataType.Boolean)
        self._state_busy = Variant("1_State/Busy", self, False, ValueDataType.Boolean)
        
        # commands
        
        self._cmd_switch_on = CommandTap("2_Commands/Switch_on", self, False, lambda v: self.switch_on(v))
        self._cmd_switch_off = CommandTap("2_Commands/Switch_off", self, False, lambda v: self.switch_off(v))
        self._cmd_switch_clean = CommandTap("2_Commands/Clean", self, False, lambda v: self.clean(v))
        self._cmd_switch_order = CommandTap("2_Commands/Order", self, False, lambda v: self.order(v))
        
        # orders
        self._order_coffee = ModelValue("3_Order/Coffee", self, ValueDataType.Boolean, False, True)
        self._order_espresso = ModelValue("3_Order/Espresso", self, ValueDataType.Boolean, False, True)
        self._order_intensity = ModelValue("3_Order/Intensity", self, ValueDataType.Int, 0, True)
        self._order_without_caffeine = ModelValue("3_Order/WithoutCaffeine", self, ValueDataType.Boolean, False, True)
        self._order_milk = ModelValue("3_Order/Addition/Milk", self, ValueDataType.Boolean, False, True)
        self._order_cream = ModelValue("3_Order/Addition/Cream", self, ValueDataType.Boolean, False, True)
        self._order_sugar = ModelValue("3_Order/Addition/Sugar", self, ValueDataType.Boolean, False, True)
        
        # parameters
        self._param_time_coffee = ModelValue("4_Parameter/Time_Coffee", self, ValueDataType.Float, 8.0, True)
        self._param_time_espresso = ModelValue("4_Parameter/Time_Espresso", self, ValueDataType.Float, 4.0, True)
        self._param_time_cleaning = ModelValue("4_Parameter/Time_Cleaning", self, ValueDataType.Float, 10.0, True)
        self._param_water_output = ModelValue("4_Parameter/Water_per_output", self, ValueDataType.Float, 10.0, True)
        
        # internal
        self._beans_container_1 = Switch("5_Beans/Container_coffee_empty", self, False, True)
     
        self._beans_container_2 = Switch("5_Beans/Container_espresso_empty", self, False, True)
        
        self._water_tank_empty = Switch("6_Water/Water_tank_empty", self, False)
        self._water_tank_level = LevelSensor("6_Water/Water_tank_level", self, 100.0, True)
        self._water_tank_available = Switch("6_Water/Water_tank_available", self, True, True)
        
        self._driptray_full = Switch("7_DripTray/Driptray_full", self, False, True)
        self._driptray_available = Switch("7_DripTray/Driptray_available", self, True, True)
        
        self._groundstray_full = Switch("8_GroundsTray/Groundstray_full", self, False, True)
        self._groundstray_available = Switch("8_GroundsTray/Groundstray_available", self, True, True)
        
        # sensors
        self._temp = TemperatureSensor("9_Sensors/Temperatur", self, 0.0, 83, 1)
        self._flow = TemperatureSensor("9_Sensors/Flow", self, 0.0, 0.05, 1)
        self._cup_available = Switch("9_Sensors/Cup_available", self, False, True)
        
        self._state = OperationState.Off
        
        self._t = timer()
        
        PaymentSystem("20_PaymentSystem", self)
    
    def _order_start(self):
        print("New Coffee Order:")
        self._print_order()
        
    def _order_end(self):
        print("Order " + str(CoffeeMachine.COFFEE_COUNTER) + " done.")
        self._reset_order()
    
    def _print_order(self):
        CoffeeMachine.COFFEE_COUNTER += 1
        x = {
            "Counter" : str(CoffeeMachine.COFFEE_COUNTER),
            "Kaffee" : str(self._order_coffee.value),
            "Espresso" : str(self._order_espresso.value),
            "Intensity" : str(self._order_intensity.value),
            "WithoutCaffeine" : str(self._order_without_caffeine.value),
            "Milk" : str(self._order_milk.value),
            "Cream" : str(self._order_cream.value),
            "WithSugar" : str(self._order_sugar.value)
            }
        print(json.dumps(x))
    
    def _reset_order(self):
        self._order_coffee.value = False
        self._order_espresso.value = False
        self._order_intensity.value = 0
        self._order_without_caffeine.value = False
        self._order_milk.value = False
        self._order_cream.value = False
        self._order_sugar.value = False
        
    def _service_required(self):

        return (self._beans_container_1.value or
                self._beans_container_2.value or
                self._water_tank_empty.value or
                not self._water_tank_available.value or
                self._driptray_full.value or 
                not self._driptray_available.value or
                self._groundstray_full.value or
                not self._groundstray_available.value)

    def switch_on(self, value):
        
        if self._state == OperationState.Off:
            self._state = OperationState.ServiceRequired
        
    def switch_off(self, value):

        if self._state == OperationState.ServiceRequired or self._state == OperationState.Ready:
            self._state = OperationState.Off
        
    def clean(self, value):
        if self._state == OperationState.ServiceRequired or self._state == OperationState.Ready:
            self._state = OperationState.Cleaning
            self._t =  timer()
        
    def order(self, value):
        if self._state == OperationState.Ready:
            self._reduce_Water()
            self._order_start()
            self._state = OperationState.HeatUp_Grind
        
    def _reduce_Water(self):
        val = self._water_tank_level.value 
        val -= self._param_water_output.value
        
        if val <= 0:
            val = 0
            
        self._water_tank_level.value = val
        
        
    def loop(self, tick):
        super().loop(tick)
        
        self._water_tank_empty.value = self._water_tank_level.value <= 0
        
        # Update States
        self._state_str.value = self._state.name
        self._state_on.value = self._state != OperationState.Off
        self._state_ready.value = self._state == OperationState.Ready
        self._state_busy.value = (self._state != OperationState.Ready and
                                  self._state != OperationState.Off and
                                  self._state != OperationState.ServiceRequired)
        
        # Monitor service
        if self._state == OperationState.ServiceRequired:
            if not self._service_required():
                self._state = OperationState.Ready
            
        if self._state == OperationState.Ready:
            if self._service_required():
                self._state = OperationState.ServiceRequired
        
        # Phase Heat up
        if self._state == OperationState.HeatUp_Grind:
            if self._temp.value > 80:
                self._state = OperationState.Output
                self._t =  timer()
        
        # cleaning
        if self._state == OperationState.Cleaning:
            
            if timer() - self._t >= self._param_time_cleaning.value:
                self._state = OperationState.ServiceRequired
        
        # output
        if self._state == OperationState.Output:
            
            if timer() - self._t >= self._param_time_coffee.value:
                self._order_end()
                self._state = OperationState.ServiceRequired
        
        # Sensors
        self._temp.heat(self._state == OperationState.HeatUp_Grind or self._state == OperationState.Output)
        self._flow.heat(self._state == OperationState.Output or self._state == OperationState.Cleaning)
        
class PaymentSystem(ModelDevice):

    def __init__(self, name, parent = None):
        super().__init__(name, parent)
        ModelValue("SystemOnline", self, ValueDataType.Boolean, True).external_write = True
        

if __name__ == "__main__":

    print("Start Application, Arguments({}): {}".format(len(sys.argv)-1, sys.argv[1:]))
    
    print("#####################################################")
    print(" ")
    print("Simulation: Kaffeemaschine, Version: " + __version__)
    print(" ")
    print("Press Ctrl + C to close the application properly. ")
    print(" ")
    print("#####################################################")
    
    options, args = getopt.getopt(sys.argv[1:], "g:h:p:l:n:",
                               ["group =","host =","port =", "node =", "log ="])
    
    group = "CoffeeMaker"
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
            print(value)
            if value.lower() == 'true':
                log_level = logging.DEBUG
            
    # Setup logger
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', 
                        level=log_level)
    
    #logger = logging.getLogger("common.runner")
    #logger.setLevel(logging.DEBUG)
    
    # Setup Model
    runner = ModelRunner(1)
    
    coffee = CoffeeMachine(node)
    runner.add_model_object(coffee)
    
    # Setup Sparkplug connection
    broker_args = (host, port, 60)
    coffeeNode = NodeConnector(coffee, group, broker_args, node)
    coffeeNode.start_loop()

    try:
        runner.loop_forever()
    except (KeyboardInterrupt, SystemExit):
        
        coffeeNode.stop_loop()
        print("Application stopped")