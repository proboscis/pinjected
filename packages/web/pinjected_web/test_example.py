"""Example file for testing the pinjected web API."""
from pinjected import design, instance

@instance
def config():
    """Example configuration."""
    return {
        "host": "localhost",
        "port": 5432,
        "name": "mydb"
    }

@instance
def connection(config):
    """Example database connection."""
    return f"Connected to {config['name']} at {config['host']}:{config['port']}"

@instance
def service(connection):
    """Example service that uses the connection."""
    return f"Service using {connection}"

example_design = design(
    db_config=config,
    db_connection=connection,
    db_service=service
)
