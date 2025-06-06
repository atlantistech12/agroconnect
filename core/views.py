# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, Sum, F
from .models import Perfil, Produto, Pedido, Avaliacao, Categoria
from .forms import SignUpForm, ProdutoForm, PerfilForm, AvaliacaoForm, PedidoForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse_lazy


def home(request):
    return render(request, 'home.html')

def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST) # ou UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # perfil com os dados adicionais
            Perfil.objects.create(
                usuario=user,
                tipo=form.cleaned_data['tipo'],
                telefone=form.cleaned_data['telefone'],
                endereco=form.cleaned_data['endereco']
            )

            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm() # ou UserCreationForm()
    return render(request, 'registration/sign_up.html', {'form' : form})

@login_required
def dashboard(request):
    perfil = request.user.perfil
    hoje = timezone.now()

    if perfil.tipo == 'fornecedor':
        # Métricas Básicas
        total_produtos = Produto.objects.filter(fornecedor=perfil).count()
        pedidos_pendentes = Pedido.objects.filter(produto__fornecedor=perfil, status='pendente').count()
        pedidos_concluidos = Pedido.objects.filter(produto__fornecedor=perfil, status='concluido').count()
        receita_total = Pedido.objects.filter(produto__fornecedor=perfil).aggregate(total=Sum('valor_total'))
        
        # Gráfico de Vendas Mensais
        meses = []
        vendas_mensais = []
        for i in range(5, -1, -1):
            mes = hoje - timedelta(days=30*i)
            total = Pedido.objects.filter(
                produto__fornecedor=perfil,
                data_pedido__month=mes.month,
                data_pedido__year=mes.year
            ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            meses.append(mes.strftime("%b/%Y"))
            vendas_mensais.append(float(total))
        
        # Distribuição de Status
        status = Pedido.objects.filter(produto__fornecedor=perfil).values('status').annotate(
            total=Count('id'))
        status_labels = [s['status'].capitalize() for s in status]
        status_values = [s['total'] for s in status]
        
        # Dados para as tabelas
        context = {
            'total_produtos': total_produtos,
            'pedidos_pendentes': pedidos_pendentes,
            'pedidos_concluidos': pedidos_concluidos,
            'receita_total': receita_total.get('total', 0),
            'meses': meses,
            'vendas_mensais': vendas_mensais,
            'status_labels': status_labels,
            'status_values': status_values,
            'ultimos_pedidos': Pedido.objects.filter(
                produto__fornecedor=perfil
            ).select_related('comprador', 'produto').order_by('-data_pedido')[:5],
            'estoque_baixo': Produto.objects.filter(
                fornecedor=perfil, 
                quantidade__lt=10
            ).order_by('quantidade')[:5]
        }
        return render(request, 'fornecedor/dashboard_fornecedor.html', context)
    
    elif perfil.tipo == 'comprador':
        perfil = request.user.perfil
    
        # Produtos disponíveis (exclui os do próprio usuário se for fornecedor)
        produtos_disponiveis = Produto.objects.exclude(
            fornecedor=perfil
        ).filter(quantidade__gt=0).order_by('-data_criacao')[:8]
    
        # Pedidos recentes
        meus_pedidos = Pedido.objects.filter(
            comprador=perfil
        ).select_related('produto').order_by('-data_pedido')[:5]

        # Pedidos pendentes
        pedidos_pendentes = Pedido.objects.filter(
            comprador=request.user.perfil,
            status='pendente'
        ).count()
    
        context = {
            'produtos_disponiveis': produtos_disponiveis,
            'meus_pedidos': meus_pedidos,
            'pedidos_pendentes': pedidos_pendentes,
        }
        return render(request, 'comprador/dashboard_comprador.html', context)
    

#Produtos --------------------------------------------------------------------------------------------------------------
@login_required
def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
    
        if form.is_valid():
            produto = form.save(commit=False)
            produto.fornecedor = request.user.perfil
            produto.save()
            form.save_m2m()
            messages.success(request, 'Produto criado com sucesso!')
            return redirect('listar_produtos')
    else:
        form = ProdutoForm()

    categorias = Categoria.objects.all().order_by('nome')
    return render(request, 'fornecedor/produtos/criar_produto.html', {
        'form': form,
        'categorias': categorias
    })

def detalhes_produto(request, produto_id):
    perfil = request.user.perfil
    produto = get_object_or_404(Produto, id=produto_id)

    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/produtos/detalhes_produto.html', {'produto': produto})
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/produtos/detalhes_produto.html', {'produto': produto})

@login_required
def listar_produtos(request):
    perfil = request.user.perfil
    # Obter parâmetros de filtro
    search_query = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', None)
    
    # Filtrar produtos disponíveis
    produtos = Produto.objects.filter(quantidade__gt=0)
    
    # Aplicar filtros
    if search_query:
        produtos = produtos.filter(
            Q(nome__icontains=search_query) |
            Q(descricao__icontains=search_query)
        )
    
    if categoria_id:
        produtos = produtos.filter(categoria__id=categoria_id)
    
    # Obter categorias para o dropdown
    categorias = Categoria.objects.all().order_by('nome')

    
    context = {
        'produtos': produtos.order_by('-data_criacao'),
        'categorias': categorias,
        'search_query': search_query,
        'categoria_selecionada': int(categoria_id) if categoria_id else None
    }

    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/produtos/listar_produtos.html', context)
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/produtos/listar_produtos.html', context)

@login_required
def editar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, fornecedor=request.user.perfil)
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('listar_produtos')
        else:
            messages.error(request, 'Corrija os erros no formulário')
    else:
        form = ProdutoForm(instance=produto)
    
    return render(request, 'fornecedor/produtos/editar_produto.html', {
        'form': form,
        'produto': produto,
        'categorias': categorias
    })

