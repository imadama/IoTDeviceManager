import json
import os
import logging
from multiprocessing import Process
from models import DeviceStatus
from device import device_worker

class DeviceManager:
    """Manages virtual IoT devices and their processes"""
    
    def __init__(self, database):
        self.db = database
        self.devices = {}  # device_id -> Process object
        self.status_file = 'device_status.json'
        self.device_counters = {
            'PV': 0,
            'Heat Pump': 0,
            'Main Grid': 0
        }
        self.logger = logging.getLogger('DeviceManager')
        
        # Load existing device status
        self._load_device_status()
        
    def _load_device_status(self):
        """Load device status from JSON file"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    self.device_counters = data.get('counters', self.device_counters)
                    devices_status = data.get('devices', {})
                    
                    # Load device status but don't start processes automatically
                    for device_id, status_data in devices_status.items():
                        if status_data['status'] == 'active':
                            # Mark as stopped since processes don't persist across app restarts
                            status_data['status'] = 'stopped'
                            
                self.logger.info(f"Loaded device status from {self.status_file}")
            except Exception as e:
                self.logger.error(f"Error loading device status: {e}")
                
    def _save_device_status(self):
        """Save device status to JSON file"""
        try:
            devices_status = {}
            for device_id in self.get_all_device_ids():
                status = self.get_device_status(device_id)
                devices_status[device_id] = {
                    'device_type': self._get_device_type_from_id(device_id),
                    'status': status.status,
                    'created_at': status.created_at
                }
            
            data = {
                'counters': self.device_counters,
                'devices': devices_status
            }
            
            with open(self.status_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.debug(f"Saved device status to {self.status_file}")
        except Exception as e:
            self.logger.error(f"Error saving device status: {e}")
            
    def _get_device_type_from_id(self, device_id):
        """Extract device type from device ID"""
        if device_id.startswith('pv'):
            return 'PV'
        elif device_id.startswith('heatpump'):
            return 'Heat Pump'
        elif device_id.startswith('maingrid'):
            return 'Main Grid'
        return 'Unknown'
        
    def _generate_device_id(self, device_type):
        """Generate a unique device ID based on type"""
        self.device_counters[device_type] += 1
        counter = self.device_counters[device_type]
        
        if device_type == 'PV':
            return f'pv{counter:03d}'
        elif device_type == 'Heat Pump':
            return f'heatpump{counter:03d}'
        elif device_type == 'Main Grid':
            return f'maingrid{counter:03d}'
        else:
            return f'device{counter:03d}'
            
    def add_device(self, device_type):
        """Add a new device"""
        device_id = self._generate_device_id(device_type)
        
        # Create device status entry
        status = DeviceStatus(device_id, device_type)
        
        self._save_device_status()
        self.logger.info(f"Added new device: {device_id} ({device_type})")
        
        return device_id
        
    def start_device(self, device_id):
        """Start a device process"""
        if device_id in self.devices and self.devices[device_id].is_alive():
            self.logger.warning(f"Device {device_id} is already running")
            return False
            
        try:
            device_type = self._get_device_type_from_id(device_id)
            process = Process(target=device_worker, args=(device_id, device_type))
            process.start()
            
            self.devices[device_id] = process
            self._save_device_status()
            
            self.logger.info(f"Started device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting device {device_id}: {e}")
            return False
            
    def stop_device(self, device_id):
        """Stop a device process"""
        if device_id not in self.devices:
            self.logger.warning(f"Device {device_id} not found in active devices")
            return False
            
        try:
            process = self.devices[device_id]
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)  # Wait up to 5 seconds for graceful shutdown
                
                if process.is_alive():
                    process.kill()  # Force kill if still alive
                    
            del self.devices[device_id]
            self._save_device_status()
            
            self.logger.info(f"Stopped device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping device {device_id}: {e}")
            return False
            
    def delete_device(self, device_id):
        """Delete a device (stop it first if running)"""
        try:
            # Stop device if running
            if device_id in self.devices:
                self.stop_device(device_id)
                
            # Remove from status file
            self._save_device_status()
            
            self.logger.info(f"Deleted device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting device {device_id}: {e}")
            return False
            
    def get_device_status(self, device_id):
        """Get the status of a specific device"""
        is_active = device_id in self.devices and self.devices[device_id].is_alive()
        device_type = self._get_device_type_from_id(device_id)
        
        return DeviceStatus(
            device_id=device_id,
            device_type=device_type,
            status='active' if is_active else 'stopped'
        )
        
    def get_all_device_ids(self):
        """Get all device IDs from the status file"""
        device_ids = set()
        
        # Get from active processes
        device_ids.update(self.devices.keys())
        
        # Get from status file
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    device_ids.update(data.get('devices', {}).keys())
            except Exception as e:
                self.logger.error(f"Error reading device IDs: {e}")
                
        return sorted(list(device_ids))
        
    def get_all_devices(self):
        """Get status of all devices"""
        devices = []
        for device_id in self.get_all_device_ids():
            devices.append(self.get_device_status(device_id))
        return devices
        
    def cleanup(self):
        """Stop all running devices"""
        self.logger.info("Cleaning up all devices...")
        for device_id in list(self.devices.keys()):
            self.stop_device(device_id)
