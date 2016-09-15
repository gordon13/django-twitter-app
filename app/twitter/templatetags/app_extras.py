from django import template

register = template.Library()

"""
Custom filters
"""
@register.filter
def to_char(value):
	return chr(64+value)
    #return chr(98-value)