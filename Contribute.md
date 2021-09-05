# Django Ledger Contribution Guidelines

* UI
  * Django Ledger UI is based on the [Bulma](https://bulma.io/) CSS Framework via [WebPack](https://webpack.js.org/).
   Any template contributions must follow Bulma's best practices.
  * Icons are implemented through [Iconify](https://iconify.design/) and Django Ledger has the built-in template tag 
  [icon](https://github.com/arrobalytics/django-ledger/blob/5f61251ce3ee8a9b159211a98d8d00c53b5cb942/django_ledger/templatetags/django_ledger.py#L78) 
  which can be used to render any icon using Iconify.
* JavaScript
  * Django Ledger uses [TypeScript](https://www.typescriptlang.org/) to ship JavaScript to the browser. Webpack is used to bundle all CSS/JS into two
  javascript files respectively. See [bundle](https://github.com/arrobalytics/django-ledger/tree/develop/django_ledger/static/django_ledger/bundle) 
  in the static file directory. The build command in the [assets/package.json](https://github.com/arrobalytics/django-ledger/blob/develop/assets/package.json)
  file will build styles and javascript and
  automatically update the application bundle with the latest compiled version.
* Models
  * Changes and contributions to Models are limited to those with proven Django experience. Also, in addition to Django
  experience, some accounting and domain knowledge is required. Changes to models must be justified and susbtantiated 
  with proper accounting best practices.
* Documentation
  * All documentation contributions are welcome. [Sphinx](https://github.com/sphinx-doc/sphinx) has been set up to 
  automatically generate static HTML documentation. 
* Unit Tests
  * All unit tests contributions are welcome if they are intended to validate program logic and/or accounting logic.