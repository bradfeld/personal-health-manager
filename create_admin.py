#!/usr/bin/env python
"""
Script to create a Django superuser (admin) account.
Run this script with: python create_admin.py
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_manager.settings")
django.setup()

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

def create_superuser():
    """Create a superuser (admin) account."""
    print("Creating a superuser (admin) account for your Health Manager application.")
    
    username = input("Enter username: ")
    email = input("Enter email: ")
    password = input("Enter password: ")
    
    try:
        user = User.objects.create_superuser(username=username, email=email, password=password)
        print(f"\nSuperuser '{username}' created successfully!")
        print("You can now log in to the admin interface at /admin/ with these credentials.")
    except IntegrityError:
        print(f"\nError: The username '{username}' is already taken.")
        retry = input("Do you want to try again? (y/n): ")
        if retry.lower() == 'y':
            create_superuser()
        else:
            print("Superuser creation cancelled.")
    except Exception as e:
        print(f"\nError creating superuser: {e}")

if __name__ == "__main__":
    create_superuser() 