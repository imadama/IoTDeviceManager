# replit.md

## Overview

This is an IoT Device Management System built with Flask that simulates and manages virtual IoT devices (Solar Panels, Heat Pumps, and Main Grid connections). The system generates synthetic measurement data, stores it in a SQLite database, and provides a web interface for device management and data visualization.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Python
- **Database**: SQLite for measurement data storage and device state persistence
- **Process Management**: Python multiprocessing for running virtual device simulations
- **Data Models**: Simple Python classes for DeviceStatus and Measurement entities
- **Device Type Abstraction**: Abstract Base Class pattern for extensible device types with DeviceTypeInterface
- **MQTT Integration**: Cumulocity IoT platform connectivity using paho-mqtt library with MQTT 3.1.1 protocol

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **UI Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JavaScript for dashboard interactions and auto-refresh functionality
- **Icons**: Font Awesome for UI elements

### Data Storage Solutions
- **Primary Database**: PostgreSQL database with proper tables and indexing
  - `device_measurements`: Stores all IoT device measurement data with timestamps
  - `device_configs`: Stores device configuration and status information
- **Fallback Database**: SQLite database (`iot_devices.db`) when PostgreSQL unavailable
- **State Persistence**: JSON file (`device_status.json`) for device configuration and counters
- **Schema Design**: Normalized PostgreSQL schema with proper data types and relationships
- **Settings Storage**: JSON files for device and MQTT configuration persistence

## Key Components

### Core Application Components
- **app.py**: Main Flask application with routes for dashboard and device management
- **device_manager.py**: Manages virtual device lifecycle and process orchestration using abstracted device types
- **device.py**: Virtual device implementation with abstracted data generation logic
- **device_types.py**: Abstract device type implementations with DeviceTypeInterface, registry pattern for extensibility
- **database.py**: SQLite database wrapper with connection management
- **models.py**: Data models for DeviceStatus and Measurement entities
- **mqtt_client.py**: Cumulocity MQTT client with SSL/TLS, certificate auth, and MQTT 3.1.1 protocol support

### Device Types Supported
- **PV (Solar Panels)**: Generates voltage (200-250V), current (5-15A), power (1000-3000W)
- **Heat Pump**: Generates voltage (220-240V), current (8-20A), power (2000-5000W)
- **Main Grid**: Generates voltage (230-240V), current (10-50A), power (2500-12000W)

### Web Interface
- **Dashboard**: Device overview, statistics, and management controls
- **Data View**: Measurement data display with filtering capabilities
- **Responsive Design**: Bootstrap-based responsive layout

## Data Flow

1. **Device Creation**: User selects device type → DeviceManager creates new device → Status saved to JSON
2. **Device Operation**: Device process generates measurement data → Data stored in SQLite → Status updated
3. **Data Visualization**: Web interface queries database → Templates render measurement data → User views results
4. **Device Management**: User controls (start/stop/delete) → DeviceManager updates processes → Status persisted

## External Dependencies

### Python Packages
- **Flask**: Web framework for HTTP handling and template rendering
- **Flask-SQLAlchemy**: ORM for database operations with PostgreSQL
- **psycopg2-binary**: PostgreSQL adapter for Python
- **paho-mqtt**: MQTT client library for Cumulocity IoT platform connectivity
- **sqlite3**: Database operations (built-in Python module) - fallback only
- **multiprocessing**: Process management for device simulation
- **logging**: Application logging and debugging

### Frontend Dependencies
- **Bootstrap 5**: CSS framework loaded from CDN
- **Font Awesome**: Icon library loaded from CDN
- **Custom JavaScript**: Dashboard functionality and auto-refresh

### Environment Configuration
- **SESSION_SECRET**: Flask session security (defaults to dev key)
- **Database Path**: Configurable SQLite database location
- **Debug Mode**: Flask development mode enabled

## Deployment Strategy

### Development Setup
- **Entry Point**: `main.py` runs Flask dev server on 0.0.0.0:5000
- **Debug Mode**: Enabled for development with auto-reload
- **File Structure**: Modular Python files with templates and static assets

### Database Initialization
- **Auto-Setup**: Database tables created automatically on first run
- **Index Optimization**: Performance index on device_id and timestamp
- **Error Handling**: Graceful database initialization with logging

### Process Management
- **Device Processes**: Separate Python processes for each virtual device
- **State Recovery**: Device status loaded from JSON on application restart
- **Process Cleanup**: Devices marked as stopped on application restart (processes don't persist)

### Static File Serving
- **Templates**: Jinja2 templates in templates/ directory
- **JavaScript**: Custom dashboard functionality in static/js/
- **CSS**: Bootstrap loaded from CDN for styling

The system is designed for development and demonstration purposes, simulating IoT device behavior without requiring actual hardware. The architecture supports easy extension for additional device types and measurement parameters.