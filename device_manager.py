import json
import os
import logging
from multiprocessing import Process
from models import DeviceStatus
from device import device_worker
from device_types import device_type_registry

class DeviceManager:
    """Manages virtual IoT devices and their processes using abstracted device types"""
    
    def __init__(self, database):
        self.db = database
        self.devices = {}  # device_id -> Process object
        self.device_statuses = {}  # device_id -> DeviceStatus object
        self.status_file = 'device_status.json'
        
        # Initialize counters dynamically from registry
        self.device_counters = {}
        for type_name in device_type_registry.get_all_type_names():
            device_type_impl = device_type_registry.get_device_type(type_name)
            self.device_counters[device_type_impl.type_id] = 0
            
        self.logger = logging.getLogger('DeviceManager')
        
        # Load existing device status
        self._load_device_status()
        
    def _load_device_status(self):
        """Load device status from JSON file"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load counters but ensure all registered device types are present
                    loaded_counters = data.get('counters', {})
                    for type_name in device_type_registry.get_all_type_names():
                        device_type_impl = device_type_registry.get_device_type(type_name)
                        type_id = device_type_impl.type_id
                        
                        # Use loaded counter or initialize to 0
                        if type_id in loaded_counters:
                            self.device_counters[type_id] = loaded_counters[type_id]
                        else:
                            # Check if old format counters exist (migrate from old names)
                            old_name_mapping = {
                                'pv': 'PV',
                                'heatpump': 'Heat Pump', 
                                'maingrid': 'Main Grid'
                            }
                            old_name = old_name_mapping.get(type_id)
                            if old_name and old_name in loaded_counters:
                                self.device_counters[type_id] = loaded_counters[old_name]
                            else:
                                self.device_counters[type_id] = 0
                    
                    devices_status = data.get('devices', {})
                    
                    # Load device status but don't start processes automatically
                    for device_id, status_data in devices_status.items():
                        if status_data['status'] == 'active':
                            # Mark as stopped since processes don't persist across app restarts
                            status_data['status'] = 'stopped'
                        
                        # Create DeviceStatus object and store it
                        device_status = DeviceStatus(
                            device_id=device_id,
                            device_type=status_data['device_type'],
                            status=status_data['status'],
                            created_at=status_data.get('created_at')
                        )
                        self.device_statuses[device_id] = device_status
                            
                self.logger.info(f"Loaded device status from {self.status_file}")
            except Exception as e:
                self.logger.error(f"Error loading device status: {e}")
                
    def _save_device_status(self):
        """Save device status to JSON file"""
        try:
            devices_status = {}
            
            # Save all devices from device_statuses
            for device_id, device_status in self.device_statuses.items():
                devices_status[device_id] = {
                    'device_type': device_status.device_type,
                    'status': device_status.status,
                    'created_at': device_status.created_at
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
        """Extract device type from device ID using registry"""
        return device_type_registry.get_type_name_from_id(device_id)
        
    def _generate_device_id(self, device_type):
        """Generate a unique device ID based on type using abstraction"""
        try:
            device_type_impl = device_type_registry.get_device_type(device_type)
            type_id = device_type_impl.type_id
            
            self.device_counters[type_id] += 1
            counter = self.device_counters[type_id]
            
            return f'{type_id}{counter:03d}'
        except ValueError:
            # Fallback for unknown device types
            self.device_counters.setdefault('unknown', 0)
            self.device_counters['unknown'] += 1
            counter = self.device_counters['unknown']
            return f'unknown{counter:03d}'
            
    def add_device(self, device_type):
        """Add a new device"""
        device_id = self._generate_device_id(device_type)
        
        # Create device status entry and store it
        status = DeviceStatus(device_id, device_type)
        self.device_statuses[device_id] = status
        
        # Save to PostgreSQL if available
        if hasattr(self.db, 'save_device_config'):
            self.db.save_device_config(device_id, device_type, 'stopped')
        
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
            
            # Get current measurement interval from settings
            from device_settings import device_settings
            interval = device_settings.get_measurement_interval()
            
            process = Process(target=device_worker, args=(device_id, device_type, interval))
            process.start()
            
            self.devices[device_id] = process
            
            # Update status in PostgreSQL if available
            if hasattr(self.db, 'save_device_config'):
                self.db.save_device_config(device_id, device_type, 'active')
            
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
            # Still try to update database status even if process not found
            if hasattr(self.db, 'save_device_config'):
                device_type = self._get_device_type_from_id(device_id)
                self.db.save_device_config(device_id, device_type, 'stopped')
            return False
            
        try:
            process = self.devices[device_id]
            self.logger.info(f"Attempting to stop device {device_id} (PID: {process.pid if process.is_alive() else 'N/A'})")
            
            if process.is_alive():
                # First try graceful termination
                process.terminate()
                self.logger.debug(f"Sent SIGTERM to device {device_id}")
                
                # Wait for graceful shutdown
                process.join(timeout=3)
                
                # If still alive, force kill
                if process.is_alive():
                    self.logger.warning(f"Device {device_id} didn't respond to SIGTERM, sending SIGKILL")
                    process.kill()
                    process.join(timeout=2)
                    
                # Final check
                if process.is_alive():
                    self.logger.error(f"Failed to kill device {device_id} process")
                else:
                    self.logger.info(f"Device {device_id} process terminated")
            else:
                self.logger.info(f"Device {device_id} process was already terminated")
                    
            # Remove from active devices
            del self.devices[device_id]
            
            # Update status in PostgreSQL if available
            if hasattr(self.db, 'save_device_config'):
                device_type = self._get_device_type_from_id(device_id)
                self.db.save_device_config(device_id, device_type, 'stopped')
                self.logger.debug(f"Updated database status for {device_id} to stopped")
            
            self._save_device_status()
            
            self.logger.info(f"Successfully stopped device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping device {device_id}: {e}")
            # Try to remove from devices list anyway
            if device_id in self.devices:
                del self.devices[device_id]
            # Still update database status
            if hasattr(self.db, 'save_device_config'):
                device_type = self._get_device_type_from_id(device_id)
                self.db.save_device_config(device_id, device_type, 'stopped')
            return False
            
    def delete_device(self, device_id):
        """Delete a device (stop it first if running)"""
        try:
            # Stop device if running
            if device_id in self.devices:
                self.stop_device(device_id)
                
            # Remove from device_statuses
            if device_id in self.device_statuses:
                del self.device_statuses[device_id]
                
            # Delete measurements from database
            if hasattr(self.db, 'delete_device_measurements'):
                self.db.delete_device_measurements(device_id)
                
            # Delete device config if using PostgreSQL
            if hasattr(self.db, 'delete_device_config'):
                self.db.delete_device_config(device_id)
                
            # Save updated status file
            self._save_device_status()
            
            self.logger.info(f"Deleted device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting device {device_id}: {e}")
            return False
            
    def get_device_status(self, device_id):
        """Get the status of a specific device"""
        is_active = device_id in self.devices and self.devices[device_id].is_alive()
        
        # Get device status from stored statuses, or create new one
        if device_id in self.device_statuses:
            device_status = self.device_statuses[device_id]
            # Update status based on actual process state
            device_status.status = 'active' if is_active else 'stopped'
            return device_status
        else:
            # Fallback: create new status
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
        
        # Get from stored device statuses
        device_ids.update(self.device_statuses.keys())
        
        # Get from status file as backup
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
