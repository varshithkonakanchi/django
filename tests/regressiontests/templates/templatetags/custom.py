from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

def trim(value, num):
    return value[:num]
trim = stringfilter(trim)

register.filter(trim)

@register.simple_tag
def no_params():
    """Expected no_params __doc__"""
    return "no_params - Expected result"
no_params.anything = "Expected no_params __dict__"

@register.simple_tag
def one_param(arg):
    """Expected one_param __doc__"""
    return "one_param - Expected result: %s" % arg
one_param.anything = "Expected one_param __dict__"

@register.simple_tag(takes_context=False)
def explicit_no_context(arg):
    """Expected explicit_no_context __doc__"""
    return "explicit_no_context - Expected result: %s" % arg
explicit_no_context.anything = "Expected explicit_no_context __dict__"

@register.simple_tag(takes_context=True)
def no_params_with_context(context):
    """Expected no_params_with_context __doc__"""
    return "no_params_with_context - Expected result (context value: %s)" % context['value']
no_params_with_context.anything = "Expected no_params_with_context __dict__"

@register.simple_tag(takes_context=True)
def params_and_context(context, arg):
    """Expected params_and_context __doc__"""
    return "params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)
params_and_context.anything = "Expected params_and_context __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_no_params():
    """Expected inclusion_no_params __doc__"""
    return {"result" : "inclusion_no_params - Expected result"}
inclusion_no_params.anything = "Expected inclusion_no_params __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_one_param(arg):
    """Expected inclusion_one_param __doc__"""
    return {"result" : "inclusion_one_param - Expected result: %s" % arg}
inclusion_one_param.anything = "Expected inclusion_one_param __dict__"

@register.inclusion_tag('inclusion.html', takes_context=False)
def inclusion_explicit_no_context(arg):
    """Expected inclusion_explicit_no_context __doc__"""
    return {"result" : "inclusion_explicit_no_context - Expected result: %s" % arg}
inclusion_explicit_no_context.anything = "Expected inclusion_explicit_no_context __dict__"

@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_no_params_with_context(context):
    """Expected inclusion_no_params_with_context __doc__"""
    return {"result" : "inclusion_no_params_with_context - Expected result (context value: %s)" % context['value']}
inclusion_no_params_with_context.anything = "Expected inclusion_no_params_with_context __dict__"

@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_params_and_context(context, arg):
    """Expected inclusion_params_and_context __doc__"""
    return {"result" : "inclusion_params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)}
inclusion_params_and_context.anything = "Expected inclusion_params_and_context __dict__"

@register.simple_tag(takes_context=True)
def current_app(context):
    return "%s" % context.current_app

@register.inclusion_tag('test_incl_tag_current_app.html', takes_context=True)
def inclusion_tag_current_app(context):
    return {}

@register.simple_tag(takes_context=True)
def use_l10n(context):
    return "%s" % context.use_l10n

@register.inclusion_tag('test_incl_tag_use_l10n.html', takes_context=True)
def inclusion_tag_use_l10n(context):
    return {}

@register.assignment_tag
def assignment_no_params():
    """Expected assignment_no_params __doc__"""
    return "assignment_no_params - Expected result"
assignment_no_params.anything = "Expected assignment_no_params __dict__"

@register.assignment_tag
def assignment_one_param(arg):
    """Expected assignment_one_param __doc__"""
    return "assignment_one_param - Expected result: %s" % arg
assignment_one_param.anything = "Expected assignment_one_param __dict__"

@register.assignment_tag(takes_context=False)
def assignment_explicit_no_context(arg):
    """Expected assignment_explicit_no_context __doc__"""
    return "assignment_explicit_no_context - Expected result: %s" % arg
assignment_explicit_no_context.anything = "Expected assignment_explicit_no_context __dict__"

@register.assignment_tag(takes_context=True)
def assignment_no_params_with_context(context):
    """Expected assignment_no_params_with_context __doc__"""
    return "assignment_no_params_with_context - Expected result (context value: %s)" % context['value']
assignment_no_params_with_context.anything = "Expected assignment_no_params_with_context __dict__"

@register.assignment_tag(takes_context=True)
def assignment_params_and_context(context, arg):
    """Expected assignment_params_and_context __doc__"""
    return "assignment_params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)
assignment_params_and_context.anything = "Expected assignment_params_and_context __dict__"

register.simple_tag(lambda x: x - 1, name='minusone')

@register.simple_tag(name='minustwo')
def minustwo_overridden_name(value):
    return value - 2
