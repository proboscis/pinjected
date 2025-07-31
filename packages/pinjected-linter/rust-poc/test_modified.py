from pinjected import injected


@injected
def test_func(db, /, user_id: str):
    """Test function."""
    return db.get_user(user_id)
