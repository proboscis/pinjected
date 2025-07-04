"""Comprehensive example demonstrating various Pinjected patterns and violations."""

from pinjected import instance, injected, design, IProxy
from typing import List, Dict, Any

# Mock classes and functions for the example
class DatabaseConnection:
    def __init__(self, url): pass
    def save(self, data): pass
    def save_batch(self, data): pass
    def get_user(self, id): pass
    async def store(self, key, data): pass

class RedisCache:
    def __init__(self, host, port): pass
    def get(self, key): pass
    def set(self, key, value, ttl): pass

class RabbitMQ:
    @staticmethod
    async def connect(url): pass

class Logger:
    def info(self, msg): pass
    def log(self, msg): pass

class ConfigManager:
    def __init__(self, env): pass

class TaskQueue:
    @staticmethod
    async def create(): pass

class ServiceOrchestrator:
    def __init__(self, *args): pass

def hash(x): return 0
def transform(item): return {**item, "processed": True}
async def create_redis_connection(): return RedisCache("localhost", 6379)
async def create_queue(): return TaskQueue()

# IProxy references
class ModelTrainer:
    def train(self, dataset, epochs): return "training"
class Model:
    def predict(self, data): return [0.0]

model_trainer = ModelTrainer()
model = Model()
trainer = ModelTrainer()
class Pipeline:
    def run(self): return "running"
pipeline = Pipeline()
test_data = []

# =============================================================================
# GOOD PATTERNS
# =============================================================================

# Good: Properly named @instance functions
@instance
def database_connection():
    """Provides database connection."""
    return DatabaseConnection("postgresql://localhost/mydb")

@instance
def cache_client():
    """Provides cache client."""
    return RedisCache(host="localhost", port=6379)

@instance
async def message_broker():
    """Provides async message broker without a_ prefix."""
    return await RabbitMQ.connect("amqp://localhost")

# Good: Configuration using design()
base_design = design(
    database=database_connection,
    cache=cache_client,
    broker=message_broker,
    # Configuration values
    timeout=30,
    retry_count=3,
    debug=True,
)

# Good: Proper @injected with dependencies declared
@injected
def data_processor(
    logger,
    database,
    cache,
    /,
    data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Process data with proper dependency injection."""
    logger.info(f"Processing {len(data)} items")
    
    # Check cache first
    cache_key = f"processed_{hash(str(data))}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Process and store
    result = [transform(item) for item in data]
    database.save_batch(result)
    cache.set(cache_key, result, ttl=3600)
    
    return result

# Good: Async @injected with a_ prefix
@injected
async def a_fetch_and_store(
    logger,
    database,
    a_http_client,  # Async dependency
    /,
    url: str,
    store_key: str
) -> Dict[str, Any]:
    """Async function with proper naming and dependencies."""
    logger.info(f"Fetching from {url}")
    data = await a_http_client.get(url)
    await database.store(store_key, data)
    return data

# Good: Entry points with IProxy annotations
train_model: IProxy = model_trainer.train(dataset="mnist", epochs=10)
run_inference: IProxy[List[float]] = model.predict(test_data)

# =============================================================================
# BAD PATTERNS (Would trigger violations)
# =============================================================================

# Bad: PINJ001 - Verb in @instance name
@instance
def create_logger():  # Should be 'logger'
    return Logger()

# Bad: PINJ002 - Default arguments in @instance
@instance
def config_manager(env="development"):  # No defaults allowed
    return ConfigManager(env)

# Bad: PINJ003 - Async @instance with a_ prefix
@instance
async def a_task_queue():  # Should not have a_ prefix
    return await TaskQueue.create()

# Bad: PINJ004 - Direct instance call
logger = create_logger()  # Direct call not allowed

# Define these @injected functions that will be called without declaration
@injected  
def process_data(processor, /, data):
    return processor.process(data)

@injected
def validate_data(validator, /, data):
    return validator.validate(data)

# Bad: PINJ008 - Undeclared injected dependency
@injected
def bad_workflow(database, /):
    # process_data is @injected but not declared!
    result = process_data([1, 2, 3])  # Will cause NameError
    return database.save(result)

# Bad: PINJ015 - Unclear if slash is needed
@injected
def ambiguous_function(logger, analyzer, data, options):
    """Are data and options dependencies or runtime args? Unclear!"""
    return analyzer.analyze(data, options)

# =============================================================================
# EDGE CASES
# =============================================================================

# Edge: Without slash, these are ALL runtime args (not dependencies!)
@injected
def service_orchestrator(
    logger,
    database,
    cache,
    message_broker,
    task_queue,
    # WRONG: Without slash, these are runtime args, NOT injected!
):
    """Without slash, caller must provide ALL 5 arguments."""
    logger.info("Starting orchestration")
    return ServiceOrchestrator(database, cache, message_broker, task_queue)

# Edge: No dependencies, only runtime args
@injected
def pure_computation(x: float, y: float) -> float:
    """Pure function with no dependencies."""
    return x * y + x / y

# Edge: Complex dependency chains
@injected
def complex_workflow(
    logger,
    data_processor,  # This is itself an @injected function
    a_fetch_and_store,  # Async @injected function
    /,
    urls: List[str]
) -> List[Any]:
    """Complex workflow with nested dependencies."""
    results = []
    for i, url in enumerate(urls):
        # Note: We're building computation graph, not executing
        fetch_result = a_fetch_and_store(url, f"item_{i}")
        processed = data_processor([fetch_result])
        results.append(processed)
    return results