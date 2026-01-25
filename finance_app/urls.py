"""
URL configuration for finance_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
import os

def service_worker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'core/static/core/js/sw.js')
    with open(sw_path, 'r') as f:
        return HttpResponse(f.read(), content_type='application/javascript')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),           
    path('transactions/', include('core.urls')),  
    path('sw.js', service_worker, name='sw'),
]
