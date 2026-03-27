from django.urls import path
from . import views

urlpatterns = [
    # Acesso e Segurança
    path('direcionar/', views.direcionar_usuario, name='direcionar_usuario'),
    path('primeiro-acesso/', views.primeiro_acesso, name='primeiro_acesso'),
    path('', views.index, name='index'),
    
    # Operacional e Transferências
    path('transferencia/processar/', views.processar_transferencia, name='processar_transferencia'),
    path('servidores/', views.lista_servidores, name='lista_servidores'),
    path('servidores/novo/', views.criar_servidor, name='criar_servidor'),
    path('servidores/editar/<int:id>/', views.editar_servidor, name='editar_servidor'),
    path('unidades/', views.lista_unidades, name='lista_unidades'),
    path('unidades/nova/', views.criar_unidade, name='criar_unidade'),
    path('alvo/deletar/<str:tipo>/<int:id>/', views.deletar_alvo, name='deletar_alvo'),
    path('carga-em-lote/', views.carga_em_lote, name='carga_em_lote'),

    # Gestão de Efetivo (Admin)
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/novo/', views.criar_usuario, name='criar_usuario'),
    path('usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/deletar/<int:id>/', views.deletar_usuario, name='deletar_usuario'),

    # --- A SOLUÇÃO: ROTAS DA VERSÃO 1.1 ---
    path('limpar-varredura/', views.limpar_varredura, name='limpar_varredura'),
    path('estatisticas/', views.estatisticas, name='estatisticas'),
]