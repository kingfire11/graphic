import json
import os
from typing import Dict, List, Optional

DB_FILE = "data.json"

def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {"employees": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_employees() -> Dict[str, List[str]]:
    """Возвращает {имя: [список станций]}"""
    return _load().get("employees", {})

def add_employee(name: str, stations: List[str]):
    data = _load()
    data["employees"][name] = stations
    _save(data)

def remove_employee(name: str):
    data = _load()
    if name in data["employees"]:
        del data["employees"][name]
        _save(data)

def get_employee_stations(name: str) -> Optional[List[str]]:
    return get_employees().get(name)
