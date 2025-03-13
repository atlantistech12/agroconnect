#forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Perfil, Produto, Mensagem, Avaliacao, Pedido
from django.core.exceptions import ValidationError

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    tipo = forms.ChoiceField(
        choices=Perfil.TIPO_USUARIO,
        required=True,
        label='Tipo de Usuário'
    )
    telefone = forms.CharField(max_length=15, required=True)
    endereco = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'tipo', 'telefone', 'endereco', 'password1', 'password2')

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'quantidade']

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['telefone', 'endereco', 'tipo']
        widgets = {
            'endereco': forms.Textarea(attrs={'rows': 4}),
        }

class MensagemForm(forms.ModelForm):
    class Meta:
        model = Mensagem
        fields = ['conteudo']
        widgets = {
            'conteudo': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Escreva sua mensagem aqui...'
            })
        }


class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        fields = ['nota', 'comentario']
        widgets = {
            'nota': forms.RadioSelect(choices=Avaliacao.NOTA_CHOICES),
            'comentario': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Conte como foi sua experiência...'
            })
        }

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido  
        fields = ['quantidade']  
    quantidade = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        self.produto = kwargs.pop('produto', None)
        super().__init__(*args, **kwargs)
        if self.produto:
            self.fields['quantidade'].widget.attrs.update({
                'min': 1,
                'max': self.produto.quantidade,
                'class': 'form-control'
            })

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if self.produto and quantidade > self.produto.quantidade:
            raise ValidationError(
                f"Estoque insuficiente. Disponível: {self.produto.quantidade}"
            )
        return quantidade