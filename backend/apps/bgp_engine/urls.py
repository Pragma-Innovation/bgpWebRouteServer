from django.urls import path
from .views import bgp_status_view, bgp_neighbors_view, bgp_rib_view

urlpatterns = [
    path('status/', bgp_status_view, name='bgp-status'),
    path('neighbors/', bgp_neighbors_view, name='bgp-neighbors'),
    path('rib/', bgp_rib_view, name='bgp-rib'),
]
