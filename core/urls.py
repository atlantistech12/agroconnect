#urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    
    
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('pedido/<int:produto_id>/', views.fazer_pedido, name='fazer_pedido'),
    path('pedido/<int:pedido_id>/detalhes/', views.detalhes_pedido, name='detalhes_pedido'),
    path('pedidos/aceitar/<int:pedido_id>/', views.aceitar_pedido, name='aceitar_pedido'),
    path('pedidos/recusar/<int:pedido_id>/', views.recusar_pedido, name='recusar_pedido'),
    path('pedido/<int:pedido_id>/avaliar/', views.avaliar_fornecedor, name='avaliar_fornecedor'),
    path('pedidos-pendentes/', views.pedidos_pendentes, name='pedidos_pendentes'),
    path('aceitar-pedido/<int:pedido_id>/', views.aceitar_pedido, name='aceitar_pedido'),
    path('recusar-pedido/<int:pedido_id>/', views.recusar_pedido, name='recusar_pedido'),
    path('concluir_pedido/<int:pedido_id>/', views.concluir_pedido, name='concluir_pedido'),
    path('cancelar_pedido/<int:pedido_id>/', views.concluir_pedido, name='cancelar_pedido'),

    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('criar_produto/', views.criar_produto, name='criar_produto'),
    path('editar_produto/<int:produto_id>/', views.editar_produto, name='editar_produto'), 
    path('remover_produto/<int:produto_id>/', views.remover_produto, name='remover_produto'), 
    path('accounts/sign_up/', views.sign_up, name='sign_up'),
    path('accounts/profile/', views.profile_view, name='profile'),
    path('comprador/', views.dashboard, name='dashboard_comprador'),
    path('fornecedor/<int:fornecedor_id>/', views.perfil_fornecedor, name='perfil_fornecedor'),
    path('produtos/', views.listar_produtos, name='listar_produtos'),
    path('produto/<int:produto_id>/', views.detalhes_produto, name='detalhes_produto'),
    
    path('alterar-senha/', auth_views.PasswordChangeView.as_view(), name='password_change'),

    
]