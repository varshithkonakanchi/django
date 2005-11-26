# Custom tag library used in conjunction with template tests

from django.core import template

register = template.Library()

class EchoNode(template.Node):
    def __init__(self, contents):
        self.contents = contents
        
    def render(self, context):
        return " ".join(self.contents)
        
def do_echo(parser, token):
    return EchoNode(token.contents.split()[1:])

register.tag("echo", do_echo)