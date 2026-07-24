"""Tests para el módulo de configuración."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

# Parchear el path de configuración antes de importar el módulo
import meteowatch.config as config_module


class TestAppConfig:
    """Pruebas para la clase AppConfig."""

    def test_load_empty_config_when_file_does_not_exist(self):
        """Debe retornar configuración vacía si el archivo no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config_module, "CONFIG_FILE", os.path.join(tmpdir, "nonexistent.json")):
                cfg = config_module.AppConfig.load()
                assert cfg.latitude == 0.0
                assert cfg.longitude == 0.0
                assert cfg.location_name == ""

    def test_load_existing_config(self):
        """Debe cargar correctamente una configuración existente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            data = {
                "latitude": 40.4168,
                "longitude": -3.7038,
                "location_name": "Madrid",
                "timezone": "Europe/Madrid",
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.latitude == 40.4168
                assert cfg.longitude == -3.7038
                assert cfg.location_name == "Madrid"
                assert cfg.timezone == "Europe/Madrid"

    def test_save_creates_directory_and_file(self):
        """Debe crear el directorio y archivo de configuración al guardar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "meteowatch")
            config_path = os.path.join(config_dir, "config.json")

            with patch.object(config_module, "CONFIG_DIR", config_dir):
                with patch.object(config_module, "CONFIG_FILE", config_path):
                    cfg = config_module.AppConfig(
                        latitude=41.3874,
                        longitude=2.1686,
                        location_name="Barcelona",
                        timezone="Europe/Madrid",
                    )
                    cfg.save()

                    assert os.path.exists(config_path)

                    with open(config_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)

                    assert saved["latitude"] == 41.3874
                    assert saved["longitude"] == 2.1686
                    assert saved["location_name"] == "Barcelona"
                    assert saved["timezone"] == "Europe/Madrid"

    def test_is_configured_returns_false_when_empty(self):
        """Debe retornar False si no hay coordenadas."""
        cfg = config_module.AppConfig()
        assert not cfg.is_configured()

    def test_is_configured_returns_true_when_coordinates_set(self):
        """Debe retornar True si las coordenadas están configuradas."""
        cfg = config_module.AppConfig(
            latitude=37.3891,
            longitude=-5.9845,
            location_name="Sevilla",
        )
        assert cfg.is_configured()

    def test_set_location_updates_and_saves(self):
        """Debe actualizar la ubicación y persistir los cambios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "meteowatch")
            config_path = os.path.join(config_dir, "config.json")

            with patch.object(config_module, "CONFIG_DIR", config_dir):
                with patch.object(config_module, "CONFIG_FILE", config_path):
                    cfg = config_module.AppConfig(latitude=0.0, longitude=0.0)
                    cfg.set_location(39.4699, -0.3763, "Valencia", "Europe/Madrid")

                    assert cfg.latitude == 39.4699
                    assert cfg.longitude == -0.3763
                    assert cfg.location_name == "Valencia"
                    assert cfg.timezone == "Europe/Madrid"

    def test_load_ignores_old_api_key_and_hash(self):
        """Debe ignorar campos de configuraciones antiguas (api_key, location_hash)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            data = {
                "api_key": "old-key-123",
                "location_hash": "oldhash",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "location_name": "London",
                "timezone": "Europe/London",
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.latitude == 51.5074
                assert cfg.longitude == -0.1278
                assert cfg.location_name == "London"

    def test_close_to_tray_default_is_true(self):
        """close_to_tray debe ser True por defecto."""
        cfg = config_module.AppConfig()
        assert cfg.close_to_tray is True

    def test_close_to_tray_persists_correctly(self):
        """close_to_tray debe guardarse y cargarse correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "meteowatch")
            config_path = os.path.join(config_dir, "config.json")

            with patch.object(config_module, "CONFIG_DIR", config_dir):
                with patch.object(config_module, "CONFIG_FILE", config_path):
                    # Guardar con close_to_tray=False
                    cfg = config_module.AppConfig(
                        latitude=40.4168,
                        longitude=-3.7038,
                        close_to_tray=False,
                    )
                    cfg.save()

                    # Cargar y verificar
                    loaded = config_module.AppConfig.load()
                    assert loaded.close_to_tray is False
                    assert loaded.latitude == 40.4168

    def test_load_missing_close_to_tray_defaults_to_true(self):
        """Si close_to_tray no está en el JSON, debe usar True como valor por defecto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            data = {
                "latitude": 40.4168,
                "longitude": -3.7038,
                "location_name": "Madrid",
                # close_to_tray no está presente
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.close_to_tray is True

    def test_load_corrupted_json_returns_empty_config(self):
        """Debe retornar configuración vacía si el JSON está corrupto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("esto no es json{")

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.latitude == 0.0
                assert cfg.longitude == 0.0

    def test_get_api_key_removed(self):
        """El método get_api_key ya no existe en la nueva configuración."""
        cfg = config_module.AppConfig(latitude=40.4168, longitude=-3.7038)
        assert not hasattr(cfg, "get_api_key")
