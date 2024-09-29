from django.urls import path
from .views import fill_pdf_view

urlpatterns = [
    path('fill_pdf/', fill_pdf_view, name='fill_pdf'),
]
