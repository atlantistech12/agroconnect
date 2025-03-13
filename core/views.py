# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from .models import Perfil, Produto, Pedido, Transporte, Mensagem, Avaliacao, Categoria
from .forms import SignUpForm, ProdutoForm, PerfilForm, MensagemForm, AvaliacaoForm, PedidoForm
from django.contrib import messages




def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    perfil = request.user.perfil
    if perfil.tipo == 'fornecedor':
        produtos = Produto.objects.filter(fornecedor=perfil)
        return render(request, 'dashboard_fornecedor.html', {'produtos': produtos})
    elif perfil.tipo == 'comprador':
        # Obter produtos de TODOS fornecedores (exceto o próprio usuário se for fornecedor)
        produtos_disponiveis = Produto.objects.exclude(fornecedor=request.user.perfil)
        
        # Obter pedidos do comprador logado
        meus_pedidos = Pedido.objects.filter(comprador=request.user.perfil)
        
        context = {
            'produtos_disponiveis': produtos_disponiveis,
            'meus_pedidos': meus_pedidos
        }
        return render(request, 'dashboard_comprador.html', context)
    elif perfil.tipo == 'transportador':
        transportes = Transporte.objects.filter(transportador=perfil)
        return render(request, 'dashboard_transportador.html', {'transportes': transportes})



@login_required
def criar_produto(request):
    if request.method == 'POST':
        nome = request.POST['nome']
        descricao = request.POST['descricao']
        preco = request.POST['preco']
        quantidade = request.POST['quantidade']
        produto = Produto(fornecedor=request.user.perfil, nome=nome, descricao=descricao, preco=preco, quantidade=quantidade)
        produto.save()
        return redirect('dashboard')
    return render(request, 'criar_produto.html')

def detalhes_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    return render(request, 'produtos/detalhes_produto.html', {'produto': produto})


@login_required
def listar_produtos(request):
    # Obter parâmetros de filtro
    search_query = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', None)
    
    # Filtrar produtos disponíveis
    produtos = Produto.objects.filter(quantidade__gt=0)
    
    # Aplicar filtros
    if search_query:
        produtos = produtos.filter(
            models.Q(nome__icontains=search_query) |
            models.Q(descricao__icontains=search_query)
        )
    
    if categoria_id:
        produtos = produtos.filter(categoria__id=categoria_id)
    
    # Obter categorias para o dropdown
    categorias = Categoria.objects.all()
    
    context = {
        'produtos': produtos.order_by('-data_criacao'),
        'categorias': categorias,
        'search_query': search_query,
        'categoria_selecionada': int(categoria_id) if categoria_id else None
    }
    
    return render(request, 'produtos/listar_produtos.html', context)

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
def profile_view(request):
    return render(request, 'registration/profile.html')

@login_required
def editar_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, fornecedor=request.user.perfil)
    
    if request.method == 'POST':
        # Atualiza os dados do produto
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
        return redirect('dashboard')
    
    else:
        form  = ProdutoForm(instance=produto) 
    
    return render(request, 'editar_produto.html', {'produto': produto})

@login_required
def remover_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, fornecedor=request.user.perfil)
    produto.delete()
    return redirect('dashboard')


@login_required
def listar_pedidos(request):
    # Filtra pedidos dos produtos do fornecedor logado
    pedidos = Pedido.objects.filter(
        produto__fornecedor=request.user.perfil
    ).select_related('comprador', 'produto')
    
    return render(request, 'listar_pedidos.html', {
        'pedidos': pedidos
    })

