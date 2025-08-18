#!/usr/bin/env python3
"""Sample pinjected usage script demonstrating dependency injection patterns with extensive logging."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import loguru
from loguru import logger
from pinjected import IProxy, injected, instance

# Configure logger for better visibility
logger.add(
    "pinjected_sample_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {extra[tag]:<20} | {message}",
    enqueue=True,
)


# Define a protocol for our database service
class DatabaseService(Protocol):
    async def get_user(self, user_id: str) -> dict: ...

    async def save_user(self, user: dict) -> None: ...


# Define a protocol for our email service
class EmailService(Protocol):
    async def send_email(self, to: str, subject: str, body: str) -> None: ...


# Concrete implementation of DatabaseService
@dataclass(frozen=True)
class InMemoryDatabase:
    users: dict[str, dict]

    async def get_user(self, user_id: str) -> dict:
        logger.debug(f"Database: Looking up user {user_id}")
        user = self.users.get(user_id, {})
        if user:
            logger.info(f"Database: Found user {user_id}: {user}")
        else:
            logger.warning(f"Database: User {user_id} not found")
        return user

    async def save_user(self, user: dict) -> None:
        logger.info(f"Database: Saving user {user['id']}")
        # Simulate some processing time
        await asyncio.sleep(0.1)
        self.users[user["id"]] = user
        logger.success(f"Database: User {user['id']} saved successfully")


# Concrete implementation of EmailService
@dataclass(frozen=True)
class ConsoleEmailService:
    async def send_email(self, to: str, subject: str, body: str) -> None:
        with logger.contextualize(service="email", recipient=to):
            logger.info("📧 Preparing to send email")
            logger.debug(f"Subject: {subject}")
            logger.debug(f"Body preview: {body[:50]}...")

            # Simulate email sending
            await asyncio.sleep(0.2)

            logger.success(f"Email sent successfully to {to}")


# Define protocols for injected functions
class CreateUserProtocol(Protocol):
    async def __call__(self, user_id: str, name: str, email_address: str) -> dict: ...


class GetUserInfoProtocol(Protocol):
    async def __call__(self, user_id: str) -> dict: ...


class UserRegistrationWorkflowProtocol(Protocol):
    async def __call__(self, user_data: list[dict]) -> None: ...


# Business logic using dependency injection
@injected(protocol=CreateUserProtocol)
async def a_create_user(
    db: DatabaseService,
    email: EmailService,
    logger: "loguru.Logger",
    /,
    user_id: str,
    name: str,
    email_address: str,
) -> dict:
    """Create a new user and send welcome email."""
    start_time = time.time()

    with logger.contextualize(
        operation="create_user", user_id=user_id, tag="user-creation"
    ):
        logger.info(f"Starting user creation for {name}")
        logger.debug(f"User details: id={user_id}, email={email_address}")

        # Create user
        user = {
            "id": user_id,
            "name": name,
            "email": email_address,
            "created_at": datetime.now().isoformat(),
        }

        # Save to database
        logger.info(f"Saving user {name} to database")
        try:
            await db.save_user(user)
            logger.debug("User saved to database successfully")
        except Exception as e:
            logger.error(f"Failed to save user: {e}")
            raise

        # Send welcome email
        logger.info("Sending welcome email")
        try:
            await email.send_email(
                to=email_address,
                subject="Welcome!",
                body=f"Hello {name}, welcome to our service! Your account was created at {user['created_at']}",
            )
            logger.debug("Welcome email sent")
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            # Continue anyway - user is created

        elapsed = time.time() - start_time
        logger.success(f"User {name} created successfully in {elapsed:.2f}s")

        return user


@injected(protocol=GetUserInfoProtocol)
async def a_get_user_info(
    db: DatabaseService, logger: "loguru.Logger", /, user_id: str
) -> dict:
    """Retrieve user information from database."""
    with logger.contextualize(
        operation="get_user", user_id=user_id, tag="user-retrieval"
    ):
        logger.info(f"Retrieving user {user_id}")

        try:
            user = await db.get_user(user_id)

            if user:
                logger.success(f"Successfully retrieved user: {user['name']}")
                logger.debug(f"User data: {user}")
            else:
                logger.warning(f"User {user_id} not found in database")

            return user

        except Exception as e:
            logger.error(f"Failed to retrieve user {user_id}: {e}")
            raise


# Define dependency providers
@instance
def provide_database() -> DatabaseService:
    """Provide an in-memory database for testing."""
    logger.info("Initializing InMemoryDatabase")
    initial_users = {
        "admin": {"id": "admin", "name": "Admin User", "email": "admin@example.com"}
    }
    logger.debug(f"Database initialized with {len(initial_users)} users")
    return InMemoryDatabase(users=initial_users)


@instance
def provide_email_service() -> EmailService:
    """Provide a console email service."""
    logger.info("Initializing ConsoleEmailService")
    return ConsoleEmailService()


# Create IProxy objects for testing
test_create_user: IProxy = injected(a_create_user).proxy(
    user_id="123", name="John Doe", email_address="john@example.com"
)

test_get_user: IProxy = injected(a_get_user_info).proxy(user_id="123")


# Example of a more complex workflow
@injected(protocol=UserRegistrationWorkflowProtocol)
async def a_user_registration_workflow(
    create_user_fn: CreateUserProtocol,
    logger: "loguru.Logger",
    /,
    user_data: list[dict],
) -> None:
    """Register multiple users in parallel."""
    with logger.contextualize(workflow="user_registration", tag="bulk-registration"):
        logger.info(f"Starting bulk registration for {len(user_data)} users")
        logger.debug(f"Users to register: {[u['name'] for u in user_data]}")

        start_time = time.time()
        success_count = 0
        error_count = 0

        async with asyncio.TaskGroup() as tg:
            tasks = []
            for idx, data in enumerate(user_data):
                logger.debug(
                    f"Creating task {idx + 1}/{len(user_data)} for user {data['name']}"
                )

                task = tg.create_task(
                    create_user_fn(
                        user_id=data["id"],
                        name=data["name"],
                        email_address=data["email"],
                    )
                )
                tasks.append((data, task))

        # Check results
        for data, task in tasks:
            try:
                task.result()
                success_count += 1
                logger.debug(f"User {data['name']} registered successfully")
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to register user {data['name']}: {e}")

        elapsed = time.time() - start_time
        logger.info(
            f"Bulk registration completed in {elapsed:.2f}s - "
            f"Success: {success_count}, Failed: {error_count}"
        )

        if error_count > 0:
            logger.warning(f"{error_count} users failed to register")


# IProxy for the workflow
test_workflow: IProxy = (
    injected(a_user_registration_workflow)
    .proxy(
        user_data=[
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"},
            {"id": "3", "name": "Charlie", "email": "charlie@example.com"},
        ]
    )
    .bind(
        CreateUserProtocol=a_create_user  # Bind the actual implementation
    )
)


# Example with custom bindings
custom_test: IProxy = (
    injected(a_create_user)
    .proxy(user_id="custom-123", name="Custom User", email_address="custom@example.com")
    .bind(
        DatabaseService=InMemoryDatabase(
            users={"existing": {"id": "existing", "name": "Existing User"}}
        ),
        EmailService=ConsoleEmailService(),
    )
)


# Example of a synchronous function
class GreetUserProtocol(Protocol):
    def __call__(self, name: str) -> str: ...


@injected(protocol=GreetUserProtocol)
def greet_user(logger: "loguru.Logger", /, name: str) -> str:
    """Simple synchronous greeting function."""
    with logger.contextualize(function="greet_user", tag="greeting"):
        logger.info(f"Greeting user: {name}")

        if not name:
            logger.warning("Empty name provided")
            greeting = "Hello, Anonymous!"
        else:
            greeting = f"Hello, {name}!"
            logger.debug(f"Generated greeting: {greeting}")

        logger.success("Greeting generated successfully")
        return greeting


test_greet: IProxy = injected(greet_user).proxy(name="World")


# Example with error handling
class ProcessDataProtocol(Protocol):
    async def __call__(self, data: dict) -> dict: ...


@injected(protocol=ProcessDataProtocol)
async def a_process_data(logger: "loguru.Logger", /, data: dict) -> dict:
    """Process data with error handling and logging."""
    with logger.contextualize(operation="process_data", tag="data-processing"):
        logger.info("Starting data processing")
        logger.debug(f"Input data: {data}")

        try:
            # Validate data
            if not data:
                logger.error("Empty data provided")
                raise ValueError("Data cannot be empty")

            if "id" not in data:
                logger.error("Missing required field: id")
                raise KeyError("Data must contain 'id' field")

            logger.info(f"Processing data for id: {data['id']}")

            # Simulate processing
            await asyncio.sleep(0.1)

            result = {
                **data,
                "processed": True,
                "processed_at": datetime.now().isoformat(),
            }

            logger.success(f"Data processed successfully for id: {data['id']}")
            logger.debug(f"Processed result: {result}")

            return result

        except Exception as e:
            logger.exception(f"Failed to process data: {e}")
            raise


test_process: IProxy = injected(a_process_data).proxy(
    data={"id": "test-123", "value": 42}
)


# Log when module is imported
logger.info("Sample pinjected usage module loaded")


if __name__ == "__main__":
    logger.info("=== Pinjected Sample Script ===")
    print("\nThis script contains IProxy objects that can be run with:")
    print("  uv run pinjected run sample_pinjected_usage.test_create_user")
    print("  uv run pinjected run sample_pinjected_usage.test_get_user")
    print("  uv run pinjected run sample_pinjected_usage.test_workflow")
    print("  uv run pinjected run sample_pinjected_usage.custom_test")
    print("  uv run pinjected run sample_pinjected_usage.test_greet")
    print("  uv run pinjected run sample_pinjected_usage.test_process")
    print("\nYou can also list all IProxy objects with:")
    print("  uv run python -m pinjected list sample_pinjected_usage")
    print("\nLogs will be written to: pinjected_sample_<date>.log")

    logger.info("Script help information displayed")
