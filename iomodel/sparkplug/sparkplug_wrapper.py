
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 13:18:46 2021

@author: mbfhn
"""
import sys
import time
import sparkplug_b as sparkplug
import sparkplug_b_pb2
import paho.mqtt.client as mqtt
import logging 

class SparkplugBaseMetricAlias:
    Next_Server = 0
    Rebirth = 1
    Reboot = 2

class SparkplugWrapper:
    """
    Base Wrapper for Nodes and Devices.
    
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._metrics = []

    @property
    def metrics(self):
        return self._metrics
    
    def extend_metrics(self, metrics):
        """
        Extend the existing metric list

        Parameters
        ----------
        metrics : list of MetricHelper

        """
        self.logger.debug("Extend metrics with:", metrics)
        self.metrics.extend(metrics)
    
    def publishBirth(self):
        """
        Publish birth certificate - Overwrite!
        
        """
        pass
    
    
    def loop(self):
        """
        Single loop to handle continuous operations - Overwrite to implement

        """
        pass
    
    
    def add_properties_to_metric(self, metric, properties):
        """
        Add custom properties to metric
    
        """
        if properties is not None:
            for prop in properties:
                metric.properties.keys.extend([prop[0]])
                prop_val = metric.properties.values.add()
                prop_val.type = prop[2]
                
                if prop_val.type == sparkplug.ParameterDataType.String:
                    prop_val.string_value = prop[1]
                else:
                    # missing type definition
                    raise Exception("Type implementation missing") 
                    
    def _consume_msg(self, sp_payload):
        """
        Consume sparkplug message

        """
        # Search for received metric and call related method to handle action
        for payload_metric in sp_payload.metrics: 
            for metric in self.metrics:
                if payload_metric.name == metric.name or payload_metric.alias == metric.alias:
                    if metric.invoke_method is not None:
                        metric.invoke_method(payload_metric)
                        
