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
                 client_id: str = None, use_ssl: bool = False, 
                 ca_cert_path: str = None, client_cert_path: str = None, 
                 client_key_path: str = None):
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
        self.client_id = client_id or f"mqtt_client_{device_id}"  # Unique client ID per device
        self.use_ssl = use_ssl
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self.client = None
        self.connected = False
        self.registered = False
        self.last_message_time = None
        self.logger = logging.getLogger(f'MQTT-{device_id}')
        
        # Reconnection parameters
        self.reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 300  # Max 5 minutes
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 50  # Try for about 4 hours max
        self.auto_reconnect = True
        self._reconnect_thread = None
        
        # Connection monitoring
        self.last_heartbeat = None
        self.heartbeat_interval = 60  # Send heartbeat every 60 seconds
        self._heartbeat_thread = None
        
        # Cumulocity MQTT topics
        self.measurement_topic = "s/us"  # Static template for measurements
        self.inventory_topic = f"s/ud/{device_id}"  # Device registration
        self.command_topic = "s/ds"  # Device commands subscription
        
    def connect(self) -> bool:
        """Connect to Cumulocity MQTT broker"""
        try:
            # Use MQTT version 3.1.1 for Cumulocity compatibility
            # Each device gets its own unique client ID (like your example script)
            self.client = mqtt.Client(
                client_id=self.client_id, 
                protocol=mqtt.MQTTv311
            )
            self.logger.info(f"Created MQTT client with unique ID: {self.client_id}")
            
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
            
            if not self.connected:
                self.logger.error(f"Failed to connect to MQTT broker within {10} seconds")
                return False
                
            return self.connected
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        # Disable auto-reconnect for manual disconnection
        self.auto_reconnect = False
        
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
        Send measurement data to Cumulocity using proper JSON format
        
        Cumulocity requires JSON structure with proper fragment format:
        {
          "type": "c8y_ElectricMeasurement", 
          "time": "ISO-timestamp",
          "c8y_ElectricMeasurement": {
            "voltage": {"value": X, "unit": "V"},
            "current": {"value": Y, "unit": "A"}, 
            "power": {"value": Z, "unit": "W"}
          }
        }
        """
        try:
            if not self.connected:
                self.logger.warning("Not connected to MQTT broker - attempting reconnection")
                # Try to reconnect if auto-reconnect is enabled
                if self.auto_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
                    if self._attempt_reconnection():
                        self.logger.info("Successfully reconnected for measurement sending")
                    else:
                        return False
                else:
                    return False
            
            timestamp = measurement_data.get('timestamp', datetime.now().isoformat())
            device_id = measurement_data.get('device_id', self.device_id)
            
            # Create proper JSON measurement payload for Cumulocity
            import json
            payload = {
                "type": "c8y_ElectricMeasurement",
                "time": timestamp,
                "c8y_ElectricMeasurement": {
                    "voltage": {
                        "value": measurement_data['voltage'],
                        "unit": "V"
                    },
                    "current": {
                        "value": measurement_data['current'], 
                        "unit": "A"
                    },
                    "power": {
                        "value": measurement_data['power'],
                        "unit": "W"
                    }
                }
            }
            
            json_payload = json.dumps(payload)
            
            # Publish to JSON measurement topic instead of SmartREST
            json_topic = f"measurement/measurements/create"
            result = self.client.publish(json_topic, json_payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.last_message_time = datetime.now()
                self.logger.info(f"📊 Device '{device_id}' sent JSON measurement to Cumulocity successfully")
                self.logger.info(f"   ⚡ Voltage: {measurement_data['voltage']}V, Current: {measurement_data['current']}A, Power: {measurement_data['power']}W")
                self.logger.debug(f"   📡 JSON Topic: {json_topic}")
                self.logger.debug(f"   📡 JSON Payload: {json_payload}")
                return True
            else:
                self.logger.error(f"Failed to publish JSON measurement to {json_topic}: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending JSON measurement: {e}")
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
            self.reconnect_attempts = 0  # Reset on successful connection
            self.last_heartbeat = datetime.now()
            self.logger.info(f"✓ Device '{self.device_id}' connected to Cumulocity MQTT broker ({self.broker_host})")
            
            # Start heartbeat monitoring
            self._start_heartbeat()
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
            # Start automatic reconnection if enabled
            if self.auto_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
                self.logger.info("Starting automatic reconnection...")
                self._start_reconnect()
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
    
    def _start_reconnect(self):
        """Start the reconnection process in a background thread"""
        import threading
        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
            self._reconnect_thread.start()
    
    def _reconnect_loop(self):
        """Background reconnection loop with exponential backoff"""
        while (not self.connected and 
               self.auto_reconnect and 
               self.reconnect_attempts < self.max_reconnect_attempts):
            
            self.reconnect_attempts += 1
            
            # Calculate delay with exponential backoff
            delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 
                       self.max_reconnect_delay)
            
            self.logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} "
                           f"in {delay} seconds...")
            
            time.sleep(delay)
            
            try:
                # Attempt to reconnect
                if self._attempt_reconnection():
                    self.logger.info("✓ Successfully reconnected to MQTT broker")
                    self.reconnect_attempts = 0  # Reset counter on success
                    self.reconnect_delay = 5  # Reset delay
                    break
                else:
                    self.logger.warning(f"Reconnection attempt {self.reconnect_attempts} failed")
                    
            except Exception as e:
                self.logger.error(f"Error during reconnection attempt {self.reconnect_attempts}: {e}")
        
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error("Maximum reconnection attempts reached. Giving up.")
            self.auto_reconnect = False
    
    def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the MQTT broker"""
        try:
            # Clean up old client
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except:
                    pass  # Ignore errors during cleanup
            
            # Create new client and connect
            return self.connect()
            
        except Exception as e:
            self.logger.error(f"Error in reconnection attempt: {e}")
            return False
    
    def enable_auto_reconnect(self, enable: bool = True):
        """Enable or disable automatic reconnection"""
        self.auto_reconnect = enable
        if enable:
            self.logger.info("Auto-reconnection enabled")
        else:
            self.logger.info("Auto-reconnection disabled")
    
    def reset_reconnect_counter(self):
        """Reset the reconnection attempt counter"""
        self.reconnect_attempts = 0
        self.logger.info("Reconnection counter reset")
    
    def _start_heartbeat(self):
        """Start heartbeat monitoring in background thread"""
        import threading
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat to monitor connection health"""
        while self.connected and self.auto_reconnect:
            try:
                time.sleep(self.heartbeat_interval)
                
                if self.connected:
                    # Send a simple ping/heartbeat
                    current_time = datetime.now()
                    
                    # Check if we haven't sent anything recently
                    if (self.last_message_time is None or 
                        (current_time - self.last_message_time).total_seconds() > self.heartbeat_interval):
                        
                        # Send a simple operation to test connection
                        test_result = self.client.publish("s/us", "400,Connection heartbeat", qos=0)
                        
                        if test_result.rc == mqtt.MQTT_ERR_SUCCESS:
                            self.last_heartbeat = current_time
                            self.logger.debug(f"Heartbeat sent successfully")
                        else:
                            self.logger.warning(f"Heartbeat failed: {test_result.rc}")
                            # Connection might be broken, let disconnect callback handle it
                            
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                break
        
        self.logger.debug("Heartbeat monitoring stopped")
    
    def get_connection_health(self) -> dict:
        """Get detailed connection health information"""
        now = datetime.now()
        return {
            'connected': self.connected,
            'registered': self.registered,
            'auto_reconnect': self.auto_reconnect,
            'reconnect_attempts': self.reconnect_attempts,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'seconds_since_last_message': (now - self.last_message_time).total_seconds() if self.last_message_time else None,
            'seconds_since_last_heartbeat': (now - self.last_heartbeat).total_seconds() if self.last_heartbeat else None,
            'broker_host': self.broker_host,
            'device_id': self.device_id
        }

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