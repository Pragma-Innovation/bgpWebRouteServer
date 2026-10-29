from django.apps import AppConfig


class PeersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.peers'
    verbose_name = 'BGP Peers'
