import time
import logging
from datetime import datetime
from multiprocessing import Process
from database import Database
from device_types import device_type_registry

class VirtualDevice:
    """Base class for virtual IoT devices using abstracted device types"""
    
    def __init__(self, device_id, device_type):
        self.device_id = device_id
        self.device_type = device_type
        self.is_running = False
        self.process = None
        
        # Get the device type implementation
        try:
            self.device_type_impl = device_type_registry.get_device_type(device_type)
        except ValueError:
            logging.warning(f"Unknown device type {device_type}, using default")
            self.device_type_impl = None
        
    def generate_data(self):
        """Generate measurement data using device type abstraction"""
        if self.device_type_impl:
            return self.device_type_impl.generate_measurement_data(self.device_id)
        else:
            # Fallback for unknown device types
            import random
            voltage = round(random.uniform(220, 240), 2)
            current = round(random.uniform(1, 10), 2)
            power = round(voltage * current, 2)  # P = V × I
            
            # Simple incremental kWh for fallback
            kwh = round(power / 1000 * 0.001, 6)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'device_id': self.device_id,
                'voltage': voltage,
                'current': current,
                'power': power,
                'kwh': kwh
            }

def device_worker(device_id, device_type):
    """Worker function that runs in a separate process for each device"""
    import os
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(f'Device-{device_id}')
    
    # Create database connection for this process
    # Check if PostgreSQL is available, otherwise use SQLite
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Import Flask app context for PostgreSQL
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from sqlalchemy.orm import DeclarativeBase
        from database_postgres import PostgresDatabase
        
        # Create minimal Flask app for database context
        class Base(DeclarativeBase):
            pass
        
        db_sqlalchemy = SQLAlchemy(model_class=Base)
        worker_app = Flask(__name__)
        worker_app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        worker_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        db_sqlalchemy.init_app(worker_app)
        
        with worker_app.app_context():
            import models_postgres  # Import models
            db = PostgresDatabase()
            logger.info(f"Device worker {device_id} using PostgreSQL")
    else:
        db = Database()
        logger.info(f"Device worker {device_id} using SQLite")
        
    device = VirtualDevice(device_id, device_type)
    
    logger.info(f"Starting device worker for {device_id} ({device_type})")
    
    try:
        while True:
            # Generate measurement data
            data = device.generate_data()
            
            # Store in database
            db.insert_measurement(
                device_id=data['device_id'],
                timestamp=data['timestamp'],
                voltage=data['voltage'],
                current=data['current'],
                power=data['power'],
                kwh=data['kwh']
            )
            
            logger.debug(f"Generated data for {device_id}: {data}")
            
            # Wait 5 seconds before next measurement
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info(f"Device worker {device_id} stopped by interrupt")
    except Exception as e:
        logger.error(f"Error in device worker {device_id}: {e}")
    finally:
        logger.info(f"Device worker {device_id} shutting down")
