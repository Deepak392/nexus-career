from django.shortcuts import render

# backend/apps/opportunities/views.py
from rest_framework import viewsets
from .models import Opportunity
from .serializers import OpportunitySerializer

class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
# Create your views here.
