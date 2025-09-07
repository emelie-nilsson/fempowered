# Testing Documentation

## Table of Contents
- [Automated Testing](#automated-testing)
- [Manual Testing](#manual-testing)
- [Validation](#validation)
- [Bugs and Fixes](#bugs-and-fixes)

---

## Automated Testing

### Checkout Form Tests
Unit tests for the `CheckoutAddressForm` are located in `checkout/tests/test_forms.py`.  
The tests verify that the form enforces key validation rules:
- **Full name**: must contain both first and last name.
- **Phone number**: must be sufficiently long and contain only valid characters.
- **Postal code**: must consist of digits only.
- **Billing fields**: required when billing address is not the same as shipping.

**Result:**  
All validation rules worked as expected. The tests passed successfully ✔

---

### Checkout Views Tests
View tests for the checkout address step are located in `checkout/tests/test_views.py`.  
The tests check the following:
- **GET request**: the checkout address page renders successfully.
- **Invalid POST**: submitting an incomplete form stays on the page and displays errors.
- **Valid POST**: submitting a valid form redirects to the next step (or responds with `400` if business preconditions, such as an empty cart, are not met).
- **Billing requirements**: ensures billing address fields are validated when `billing_same_as_shipping` is unchecked.

**Result:**  
All tests passed ✔.  
The tests are written to tolerate variations in URL structure or checkout preconditions.

---

### Smoke Tests
High-level smoke tests are located in `tests/test_smoke.py`.  
These perform lightweight checks on key routes:
- Home (`/`)
- Shop (`/shop/` or `/products/`)
- Cart (`/cart/` or `/basket/`)
- Checkout (`/checkout/` or `/checkout/address/`)
- Login (`/accounts/login/`)
- Signup (`/accounts/signup/`)

The smoke test accepts common response codes (200, 302, 303, 403, 400) and skips gracefully if a route is not found in the project.

**Result:**  
Some paths were skipped depending on the project’s URL configuration.  
The smoke testing framework is in place and can easily be updated as routes are finalized.


## Manual Testing

### User Story 1  
**As a Visitor, I want to browse available products so that I can explore what the shop offers without needing an account.**

**Category:** Must Have  

**Tasks:**  
- Create product listing page  
- Connect to database and fetch products  
- Display product images, names, prices  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| User can view all products on a products page without logging in | | | | |

---

### User Story 2  
**As a Visitor, I want to view product details so that I can learn more before deciding to buy.**

**Category:** Must Have  

**Tasks:**  
- Create product detail template  
- Query product from database  
- Display all fields  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Clicking a product opens a product detail page with image, description, price, available sizes/colors | | | | |

---

### User Story 3  
**As a Visitor, I want to search and filter products so that I can quickly find what I'm looking for.**

**Category:** Should Have  

**Tasks:**  
- Implement search function  
- Add filters  
- Test search accuracy  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Search bar returns relevant products | | | | |
| Filters narrow down results by category, size, and color | | | | |

---

### User Story 4  
**As a Visitor, I want to add items to a shopping cart so that I can build my order before checking out.**

**Category:** Must Have  

**Tasks:**  
- Create cart model/session  
- Add "Add to Cart" buttons  
- Display cart count  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Items remain in cart during session | | | | |
| Cart icon updates with quantity | | | | |

---

### User Story 5  
**As a Visitor, I want to be prompted to sign up or log in so that I can proceed to checkout.**

**Category:** Must Have  

**Tasks:**  
- Add authentication check to checkout  
- Redirect to login/register  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Checkout flow redirects unauthenticated users to login/register page | | | | |

---

### User Story 6  
**As a Registered User, I want to register an account so that I can make purchases and track orders.**

**Category:** Must Have  

**Tasks:**  
- Implement registration view and form  
- Test form validation  
- Save user to database  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Registration form with validation | | | | |
| Success message shown after registration | | | | |
| User stored in database | | | | |

---

### User Story 7  
**As a Registered User, I want to log in and log out securely so that I can access and protect my data.**

**Category:** Must Have  

**Tasks:**  
- Implement login/logout views  
- Handle sessions securely  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| User can log in and log out | | | | |
| Session ends on logout | | | | |
| Protected pages require login | | | | |

---

### User Story 8  
**As a Registered User, I want to view my order history so that I can keep track of past purchases.**

**Category:** Should Have  

**Tasks:**  
- Create order history page  
- Query orders by logged-in user  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Orders are linked to user accounts | | | | |
| Orders are displayed in profile | | | | |

---

### User Story 9  
**As a Registered User, I want to leave product reviews so that I can share feedback with others.**

**Category:** Should Have  

**Tasks:**  
- Create review model  
- Add review form to product page  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Review form visible to logged-in users | | | | |
| Reviews stored and displayed under products | | | | |

---

### User Story 10  
**As a Registered User, I want to edit or delete my own reviews so that I can manage my contributions.**

**Category:** Should Have  

**Tasks:**  
- Implement edit/delete views with permissions  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| User can edit or delete only their own reviews | | | | |
| Changes update instantly | | | | |

---

### User Story 11  
**As a Registered User, I want to trust that my personal data is handled securely so that I feel safe using the platform.**

**Category:** Could Have  

**Tasks:**  
- Enable SSL  
- Use Django security settings  
- Hide secrets in environment variables  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| HTTPS enabled | | | | |
| Secure password storage | | | | |
| API keys and secrets are hidden | | | | |
| GDPR compliance | | | | |

---

### User Story 12  
**As a Customer, I want to add and remove products from the cart so that I can manage my order.**

**Category:** Must Have  

**Tasks:**  
- Update cart view  
- Add remove functionality  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Cart updates instantly when items are added/removed | | | | |

---

### User Story 13  
**As a Customer, I want to view a cart summary with totals so that I know what I’m about to pay.**

**Category:** Must Have  

**Tasks:**  
- Create cart summary template  
- Calculate totals dynamically  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Cart page shows product names, quantities, subtotals, and total | | | | |

---

### User Story 14  
**As a Customer, I want to go to checkout and enter shipping details so that my order can be delivered.**

**Category:** Must Have  

**Tasks:**  
- Create checkout form  
- Save data to database  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Checkout form collects name, address, and contact details | | | | |
| Shipping info saved to order | | | | |

---

### User Story 15  
**As a Customer, I want to pay securely via Stripe so that I can complete my purchase safely.**

**Category:** Must Have  

**Tasks:**  
- Set up Stripe API  
- Test payment flow  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Stripe integration for secure payments | | | | |
| Payment success/fail handled | | | | |

---

### User Story 16  
**As a Customer, I want to receive a confirmation message after a successful payment so that I know the order went through.**

**Category:** Must Have  

**Tasks:**  
- Create order confirmation view/template  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Success page shows order details and confirmation | | | | |

---

### User Story 17  
**As a Customer, I want to see helpful error messages on failed payments so that I know how to fix issues.**

**Category:** Could Have  

**Tasks:**  
- Handle Stripe error responses  
- Create failed payment template  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Failed payment page explains the error and offers retry | | | | |

---

### User Story 18  
**As an Admin, I want to log in to the admin panel so that I can manage the shop backend.**

**Category:** Must Have  

**Tasks:**  
- Configure Django admin  
- Add staff accounts  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Admin login page | | | | |
| Access restricted to staff accounts | | | | |

---

### User Story 19  
**As an Admin, I want to add, update, and delete products so that I can keep the catalogue current.**

**Category:** Must Have  

**Tasks:**  
- Configure product model in admin  
- Test forms and saving  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| CRUD operations for products in admin panel | | | | |

---

### User Story 20  
**As an Admin, I want to manage product categories so that items are well organized.**

**Category:** Should Have  

**Tasks:**  
- Add Category model to admin panel  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Categories can be created, edited, and deleted in admin | | | | |

---

### User Story 21  
**As an Admin, I want to view incoming orders and their details so that I can fulfill them efficiently.**

**Category:** Must Have  

**Tasks:**  
- Add orders to admin  
- Test queries  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Orders listed in admin | | | | |
| Order detail view shows customer/shipping info | | | | |

---

### User Story 22  
**As an Admin, I want to mark orders as fulfilled or shipped so that customers stay informed.**

**Category:** Must Have  

**Tasks:**  
- Add status field to order model  
- Enable status updates in admin  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Order status can be updated in admin | | | | |

---

### User Story 23  
**As an Admin, I want to restrict access to admin-only features so that only authorized staff can manage content.**

**Category:** Must Have  

**Tasks:**  
- Set permissions for admin and protected views  

#### Testing  

| Acceptance Criteria | Steps to Test | Expected Outcome | Pass/Fail | Screenshot |
|----------------------|---------------|------------------|-----------|------------|
| Admin pages require staff login | | | | |
