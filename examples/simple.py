# -*- coding: utf-8 -*-


from common.runner import ModelRunner
from common.components import TemperatureSensor
from common.util_behavior import LatchIntervall
import logging

if __name__ == "__main__":
    
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', 
                        filename="log.log", level=logging.DEBUG)
    
    logger = logging.getLogger("common.runner")
    logger.setLevel(logging.DEBUG)
    
    
    runner = ModelRunner(0.2)
    
    sensor = TemperatureSensor(80)
    
    intervall = LatchIntervall(5, [lambda: sensor.heat(True), lambda: sensor.heat(False)])
    
    runner.add_model_object(sensor)
    runner.add_model_object(intervall)
    
    runner.loop_forever()