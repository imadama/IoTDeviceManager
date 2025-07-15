// Dashboard JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-refresh device status every 30 seconds
    setInterval(updateDeviceStatus, 30000);
    
    // Update last update time every second
    setInterval(updateLastUpdateTime, 1000);
    
    // Load MQTT devices info every 30 seconds
    setInterval(loadMqttDevices, 30000);
    
    // Initial updates
    updateLastUpdateTime();
    loadMqttDevices();
    
    // Add confirmation dialogs for critical actions
    setupConfirmationDialogs();
    
    // Setup form validation
    setupFormValidation();
});

function updateDeviceStatus() {
    fetch('/api/device_status')
        .then(response => response.json())
        .then(data => {
            console.log('Checking for device status updates...');
            
            // Update MQTT status indicators
            if (data.devices) {
                data.devices.forEach(device => {
                    const mqttElement = document.querySelector(`.mqtt-status-${device.device_id}`);
                    if (mqttElement) {
                        const textElement = mqttElement.querySelector('.mqtt-text');
                        const iconElement = mqttElement.querySelector('i');
                        
                        // Update MQTT status display
                        if (device.mqtt_status === 'connected') {
                            mqttElement.className = `badge bg-success ms-1 mqtt-status-${device.device_id}`;
                            iconElement.className = 'fas fa-wifi me-1';
                            if (textElement) textElement.textContent = 'MQTT ✓';
                            mqttElement.title = 'MQTT Connected to Cumulocity';
                        } else if (device.mqtt_status === 'disconnected') {
                            mqttElement.className = `badge bg-warning ms-1 mqtt-status-${device.device_id}`;
                            iconElement.className = 'fas fa-wifi me-1';
                            if (textElement) textElement.textContent = 'MQTT ✗';
                            mqttElement.title = 'MQTT Disconnected';
                        } else if (device.mqtt_status === 'disabled') {
                            mqttElement.className = `badge bg-secondary ms-1 mqtt-status-${device.device_id}`;
                            iconElement.className = 'fas fa-wifi-slash me-1';
                            if (textElement) textElement.textContent = 'MQTT Off';
                            mqttElement.title = 'MQTT Disabled';
                        } else {
                            mqttElement.className = `badge bg-info ms-1 mqtt-status-${device.device_id}`;
                            iconElement.className = 'fas fa-wifi me-1';
                            if (textElement) textElement.textContent = 'MQTT ?';
                            mqttElement.title = 'MQTT Status Unknown';
                        }
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error fetching device status:', error);
        });
}

function updateLastUpdateTime() {
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement) {
        const now = new Date();
        lastUpdateElement.textContent = now.toLocaleTimeString('nl-NL');
    }
}

function setupConfirmationDialogs() {
    // Add extra confirmation for delete actions
    const deleteButtons = document.querySelectorAll('a[href*="delete_device"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const deviceId = this.href.split('/').pop();
            const confirmed = confirm(
                `Are you sure you want to delete device ${deviceId}?\n\n` +
                'This action will:\n' +
                '• Stop the device if it\'s running\n' +
                '• Delete all measurement data\n' +
                '• Remove the device permanently\n\n' +
                'This action cannot be undone.'
            );
            
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
    
    // Add confirmation for stop actions
    const stopButtons = document.querySelectorAll('a[href*="stop_device"]');
    stopButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const deviceId = this.href.split('/').pop();
            const confirmed = confirm(
                `Stop device ${deviceId}?\n\n` +
                'The device will stop generating measurement data.'
            );
            
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
}

function setupFormValidation() {
    const addDeviceForm = document.querySelector('form[action*="add_device"]');
    if (addDeviceForm) {
        addDeviceForm.addEventListener('submit', function(e) {
            const deviceType = document.getElementById('device_type').value;
            
            if (!deviceType) {
                e.preventDefault();
                alert('Please select a device type before adding a device.');
                document.getElementById('device_type').focus();
                return false;
            }
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
            submitButton.disabled = true;
            
            // Re-enable button after 3 seconds (in case of redirect failure)
            setTimeout(() => {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }, 3000);
        });
    }
}

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    // Create toast element
    const toastHtml = `
        <div class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Add to page
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Show toast
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Function to handle device action buttons with loading states
function handleDeviceAction(button, action) {
    const originalHtml = button.innerHTML;
    const deviceId = button.href ? button.href.split('/').pop() : 'unknown';
    
    // Show loading state
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.classList.add('disabled');
    
    // Restore button after 2 seconds
    setTimeout(() => {
        button.innerHTML = originalHtml;
        button.classList.remove('disabled');
    }, 2000);
}

// Load MQTT connected devices
function loadMqttDevices() {
    const mqttDevicesList = document.getElementById('mqtt-devices-list');
    if (!mqttDevicesList) return;
    
    fetch('/api/mqtt_devices')
        .then(response => response.json())
        .then(data => {
            if (!data.mqtt_enabled) {
                mqttDevicesList.innerHTML = '<div class="text-muted">MQTT is not enabled</div>';
                return;
            }
            
            if (data.connected_devices.length === 0) {
                mqttDevicesList.innerHTML = `
                    <div class="text-center py-3">
                        <i class="fas fa-wifi-slash fa-2x text-muted mb-2"></i>
                        <div class="text-muted">No devices connected to ${data.broker_host}</div>
                        <small class="text-muted">Start a device to see it here</small>
                    </div>
                `;
                return;
            }
            
            let deviceHtml = `
                <div class="mb-3">
                    <small class="text-muted">Connected to: <strong>${data.broker_host}</strong></small>
                </div>
                <div class="row">
            `;
            
            data.connected_devices.forEach(device => {
                deviceHtml += `
                    <div class="col-md-6 mb-3">
                        <div class="card border-success">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <h6 class="card-title mb-1">
                                            <i class="fas fa-wifi text-success me-2"></i>${device.device_id}
                                        </h6>
                                        <small class="text-muted">${device.device_type}</small>
                                    </div>
                                    <div class="text-end">
                                        <span class="badge bg-success">Connected</span>
                                        <div class="mt-1">
                                            <small class="text-muted">Cumulocity: ${device.cumulocity_name}</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            deviceHtml += '</div>';
            mqttDevicesList.innerHTML = deviceHtml;
        })
        .catch(error => {
            console.error('Error loading MQTT devices:', error);
            mqttDevicesList.innerHTML = '<div class="text-danger">Error loading MQTT device status</div>';
        });
}

// Add click handlers for action buttons
document.addEventListener('DOMContentLoaded', function() {
    const actionButtons = document.querySelectorAll('a[href*="start_device"], a[href*="stop_device"]');
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.href.includes('start_') ? 'start' : 'stop';
            handleDeviceAction(this, action);
        });
    });
});
