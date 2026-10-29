#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

    # Enable remote debugging with debugpy when inside containers or configured
    if os.environ.get('ENABLE_DEBUGPY', 'False').lower() in ('true', '1') and 'runserver' in sys.argv:
        if os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv:
            try:
                import debugpy
                debugpy.listen(('0.0.0.0', 5678))
                sys.stdout.write("⚡ [debugpy] Remote debugger listening on port 5678 (ready for VS Code attach)\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"⚠️ [debugpy] Could not start debugpy: {e}\n")
                sys.stderr.flush()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
