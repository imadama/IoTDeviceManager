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
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(f'Device-{device_id}')
    
    # Create database connection for this process
    db = Database()
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
