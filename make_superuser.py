#!/usr/bin/env python
"""
Script to make an existing user a superuser (admin) in Django.
Run this script with: python make_superuser.py
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_manager.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

def make_superuser():
    """Make an existing user a superuser (admin)."""
    print("Make an existing user a superuser (admin) for your Health Manager application.")
    
    username = input("Enter username of existing user: ")
    
    try:
        user = User.objects.get(username=username)
        
        # Check if user is already a superuser
        if user.is_superuser and user.is_staff:
            print(f"\nUser '{username}' is already a superuser with admin privileges.")
            return
        
        # Make the user a superuser
        user.is_superuser = True
        user.is_staff = True
        user.save()
        
        print(f"\nUser '{username}' has been upgraded to superuser status with admin privileges!")
        print("They can now log in to the admin interface at /admin/ with their existing credentials.")
        
    except ObjectDoesNotExist:
        print(f"\nError: No user found with username '{username}'.")
        print("Available users:")
        for u in User.objects.all():
            print(f" - {u.username}")
        
        retry = input("\nDo you want to try again? (y/n): ")
        if retry.lower() == 'y':
            make_superuser()
        else:
            print("Operation cancelled.")
    except Exception as e:
        print(f"\nError updating user: {e}")

if __name__ == "__main__":
    make_superuser() 