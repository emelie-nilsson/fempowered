# Testing Documentation

## Table of Contents
- [Automated Testing](#automated-testing)
- [Manual Testing](#manual-testing)
- [Validation](#validation)
- [Bugs and Fixes](#bugs-and-fixes)

---

## Automated Testing

### Checkout Form Validation

**File:** checkout/tests/test_forms.py  
**Command:** python manage.py test checkout.tests.test_forms  

**Purpose:**  
To confirm that the checkout form enforces key server-side validation rules:  
- Full name must include both first and last name  
- Phone number may only contain digits (and +, - or spaces)  
- Postal code must be numeric and within a valid length  

**Result:**  
All validation rules worked as expected, and the tests passed successfully ✔
