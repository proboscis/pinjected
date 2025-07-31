from pinjected import IProxy, injected, instance


class APIService:
    def call(self, endpoint: str):
        pass


class DatabaseClient:
    def connect(self):
        pass


class NotificationHandler:
    def send(self, msg: str):
        pass


class EmailService:
    def send(self, to: str, subject: str, body: str):
        pass


class PaymentGateway:
    def process(self, amount: float):
        pass


# Bad - @instance functions returning service types should use IProxy
@instance
def api_service() -> APIService:  # Bad - entry point should return IProxy[APIService]
    return APIService()


@instance
def database_client() -> DatabaseClient:  # Bad - should return IProxy[DatabaseClient]
    client = DatabaseClient()
    client.connect()
    return client


@instance
def notification_handler() -> NotificationHandler:  # Bad
    return NotificationHandler()


# Good - @instance functions returning IProxy
@instance
def email_service() -> IProxy[EmailService]:  # Good - returns IProxy
    return EmailService()


@instance
def payment_gateway() -> IProxy[PaymentGateway]:  # Good
    gateway = PaymentGateway()
    # Some initialization
    return gateway


# OK - @instance functions returning non-service types
@instance
def config_dict() -> dict:  # OK - not a service type
    return {"timeout": 30, "retries": 3}


@instance
def port_number() -> int:  # OK - not a service type
    return 8080


@instance
def api_url() -> str:  # OK - not a service type
    return "https://api.example.com"


# @injected functions - parameters don't need IProxy
@injected
def process_data(
    database_service: DatabaseClient,  # Good - injected deps use actual types
    logger: NotificationHandler,  # Good - injected deps use actual types
    config_manager: APIService,  # Good - injected deps use actual types
    /,
    data: dict,
):
    logger.send("Processing data")
    return database_service.connect()


# Async examples
class AsyncService:
    @classmethod
    async def create(cls):
        return cls()


@instance
async def async_service() -> IProxy[AsyncService]:  # Good - async instance with IProxy
    service = await AsyncService.create()
    return service


class DataProcessor:
    async def process(self, data):
        pass


@instance
async def data_processor() -> (
    DataProcessor
):  # Bad - should return IProxy[DataProcessor]
    return DataProcessor()


# No return type annotation - no check
@instance
def mystery_service():
    return "something"


# Not @instance - no check
def regular_function() -> APIService:
    return APIService()
