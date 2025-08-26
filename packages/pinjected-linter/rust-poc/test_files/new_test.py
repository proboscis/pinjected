from pinjected import injected


@injected
def process_data(db_conn, /, data: str) -> str:
    return f"Processing {data} with {db_conn}"


@injected
def validate_input(validator, /, input_data: dict) -> bool:
    return validator.validate(input_data)
