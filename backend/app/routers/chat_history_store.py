from typing import List, Tuple

# Dictionary để lưu trữ session_id -> list of tuples (role, message)
_store = {}

def get_history(session_id: str):
    if session_id not in _store:
        _store[session_id] = []
    
    # Langchain yêu cầu dạng tuple hoặc message class, ta truyền list dạng [("human", msg), ("ai", msg)]
    return _store[session_id]

def add_message(session_id: str, role: str, message: str):
    if session_id not in _store:
        _store[session_id] = []
    _store[session_id].append((role, message))
