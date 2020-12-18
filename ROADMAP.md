![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

# Roadmap to Version 1.0 Stable

### Version 0.3
* Implementation of Bill Model & Invoice Model.
* Vendor Model & Customer Models association with Bill/Invoice models respectively.
* Define Django Ledger IO Engine JSON Schema.
* Optimize charts for mobile.
* Bugfixes & UI/UX Enhancements.

### Version 0.4
* Items, resources and & lists for bills & invoices itemization.
* Entity internal organizations, department, branches, etc.
* Testing framework implementation that will include:
    * Unit tests using the [Built-in Django](https://docs.djangoproject.com/en/3.1/topics/testing/) unit test modules.
    * Behavioral Driven Testing using the [behave](https://behave.readthedocs.io/en/latest/) library.
* Work with Accountants, Subject Matter Experts and Developers to develop a comprehensive 
list of Unit Tests to validate accounting engine output.
* Enhance and optimize Django Ledger the random data generation functionality to properly populate
relevant random data for testing.
* Start creating basic package documentation via [Sphinx](https://www.sphinx-doc.org/en/master/)
    * Document code and functions within code base.
    * Generate HTML documentation.  
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.5
* Inventory tracking.
* Cash flow statement.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.6
* Customer jobs & project tracking.
* Client proposals & estimates.
* Time tracking.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.


### Version 0.7
* Currency Models implementation as a way to define EntityModel default currency.
* Produce financial statements in different currencies.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.8
* User roles and permissions on views to support read/write permissions for assigned managers
to entities.
* User preferences and settings & account creation views.
* Update package and code documentation.

### Version 0.9
* Enable Hierarchical Entity structures via MPTT. 
* Consolidated financial statements.
* Intercompany transactions.
* Update package and code documentation.

### Version 1.0
* Complete Internationalization of all user-related fields.
 
*** Roadmap subject to change based on user feedback and backlog priorities.

