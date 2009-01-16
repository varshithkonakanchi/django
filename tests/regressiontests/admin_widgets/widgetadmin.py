"""

"""
from django.contrib import admin

import models

class WidgetAdmin(admin.AdminSite):
    pass


class CarTireAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "car":
            kwargs["queryset"] = models.Car.objects.filter(owner=request.user)
            return db_field.formfield(**kwargs)
        return super(CarTireAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

site = WidgetAdmin()

site.register(models.Car)
site.register(models.CarTire, CarTireAdmin)
