import pathlib

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from django.core.cache.backends.filebased import FileBasedCache

from . import Error, Tags, Warning, register

E001 = Error(
    "You must define a '%s' cache in your CACHES setting." % DEFAULT_CACHE_ALIAS,
    id='caches.E001',
)


@register(Tags.caches)
def check_default_cache_is_configured(app_configs, **kwargs):
    if DEFAULT_CACHE_ALIAS not in settings.CACHES:
        return [E001]
    return []


@register(Tags.caches, deploy=True)
def check_cache_location_not_exposed(app_configs, **kwargs):
    errors = []
    for name in ('MEDIA_ROOT', 'STATIC_ROOT', 'STATICFILES_DIRS'):
        setting = getattr(settings, name, None)
        if not setting:
            continue
        if name == 'STATICFILES_DIRS':
            paths = {
                pathlib.Path(staticfiles_dir).resolve()
                for staticfiles_dir in setting
            }
        else:
            paths = {pathlib.Path(setting).resolve()}
        for alias in settings.CACHES:
            cache = caches[alias]
            if not isinstance(cache, FileBasedCache):
                continue
            cache_path = pathlib.Path(cache._dir).resolve()
            if any(path == cache_path for path in paths):
                relation = 'matches'
            elif any(path in cache_path.parents for path in paths):
                relation = 'is inside'
            elif any(cache_path in path.parents for path in paths):
                relation = 'contains'
            else:
                continue
            errors.append(Warning(
                f"Your '{alias}' cache configuration might expose your cache "
                f"or lead to corruption of your data because its LOCATION "
                f"{relation} {name}.",
                id='caches.W002',
            ))
    return errors
