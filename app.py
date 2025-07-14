import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from device_manager import DeviceManager
from database import Database
from models import DeviceStatus

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize components
db = Database()
device_manager = DeviceManager(db)

@app.route('/')
def dashboard():
    """Main dashboard page showing all devices and their status"""
    devices = device_manager.get_all_devices()
    device_types = ['PV', 'Heat Pump', 'Main Grid']
    return render_template('dashboard.html', devices=devices, device_types=device_types)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
