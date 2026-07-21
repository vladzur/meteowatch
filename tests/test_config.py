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
                assert cfg.api_key == ""
                assert cfg.location_hash == ""
                assert cfg.location_name == ""

    def test_load_existing_config(self):
        """Debe cargar correctamente una configuración existente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            data = {
                "api_key": "test-key-123",
                "location_hash": "abc123hash",
                "location_name": "Madrid",
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.api_key == "test-key-123"
                assert cfg.location_hash == "abc123hash"
                assert cfg.location_name == "Madrid"

    def test_save_creates_directory_and_file(self):
        """Debe crear el directorio y archivo de configuración al guardar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "meteowatch")
            config_path = os.path.join(config_dir, "config.json")

            with patch.object(config_module, "CONFIG_DIR", config_dir):
                with patch.object(config_module, "CONFIG_FILE", config_path):
                    cfg = config_module.AppConfig(
                        api_key="my-key",
                        location_hash="hash123",
                        location_name="Barcelona",
                    )
                    cfg.save()

                    assert os.path.exists(config_path)

                    with open(config_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)

                    assert saved["api_key"] == "my-key"
                    assert saved["location_hash"] == "hash123"
                    assert saved["location_name"] == "Barcelona"

    def test_is_configured_returns_false_when_empty(self):
        """Debe retornar False si no hay API key ni ubicación."""
        cfg = config_module.AppConfig()
        assert not cfg.is_configured()

    def test_is_configured_returns_false_when_missing_hash(self):
        """Debe retornar False si falta el hash de ubicación."""
        cfg = config_module.AppConfig(api_key="key123")
        assert not cfg.is_configured()

    def test_is_configured_returns_true_when_complete(self):
        """Debe retornar True si API key y ubicación están configuradas."""
        cfg = config_module.AppConfig(
            api_key="key123",
            location_hash="hash456",
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
                    cfg = config_module.AppConfig(api_key="key123")
                    cfg.set_location("newhash", "Valencia")

                    assert cfg.location_hash == "newhash"
                    assert cfg.location_name == "Valencia"

                    # Verificar que se persistió
                    with open(config_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    assert saved["location_hash"] == "newhash"
                    assert saved["location_name"] == "Valencia"

    def test_load_corrupted_json_returns_empty_config(self):
        """Debe retornar configuración vacía si el JSON está corrupto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("esto no es json{")

            with patch.object(config_module, "CONFIG_FILE", config_path):
                cfg = config_module.AppConfig.load()
                assert cfg.api_key == ""
                assert cfg.location_hash == ""

    def test_get_api_key(self):
        """Debe retornar la API key configurada."""
        cfg = config_module.AppConfig(api_key="my-secret-key")
        assert cfg.get_api_key() == "my-secret-key"
