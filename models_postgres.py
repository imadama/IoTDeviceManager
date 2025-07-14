from datetime import datetime
from app import db_sqlalchemy as db

class DeviceMeasurement(db.Model):
    """PostgreSQL model for device measurements"""
    __tablename__ = 'device_measurements'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    voltage = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, nullable=False)
    power = db.Column(db.Float, nullable=False)
    kwh = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeviceMeasurement {self.device_id} at {self.timestamp}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat(),
            'voltage': self.voltage,
            'current': self.current,
            'power': self.power,
            'kwh': self.kwh,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DeviceConfig(db.Model):
    """PostgreSQL model for device configuration"""
    __tablename__ = 'device_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    device_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='stopped')  # 'active' or 'stopped'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeviceConfig {self.device_id} ({self.device_type})>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_type': self.device_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }