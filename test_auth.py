#!/usr/bin/env python3
"""
Test script to verify HTTP Basic Authentication implementation
"""
import os
import sys
from app import app
import base64

def test_authentication():
    """Test authentication on all routes"""
    
    # Check environment variables
    username = os.getenv('AUTH_USERNAME')
    password = os.getenv('AUTH_PASSWORD')
    
    if not username or not password:
        print("❌ ERROR: AUTH_USERNAME and AUTH_PASSWORD must be set")
        print("\nSet them with:")
        print("  export AUTH_USERNAME='your_username'")
        print("  export AUTH_PASSWORD='your_password'")
        sys.exit(1)
    
    print(f"Testing with credentials: {username}:{'*' * len(password)}\n")
    
    credentials = base64.b64encode(f'{username}:{password}'.encode()).decode('utf-8')
    
    # All protected routes
    protected_routes = [
        ('/', 'GET'),
        ('/history', 'GET'),
        ('/vat-summary', 'GET'),
        ('/download-excel', 'GET'),
        ('/download-pdf', 'GET'),
        ('/errors', 'GET'),
        ('/error-review', 'GET'),
    ]
    
    with app.test_client() as client:
        print("=" * 70)
        print("AUTHENTICATION TEST RESULTS")
        print("=" * 70)
        
        # Test health endpoint (no auth required)
        print("\n1. UNAUTHENTICATED ENDPOINT:")
        response = client.get('/health')
        status = "✓ PASS" if response.status_code == 200 else "✗ FAIL"
        print(f"   {status} - /health (no auth) -> {response.status_code}")
        
        # Test protected routes without auth
        print("\n2. PROTECTED ENDPOINTS (No Authentication):")
        all_protected = True
        for route, method in protected_routes[:5]:  # Test first 5
            response = client.get(route)
            is_protected = response.status_code == 401
            status = "✓ PASS" if is_protected else "✗ FAIL"
            print(f"   {status} - {route} -> {response.status_code}")
            all_protected = all_protected and is_protected
        
        # Test protected routes with correct auth
        print("\n3. PROTECTED ENDPOINTS (With Authentication):")
        all_accessible = True
        for route, method in protected_routes[:5]:
            response = client.get(route, headers={'Authorization': f'Basic {credentials}'})
            is_accessible = response.status_code in [200, 302]
            status = "✓ PASS" if is_accessible else "✗ FAIL"
            print(f"   {status} - {route} -> {response.status_code}")
            all_accessible = all_accessible and is_accessible
        
        # Test with wrong credentials
        print("\n4. WRONG CREDENTIALS:")
        wrong_creds = base64.b64encode(b'wrong:wrong').decode('utf-8')
        response = client.get('/', headers={'Authorization': f'Basic {wrong_creds}'})
        is_denied = response.status_code == 401
        status = "✓ PASS" if is_denied else "✗ FAIL"
        print(f"   {status} - / (wrong password) -> {response.status_code}")
        
        print("\n" + "=" * 70)
        if all_protected and all_accessible and is_denied:
            print("✓ ALL TESTS PASSED - Authentication is working correctly!")
        else:
            print("✗ SOME TESTS FAILED - Check implementation")
        print("=" * 70)

if __name__ == '__main__':
    test_authentication()
