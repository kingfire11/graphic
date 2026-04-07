from typing import Dict, List, Optional
import random
from config import STATIONS

def generate_schedule(
    employees: Dict[str, List[str]],
    days_off: Dict[str, List[int]]  # {имя: [индексы выходных дней 0-6]}
) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Генерирует расписание на 7 дней.
    
    Возвращает: {станция: {день_индекс: имя_сотрудника}}
    или None если невозможно составить расписание.
    """
    # schedule[station][day_index] = employee_name
    schedule: Dict[str, Dict[int, str]] = {s: {} for s in STATIONS}

    for day_idx in range(7):
        # Доступные в этот день сотрудники
        available = [
            name for name, stations in employees.items()
            if day_idx not in days_off.get(name, [])
        ]

        # Для каждой станции назначаем сотрудника
        # Пытаемся равномерно распределить нагрузку
        day_assignments: Dict[str, str] = {}  # {station: employee}
        
        # Счётчик смен за эту неделю
        shift_count: Dict[str, int] = {name: 0 for name in available}
        
        for station in STATIONS:
            # Сотрудники, которые могут работать на этой станции и доступны сегодня
            candidates = [
                name for name in available
                if station in employees[name]
                and name not in day_assignments.values()  # не поставлен уже на другую станцию сегодня
            ]
            
            if not candidates:
                # Допускаем повтор (один человек — одна станция, но если выбора нет, пропускаем)
                candidates = [
                    name for name in available
                    if station in employees[name]
                ]
            
            if not candidates:
                schedule[station][day_idx] = "—"
                continue
            
            # Выбираем кандидата с наименьшим числом смен
            chosen = min(candidates, key=lambda n: shift_count.get(n, 0))
            schedule[station][day_idx] = chosen
            day_assignments[station] = chosen
            if chosen in shift_count:
                shift_count[chosen] += 1

    return schedule
