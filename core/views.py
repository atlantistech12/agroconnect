# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, Sum, F
from .models import Perfil, Produto, Pedido, Transporte, Mensagem, Avaliacao, Categoria
from .forms import SignUpForm, ProdutoForm, PerfilForm, MensagemForm, AvaliacaoForm, PedidoForm
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta



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
        pedidos_concluidos = Pedido.objects.filter(produto__fornecedor=perfil, status='entregue').count()
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

        # Mensagens nao lidas
        mensagens_nao_lidas = Mensagem.objects.filter(
            destinatario=request.user.perfil,
            lida=False
        ).count()
    
        context = {
            'produtos_disponiveis': produtos_disponiveis,
            'meus_pedidos': meus_pedidos,
            'pedidos_pendentes': pedidos_pendentes,
            'mensagens_nao_lidas':mensagens_nao_lidas
        }
        return render(request, 'comprador/dashboard_comprador.html', context)
    
    elif perfil.tipo == 'transportador':
        transportes = Transporte.objects.filter(transportador=perfil)
        return render(request, 'dashboard_transportador.html', {'transportes': transportes})

#Produtos --------------------------------------------------------------------------------------------------------------
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
    categorias = Categoria.objects.all()
    return render(request, 'fornecedor/produtos/criar_produto.html', {'categorias': categorias})

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
    categorias = Categoria.objects.all()
    
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
    
    if request.method == 'POST':
        # Atualiza os dados do produto
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
        return redirect('dashboard')
    
    else:
        form  = ProdutoForm(instance=produto) 
    
    return render(request, 'fornecedor/produtos/editar_produto.html', {'produto': produto})

@login_required
def remover_produto(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, fornecedor=request.user.perfil)
    produto.delete()
    return redirect('dashboard')

#Pedidos --------------------------------------------------------------------------------------------------------------

@login_required
def listar_pedidos(request):
    perfil = request.user.perfil
    # Filtra pedidos dos produtos do fornecedor logado
    pedidos = Pedido.objects.filter(
        produto__fornecedor=request.user.perfil
    ).select_related('comprador', 'produto').order_by('-data_pedido')

    # Paginação
    paginator = Paginator(pedidos, 10)  # 10 pedidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/pedido/listar_pedidos.html', {
        'pedidos': pedidos
    })
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/pedido/listar_pedidos.html', {
        'pedidos': pedidos
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
def meus_pedidos(request):
    perfil = request.user.perfil
    
    # Filtra os pedidos do comprador logado
    pedidos = Pedido.objects.filter(
        comprador=perfil
    ).select_related('produto', 'produto__fornecedor').order_by('-data_pedido')
    
    # Filtro por status
    status = request.GET.get('status')
    if status in dict(Pedido.STATUS_CHOICES).keys():
        pedidos = pedidos.filter(status=status)
    
    # Paginação (10 itens por página)
    paginator = Paginator(pedidos, 10)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'selected_status': status,
        'status_choices': Pedido.STATUS_CHOICES
    }
    
    if perfil.tipo == 'fornecedor':
        return render(request, 'fornecedor/pedido/meus_pedidos.html', context)
    
    elif perfil.tipo == 'comprador':
        return render(request, 'comprador/pedido/meus_pedidos.html', context)

# Conversa ----------------------------------------------------------------------------------------

