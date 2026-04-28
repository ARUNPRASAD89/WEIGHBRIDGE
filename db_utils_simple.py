# Simple database utilities for supplier functionality
# This is a minimal implementation for the supplier button panel

def fetch_all_suppliers():
    """Fetch all suppliers from database. 
    For now, returns dummy data until database is properly configured."""
    
    # Mock supplier data for development/testing
    return [
        {"suppliercode": 1, "suppliername": "ABC Suppliers"},
        {"suppliercode": 2, "suppliername": "XYZ Materials"},
        {"suppliercode": 3, "suppliername": "Best Stones"},
        {"suppliercode": 4, "suppliername": "Quality Cement"},
        {"suppliercode": 5, "suppliername": "Prime Steel"},
        {"suppliercode": 6, "suppliername": "Metro Goods"},
        {"suppliercode": 7, "suppliername": "City Traders"},
        {"suppliercode": 8, "suppliername": "Elite Supply"},
    ]

def get_supplier_details(suppliername):
    """Get supplier details by name"""
    suppliers = fetch_all_suppliers()
    for supplier in suppliers:
        if supplier["suppliername"] == suppliername:
            return supplier
    return None