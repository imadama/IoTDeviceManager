"""
MQTT Client for Cumulocity IoT Platform Integration
"""

import json
import logging
import time
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from datetime import datetime

class CumulocityMqttClient:
    """MQTT client for connecting to Cumulocity IoT platform"""
    
    def __init__(self, broker_host: str, broker_port: int = 1883, 
                 username: str = None, password: str = None, 
                 tenant: str = None, device_id: str = None):
        """
        Initialize Cumulocity MQTT client
        
        Args:
            broker_host: MQTT broker hostname (e.g., your-tenant.cumulocity.com)
            broker_port: MQTT broker port (default 1883, use 8883 for SSL)
            username: Username for authentication
            password: Password for authentication  
            tenant: Cumulocity tenant ID
            device_id: Unique device identifier
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.tenant = tenant
        self.device_id = device_id
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(f'MQTT-{device_id}')
        
        # Cumulocity MQTT topics
        self.measurement_topic = f"s/us"  # Static template for measurements
        self.inventory_topic = f"s/ud/{device_id}"  # Device registration
        
    def connect(self) -> bool:
        """Connect to Cumulocity MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=f"{self.device_id}_{int(time.time())}")
            
            # Set authentication if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_log = self._on_log
            
            # Connect to broker
            self.logger.info(f"Connecting to Cumulocity broker {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # Start network loop
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(0.5)
                timeout -= 0.5
                
            return self.connected
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.logger.info("Disconnected from MQTT broker")
    
    def register_device(self, device_type: str, device_name: str) -> bool:
        """Register device with Cumulocity"""
        try:
            # Device registration message using static template
            # 100,<device_name>,<device_type>
            registration_msg = f"100,{device_name},{device_type}"
            
            result = self.client.publish(self.inventory_topic, registration_msg)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Device registration sent: {device_name} ({device_type})")
                return True
            else:
                self.logger.error(f"Failed to send device registration: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error registering device: {e}")
            return False
    
    def send_measurement(self, measurement_data: Dict[str, Any]) -> bool:
        """
        Send measurement data to Cumulocity using static templates
        
        Cumulocity static template format for measurements:
        200,<measurement_type>,<value>,<unit>,<timestamp>
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected to MQTT broker")
                return False
            
            timestamp = measurement_data.get('timestamp', datetime.now().isoformat())
            device_id = measurement_data.get('device_id', self.device_id)
            
            # Send multiple measurements using Cumulocity static templates
            measurements = [
                f"200,c8y_Voltage,{measurement_data['voltage']},V,{timestamp}",
                f"200,c8y_Current,{measurement_data['current']},A,{timestamp}",
                f"200,c8y_Power,{measurement_data['power']},W,{timestamp}",
                f"200,c8y_EnergyConsumption,{measurement_data['kwh']},kWh,{timestamp}"
            ]
            
            success_count = 0
            for measurement in measurements:
                result = self.client.publish(self.measurement_topic, measurement)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    success_count += 1
                else:
                    self.logger.error(f"Failed to publish measurement: {measurement}")
            
            if success_count > 0:
                self.logger.debug(f"Sent {success_count}/{len(measurements)} measurements for {device_id}")
                return True
            else:
                self.logger.error("Failed to send any measurements")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending measurement: {e}")
            return False
    
    def send_alarm(self, alarm_type: str, alarm_text: str, severity: str = "MINOR") -> bool:
        """Send alarm to Cumulocity"""
        try:
            # Alarm template: 301,<alarm_type>,<alarm_text>,<severity>
            alarm_msg = f"301,{alarm_type},{alarm_text},{severity}"
            
            result = self.client.publish(self.measurement_topic, alarm_msg)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Alarm sent: {alarm_type} - {alarm_text}")
                return True
            else:
                self.logger.error(f"Failed to send alarm: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending alarm: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.connected = True
            self.logger.info("Successfully connected to Cumulocity MQTT broker")
        else:
            self.connected = False
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            self.logger.info("Cleanly disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for successful publish"""
        self.logger.debug(f"Message {mid} published successfully")
    
    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT logging"""
        self.logger.debug(f"MQTT Log: {buf}")

class MqttSettings:
    """Manages MQTT connection settings"""
    
    def __init__(self, settings_file='mqtt_settings.json'):
        self.settings_file = settings_file
        self.default_settings = {
            'enabled': False,
            'broker_host': '',
            'broker_port': 1883,
            'username': '',
            'password': '',
            'tenant': '',
            'use_ssl': False,
            'device_prefix': 'iot_sim_'
        }
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load MQTT settings from JSON file"""
        import os
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
            except Exception as e:
                print(f"Error loading MQTT settings: {e}")
        
        return self.default_settings.copy()
    
    def save_settings(self):
        """Save MQTT settings to JSON file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving MQTT settings: {e}")
    
    def update_settings(self, **kwargs):
        """Update MQTT settings"""
        for key, value in kwargs.items():
            if key in self.default_settings:
                self.settings[key] = value
        self.save_settings()
    
    def is_enabled(self) -> bool:
        """Check if MQTT is enabled"""
        return self.settings.get('enabled', False)
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for MQTT client"""
        return {
            'broker_host': self.settings.get('broker_host', ''),
            'broker_port': 8883 if self.settings.get('use_ssl', False) else self.settings.get('broker_port', 1883),
            'username': self.settings.get('username', ''),
            'password': self.settings.get('password', ''),
            'tenant': self.settings.get('tenant', '')
        }

# Global MQTT settings instance
mqtt_settings = MqttSettings()