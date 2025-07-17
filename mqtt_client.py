"""
MQTT Client for Cumulocity IoT Platform Integration
"""

import json
import logging
import time
import ssl
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from datetime import datetime

class CumulocityMqttClient:
    """MQTT client for connecting to Cumulocity IoT platform"""
    
    def __init__(self, broker_host: str, broker_port: int = 1883, 
                 username: str = None, password: str = None, 
                 tenant: str = None, device_id: str = None,
                 use_ssl: bool = False, ca_cert_path: str = None,
                 client_cert_path: str = None, client_key_path: str = None):
        """
        Initialize Cumulocity MQTT client
        
        Args:
            broker_host: MQTT broker hostname (e.g., your-tenant.cumulocity.com)
            broker_port: MQTT broker port (default 1883, use 8883 for SSL)
            username: Username for authentication (format: tenant/username)
            password: Password for authentication  
            tenant: Cumulocity tenant ID
            device_id: Unique device identifier
            use_ssl: Enable SSL/TLS connection
            ca_cert_path: Path to CA certificate file
            client_cert_path: Path to client certificate file  
            client_key_path: Path to client key file
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.tenant = tenant
        self.device_id = device_id
        self.use_ssl = use_ssl
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self.client = None
        self.connected = False
        self.registered = False
        self.last_message_time = None
        self.logger = logging.getLogger(f'MQTT-{device_id}')
        
        # Cumulocity MQTT topics
        self.measurement_topic = "s/us"  # Static template for measurements
        self.inventory_topic = f"s/ud/{device_id}"  # Device registration
        self.command_topic = "s/ds"  # Device commands subscription
        
    def connect(self) -> bool:
        """Connect to Cumulocity MQTT broker"""
        try:
            # Use MQTT version 3.1.1 for Cumulocity compatibility
            self.client = mqtt.Client(
                client_id=f"{self.device_id}_{int(time.time())}", 
                protocol=mqtt.MQTTv311
            )
            
            # Set authentication if provided
            if self.username and self.password:
                # Ensure username includes tenant if not already formatted correctly
                formatted_username = self.username
                if self.tenant and '/' not in self.username:
                    formatted_username = f"{self.tenant}/{self.username}"
                elif '/' not in self.username:
                    self.logger.warning("Username should be in format 'tenant/username' for Cumulocity")
                
                self.client.username_pw_set(formatted_username, self.password)
                self.logger.info(f"Authentication set for user: {formatted_username}")
            
            # Configure SSL/TLS if enabled
            if self.use_ssl:
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                
                # Load CA certificate if provided
                if self.ca_cert_path:
                    context.load_verify_locations(self.ca_cert_path)
                
                # Load client certificate and key if provided (for mutual TLS)
                if self.client_cert_path and self.client_key_path:
                    context.load_cert_chain(self.client_cert_path, self.client_key_path)
                
                # Set SSL context
                self.client.tls_set_context(context)
                self.logger.info(f"SSL/TLS enabled for connection to {self.broker_host}:{self.broker_port}")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_message = self._on_message
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
            self.registered = False
            self.last_message_time = None
            self.logger.info("Disconnected from MQTT broker")
    
    def get_connection_status(self) -> dict:
        """Get detailed connection status for monitoring"""
        return {
            'connected': self.connected,
            'registered': self.registered,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'broker_host': self.broker_host,
            'device_id': self.device_id
        }
    
    def register_device(self, device_type: str, device_name: str, force_register: bool = False) -> bool:
        """Register device with Cumulocity using proper device bootstrap"""
        try:
            # Check if device is already registered (unless forced)
            if not force_register:
                reg_status = self._get_registration_status()
                if reg_status['is_registered']:
                    self.logger.info(f"✓ Device '{self.device_id}' already registered in Cumulocity as '{reg_status['device_name']}' - skipping registration")
                    self.registered = True
                    
                    # Still subscribe to commands
                    self.client.subscribe("s/ds")
                    self.logger.info("Subscribed to device commands topic (s/ds)")
                    return True
                else:
                    self.logger.info(f"Device '{self.device_id}' not yet registered - proceeding with registration")
            
            # Subscribe to device commands first
            self.client.subscribe("s/ds")
            self.logger.info("Subscribed to device commands topic (s/ds)")
            
            # Device registration message using static template
            # 100,<device_name>,<device_type>
            registration_msg = f"100,{device_name},c8y_MQTTDevice"
            
            result = self.client.publish("s/us", registration_msg, qos=2)
            result.wait_for_publish()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"✓ Device '{self.device_id}' registered in Cumulocity as '{device_name}' (FIRST TIME)")
                self.registered = True
                
                # Mark device as registered in persistent storage
                self._mark_device_registered(device_name)
                
                # Send device hardware info (110 template)
                hardware_msg = f"110,{self.device_id},IoT Simulator Model,v1.0"
                hw_result = self.client.publish("s/us", hardware_msg)
                
                # Send supported operations (114 template)
                operations_msg = "114,c8y_Restart,c8y_Configuration"
                ops_result = self.client.publish("s/us", operations_msg)
                
                if hw_result.rc == mqtt.MQTT_ERR_SUCCESS and ops_result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info(f"Device metadata sent for {device_name}")
                
                return True
            else:
                self.logger.error(f"Failed to send device registration: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error registering device: {e}")
            return False
    
    def _get_registration_status(self) -> dict:
        """Get detailed registration status for device"""
        try:
            import json
            import os
            
            status_file = 'device_status.json'
            if not os.path.exists(status_file):
                self.logger.debug(f"No status file found - device {self.device_id} not registered")
                return {'is_registered': False, 'device_name': None, 'registered_at': None}
                
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            devices = status_data.get('devices', {})
            device_info = devices.get(self.device_id, {})
            
            is_registered = device_info.get('cumulocity_registered', False)
            device_name = device_info.get('cumulocity_device_name', None)
            registered_at = device_info.get('cumulocity_registered_at', None)
            
            result = {
                'is_registered': is_registered,
                'device_name': device_name,
                'registered_at': registered_at
            }
            
            if is_registered:
                self.logger.debug(f"Device {self.device_id} found in registration cache as '{device_name}' (registered: {registered_at})")
            else:
                self.logger.debug(f"Device {self.device_id} not found in registration cache or not registered")
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Could not check registration status: {e}")
            return {'is_registered': False, 'device_name': None, 'registered_at': None}
    
    def _mark_device_registered(self, device_name: str):
        """Mark device as registered in persistent storage"""
        try:
            import json
            import os
            
            status_file = 'device_status.json'
            status_data = {}
            
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
            
            if 'devices' not in status_data:
                status_data['devices'] = {}
                
            if self.device_id not in status_data['devices']:
                status_data['devices'][self.device_id] = {}
            
            status_data['devices'][self.device_id]['cumulocity_registered'] = True
            status_data['devices'][self.device_id]['cumulocity_device_name'] = device_name
            status_data['devices'][self.device_id]['cumulocity_registered_at'] = datetime.now().isoformat()
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
            self.logger.info(f"Marked device {self.device_id} as registered in Cumulocity with name '{device_name}'")
            
        except Exception as e:
            self.logger.warning(f"Could not mark device as registered: {e}")
    
    def send_measurement(self, measurement_data: Dict[str, Any]) -> bool:
        """
        Send measurement data to Cumulocity using c8y_Measurement format
        
        Cumulocity c8y_Measurement format:
        200,c8y_Measurement,<timestamp>,<voltage>,V,<current>,A,<power>,W
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected to MQTT broker")
                return False
            
            timestamp = measurement_data.get('timestamp', datetime.now().isoformat())
            device_id = measurement_data.get('device_id', self.device_id)
            
            # Send single combined measurement using c8y_Measurement format
            payload = f"200,c8y_Measurement,{timestamp},{measurement_data['voltage']},V,{measurement_data['current']},A,{measurement_data['power']},W"
            
            result = self.client.publish(self.measurement_topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.last_message_time = datetime.now()
                self.logger.info(f"📊 Device '{device_id}' sent c8y_Measurement to Cumulocity successfully")
                self.logger.info(f"   ⚡ Voltage: {measurement_data['voltage']}V, Current: {measurement_data['current']}A, Power: {measurement_data['power']}W")
                self.logger.debug(f"   📡 Payload: {payload}")
                return True
            else:
                self.logger.error(f"Failed to publish c8y_Measurement: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending c8y_Measurement: {e}")
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
    
    def send_test_message(self, topic: str = None, message: str = None) -> bool:
        """Send a test message to a custom topic or default measurement topic"""
        try:
            if not self.connected:
                self.logger.warning("Not connected to MQTT broker")
                return False
            
            # Validate topic for MQTT compliance
            if topic and ('*' in topic or '+' in topic or '#' in topic):
                self.logger.error("Topic cannot contain MQTT wildcards (* + #)")
                return False
            
            # Use default topic and message if not provided
            test_topic = topic or self.measurement_topic
            test_message = message or f"400,Test message from IoT simulator,{datetime.now().isoformat()}"
            
            result = self.client.publish(test_topic, test_message)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Test message sent to topic '{test_topic}': {test_message}")
                return True
            else:
                self.logger.error(f"Failed to send test message: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending test message: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.connected = True
            self.logger.info(f"✓ Device '{self.device_id}' connected to Cumulocity MQTT broker ({self.broker_host})")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable", 
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            self.logger.error(f"Failed to connect to MQTT broker: {error_msg} (code {rc})")
    
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
    
    def _on_message(self, client, userdata, message):
        """Callback for incoming messages"""
        try:
            payload = message.payload.decode("utf-8")
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # Handle device restart command (510)
            if payload.startswith("510"):
                self.logger.info("Received restart command from Cumulocity")
                self._handle_restart_command()
                
        except Exception as e:
            self.logger.error(f"Error processing incoming message: {e}")
    
    def _handle_restart_command(self):
        """Handle device restart command from Cumulocity"""
        try:
            # Send restart executing status (501)
            self.client.publish("s/us", "501,c8y_Restart", qos=2)
            self.logger.info("Restart command acknowledged")
            
            # Simulate restart delay
            import time
            time.sleep(1)
            
            # Send restart completed status (503) 
            self.client.publish("s/us", "503,c8y_Restart", qos=2)
            self.logger.info("Restart command completed")
            
        except Exception as e:
            self.logger.error(f"Error handling restart command: {e}")
    
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
            'device_prefix': 'iot_sim_',
            'ca_cert_path': '',
            'client_cert_path': '',
            'client_key_path': '',
            'bootstrap_user': '',
            'bootstrap_password': ''
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
            'tenant': self.settings.get('tenant', ''),
            'use_ssl': self.settings.get('use_ssl', False),
            'ca_cert_path': self.settings.get('ca_cert_path', ''),
            'client_cert_path': self.settings.get('client_cert_path', ''),
            'client_key_path': self.settings.get('client_key_path', '')
        }

# Global MQTT settings instance
mqtt_settings = MqttSettings()