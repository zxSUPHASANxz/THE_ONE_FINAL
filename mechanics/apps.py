from django.apps import AppConfig


class MechanicsConfig(AppConfig):
    name = 'mechanics'
    
    def ready(self):
        import mechanics.signals
