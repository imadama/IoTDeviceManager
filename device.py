import time
import random
import logging
from datetime import datetime
from multiprocessing import Process
from database import Database

class VirtualDevice:
    """Base class for virtual IoT devices"""
    
    def __init__(self, device_id, device_type):
        self.device_id = device_id
        self.device_type = device_type
        self.is_running = False
        self.process = None
        
    def generate_data(self):
        """Generate measurement data based on device type"""
        base_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id
        }
        
        if self.device_type == 'PV':
            # Solar panel data
            base_data.update({
                'voltage': round(random.uniform(200, 250), 2),
                'current': round(random.uniform(5, 15), 2),
                'power': round(random.uniform(1000, 3000), 2),
                'kwh': round(random.uniform(0.1, 0.5), 3)
            })
        elif self.device_type == 'Heat Pump':
            # Heat pump data
            base_data.update({
                'voltage': round(random.uniform(220, 240), 2),
                'current': round(random.uniform(8, 20), 2),
                'power': round(random.uniform(2000, 5000), 2),
                'kwh': round(random.uniform(0.3, 0.8), 3)
            })
        elif self.device_type == 'Main Grid':
            # Main grid connection data
            base_data.update({
                'voltage': round(random.uniform(230, 240), 2),
                'current': round(random.uniform(10, 50), 2),
                'power': round(random.uniform(2500, 12000), 2),
                'kwh': round(random.uniform(0.4, 2.0), 3)
            })
        else:
            # Default generic device
            base_data.update({
                'voltage': round(random.uniform(220, 240), 2),
                'current': round(random.uniform(1, 10), 2),
                'power': round(random.uniform(100, 2000), 2),
                'kwh': round(random.uniform(0.02, 0.3), 3)
            })
            
        return base_data

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