@login_required
def remover_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, fornecedor=request.user.perfil)
    produto.delete()
    return redirect('dashboard')

#Pedidos --------------------------------------------------------------------------------------------------------------

@login_required
def listar_pedidos(request):
    perfil = request.user.perfil
    status_filter = request.GET.get('status', None)
    
    # Filtragem baseada no tipo de usuário
    if perfil.tipo == 'fornecedor':
        pedidos = Pedido.objects.filter(produto__fornecedor=perfil)
    elif perfil.tipo == 'comprador':
        pedidos = Pedido.objects.filter(comprador=perfil)
    else:
        pedidos = Pedido.objects.none()

    # Filtro adicional por status
    if status_filter and status_filter in dict(Pedido.STATUS_CHOICES):
        pedidos = pedidos.filter(status=status_filter)

    # Ordenação e otimização
    pedidos = pedidos.select_related('comprador', 'produto').order_by('-data_pedido')

    # Paginação
    paginator = Paginator(pedidos, 10)  # 10 itens por página
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Contagem de status para sidebar
    status_counts = {}
    for status_key, _ in Pedido.STATUS_CHOICES:
        status_counts[status_key] = Pedido.objects.filter(
        produto__fornecedor=perfil, 
        status=status_key
        ).count()

    template_path = f'{perfil.tipo}/pedido/listar_pedidos.html'
    
    return render(request, template_path, {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'status_choices': Pedido.STATUS_CHOICES,
    })

@login_required
def aceitar_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related('produto'),
        id=pedido_id,
        produto__fornecedor=request.user.perfil
    )
    
    if pedido.status == 'pendente':
        # Verificar estoque
        if pedido.produto.quantidade >= pedido.quantidade:
            # Atualizar estoque
            Produto.objects.filter(id=pedido.produto.id).update(
            quantidade=F('quantidade') - pedido.quantidade)
            
            # Atualizar status do pedido
            pedido.status = 'aceito'
            pedido.save()
            messages.success(request, 'Pedido aceito e estoque atualizado!')
        else:
            messages.error(request, 'Estoque insuficiente para aceitar o pedido!')
    else:
        messages.error(request, 'Este pedido já foi processado anteriormente.')
    
    return redirect('pedidos_pendentes')

@login_required
def fazer_pedido(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    
    if request.method == 'POST':
        form = PedidoForm(request.POST, produto=produto)
        if form.is_valid():
            # Crie o pedido manualmente
            pedido = form.save(commit=False)
            pedido.produto = produto
            pedido.comprador = request.user.perfil
            pedido.valor_total = produto.preco * pedido.quantidade
            pedido.save()
            return redirect('detalhes_pedido', pedido_id=pedido.id)
    else:
        form = PedidoForm(produto=produto)
    
    return render(request, 'comprador/pedido/fazer_pedido.html', {
        'form': form,
        'produto': produto
    })

@login_required
def detalhes_pedido(request, pedido_id):
    perfil = request.user.perfil
    try:
        pedido = get_object_or_404(
            Pedido.objects.select_related('produto__fornecedor', 'comprador'),
            id=pedido_id
        )
        
        # Verificar permissões
        if not (perfil == pedido.comprador or perfil == pedido.produto.fornecedor):
            raise Http404("Você não tem permissão para acessar este pedido.")
            
    except Pedido.DoesNotExist:
        raise Http404("Pedido não encontrado.")
    
    context = {'pedido': pedido}
    
    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/pedido/detalhes_pedido.html', context)
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/pedido/detalhes_pedido.html', context)

@login_required
def pedidos_pendentes(request):
    # Para fornecedores verem seus pedidos pendentes
    pedidos = Pedido.objects.filter(
        produto__fornecedor=request.user.perfil,
        status='pendente'
    ).select_related('comprador__usuario', 'produto')

    return render(request, 'fornecedor/pedido/pedidos_pendentes.html', {'pedidos' : pedidos})

@login_required
def recusar_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related('produto'),
        id=pedido_id,
        produto__fornecedor=request.user.perfil
    )
    
    if pedido.status == 'pendente':
        pedido.status = 'recusado'
        pedido.save()
        messages.success(request, 'Pedido recusado com sucesso!')
    else:
        messages.warning(request, 'Este pedido já foi processado!')
    
    return redirect('pedidos_pendentes')

