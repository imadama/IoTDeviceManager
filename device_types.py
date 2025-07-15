"""
Abstract Device Types for IoT Management System
Provides abstraction layer for different device types and their specifications.
"""

from abc import ABC, abstractmethod
import random
import os
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
    
    def _calculate_cumulative_kwh(self, device_id: str, current_power: float) -> float:
        """Calculate cumulative kWh based on power consumption over time interval"""
        try:
            # Get the last measurement from database to get previous kWh
            database_url = os.environ.get("DATABASE_URL")
            if database_url:
                # Use PostgreSQL database
                from database_postgres import PostgresDatabase
                db = PostgresDatabase()
                measurements = db.get_measurements(device_id=device_id, limit=1)
            else:
                # Use SQLite database
                from database import Database
                db = Database()
                measurements = db.get_measurements(device_id=device_id, limit=1)
            
            # Get previous kWh value (start from 0 if no previous measurements)
            previous_kwh = 0.0
            if measurements:
                previous_kwh = float(measurements[0].get('kwh', 0))
            
            # Calculate energy consumed in this interval
            # Get interval from device settings or default to 5 seconds
            try:
                from device_settings import device_settings
                interval_seconds = device_settings.get_measurement_interval()
            except:
                interval_seconds = 5  # Fallback to 5 seconds
                
            interval_hours = interval_seconds / 3600  # Convert to hours
            
            # Energy = Power × Time (kWh = kW × hours)
            power_kw = current_power / 1000  # Convert watts to kilowatts
            energy_consumed = power_kw * interval_hours
            
            # Add to previous cumulative total
            new_kwh = previous_kwh + energy_consumed
            
            return round(new_kwh, 6)  # Round to 6 decimal places for precision
            
        except Exception as e:
            # Fallback: return a small increment based on power
            power_kw = current_power / 1000
            return round(power_kw * 0.001, 6)  # Small increment
    
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
        
        # Calculate power: P = V × I
        power = round(voltage * current, 2)
        
        # Get previous kWh reading to calculate cumulative kWh
        kwh = self._calculate_cumulative_kwh(device_id, power)
        
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
        
        # Calculate power: P = V × I
        power = round(voltage * current, 2)
        
        # Get previous kWh reading to calculate cumulative kWh
        kwh = self._calculate_cumulative_kwh(device_id, power)
        
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
        
        # Calculate power: P = V × I
        power = round(voltage * current, 2)
        
        # Get previous kWh reading to calculate cumulative kWh
        kwh = self._calculate_cumulative_kwh(device_id, power)
        
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