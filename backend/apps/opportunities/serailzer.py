from rest_framework import serializers
from .models import Opportunity # Replace with your exact model name

class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = '__all__'
