"""
Abstract Device Types for IoT Management System
Provides abstraction layer for different device types and their specifications.
"""

from abc import ABC, abstractmethod
import random
from typing import Dict, Any
from datetime import datetime


class DeviceTypeInterface(ABC):
    """Abstract base class for device types"""
    
    @property
    @abstractmethod
    def type_name(self) -> str:
        """Return the display name of the device type"""
        pass
    
    @property 
    @abstractmethod
    def type_id(self) -> str:
        """Return the internal ID used for device naming (e.g., 'pv' for pv001)"""
        pass
    
    @property
    @abstractmethod
    def icon_class(self) -> str:
        """Return Font Awesome icon class for UI display"""
        pass
    
    @property
    @abstractmethod
    def color_class(self) -> str:
        """Return Bootstrap color class for UI styling"""
        pass
    
    @abstractmethod
    def generate_measurement_data(self, device_id: str) -> Dict[str, Any]:
        """Generate realistic measurement data for this device type"""
        pass
    
    @property
    @abstractmethod
    def voltage_range(self) -> tuple:
        """Return (min, max) voltage range for this device type"""
        pass
    
    @property
    @abstractmethod
    def current_range(self) -> tuple:
        """Return (min, max) current range for this device type"""
        pass
    
    @property
    @abstractmethod
    def power_range(self) -> tuple:
        """Return (min, max) power range for this device type"""
        pass


class SolarPanelType(DeviceTypeInterface):
    """Solar Panel (PV) device type implementation"""
    
    @property
    def type_name(self) -> str:
        return "PV"
    
    @property
    def type_id(self) -> str:
        return "pv"
    
    @property
    def icon_class(self) -> str:
        return "fas fa-solar-panel"
    
    @property
    def color_class(self) -> str:
        return "text-warning"
    
    @property
    def voltage_range(self) -> tuple:
        return (200, 250)
    
    @property
    def current_range(self) -> tuple:
        return (5, 15)
    
    @property
    def power_range(self) -> tuple:
        return (1000, 3000)
    
    def generate_measurement_data(self, device_id: str) -> Dict[str, Any]:
        voltage = round(random.uniform(*self.voltage_range), 2)
        current = round(random.uniform(*self.current_range), 2)
        power = round(random.uniform(*self.power_range), 2)
        kwh = round(random.uniform(0.1, 0.5), 3)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'device_id': device_id,
            'voltage': voltage,
            'current': current,
            'power': power,
            'kwh': kwh
        }


class HeatPumpType(DeviceTypeInterface):
    """Heat Pump device type implementation"""
    
    @property
    def type_name(self) -> str:
        return "Heat Pump"
    
    @property
    def type_id(self) -> str:
        return "heatpump"
    
    @property
    def icon_class(self) -> str:
        return "fas fa-thermometer-half"
    
    @property
    def color_class(self) -> str:
        return "text-info"
    
    @property
    def voltage_range(self) -> tuple:
        return (220, 240)
    
    @property
    def current_range(self) -> tuple:
        return (8, 20)
    
    @property
    def power_range(self) -> tuple:
        return (2000, 5000)
    
    def generate_measurement_data(self, device_id: str) -> Dict[str, Any]:
        voltage = round(random.uniform(*self.voltage_range), 2)
        current = round(random.uniform(*self.current_range), 2)
        power = round(random.uniform(*self.power_range), 2)
        kwh = round(random.uniform(0.3, 0.8), 3)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'device_id': device_id,
            'voltage': voltage,
            'current': current,
            'power': power,
            'kwh': kwh
        }


class MainGridType(DeviceTypeInterface):
    """Main Grid connection device type implementation"""
    
    @property
    def type_name(self) -> str:
        return "Main Grid"
    
    @property
    def type_id(self) -> str:
        return "maingrid"
    
    @property
    def icon_class(self) -> str:
        return "fas fa-bolt"
    
    @property
    def color_class(self) -> str:
        return "text-primary"
    
    @property
    def voltage_range(self) -> tuple:
        return (230, 240)
    
    @property
    def current_range(self) -> tuple:
        return (10, 50)
    
    @property
    def power_range(self) -> tuple:
        return (2500, 12000)
    
    def generate_measurement_data(self, device_id: str) -> Dict[str, Any]:
        voltage = round(random.uniform(*self.voltage_range), 2)
        current = round(random.uniform(*self.current_range), 2)
        power = round(random.uniform(*self.power_range), 2)
        kwh = round(random.uniform(0.4, 2.0), 3)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'device_id': device_id,
            'voltage': voltage,
            'current': current,
            'power': power,
            'kwh': kwh
        }


class DeviceTypeRegistry:
    """Registry to manage available device types"""
    
    def __init__(self):
        self._device_types = {
            'PV': SolarPanelType(),
            'Heat Pump': HeatPumpType(),
            'Main Grid': MainGridType()
        }
    
    def get_device_type(self, type_name: str) -> DeviceTypeInterface:
        """Get device type implementation by name"""
        if type_name not in self._device_types:
            raise ValueError(f"Unknown device type: {type_name}")
        return self._device_types[type_name]
    
    def get_all_type_names(self) -> list:
        """Get list of all available device type names"""
        return list(self._device_types.keys())
    
    def register_device_type(self, type_name: str, device_type: DeviceTypeInterface):
        """Register a new device type"""
        self._device_types[type_name] = device_type
    
    def get_type_id_from_name(self, type_name: str) -> str:
        """Get the type ID for device naming from type name"""
        return self.get_device_type(type_name).type_id
    
    def get_type_name_from_id(self, device_id: str) -> str:
        """Extract device type name from device ID"""
        for type_name, device_type in self._device_types.items():
            if device_id.startswith(device_type.type_id):
                return type_name
        return 'Unknown'


# Global registry instance
device_type_registry = DeviceTypeRegistry()