@login_required
def relatorios(request):
    perfil = request.user.perfil
    
    # Estatísticas básicas
    total_produtos = Produto.objects.filter(fornecedor=perfil).count()
    total_pedidos = Pedido.objects.filter(produto__fornecedor=perfil).count()
    pedidos_ativos = Pedido.objects.filter(
        produto__fornecedor=perfil,
        status='pendente'
    ).count()
    
    # Dados para gráficos (exemplo simples)
    vendas_por_produto = Pedido.objects.filter(
        produto__fornecedor=perfil
    ).values('produto__nome').annotate(total=Count('id'))
    
    return render(request, 'relatorios.html', {
        'total_produtos': total_produtos,
        'total_pedidos': total_pedidos,
        'pedidos_ativos': pedidos_ativos,
        'vendas_por_produto': list(vendas_por_produto)
    })

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
    
    return render(request, 'configuracoes.html', {
        'form': form
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
            pedido.produto.quantidade -= pedido.quantidade
            pedido.produto.save()
            
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
def recusar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, produto__fornecedor=request.user.perfil)
    
    if pedido.status == 'pendente':
        pedido.status = 'recusado'
        pedido.save()
        messages.success(request, 'Pedido recusado com sucesso!')
    else:
        messages.error(request, 'Este pedido já foi processado.')
    
    return redirect('listar_pedidos')

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
    
    return render(request, 'pedidos/fazer_pedido.html', {
        'form': form,
        'produto': produto
    })

@login_required
def detalhes_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related('produto', 'comprador'),
        id=pedido_id,
        comprador=request.user.perfil
    )
    return render(request, 'pedidos/detalhes_pedido.html', {'pedido': pedido})

@login_required
def perfil_fornecedor(request, fornecedor_id):
    fornecedor = get_object_or_404(Perfil, id=fornecedor_id, tipo='fornecedor')
    avaliacoes = Avaliacao.objects.filter(fornecedor=fornecedor)
    media_avaliacoes = fornecedor.avaliacoes_recebidas.aggregate(Avg('nota'))['nota__avg']
    
    context = {
        'fornecedor': fornecedor,
        'avaliacoes': avaliacoes,
        'rating_medio': avaliacoes.aggregate(Avg('nota'))['nota__avg'] or 0
    }
    return render(request, 'perfil_fornecedor.html', context)

@login_required
def enviar_mensagem(request, fornecedor_id):
    fornecedor = get_object_or_404(Perfil, id=fornecedor_id, tipo='fornecedor')
    if request.method == 'POST':
        form = MensagemForm(request.POST)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.remetente = request.user.perfil
            mensagem.destinatario = fornecedor
            mensagem.save()
            return redirect('detalhes_conversa', fornecedor_id=fornecedor_id)
        else:
            form = MensagemForm()
    return render(request, 'enviar_mensagem.html', {'form':form, 'fornecedor': fornecedor})

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
def detalhes_conversa(request, fornecedor_id):
    # Obter o perfil do fornecedor
    fornecedor = get_object_or_404(Perfil, id=fornecedor_id, tipo='fornecedor')
    
    # Obter todas as mensagens da conversa
    conversa = Mensagem.objects.filter(
        (models.Q(remetente=request.user.perfil) & models.Q(destinatario=fornecedor)) |
        (models.Q(remetente=fornecedor) & models.Q(destinatario=request.user.perfil))
    ).order_by('data_envio')
    
    # Marcar mensagens como lidas
    conversa.filter(destinatario=request.user.perfil).update(lida=True)
    
    if request.method == 'POST':
        form = MensagemForm(request.POST)
        if form.is_valid():
            nova_mensagem = form.save(commit=False)
            nova_mensagem.remetente = request.user.perfil
            nova_mensagem.destinatario = fornecedor
            nova_mensagem.save()
            return redirect('detalhes_conversa', fornecedor_id=fornecedor_id)
    else:
        form = MensagemForm()
    
    return render(request, 'conversas/detalhes_conversa.html', {
        'conversa': conversa,
        'fornecedor': fornecedor,
        'form': form
    })

@login_required
def pedidos_pendentes(request):
    # Para fornecedores verem seus pedidos pendentes
    pedidos = Pedido.objects.filter(
        produto__fornecedor=request.user.perfil,
        status='pendente'
    ).select_related('comprador__usuario', 'produto')

    return render(request, 'fornecedor/pedidos_pendentes.html', {'pedidos' : pedidos})

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