@login_required
def mensagens(request):
    perfil_usuario = request.user.perfil
    
    # Obter todas as conversas
    conversas = Mensagem.objects.filter(
        Q(remetente=perfil_usuario) | Q(destinatario=perfil_usuario)
    ).values('remetente', 'destinatario').distinct()
    
    threads = []
    for conversa in conversas:
        rem_id = conversa['remetente']
        dest_id = conversa['destinatario']
        
        # Determinar o outro usuário da conversa
        if rem_id == perfil_usuario.id:
            outro_usuario_id = dest_id
        else:
            outro_usuario_id = rem_id
            
        try:
            outro_usuario = Perfil.objects.get(id=outro_usuario_id)
            ultima_msg = Mensagem.objects.filter(
                Q(remetente=perfil_usuario, destinatario=outro_usuario) |
                Q(remetente=outro_usuario, destinatario=perfil_usuario)
            ).latest('data_envio')
            
            threads.append({
                'user': outro_usuario,
                'ultima_msg': ultima_msg,
                'nao_lidas': Mensagem.objects.filter(
                    destinatario=perfil_usuario,
                    remetente=outro_usuario,
                    lida=False
                ).count()
            })
            
        except (Perfil.DoesNotExist, Mensagem.DoesNotExist):
            continue
    
    context = {
        'threads': sorted(threads, key=lambda x: x['ultima_msg'].data_envio, reverse=True),
        'todos_usuarios': Perfil.objects.exclude(id=perfil_usuario.id)
    }

    if perfil_usuario.tipo == 'fornecedor':
        return render(request, 'fornecedor/conversas/mensagens.html', context)
    
    elif perfil_usuario.tipo == 'comprador':
        return render(request, 'comprador/conversas/mensagens.html', context)

@login_required
def nova_mensagem(request):
    if request.method == 'POST':
        destinatario_id = request.POST.get('destinatario')
        conteudo = request.POST.get('conteudo', '').strip()
        
        # Validação básica
        if not conteudo:
            messages.error(request, "O conteúdo da mensagem não pode estar vazio.")
            return redirect('mensagens')
            
        try:
            destinatario = Perfil.objects.get(id=destinatario_id)
        except Perfil.DoesNotExist:
            messages.error(request, "Destinatário inválido.")
            return redirect('mensagens')
            
        if destinatario == request.user.perfil:
            messages.error(request, "Você não pode enviar mensagens para si mesmo.")
            return redirect('mensagens')
            
        # Criar a mensagem
        Mensagem.objects.create(
            remetente=request.user.perfil,
            destinatario=destinatario,
            conteudo=conteudo
        )
        
        messages.success(request, "Mensagem enviada com sucesso!")
        return redirect('detalhes_conversa', usuario_id=destinatario.id)
    
    return redirect('mensagens')

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
def detalhes_conversa(request, usuario_id):
    perfil_usuario = request.user.perfil
    outro_usuario = get_object_or_404(Perfil, id=usuario_id)
    
    # Marcar mensagens como lidas
    Mensagem.objects.filter(
        destinatario=perfil_usuario,
        remetente=outro_usuario,
        lida=False
    ).update(lida=True)
    
    if request.method == 'POST':
        form = MensagemForm(request.POST)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.remetente = perfil_usuario
            mensagem.destinatario = outro_usuario
            mensagem.save()
            return redirect('detalhes_conversa', usuario_id=usuario_id)
    else:
        form = MensagemForm()
    
    mensagens = Mensagem.objects.filter(
        Q(remetente=perfil_usuario, destinatario=outro_usuario) |
        Q(remetente=outro_usuario, destinatario=perfil_usuario)
    ).order_by('data_envio')
    
    context = {
        'outro_usuario': outro_usuario,
        'mensagens': mensagens,
        'form': form
    }
    if perfil_usuario.tipo == 'fornecedor':
        return render(request, 'fornecedor/conversas/detalhes_conversa.html', context)
    
    elif perfil_usuario.tipo == 'comprador':
        return render(request, 'comprador/conversas/detalhes_conversa.html', context)

# Outras Config -------------------------------------------------------------------------------------

@login_required
def relatorios(request):
    perfil = request.user.perfil
    hoje = timezone.now()
    
    # Métricas Principais
    total_produtos = Produto.objects.filter(fornecedor=perfil).count()
    pedidos_concluidos = Pedido.objects.filter(produto__fornecedor=perfil, status='entregue').count()
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
        'ticket_medio': receita_total / pedidos_concluidos if pedidos_concluidos else 0,
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
    avaliacoes = Avaliacao.objects.filter(fornecedor=fornecedor)
    media_avaliacoes = fornecedor.avaliacoes_recebidas.aggregate(Avg('nota'))['nota__avg']
    
    context = {
        'fornecedor': fornecedor,
        'avaliacoes': avaliacoes,
        'rating_medio': avaliacoes.aggregate(Avg('nota'))['nota__avg'] or 0
    }
    return render(request, 'perfil_fornecedor.html', context)

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