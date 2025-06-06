from django import template

register = template.Library()

@register.filter(name='status_color')
def status_color(status):
    color_map = {
        'pendente': 'warning',
        'aceito': 'success',
        'concluido': 'primary',
        'recusado': 'danger'
    }
    return color_map.get(status, 'secondary')

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key, 0)