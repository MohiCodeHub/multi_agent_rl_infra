"""Site specifications for mock website generation"""

SITE_SPECS = [
    {
        "name": "signup",
        "purpose": "User registration form with validation",
        "elements": [
            {"type": "input", "label": "Email", "input_type": "email", "required": True},
            {"type": "input", "label": "Password", "input_type": "password", "required": True},
            {"type": "input", "label": "Confirm Password", "input_type": "password", "required": True},
            {"type": "button", "label": "Sign Up"}
        ],
        "validations": [
            "Email must contain @ and . characters",
            "Password must be at least 8 characters",
            "Password must contain at least one number",
            "Password and Confirm Password must match"
        ],
        "success_state": {
            "type": "message",
            "text": "Account created successfully",
            "class": "success"
        },
        "error_display": {
            "class": "error",
            "position": "below_field"
        }
    },
    {
        "name": "todo",
        "purpose": "Todo list with add, complete, and delete functionality",
        "elements": [
            {"type": "input", "label": "New Todo", "input_type": "text", "placeholder": "Enter a new todo"},
            {"type": "button", "label": "Add Todo"},
            {"type": "list", "label": "Todo List", "item_template": {
                "text": "Todo item text",
                "actions": [
                    {"type": "button", "label": "Complete"},
                    {"type": "button", "label": "Delete"}
                ]
            }}
        ],
        "validations": [
            "Cannot add empty todo",
            "Cannot add duplicate todo"
        ],
        "success_state": {
            "type": "element_present",
            "selector": ".todo-item"
        },
        "error_display": {
            "class": "error",
            "position": "above_list"
        }
    },
    {
        "name": "cart",
        "purpose": "Shopping cart with product selection and checkout",
        "elements": [
            {"type": "product_list", "label": "Products", "items": [
                {"name": "Product A", "price": 10.00},
                {"name": "Product B", "price": 20.00},
                {"name": "Product C", "price": 15.00}
            ]},
            {"type": "button", "label": "Add to Cart", "per_product": True},
            {"type": "input", "label": "Quantity", "input_type": "number", "default": 1},
            {"type": "input", "label": "Coupon Code", "input_type": "text"},
            {"type": "button", "label": "Apply Coupon"},
            {"type": "button", "label": "Checkout"}
        ],
        "validations": [
            "Quantity must be between 1 and 10",
            "Coupon code 'SAVE10' gives 10% discount",
            "Coupon code 'SAVE20' gives 20% discount",
            "Invalid coupon code shows error",
            "Cart must not be empty to checkout"
        ],
        "success_state": {
            "type": "page_change",
            "indicator": "Order confirmed"
        },
        "error_display": {
            "class": "error",
            "position": "inline"
        }
    },
    {
        "name": "settings",
        "purpose": "User settings page with toggles and preferences",
        "elements": [
            {"type": "checkbox", "label": "Email Notifications", "default": True},
            {"type": "checkbox", "label": "SMS Notifications", "default": False},
            {"type": "checkbox", "label": "Dark Mode", "default": False},
            {"type": "select", "label": "Language", "options": ["English", "Spanish", "French", "German"]},
            {"type": "select", "label": "Timezone", "options": ["UTC", "EST", "PST", "GMT"]},
            {"type": "button", "label": "Save Settings"},
            {"type": "button", "label": "Reset to Defaults"}
        ],
        "validations": [
            "Must change at least one setting before saving",
            "Show confirmation after successful save"
        ],
        "success_state": {
            "type": "message",
            "text": "Settings saved successfully",
            "class": "success"
        },
        "error_display": {
            "class": "error",
            "position": "top"
        }
    },
    {
        "name": "wizard",
        "purpose": "Multi-step form wizard with validation per step",
        "elements": [
            {"type": "step", "number": 1, "label": "Personal Info", "fields": [
                {"type": "input", "label": "First Name", "input_type": "text", "required": True},
                {"type": "input", "label": "Last Name", "input_type": "text", "required": True}
            ]},
            {"type": "step", "number": 2, "label": "Contact Info", "fields": [
                {"type": "input", "label": "Email", "input_type": "email", "required": True},
                {"type": "input", "label": "Phone", "input_type": "tel", "required": False}
            ]},
            {"type": "step", "number": 3, "label": "Review", "fields": []},
            {"type": "button", "label": "Next"},
            {"type": "button", "label": "Back"},
            {"type": "button", "label": "Submit"}
        ],
        "validations": [
            "Required fields must be filled before proceeding",
            "Email must be valid format",
            "Cannot skip steps"
        ],
        "success_state": {
            "type": "message",
            "text": "Form submitted successfully",
            "class": "success"
        },
        "error_display": {
            "class": "error",
            "position": "below_field"
        }
    }
]

