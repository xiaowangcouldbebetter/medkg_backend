from django.urls import path
from . import views

urlpatterns = [
    path('graph/', views.get_graph_data, name='get_graph_data'),
    path('entity/search/', views.entity_search, name='entity_search'),
    path('entity/relations/', views.entity_relations, name='entity_relations'),
    path('disease/info/', views.disease_info, name='disease_info'),
    path('disease/similar/', views.similar_diseases, name='similar_diseases'),
    path('entity/types/', views.entity_types, name='entity_types'),
    path('relation/types/', views.relation_types, name='relation_types'),
    path('entity/statistics/', views.entity_statistics, name='entity_statistics'),
] 