class SparkplugNodeWrapper(SparkplugWrapper):
    """
    Wrapper base class for a sparkplug_b Node
    
    """
    
    def __init__(self,  group_id, node_id, mqtt_args):
        """        

        Parameters
        ----------
        group_id : TYPE
            DESCRIPTION.
        node_id : TYPE
            DESCRIPTION.
        mqtt_args : TYPE
            Tuple:
                ip, port, timeout

        Returns
        -------
        None.

        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        self._group_id = group_id
        self._node_id = node_id
        self._setup_default_metrics()
        
        # Setup mqtt
        self._broker_ip = mqtt_args[0]
        self._broker_port = mqtt_args[1]
        self._broker_timeout = mqtt_args[2]

        self._client = mqtt.Client(self._broker_ip, self._broker_port, self._broker_timeout)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        
        # node devices
        self._node_devices = {}
        
   
    
    @property
    def group_id(self):
        """
        Group ID

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        return self._group_id
    
    @property
    def node_id(self):
        """
        Node id

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        return self._node_id
    
    @property
    def client(self):
        """
        MQTT Client

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        return self._client
    
    
    def publishBirth(self, *args):
        self.logger.debug("Publishing Node Birth")

        # Create the node birth payload
        payload = sparkplug.getNodeBirthPayload()
    
        # Add all metrics to payload, including custom properties
        for metric in self.metrics:
            m = sparkplug.addMetric(payload, metric.name, metric.alias, metric.datatype, metric.initial)
            
            super().add_properties_to_metric(m, metric.property_list)
            
            
        byteArray = bytearray(payload.SerializeToString())
        self.client.publish("spBv1.0/" + self.group_id + "/NBIRTH/" + self.node_id, byteArray, 0, False)


    def register_device(self, device):
        """
        Register device on its node
        """
        self._node_devices[device.device_name] = device
    
    def loop_devices(self):
        """
        Call all loop() from each device

        """
        for device_key in self._node_devices:
            self._node_devices[device_key].loop()
       
    def publishBirth_devices(self):
        """
        Send Birth message for all devices

        """
        for key in self._node_devices:
            self._node_devices[key].publishBirth()
    
    def loop_start(self):
        # Prepare last will
        self.logger.debug("set last will message")
        deathPayload = sparkplug.getNodeDeathPayload()
        deathByteArray = bytearray(deathPayload.SerializeToString())
        self._client.will_set("spBv1.0/" + self.group_id + "/NDEATH/" + self.node_id, deathByteArray, 0, False)

        self._client.connect(self._broker_ip, self._broker_port, self._broker_timeout)
        
        time.sleep(.1)
        self._client.loop()

        self.publishBirth()
        self.publishBirth_devices()
        
    def loop_stop(self):
        pass
    
    def loop_forever(self):
        """
        Loops forever (blocking)

        Returns
        -------
        None.

        """
        self.loop_start()
        
        while True:
            self._client.loop()
            self.loop()
            time.sleep(0.5)
            
    def _setup_default_metrics(self):
        """
        Default metrics (e.g. Next Server, Rebirth, Reboot)

        Returns
        -------
        None.

        """
        default_node_metrics = []
        default_node_metrics.append(MetricHelper("Node Control/Next Server", SparkplugBaseMetricAlias.Next_Server, sparkplug.MetricDataType.Boolean, False, None))
        default_node_metrics.append(MetricHelper("Node Control/Rebirth", SparkplugBaseMetricAlias.Rebirth, sparkplug.MetricDataType.Boolean, False, self.publishBirth))
        default_node_metrics.append(MetricHelper("Node Control/Reboot", SparkplugBaseMetricAlias.Reboot, sparkplug.MetricDataType.Boolean, False, self.publishBirth))
        super().extend_metrics(default_node_metrics)

    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback - MQTT client connected
        Subscribe on Command Topics NCMD / DCMD

        """
        if rc == 0:
            self.logger.info("Connected with result code "+str(rc))
            client.subscribe("spBv1.0/" + self.group_id + "/NCMD/" + self.node_id + "/#")
            client.subscribe("spBv1.0/" + self.group_id + "/DCMD/" + self.node_id + "/#")
        else:
            self.logger.info("Failed to connect with result code "+str(rc))
            sys.exit()
    
    def _on_message(self, client, userdata, msg):
        """
        Callback - MQTT client message received

        """
        self.logger.debug("Message arrived: " + msg.topic)
    
        tokens = msg.topic.split("/")
        
        # Ensure topic matches current node
        if tokens[0] == "spBv1.0" and tokens[1] == self.group_id and (tokens[2] == "NCMD" or tokens[2] == "DCMD") and tokens[3] == self.node_id:
            payload = sparkplug_b_pb2.Payload()
            payload.ParseFromString(msg.payload)

            if tokens[4] is not None:
                for device_key in self._node_devices:
                    if device_key == tokens[4]:
  
                        self._node_devices[device_key]._consume_msg(payload)
            else:
                super()._consume_msg(payload)
                
        else:
            self.logger.error("subscribed topic is unequal to compared node / device id")
    
    
    
    

class SparkplugDeviceWrapper(SparkplugWrapper):
    """
    Base Wrapperclass for a sparkplug device
    """
    
    def __init__(self, device_name, node):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        self._node = node
        self._device_name = device_name
        self._client = self._node.client
        self._node.register_device(self)
        
    @property
    def node(self):
        return self._node
    
    @property
    def client(self):
        return self._client

    @property
    def device_name(self):
        return self._device_name
    
    def report_changed_metric(self, changed_list):
        
        if changed_list == None or len(changed_list) == 0:
            return
        
        payload = sparkplug.getDdataPayload()
    
        for change in changed_list:
            metric = change[0]
            new_val = change[1]
            sparkplug.addMetric(payload, None, metric.alias, metric.datatype, new_val)
          
        byteArray = bytearray(payload.SerializeToString())
        self.client.publish("spBv1.0/" + self.node.group_id + "/DDATA/" + self.node.node_id + "/" + self.device_name, byteArray, 0, False)
        
    
    def publishBirth(self, *args):
        self.logger.debug("Publishing Device Birth")

        # Create the node birth payload
        payload = sparkplug.getDeviceBirthPayload()
    
        # Add all metrics to payload, including custom properties
        for metric in self.metrics:
            m = sparkplug.addMetric(payload, metric.name, metric.alias, metric.datatype, metric.initial)
            
            super().add_properties_to_metric(m, metric.property_list)
            
        byteArray = bytearray(payload.SerializeToString())
        self.client.publish("spBv1.0/" + self.node.group_id + "/DBIRTH/" + self.node.node_id + "/" + self.device_name, byteArray, 0, False)


class MetricHelper:
    """
    Helper Class to define metrics
    """
    
    def __init__(self, name, alias, datatype, initial, invoke_method, property_list = None):
        self._name = name
        self._alias = alias
        self._datatype = datatype
        self._initial = initial 
        self._invoke_method = invoke_method
        self._property_list = property_list
        
    def add_property(self, prop = ("myProp", "MyValue", sparkplug.ParameterDataType.String)):
        if self._property_list is None:
            self._property_list = []
            
        self._property_list.append(prop)
        
    @property
    def name(self):
        return self._name
    
    @property
    def alias(self):
        return self._alias
    
    @property
    def datatype(self):
        return self._datatype
    
    @property
    def initial(self):
        return self._initial
    
    @property
    def invoke_method(self):
        return self._invoke_method
    
    @property
    def property_list(self):
        return self._property_list
    
    
class DeviceVarObserver:

    def __init__(self, metric):
        self._metric = metric
        self._last_value = None
        
    @property
    def metric(self):
        return self._metric
    
    def observe(self, new_value, change_list):
        
        if new_value != self._last_value:
            self._last_value = new_value
            
            change_list.append((self.metric, new_value))
    
    
    