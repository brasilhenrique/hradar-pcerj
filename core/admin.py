from django.contrib import admin
from .models import PerfilAgente, ServidorMonitorado, OrgaoMonitorado, RegraClassificacao, TermoMonitorado

admin.site.register(PerfilAgente)
admin.site.register(ServidorMonitorado)
admin.site.register(OrgaoMonitorado)
admin.site.register(RegraClassificacao)
admin.site.register(TermoMonitorado)