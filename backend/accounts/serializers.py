from rest_framework import serializers
from django.contrib.auth.models import User
from tickets.models import Agent, Customer, Organization

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['customer', 'agent'], write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role')
    
    def create(self, validated_data):
        role = validated_data.pop('role')
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Get or create default organization (QuickCart)
        org, _ = Organization.objects.get_or_create(name="QuickCart")
        
        # Create agent or customer based on role
        if role == 'agent':
            Agent.objects.create(
                user=user,
                organization=org,
                department='general'
            )
        else:
            Customer.objects.create(
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                email=user.email,
                organization=org
            )
        
        return user