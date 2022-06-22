import logging
from ipaddress import IPv4Address
from pathlib import Path
import configparser
from typing import List
from enum import Enum
# from __future__ import annotations
from .fo_zabbix import ZabbixAdapter, ZabbixNodeFields, MetricType
from .fo_prometheus import PrometheusApi, PrometheusNode, PrometheusNodeFields

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

config = configparser.ConfigParser()
config.read("/home/gaucho/unibo_gaucho-master/main/src/main/main.ini")

class MonitoringSystemAdapter(object):

  __monitoring_system = ""
  __key = object() 
  __ma = None  

  def __init__(self, *, key=None):

    assert key == self.__class__.__key, f"There can only be one {self.__class__.__name__} object and it can only be accessed with {self.__class__.__name__}.get_instance()"
    
    if 'MONITORING SYSTEM' in config.sections():
    
      self.__monitoring_system = config['MONITORING SYSTEM']['msystem_is']
      logging.info(f"The selected monitoring system is: {config['MONITORING SYSTEM']['msystem_is']}")

    else: 

      self.__monitoring_system = 'ZABBIX'
      logging.info(f"No monitoring system specified, defualt applied: ZABBIX") 

  @classmethod
  def get_instance(cls):
      
    if cls.__ma is None:
    
      cls.__ma = cls(key=cls.__key)
    
    return cls.__ma

  def get_monitoring_node(self, *, ipv4:IPv4Address=None):

    if self.__monitoring_system == 'ZABBIX':

      node = ZabbixAdapter.get_instance().get_node_by_ip(ipv4) #--no check on ipv4?

    elif self.__monitoring_system == 'PROMETHEUS':

      node = PrometheusApi.get_instance().get_node_by_ip(url=ipv4) #--no check on ipv4?

    return node

  def monitoring_node_is_available(self, *, node=None):

    node_dict = node.to_dict()

    if self.__monitoring_system == 'ZABBIX':

      node_dict[ZabbixNodeFields.AVAILABLE.value] = node_dict[ZabbixNodeFields.AVAILABLE.value] == "1"

      return node_dict[ZabbixNodeFields.AVAILABLE.value]

    elif self.__monitoring_system == 'PROMETHEUS':

      node.set_is_available(PrometheusApi.get_instance().is_node_available(url=node.get_node_ipv4(), port=node.get_node_port()))

      return node_dict[PrometheusNodeFields.AVL.value]

  def get_msn_id(self, *, node_dict:dict={}):

    if self.__monitoring_system == 'ZABBIX':

      return node_dict[ZabbixNodeFields.ID.value]
    
    elif self.__monitoring_system == 'PROMETHEUS':

      return node_dict[PrometheusNodeFields.ID.value]

  def get_msn_avaiability(self, *, node_dict:dict={}):

    if self.__monitoring_system == 'ZABBIX':

      return node_dict[ZabbixNodeFields.AVAILABLE.value]
    
    elif self.__monitoring_system == 'PROMETHEUS':

      return node_dict[PrometheusNodeFields.AVL.value]
    
  def get_msn_name(self, *, node_dict:dict={}):

    if self.__monitoring_system == 'ZABBIX':

      return node_dict[ZabbixNodeFields.NAME.value]

    elif self.__monitoring_system == 'PROMETHEUS':

      return node_dict[PrometheusNodeFields.NAME.value]

  def metric_id_finder(self, *, elem:MetricType=None, node:PrometheusNode=None):

    if self.__monitoring_system == 'ZABBIX':

      return ZabbixAdapter.get_instance().get_item_id_by_node_and_item_name(node, elem.value) 

    elif self.__monitoring_system == 'PROMETHEUS':

      return PrometheusApi.get_instance().get_item_id(node=node, item=elem) 

  def get_measurements_by_nl(self, *, node_id_list:List[str]=[], node_ip_list:List[IPv4Address]=[], item_name_list:List[str]=[], metric_name_list:List[str]=[]):

    if self.__monitoring_system == 'ZABBIX':

      return ZabbixAdapter.get_instance().get_measurements_by_node_list(node_id_list, item_name_list=item_name_list)

    elif self.__monitoring_system == 'PROMETHEUS':

      return PrometheusApi.get_instance().get_measurements_by_nl(node_ip_list=node_ip_list, item_list=metric_name_list) 

  def get_measurements_by_item_id_list(self, *, item_id_list:List[str]=[]):

    if self.__monitoring_system == 'ZABBIX':

      return ZabbixAdapter.get_instance().get_measurements_by_item_id_list(item_id_list)

    elif self.__monitoring_system == 'PROMETHEUS':

      return PrometheusApi.get_instance().get_measurements_by_item_id_list(item_id_list=item_id_list) 

  def get_measurements_by_item_id(self, *, item_id:str=""):

    if self.__monitoring_system == 'ZABBIX':

      return ZabbixAdapter.get_instance().get_measurements_by_item_id(item_id)

    elif self.__monitoring_system == 'PROMETHEUS':

      return PrometheusApi.get_instance().get_measurements_by_item_id(item_id=item_id) 
