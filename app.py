import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from device_manager import DeviceManager
from database import Database

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db_sqlalchemy = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    # Initialize SQLAlchemy
    db_sqlalchemy.init_app(app)
    
    # Create tables
    with app.app_context():
        import models_postgres  # Import models to register them
        db_sqlalchemy.create_all()
else:
    logging.warning("DATABASE_URL not found, continuing with SQLite")

# Initialize components
if database_url:
    from database_postgres import PostgresDatabase
    db = PostgresDatabase()
    logging.info("Using PostgreSQL database")
else:
    db = Database()  # Fallback to SQLite
    logging.info("Using SQLite database")

device_manager = DeviceManager(db)

@app.route('/')
def dashboard():
    """Main dashboard page showing all devices and their status"""
    devices = device_manager.get_all_devices()
    # Get device types from registry
    from device_types import device_type_registry
    device_types = device_type_registry.get_all_type_names()
    
    # Get current measurement interval setting
    from device_settings import device_settings
    current_interval = device_settings.get_measurement_interval()
    
    # Create device type info mapping for template
    device_type_info_map = {}
    for type_name in device_types:
        device_type_impl = device_type_registry.get_device_type(type_name)
        device_type_info_map[type_name] = {
            'icon': device_type_impl.icon_class,
            'color': device_type_impl.color_class
        }
    
    return render_template('dashboard.html', 
                         devices=devices, 
                         device_types=device_types,
                         device_type_info_map=device_type_info_map,
                         current_interval=current_interval)

@app.route('/add_device', methods=['POST'])
def add_device():
    """Add a new device"""
    device_type = request.form.get('device_type')
    if not device_type:
        flash('Please select a device type', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        device_id = device_manager.add_device(device_type)
        flash(f'Device {device_id} added successfully', 'success')
    except Exception as e:
        flash(f'Error adding device: {str(e)}', 'error')
        logging.error(f"Error adding device: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/start_device/<device_id>')
def start_device(device_id):
    """Start a specific device"""
    try:
        success = device_manager.start_device(device_id)
        if success:
            flash(f'Device {device_id} started successfully', 'success')
        else:
            flash(f'Failed to start device {device_id}', 'error')
    except Exception as e:
        flash(f'Error starting device: {str(e)}', 'error')
        logging.error(f"Error starting device {device_id}: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/stop_device/<device_id>')
def stop_device(device_id):
    """Stop a specific device"""
    try:
        success = device_manager.stop_device(device_id)
        if success:
            flash(f'Device {device_id} stopped successfully', 'success')
        else:
            flash(f'Failed to stop device {device_id}', 'error')
    except Exception as e:
        flash(f'Error stopping device: {str(e)}', 'error')
        logging.error(f"Error stopping device {device_id}: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/data_view')
def data_view():
    """Page to view measurement data"""
    device_filter = request.args.get('device_id', '')
    
    # Get all devices for the filter dropdown
    devices = device_manager.get_all_devices()
    
    # Get measurement data
    measurements = db.get_measurements(device_id=device_filter if device_filter else None)
    
    return render_template('data_view.html', 
                         measurements=measurements, 
                         devices=devices, 
                         selected_device=device_filter)

@app.route('/api/device_status')
def api_device_status():
    """API endpoint to get current device status (for AJAX updates)"""
    devices = device_manager.get_all_devices()
    return jsonify(devices)

@app.route('/delete_device/<device_id>')
def delete_device(device_id):
    """Delete a device"""
    try:
        success = device_manager.delete_device(device_id)
        if success:
            flash(f'Device {device_id} deleted successfully', 'success')
        else:
            flash(f'Failed to delete device {device_id}', 'error')
    except Exception as e:
        flash(f'Error deleting device: {str(e)}', 'error')
        logging.error(f"Error deleting device {device_id}: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update measurement settings"""
    try:
        measurement_interval = int(request.form.get('measurement_interval', 5))
        
        # Validate interval
        if measurement_interval < 1:
            measurement_interval = 1
        elif measurement_interval > 300:
            measurement_interval = 300
        
        # Update settings
        from device_settings import device_settings
        device_settings.set_measurement_interval(measurement_interval)
        
        flash(f'Measurement interval updated to {measurement_interval} seconds', 'success')
        logging.info(f"Measurement interval updated to {measurement_interval}s")
        
    except ValueError:
        flash('Invalid interval value. Please enter a number between 1 and 300.', 'error')
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
        logging.error(f"Error updating settings: {e}")
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