@login_required
def concluir_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    perfil = request.user.perfil

    if perfil.tipo != 'fornecedor' or pedido.produto.fornecedor != perfil:
        messages.error(request, "Você não tem permissão para concluir este pedido.")
        return redirect('listar_pedidos')

    if request.method == 'POST' and pedido.status == 'aceito':
        pedido.status = 'concluido'
        pedido.save()
        messages.success(request, f"Pedido #{pedido.id} concluído com sucesso.")
    else:
        messages.error(request, "Este pedido não pode ser concluído.")

    return redirect('detalhes_pedido', pedido_id=pedido.id)

@login_required
def cancelar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    perfil = request.user.perfil

    if perfil.tipo != 'comprador' or pedido.comprador != perfil:
        messages.error(request, "Você não tem permissão para cancelar este pedido.")
        return redirect('listar_pedidos')

    if request.method == 'POST' and pedido.status == 'pendente':
        pedido.status = 'cancelado'
        pedido.save()
        messages.success(request, f"Pedido #{pedido.id} cancelado com sucesso.")
    else:
        messages.error(request, "Este pedido não pode ser cancelado.")

    return redirect('listar_pedidos')

# Outras Config -------------------------------------------------------------------------------------

@login_required
def relatorios(request):
    perfil = request.user.perfil
    hoje = timezone.now()
    
    # Métricas Principais
    total_produtos = Produto.objects.filter(fornecedor=perfil).count()
    pedidos_concluidos = Pedido.objects.filter(produto__fornecedor=perfil, status='concluido').count()
    receita_total = Pedido.objects.filter(produto__fornecedor=perfil).aggregate(
        total=Sum('valor_total')
    )['total'] or 0
    
    # Dados para Gráficos
    meses = []
    receita_mensal = []
    pedidos_mensais = []
    for i in range(5, -1, -1):
        mes = hoje - timedelta(days=30*i)
        periodo = Pedido.objects.filter(
            produto__fornecedor=perfil,
            data_pedido__month=mes.month,
            data_pedido__year=mes.year
        )
        meses.append(mes.strftime("%b/%Y"))
        receita_mensal.append(float(periodo.aggregate(Sum('valor_total'))['valor_total__sum'] or 0))
        pedidos_mensais.append(periodo.count())
    
    # Categorias
    categorias = Categoria.objects.annotate(
        total_vendas=Count('produto__pedidos'),
        receita_total=Sum('produto__pedidos__valor_total')
    ).filter(produto__fornecedor=perfil)
    
    # Top Produtos
    top_produtos = Produto.objects.filter(fornecedor=perfil).annotate(
        total_vendas=Count('pedidos'),
        receita_total=Sum('pedidos__valor_total')
    ).order_by('-receita_total')[:5]
    
    context = {
        'total_produtos': total_produtos,
        'pedidos_concluidos': pedidos_concluidos,
        'receita_total': receita_total,
        'ticket_medio': (receita_total / pedidos_concluidos) if pedidos_concluidos > 0 else 0,
        'meses': meses,
        'receita_mensal': receita_mensal,
        'pedidos_mensais': pedidos_mensais,
        'categorias_labels': [c.nome for c in categorias],
        'categorias_values': [float(c.receita_total or 0) for c in categorias],
        'top_produtos': top_produtos,
        'ultimas_transacoes': Pedido.objects.filter(
            produto__fornecedor=perfil
        ).select_related('comprador').order_by('-data_pedido')[:10],
        'produtos_estoque_baixo': Produto.objects.filter(
        fornecedor=perfil,
        quantidade__lt=F('estoque_minimo')
    ).count()
    }
    return render(request, 'fornecedor/relatorios.html', context)

@login_required
def profile_view(request):
    return render(request, 'registration/profile.html')

@login_required
def perfil_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Perfil, id=fornecedor_id, tipo='fornecedor')
    context = {
        'fornecedor': fornecedor,
        'produtos': Produto.objects.filter(fornecedor=fornecedor),
        'avaliacoes': Avaliacao.objects.filter(fornecedor=fornecedor),
        'total_produtos': Produto.objects.filter(fornecedor=fornecedor).count(),
        'total_vendas': Pedido.objects.filter(produto__fornecedor=fornecedor, status='concluido').count(),
        'media_avaliacoes': Avaliacao.objects.filter(fornecedor=fornecedor).aggregate(Avg('nota'))['nota__avg']
    }
    return render(request, 'fornecedor/perfil.html', context)

@login_required
def configuracoes(request):
    perfil = request.user.perfil
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('configuracoes')
    else:
        form = PerfilForm(instance=perfil)
    
    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/configuracoes.html', {
        'form': form
    })
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/configuracoes.html', {
        'form': form
    })

@login_required
def avaliar_fornecedor(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, comprador=request.user.perfil)
    
    if request.method == 'POST':
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.pedido = pedido
            avaliacao.avaliador = request.user.perfil
            avaliacao.fornecedor = pedido.produto.fornecedor
            avaliacao.save()
            return redirect('detalhes_pedido', pedido_id=pedido.id)
    else:
        form = AvaliacaoForm()
    
    return render(request, 'avaliar_fornecedor.html', {
        'form': form,
        'pedido': pedido
    })

@login_required
def relatorio_financeiro(request):
    pass
