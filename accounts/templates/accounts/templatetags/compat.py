from django import template
register = template.Library()

@register.filter
def length_is(value, arg):
    try:
        return len(value) == int(arg)
    except:
        return False
