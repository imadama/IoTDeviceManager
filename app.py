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
    
    # Get MQTT settings
    from mqtt_client import mqtt_settings
    mqtt_config = mqtt_settings.settings
    
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
                         current_interval=current_interval,
                         mqtt_enabled=mqtt_config.get('enabled', False),
                         mqtt_broker_host=mqtt_config.get('broker_host', ''),
                         mqtt_broker_port=mqtt_config.get('broker_port', 1883),
                         mqtt_username=mqtt_config.get('username', ''),
                         mqtt_password=mqtt_config.get('password', ''),
                         mqtt_tenant=mqtt_config.get('tenant', ''),
                         mqtt_use_ssl=mqtt_config.get('use_ssl', False))

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

@app.route('/update_mqtt_settings', methods=['POST'])
def update_mqtt_settings():
    """Update MQTT settings"""
    try:
        from mqtt_client import mqtt_settings
        
        # Get form data
        enabled = 'mqtt_enabled' in request.form
        broker_host = request.form.get('broker_host', '').strip()
        broker_port = int(request.form.get('broker_port', 1883))
        username = request.form.get('mqtt_username', '').strip()
        password = request.form.get('mqtt_password', '').strip()
        tenant = request.form.get('mqtt_tenant', '').strip()
        use_ssl = 'use_ssl' in request.form
        
        # Validate port
        if broker_port < 1 or broker_port > 65535:
            broker_port = 8883 if use_ssl else 1883
        
        # Update settings
        mqtt_settings.update_settings(
            enabled=enabled,
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password,
            tenant=tenant,
            use_ssl=use_ssl
        )
        
        if enabled and broker_host:
            flash(f'MQTT settings updated - connected to {broker_host}', 'success')
        elif enabled:
            flash('MQTT enabled but broker host is required', 'warning')
        else:
            flash('MQTT disabled', 'info')
            
        logging.info(f"MQTT settings updated: enabled={enabled}, host={broker_host}")
        
    except ValueError as e:
        flash(f'Invalid port number: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error updating MQTT settings: {str(e)}', 'error')
        logging.error(f"Error updating MQTT settings: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/test_mqtt_connection')
def test_mqtt_connection():
    """Test MQTT connection to Cumulocity"""
    try:
        from mqtt_client import CumulocityMqttClient, mqtt_settings
        
        if not mqtt_settings.is_enabled():
            flash('MQTT is not enabled. Please enable and configure MQTT first.', 'warning')
            return redirect(url_for('dashboard'))
        
        connection_params = mqtt_settings.get_connection_params()
        
        if not connection_params['broker_host']:
            flash('MQTT broker host is required. Please configure MQTT settings.', 'error')
            return redirect(url_for('dashboard'))
        
        # Create test client
        test_client = CumulocityMqttClient(
            broker_host=connection_params['broker_host'],
            broker_port=connection_params['broker_port'],
            username=connection_params['username'],
            password=connection_params['password'],
            tenant=connection_params['tenant'],
            device_id='test_device',
            use_ssl=connection_params['use_ssl'],
            ca_cert_path=connection_params['ca_cert_path'],
            client_cert_path=connection_params['client_cert_path'],
            client_key_path=connection_params['client_key_path']
        )
        
        # Test connection
        if test_client.connect():
            flash('MQTT connection successful! Ready to send device data to Cumulocity.', 'success')
            test_client.disconnect()
        else:
            flash('MQTT connection failed. Please check your credentials and settings.', 'error')
            
    except Exception as e:
        flash(f'Error testing MQTT connection: {str(e)}', 'error')
        logging.error(f"Error testing MQTT connection: {e}")
    
    return redirect(url_for('dashboard'))

@app.route('/send_mqtt_test', methods=['POST'])
def send_mqtt_test():
    """Send a test message to MQTT topic"""
    try:
        from mqtt_client import CumulocityMqttClient, mqtt_settings
        
        if not mqtt_settings.is_enabled():
            flash('MQTT is not enabled. Please enable and configure MQTT first.', 'warning')
            return redirect(url_for('dashboard'))
        
        # Get form data
        test_topic = request.form.get('test_topic', '').strip()
        test_message = request.form.get('test_message', '').strip()
        
        connection_params = mqtt_settings.get_connection_params()
        
        if not connection_params['broker_host']:
            flash('MQTT broker host is required. Please configure MQTT settings.', 'error')
            return redirect(url_for('dashboard'))
        
        # Create test client
        test_client = CumulocityMqttClient(
            broker_host=connection_params['broker_host'],
            broker_port=connection_params['broker_port'],
            username=connection_params['username'],
            password=connection_params['password'],
            tenant=connection_params['tenant'],
            device_id='test_device',
            use_ssl=connection_params['use_ssl'],
            ca_cert_path=connection_params['ca_cert_path'],
            client_cert_path=connection_params['client_cert_path'],
            client_key_path=connection_params['client_key_path']
        )
        
        # Test connection and send message
        if test_client.connect():
            success = test_client.send_test_message(test_topic if test_topic else None, 
                                                  test_message if test_message else None)
            if success:
                topic_name = test_topic if test_topic else 's/us (default)'
                flash(f'Test message sent successfully to topic: {topic_name}', 'success')
            else:
                flash('Failed to send test message. Check logs for details.', 'error')
            test_client.disconnect()
        else:
            flash('Failed to connect to MQTT broker for test.', 'error')
            
    except Exception as e:
        flash(f'Error sending test message: {str(e)}', 'error')
        logging.error(f"Error sending test message: {e}")
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
