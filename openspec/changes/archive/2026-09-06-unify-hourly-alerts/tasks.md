## 1. Reglas unificadas por hora

- [x] 1.1 Añadir `get_hour_alerts(hour)` en `meteowatch/alerts/rules.py` evaluando WMO, viento, inundación, heladas y calor
- [x] 1.2 Exportar `get_hour_alerts` desde `meteowatch/alerts/__init__.py`

## 2. Motor de alertas

- [x] 2.1 Refactorizar `AlertEngine.evaluate()` en `meteowatch/alerts/engine.py` para agregar sobre `get_hour_alerts` conservando ventanas, lluvia diaria y dedup

## 3. Desglose por hora

- [x] 3.1 Refactorizar `_build_hour_row` en `meteowatch/widgets/hourly_panel.py` para usar `get_hour_alerts` y eliminar el hardcode `>= 50`
- [x] 3.2 Añadir icono de alerta (🔴/⚠️) junto a la hora con tooltip descriptivo

## 4. Tests

- [x] 4.1 Añadir tests de `get_hour_alerts` en `tests/test_alerts.py` (cada regla y caso benigno)
- [x] 4.2 Añadir/actualizar tests en `tests/test_hourly_panel.py` para helpers puros de icono/tooltip y lógica unificada
- [x] 4.3 Ejecutar `python -m pytest tests/ -v` y linters
