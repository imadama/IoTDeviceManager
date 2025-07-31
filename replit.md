# replit.md

## Overview

This is an IoT Device Management System built with Flask that simulates and manages virtual IoT devices (Solar Panels, Heat Pumps, and Main Grid connections). The system generates synthetic measurement data, stores it in a PostgreSQL database, and provides a web interface for device management and data visualization with complete Cumulocity IoT platform integration. Each device operates as an independent script with unique MQTT client connections, preventing duplicate registrations and ensuring proper device isolation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Python and Gunicorn production server
- **Database**: PostgreSQL primary database with SQLite fallback for measurement data and device state persistence
- **Process Management**: Python multiprocessing for running virtual device simulations as independent scripts
- **Data Models**: SQLAlchemy ORM models for PostgreSQL with fallback Python classes for SQLite
- **Device Type Abstraction**: Abstract Base Class pattern for extensible device types with DeviceTypeInterface
- **MQTT Integration**: Cumulocity IoT platform connectivity using paho-mqtt library with MQTT 3.1.1 protocol
- **Device Isolation**: Each device runs as independent script with unique MQTT client ID (`iot_sim_{device_id}_client`)

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
- **main.py**: Entry point for Gunicorn production server
- **app.py**: Main Flask application with routes for dashboard and device management
- **device_manager.py**: Manages virtual device lifecycle and process orchestration using abstracted device types
- **device.py**: Virtual device implementation with abstracted data generation logic and unique MQTT client support
- **device_types.py**: Abstract device type implementations with DeviceTypeInterface, registry pattern for extensibility
- **database.py**: SQLite database wrapper with connection management (fallback)
- **database_postgres.py**: PostgreSQL database wrapper with SQLAlchemy ORM
- **models.py**: SQLite data models for DeviceStatus and Measurement entities (fallback)
- **models_postgres.py**: PostgreSQL SQLAlchemy models for production database
- **mqtt_client.py**: Cumulocity MQTT client with unique client IDs, SSL/TLS, certificate auth, MQTT 3.1.1 protocol
- **device_settings.py**: Device configuration management and measurement intervals

### MQTT Integration Features
- **Device Registration**: Complete Cumulocity device bootstrap with hardware info and supported operations
- **Real-time Measurements**: JSON format via MQTT with proper c8y_ElectricMeasurement fragment structure
- **Command Handling**: Device restart commands (510) with proper acknowledgment (501/503)
- **Device Metadata**: Hardware information (110) and supported operations (114) templates
- **Test Messaging**: Custom topic and message testing with wildcard validation
- **SSL/TLS Security**: Production-ready secure connections with tenant/username authentication
- **Error Handling**: Comprehensive connection, authentication, and message validation
- **Optimized Data Format**: Single JSON payload per measurement cycle with proper c8y fragment structure
- **Rate Limiting Handling**: Cumulocity MQTT rate limits handled automatically via queue mechanism
- **Unique Client IDs**: Each device has individual MQTT client (`iot_sim_{device_id}_client`) preventing conflicts
- **Registration Persistence**: Device registration status stored in `device_status.json` to prevent duplicates
- **Independent Script Architecture**: Each device behaves like a standalone script with only devicename and clientID differences

### Device Types Supported
- **PV (Solar Panels)**: Generates voltage (200-250V), current (5-15A), power (calculated: V×I, typically 1000-3750W)
- **Heat Pump**: Generates voltage (220-240V), current (8-20A), power (calculated: V×I, typically 1760-4800W)
- **Main Grid**: Generates voltage (230-240V), current (10-50A), power (calculated: V×I, typically 2300-12000W)

### Web Interface
- **Dashboard**: Device overview, statistics, and management controls
- **Data View**: Measurement data display with filtering capabilities
- **Responsive Design**: Bootstrap-based responsive layout

## Data Flow

1. **Device Creation**: User selects device type → DeviceManager creates new device → Status saved to JSON
2. **Device Registration**: Each device checks registration status → If not registered, registers once in Cumulocity → Status persisted
3. **Device Operation**: Independent device process generates measurement data → Data stored in PostgreSQL → MQTT sent to Cumulocity
4. **Data Visualization**: Web interface queries database → Templates render measurement data → User views results
5. **Device Management**: User controls (start/stop/delete) → DeviceManager updates processes → Status persisted
6. **MQTT Communication**: Each device maintains separate MQTT connection with unique client ID → No registration conflicts

