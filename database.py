import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

class Database:
    """Database handler for IoT device measurements"""
    
    def __init__(self, db_path='iot_devices.db'):
        self.db_path = db_path
        self.logger = logging.getLogger('Database')
        self._init_database()
        
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        voltage REAL NOT NULL,
                        current REAL NOT NULL,
                        power REAL NOT NULL,
                        kwh REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for better query performance
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_device_timestamp 
                    ON measurements(device_id, timestamp)
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
            
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
            
    def insert_measurement(self, device_id, timestamp, voltage, current, power, kwh):
        """Insert a new measurement record"""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO measurements 
                    (device_id, timestamp, voltage, current, power, kwh)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (device_id, timestamp, voltage, current, power, kwh))
                
                conn.commit()
                self.logger.debug(f"Inserted measurement for device {device_id}")
                
        except Exception as e:
            self.logger.error(f"Error inserting measurement: {e}")
            raise
            
    def get_measurements(self, device_id=None, limit=100, offset=0):
        """Get measurements, optionally filtered by device_id"""
        try:
            with self._get_connection() as conn:
                if device_id:
                    cursor = conn.execute('''
                        SELECT * FROM measurements 
                        WHERE device_id = ?
                        ORDER BY timestamp DESC, id DESC
                        LIMIT ? OFFSET ?
                    ''', (device_id, limit, offset))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM measurements 
                        ORDER BY timestamp DESC, id DESC
                        LIMIT ? OFFSET ?
                    ''', (limit, offset))
                
                rows = cursor.fetchall()
                measurements = []
                
                for row in rows:
                    measurements.append({
                        'id': row['id'],
                        'device_id': row['device_id'],
                        'timestamp': row['timestamp'],
                        'voltage': row['voltage'],
                        'current': row['current'],
                        'power': row['power'],
                        'kwh': row['kwh'],
                        'created_at': row['created_at']
                    })
                
                self.logger.debug(f"Retrieved {len(measurements)} measurements")
                return measurements
                
        except Exception as e:
            self.logger.error(f"Error retrieving measurements: {e}")
            return []
            
    def get_device_count(self):
        """Get count of unique devices that have measurements"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT COUNT(DISTINCT device_id) as count FROM measurements')
                row = cursor.fetchone()
                return row['count'] if row else 0
                
        except Exception as e:
            self.logger.error(f"Error getting device count: {e}")
            return 0
            
    def get_measurement_count(self, device_id=None):
        """Get total count of measurements, optionally for a specific device"""
        try:
            with self._get_connection() as conn:
                if device_id:
                    cursor = conn.execute(
                        'SELECT COUNT(*) as count FROM measurements WHERE device_id = ?',
                        (device_id,)
                    )
                else:
                    cursor = conn.execute('SELECT COUNT(*) as count FROM measurements')
                    
                row = cursor.fetchone()
                return row['count'] if row else 0
                
        except Exception as e:
            self.logger.error(f"Error getting measurement count: {e}")
            return 0
            
    def delete_device_measurements(self, device_id):
        """Delete all measurements for a specific device"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'DELETE FROM measurements WHERE device_id = ?',
                    (device_id,)
                )
                conn.commit()
                
                deleted_count = cursor.rowcount
                self.logger.info(f"Deleted {deleted_count} measurements for device {device_id}")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error deleting measurements for device {device_id}: {e}")
            return 0
