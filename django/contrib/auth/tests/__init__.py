from django.contrib.auth.tests.basic import BASIC_TESTS
from django.contrib.auth.tests.views \
        import PasswordResetTest, ChangePasswordTest, LoginTest, LogoutTest
from django.contrib.auth.tests.forms import FORM_TESTS
from django.contrib.auth.tests.remote_user \
        import RemoteUserTest, RemoteUserNoCreateTest, RemoteUserCustomTest
from django.contrib.auth.tests.tokens import TOKEN_GENERATOR_TESTS

# The password for the fixture data users is 'password'

__test__ = {
    'BASIC_TESTS': BASIC_TESTS,
    'PASSWORDRESET_TESTS': PasswordResetTest,
    'FORM_TESTS': FORM_TESTS,
    'TOKEN_GENERATOR_TESTS': TOKEN_GENERATOR_TESTS,
    'CHANGEPASSWORD_TESTS': ChangePasswordTest,
    'LOGIN_TESTS': LoginTest,
    'LOGOUT_TESTS': LogoutTest,
}
