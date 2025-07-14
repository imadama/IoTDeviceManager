import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import desc
from app import db_sqlalchemy as db
from models_postgres import DeviceMeasurement, DeviceConfig

class PostgresDatabase:
    """PostgreSQL database handler for IoT device measurements"""
    
    def __init__(self):
        self.logger = logging.getLogger('PostgresDatabase')
        
    def insert_measurement(self, device_id: str, timestamp: str, voltage: float, 
                          current: float, power: float, kwh: float) -> bool:
        """Insert a new measurement record"""
        try:
            # Convert ISO timestamp string to datetime object
            if isinstance(timestamp, str):
                timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                timestamp_dt = timestamp
                
            measurement = DeviceMeasurement(
                device_id=device_id,
                timestamp=timestamp_dt,
                voltage=voltage,
                current=current,
                power=power,
                kwh=kwh
            )
            
            db.session.add(measurement)
            db.session.commit()
            
            self.logger.debug(f"Inserted measurement for device {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting measurement: {e}")
            db.session.rollback()
            return False
            
    def get_measurements(self, device_id: Optional[str] = None, 
                        limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get measurements, optionally filtered by device_id"""
        try:
            query = DeviceMeasurement.query
            
            if device_id:
                query = query.filter(DeviceMeasurement.device_id == device_id)
                
            measurements = query.order_by(
                desc(DeviceMeasurement.timestamp),
                desc(DeviceMeasurement.id)
            ).limit(limit).offset(offset).all()
            
            result = []
            for m in measurements:
                result.append({
                    'id': m.id,
                    'device_id': m.device_id,
                    'timestamp': m.timestamp.isoformat(),
                    'voltage': m.voltage,
                    'current': m.current,
                    'power': m.power,
                    'kwh': m.kwh,
                    'created_at': m.created_at.isoformat() if m.created_at else None
                })
                
            self.logger.debug(f"Retrieved {len(result)} measurements")
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving measurements: {e}")
            return []
            
    def get_device_count(self) -> int:
        """Get count of unique devices that have measurements"""
        try:
            count = db.session.query(DeviceMeasurement.device_id).distinct().count()
            return count
        except Exception as e:
            self.logger.error(f"Error getting device count: {e}")
            return 0
            
    def get_measurement_count(self, device_id: Optional[str] = None) -> int:
        """Get total count of measurements, optionally for a specific device"""
        try:
            query = DeviceMeasurement.query
            if device_id:
                query = query.filter(DeviceMeasurement.device_id == device_id)
            return query.count()
        except Exception as e:
            self.logger.error(f"Error getting measurement count: {e}")
            return 0
            
    def delete_device_measurements(self, device_id: str) -> int:
        """Delete all measurements for a specific device"""
        try:
            deleted_count = DeviceMeasurement.query.filter(
                DeviceMeasurement.device_id == device_id
            ).delete()
            db.session.commit()
            
            self.logger.info(f"Deleted {deleted_count} measurements for device {device_id}")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error deleting measurements for device {device_id}: {e}")
            db.session.rollback()
            return 0
            
    def save_device_config(self, device_id: str, device_type: str, status: str = 'stopped') -> bool:
        """Save or update device configuration"""
        try:
            # Check if device already exists
            device_config = DeviceConfig.query.filter_by(device_id=device_id).first()
            
            if device_config:
                # Update existing
                device_config.status = status
                device_config.updated_at = datetime.utcnow()
            else:
                # Create new
                device_config = DeviceConfig(
                    device_id=device_id,
                    device_type=device_type,
                    status=status
                )
                db.session.add(device_config)
                
            db.session.commit()
            self.logger.debug(f"Saved device config for {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving device config: {e}")
            db.session.rollback()
            return False
            
    def get_device_configs(self) -> List[Dict]:
        """Get all device configurations"""
        try:
            configs = DeviceConfig.query.all()
            return [config.to_dict() for config in configs]
        except Exception as e:
            self.logger.error(f"Error getting device configs: {e}")
            return []
            
    def get_device_config(self, device_id: str) -> Optional[Dict]:
        """Get configuration for a specific device"""
        try:
            config = DeviceConfig.query.filter_by(device_id=device_id).first()
            return config.to_dict() if config else None
        except Exception as e:
            self.logger.error(f"Error getting device config: {e}")
            return None
            
    def delete_device_config(self, device_id: str) -> bool:
        """Delete device configuration"""
        try:
            deleted_count = DeviceConfig.query.filter_by(device_id=device_id).delete()
            db.session.commit()
            return deleted_count > 0
        except Exception as e:
            self.logger.error(f"Error deleting device config: {e}")
            db.session.rollback()
            return False