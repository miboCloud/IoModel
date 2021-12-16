# -*- coding: utf-8 -*-

from common.base import ModelDevice, ModelValue, ModelDataSet, ValueDataType
from timeit import default_timer as timer

import sys
import time
import logging
import threading
import paho.mqtt.client as mqtt

import sparkplug.sparkplug_b as sp
import sparkplug.sparkplug_b_pb2



class NodeConnector:
    """
    Represents one node connected to MQTT Broker with
    Sparkplug B.
    """
    
    def __init__(self, model, group = "defaultGroup", mqtt_args = ("127.0.0.1", 1883, 60), connect_id = None):
        """
        

        Parameters
        ----------
        model : ModelDevice
            A ModelDevice - Can consist of more child devices.
            The first model is taken as node for sparkplug.
        group : String, optional
            GroupName for this node
        mqtt_args : Args, optional
            MQTT Arguments. The default is ("127.0.0.1", 1883, 60).

        """
        self.logger = logging.getLogger(__name__)
        
        if not isinstance(model, ModelDevice):
            raise Exception("Injected model is no device")
        
        self._group = group
        self._model = model
        self._connect_id = connect_id
        # Setup mqtt
        self._broker_ip = mqtt_args[0]
        self._broker_port = mqtt_args[1]
        self._broker_timeout = mqtt_args[2]

        self._client = mqtt.Client(self._connect_id, clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        
        self._thread = None
        self._thread_terminate = False
        
        # Assign node and create SparkplugNode
        self._node = SparkplugNode(self, self._model)
        
    @property
    def group(self):
        """
        Return: group, string
        """
        return self._group
    
    @property
    def client(self):
        """
        Return: client, MQTT Client
        """
        return self._client

    def start_loop(self):
        """
        Start the node connector
        Establishes main thread to establish connection,
        and handle nodes / devices

        """
        self._thread_terminate = False
        
        if self._thread is not None:
            raise Exception("Thread already started")
        
        self._thread = threading.Thread(target = self._main_thread)
        self._thread.daemon = True
        self._thread.start()
        self.logger.debug("Thread started: %s", self._thread)
        
    
    def stop_loop(self):
        """
        Stops the node connector

        """
        if self._thread is None:
            raise Exception("No running thread.")
        
        self._thread_terminate = True
        
        if threading.current_thread() != self._thread:
            self._thread.join()
            self.logger.debug("Thread stopped: %s", self._thread)
            self._thread = None

    
    def _main_thread(self):
        """
        Main Thread


        """
        self.logger.debug("Setup Last Will")
        deathPayload = sp.getNodeDeathPayload()
        deathByteArray = bytearray(deathPayload.SerializeToString())
        self._client.will_set("spBv1.0/" + self.group + "/NDEATH/" + self._node.name, deathByteArray, 0, False)

        
        self.logger.debug("MQTT - Connect...")
        try:
            self._client.connect(self._broker_ip, self._broker_port, self._broker_timeout)
            self.logger.debug("MQTT - Connected.")
            print("Connected", "MQTT-ID:", self._client._client_id)
        except:
            self.logger.debug("MQTT - Connection failed")
            self.logger.warn("%s-%s Connector failed.",self.group, self._model.name)
            sys.exit()
        
        self._node.publishBirth()
        self._client.loop()
        self._node.loop()
        time.sleep(0.2)
        
        while not self._thread_terminate:
            self._node.loop()
            self._client.loop()
            time.sleep(0.5)
        
        print("Connection closed")

    def _on_message(self, client, userdata, msg):
        """
        Callback - MQTT client message received

        """
        self.logger.debug("Message arrived: " + msg.topic)
    
        tokens = msg.topic.split("/")

        # Ensure topic matches current node
        if tokens[0] == "spBv1.0" and tokens[1] == self.group and (tokens[2] == "NCMD" or tokens[2] == "DCMD") and tokens[3] == self._node.name:
            payload = sparkplug.sparkplug_b_pb2.Payload()
            payload.ParseFromString(msg.payload)

            if len(tokens) > 4:
                self._node.consume_msg(payload, tokens[4])
            else:
                self._node.consume_msg(payload, None)

        else:
            self.logger.error("subscribed topic is unequal to compared node / device id")
            
            
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback - MQTT client connected
        Subscribe on Command Topics NCMD / DCMD

        """
        if rc == 0:
            self.logger.info("Connected with result code " + str(rc))
            client.subscribe("spBv1.0/" + self.group + "/NCMD/" + self._node.name + "/#")
            client.subscribe("spBv1.0/" + self.group + "/DCMD/" + self._node.name + "/#")
        else:
            self.logger.info("Failed to connect with result code " + str(rc))
            

    def _on_disconnect(self, client, userdata, rc):
        self.logger.info("Connection closed")
        print("Connection closed")


class SparkplugBase:

    """
    Sparkplug base class for nodes and devices
    """
    def __init__(self, model):
        self.logger = logging.getLogger(__name__)
        self._metrics = [] 
        self._model = model
        self._min_publish_interval = 0.5
        self._lock = threading.Lock()
        self._last_publish_time = timer()
        self._metric_publish_queue = {}

    @property
    def model(self):
        return self._model

    @property
    def metrics(self):
        return self._metrics
    
    @property
    def min_publish_interval(self):
        return self._min_publish_interval
    
    @min_publish_interval.setter
    def min_publish_interval(self, value):
        self._min_publish_interval = value 
    
    
    def publishData(self, metric_list):
        """
        Publish metrics to the broker
        To overwrite!
        """
        pass
    
    def queue_publishData(self, metric):
        """
        Queue metric message 
        This is to ensure a minimal pubish intervall to not overflow
        a communication.

        Parameters
        ----------
        metric : SparkplugMetric
            Metric to be queued

        """
        self._lock.acquire()
        self._metric_publish_queue[metric.alias] = metric
        self._lock.release()
        
    def get_payload_value(self, payload, datatype):
        """
        Method to access the corresponding value on the payload


        """
        if (datatype == sp.MetricDataType.Int8 or
            datatype == sp.MetricDataType.Int16 or
            datatype == sp.MetricDataType.Int32 or
            datatype == sp.MetricDataType.Int64 or
            datatype == sp.MetricDataType.UInt8 or
            datatype == sp.MetricDataType.UInt16 or
            datatype == sp.MetricDataType.UInt32 or
            datatype == sp.MetricDataType.UInt64) :
            
            return payload.int_value
        
        elif datatype == sp.MetricDataType.Float:
            
            return payload.float_value
        
        elif datatype == sp.MetricDataType.Double:
            
            return payload.double_value
        
        elif datatype == sp.MetricDataType.Boolean:
            
            return payload.boolean_value
        
        elif datatype == sp.MetricDataType.String:
            
            return payload.string_value
        else:
            raise Exception("Access Value for Datatype:", datatype)
        
    def consume_metrics(self, payload):
        """
        Incoming metrics are forwarded to the real value to be updated

        """
        for payload_metric in payload.metrics:
            for metric in self.metrics:
                if payload_metric.name == metric.name or payload_metric.alias == metric.alias:
                    value = self.get_payload_value(payload_metric, metric.datatype)
                    metric.update_value(value)   
        
    def _metrics_to_bytearray(self, metrics, payload, use_name = False):
        """
        Transform all metrics to a byte array to be send

        """
        for metric in metrics:
            if use_name:
                name = metric.name
            else:
                name = None
                
            if isinstance(metric, SparkplugDataSetMetric):
                if not isinstance(metric.value, list):
                    raise Exception("SparkplugDataSetMetric has no list as value")
                
                column_names = [c[0] for c in metric.columns]
                column_data_types = [c[1] for c in metric.columns]
                columns_count = metric.columns_count

                dataset = sp.initDatasetMetric(payload, name, metric.alias, column_names, column_data_types)   
                
                for data_entry in metric.value:
                    row = dataset.rows.add()
                    for data_idx in range(columns_count):
                        element = row.elements.add()
                        self._set_element_value(element, data_entry[data_idx], column_data_types[data_idx])

            else:
                sp.addMetric(payload, name, metric.alias, metric.datatype, metric.value)     

        return bytearray(payload.SerializeToString())
        
    def _set_element_value(self, element, value, datatype):
        if (datatype == sp.MetricDataType.Int8 or
            datatype == sp.MetricDataType.Int16 or
            datatype == sp.MetricDataType.Int32 or
            datatype == sp.MetricDataType.Int64 or
            datatype == sp.MetricDataType.UInt8 or
            datatype == sp.MetricDataType.UInt16 or
            datatype == sp.MetricDataType.UInt32 or
            datatype == sp.MetricDataType.UInt64) :
            
            element.int_value = value
        
        elif datatype == sp.MetricDataType.Float:
            
            element.float_value = value
        
        elif datatype == sp.MetricDataType.Double:
            
            element.double_value = value
        
        elif datatype == sp.MetricDataType.Boolean:
            
            element.boolean_value = value
        
        elif datatype == sp.MetricDataType.String:
            
           element.string_value = value
        else:
            raise Exception("Cannot write Value for Datatype:", datatype)
  
    def _publish_queue(self):
        """
        Publish all queued metrics and clear queue


        """
        if len(self._metric_publish_queue) == 0:
            return
        
        self.publishData(list(self._metric_publish_queue.values()))
        self._metric_publish_queue.clear()
    
    def loop(self):
        
        elapsed = timer() - self._last_publish_time
        
        if elapsed >= self.min_publish_interval:

            self._last_publish_time = timer()
            self._lock.acquire()
            self._publish_queue()
            self._lock.release()
            


class SparkplugNode(SparkplugBase):
    """
    Sparkplug Node
    """
    def __init__(self, connector, model):
        super().__init__(model)
        self.logger = logging.getLogger(__name__)
        
        self._devices = {}
        self._connector = connector
        self._build_devices_and_metrics()
        self._append_internal_metrics()
        
    @property    
    def sparkplug_name(self):
        return "spBv1.0/" + self._connecter.group + "/DDATA/" + self.model.name + "/" + self.device_name
        
    @property
    def connector(self):
        return self._connector
    
    def publishBirth(self):
        self.publishNodeBirth()
        self.publishDeviceBirth()
        
    def publishNodeBirth(self):
        self.logger.debug("Publishing Node Birth")

        # Create the node birth payload
        payload = sp.getNodeBirthPayload()
    
        byteArray = self._metrics_to_bytearray(self.metrics, payload, True)
    
        self._connector.client.publish("spBv1.0/" + self._connector.group + "/NBIRTH/" + self.name, byteArray, 0, False)
    
    def loop(self):
        super().loop()
        
        for device_name in self._devices:
            self._devices[device_name].loop()

    def publishDeviceBirth(self):
        for device_name in self._devices:
            self._devices[device_name].publishBirth()


    def publishData(self, metric_list):
        
        payload = sp.getDdataPayload()
        
        byteArray = self._metrics_to_bytearray(metric_list, payload)
        
        self._connector.client.publish("spBv1.0/" + self._connector.group + "/NDATA/" + self.name, byteArray, 0, False)
        
    
    def consume_msg(self, payload, device_name = None):
        
        if device_name is None:
            self.logger.debug("Consume message on node")
            self.consume_metrics(payload)
            
        else:
            self.logger.debug("Consume message on device %s", device_name)

            try:
                device = self._devices[device_name]
                device.consume_device_msg(payload)
            except Exception as e:
                self.logger.warn("Device %s is not part of node %s", device_name, self.name, "Exception:", e)
    
    @property
    def name(self):
        return self.model.qualified_name
    
    @property
    def devices(self):
        return self._devices
    
    def _build_devices_and_metrics(self):

        for item in self.model.children:
            if isinstance(item, ModelDevice):
                self._devices[item.name] = SparkplugDevice(self, item)
                
            else:
                self.metrics.append(SparkplugValueMetric(self, item))
    
    def _append_internal_metrics(self):

        self.metrics.append(SparkplugInternalMetric(self, "Node Control/Next Server", sp.MetricDataType.Boolean, False, None))
        self.metrics.append(SparkplugInternalMetric(self, "Node Control/Rebirth", sp.MetricDataType.Boolean, False, self.publishBirth))
        self.metrics.append(SparkplugInternalMetric(self, "Node Control/Reboot", sp.MetricDataType.Boolean, False, self.publishBirth))
        
    
    
class SparkplugDevice(SparkplugBase):
    
    def __init__(self, node, model):
        super().__init__(model)  
        self.logger = logging.getLogger(__name__)
        
        self._node = node
        self._build_metrics()
 
        
    def publishBirth(self):
        self.logger.debug("Publishing Node Birth")

        # Create the node birth payload
        payload = sp.getDeviceBirthPayload()
    
        byteArray = self._metrics_to_bytearray(self.metrics, payload, True)
    
        self._node.connector.client.publish("spBv1.0/" + self._node.connector.group + "/DBIRTH/" +  self._node.name + "/" + self.name, byteArray, 0, False)
    

    def publishData(self, metric_list):
        
        payload = sp.getDdataPayload()
        
        byteArray = self._metrics_to_bytearray(metric_list, payload)
        
        self._node.connector.client.publish("spBv1.0/" + self._node.connector.group + "/DDATA/" + self._node.name + "/" + self.name, byteArray, 0, False)
        
 

    def consume_device_msg(self, payload):
        self.consume_metrics(payload)
        
    @property
    def name(self):
        return self.model.qualified_name
            

    def _build_metrics(self):
        
        for metric in self.model.children:
            if isinstance(metric, ModelDataSet):
                self.metrics.append(SparkplugDataSetMetric(self, metric))
            elif isinstance(metric, ModelValue):
                self.metrics.append(SparkplugValueMetric(self, metric))
            else:
                raise Exception("Device found on device children")
                

class SparkplugHelper:
    @staticmethod
    def translate_datatype(value_data_type):

        if value_data_type == ValueDataType.Int:
            return sp.MetricDataType.Int32
        elif value_data_type == ValueDataType.Float:
            return sp.MetricDataType.Float
        elif value_data_type == ValueDataType.Boolean:
            return sp.MetricDataType.Boolean
        elif value_data_type == ValueDataType.Bytes:
            return sp.MetricDataType.Bytes
        elif value_data_type == ValueDataType.String:
            return sp.MetricDataType.String
        elif value_data_type == ValueDataType.DataSet:
            return sp.MetricDataType.DataSet
  
        return sp.MetricDataType.Unknown


class SparkplugMetric:
    
    ALIAS_COUNTER = 10
    
    def __init__(self, parent):
        self.logger = logging.getLogger(__name__)
        self._parent = parent
        
        SparkplugMetric.ALIAS_COUNTER += 1
        self._alias = SparkplugMetric.ALIAS_COUNTER
        
    @property
    def parent(self):
        return self._parent
    
    @property
    def name(self):
        return "noname"
    
    @property
    def alias(self):
        return self._alias
    
    @property
    def datatype(self):
        return SparkplugHelper.translate_datatype(self._model_io.datatype)
    
    @property
    def initial(self):
        return None
    
    @property
    def value(self):
        return None
    
    def update_value(self, value):
        return 0
    
    def _value_has_changed(self, callback, source):
        pass
        
        
class SparkplugValueMetric(SparkplugMetric):
    
    def __init__(self, parent, model_io):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
    
        self._model_io = model_io
        self._model_io.add_value_changed_listener(self._value_has_changed)
        
    @property
    def model_io(self):
        return self.model_io
    
    @property
    def name(self):
        return self._model_io.qualified_name
    
    @property
    def datatype(self):
        return SparkplugHelper.translate_datatype(self._model_io.datatype)
    
    @property
    def initial(self):
        return self._model_io.initial
    
    @property
    def value(self):
        return self._model_io.value
    
    def update_value(self, value):
        return self._model_io.update_request(value)
    
    def _value_has_changed(self, callback, source):
        self.parent.queue_publishData(self)

    
class SparkplugDataSetMetric(SparkplugValueMetric):
    
    def __init__(self, parent, model_io):
        super().__init__(parent, model_io)
        self.logger = logging.getLogger(__name__)
        
    @property
    def columns(self):
        return [(c[0], SparkplugHelper.translate_datatype(c[1])) for c in self._model_io.columns]
    
    @property
    def columns_count(self):
        return self._model_io.columns_count      
        

class SparkplugInternalMetric(SparkplugMetric):
    
    def __init__(self, parent, name, datatype, initial, invoke_method = None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._name = name
        self._datatype = datatype
        self._initial = initial
        self._value = initial
        self._invoke_method = invoke_method
        
    def update_value(self, value):
        
        if self._invoke_method is not None and callable(self._invoke_method):
            self._invoke_method()
        
        return 0   
    
    @property
    def name(self):
        return self._name
    
    @property
    def initial(self):
        return self._initial
    
    @property
    def value(self):
        return self._value
    
    @property
    def datatype(self):
        return self._datatype


        
    
    
    
    
    
    
    