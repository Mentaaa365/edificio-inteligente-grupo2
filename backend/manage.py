#!/usr/bin/env python
"""Herramienta de línea de comandos de Django (runserver, migrate, test, simular_esp32...)."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edificio.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