## External Dependencies

### Python Packages
- **Flask**: Web framework for HTTP handling and template rendering
- **Flask-SQLAlchemy**: ORM for database operations with PostgreSQL
- **Gunicorn**: Production WSGI server for Flask application
- **psycopg2-binary**: PostgreSQL adapter for Python
- **paho-mqtt**: MQTT client library for Cumulocity IoT platform connectivity
- **email-validator**: Email validation support for Flask forms
- **sqlite3**: Database operations (built-in Python module) - fallback only
- **multiprocessing**: Process management for device simulation
- **logging**: Application logging and debugging

### Frontend Dependencies
- **Bootstrap 5**: CSS framework with Replit dark theme (`bootstrap-agent-dark-theme.min.css`)
- **Font Awesome 6**: Icon library loaded from CDN
- **Custom JavaScript**: Dashboard functionality with real-time auto-refresh and device status monitoring

### Environment Configuration
- **DATABASE_URL**: PostgreSQL connection string (primary database)
- **PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE**: PostgreSQL connection parameters
- **SESSION_SECRET**: Flask session security (defaults to dev key)
- **Debug Mode**: Gunicorn production server with reload support for development

## Deployment Strategy

### Development Setup
- **Entry Point**: `main.py` runs Gunicorn production server on 0.0.0.0:5000
- **Production Ready**: Gunicorn with reload support for development
- **File Structure**: Modular Python files with templates and static assets
- **Environment**: PostgreSQL database with automatic fallback to SQLite

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

## Recent Changes (July 2025)

### Unique MQTT Client Architecture Implementation
- **Date**: July 21-24, 2025
- **Issue Resolved**: Devices were sharing MQTT client instances causing registration conflicts
- **Solution Implemented**: Each device now has unique MQTT client ID (`iot_sim_{device_id}_client`)
- **Architecture Change**: Devices now behave as completely independent scripts, matching user requirements
- **Registration Logic**: Persistent storage prevents duplicate device registrations in Cumulocity
- **Testing Confirmed**: Multiple devices (test002, test003) running simultaneously with separate MQTT connections

### Database Migration to PostgreSQL
- **Date**: July 2025
- **Primary Database**: PostgreSQL with proper schema and indexing using SQLAlchemy ORM
- **Fallback Support**: SQLite database maintained for environments without PostgreSQL
- **ORM Integration**: Separate model files for PostgreSQL (`models_postgres.py`) and SQLite (`models.py`)
- **Production Ready**: Database connection pooling and proper environment variable configuration

### Production Server Implementation
- **Date**: July 2025
- **Server**: Migrated from Flask dev server to Gunicorn production server
- **Configuration**: Gunicorn with `--bind 0.0.0.0:5000 --reuse-port --reload` for development
- **Performance**: Better handling of concurrent requests and device processes

### MQTT Reconnection Logic Implementation
- **Date**: July 31, 2025
- **Enhancement**: Added comprehensive MQTT broker reconnection logic for reliable IoT device connectivity
- **Features Implemented**:
  - **Automatic Reconnection**: Background thread with exponential backoff (5s to 5min delays)
  - **Connection Monitoring**: Heartbeat mechanism every 60 seconds to detect connection issues
  - **Resilient Recovery**: Up to 50 reconnection attempts (~4 hours) before giving up
  - **Smart Reconnection**: Triggers on unexpected disconnections, preserves manual disconnects
  - **Connection Health API**: Detailed status monitoring with timestamps and attempt counters
- **Raspberry Pi Compatibility**: Specifically addresses connectivity issues on resource-constrained devices
- **Production Ready**: Thread-safe implementation with proper cleanup and error handling

The system is designed for production IoT device simulation and management, providing realistic device behavior without requiring actual hardware. The architecture supports easy extension for additional device types and measurement parameters while maintaining proper device isolation and Cumulocity integration standards. The robust reconnection logic ensures reliable operation in production environments with unstable network conditions.