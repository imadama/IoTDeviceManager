from datetime import datetime

class DeviceStatus:
    """Model representing the status of a device"""
    
    def __init__(self, device_id, device_type, status='stopped', created_at=None):
        self.device_id = device_id
        self.device_type = device_type
        self.status = status  # 'active' or 'stopped'
        self.created_at = created_at or datetime.now().isoformat()
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'device_id': self.device_id,
            'device_type': self.device_type,
            'status': self.status,
            'created_at': self.created_at
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary"""
        return cls(
            device_id=data['device_id'],
            device_type=data['device_type'],
            status=data['status'],
            created_at=data['created_at']
        )

class Measurement:
    """Model representing a device measurement"""
    
    def __init__(self, device_id, timestamp, voltage, current, power, kwh):
        self.device_id = device_id
        self.timestamp = timestamp
        self.voltage = voltage
        self.current = current
        self.power = power
        self.kwh = kwh
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'device_id': self.device_id,
            'timestamp': self.timestamp,
            'voltage': self.voltage,
            'current': self.current,
            'power': self.power,
            'kwh': self.kwh
        }
