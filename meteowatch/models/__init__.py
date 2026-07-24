"""Modelos de datos de la API de Open-Meteo."""

from meteowatch.models.location import Location
from meteowatch.models.daily import DailyForecast, DayData
from meteowatch.models.hourly import HourData, HourlyForecast

__all__ = ["Location", "DailyForecast", "DayData", "HourlyForecast", "HourData"]
