import warnings
from functools import wraps

from django_ledger.settings import DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR

if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
    warnings.warn(
        message=(
            'You are using the deprecated behavior of django_ledger. '
            'Set DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR = False to transition to new API.'
        )
    )


def deprecated_entity_slug_behavior(func=None, *, message=None):
    """
    Decorator for for_entity(...) methods to warn about the deprecated `entity_slug` argument
    and optionally map it to `entity_model` for backward compatibility.

    Usage:
      @deprecated_for_entity_behavior
      def for_entity(self, entity_model=None, **kwargs):
          ...

      or with custom message:
      @deprecated_for_entity_behavior(message="custom deprecation message")
      def for_entity(...):
          ...
    """
    default_message = (
        'entity_slug parameter is deprecated and will be removed in a future release. '
        'Use entity_model instead (accepts EntityModel instance, UUID, or slug string).'
    )

    if func is None:
        # Called as @deprecated_for_entity_behavior(...)
        return lambda f: deprecated_entity_slug_behavior(f, message=message)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'entity_slug' in kwargs and kwargs.get('entity_slug') is not None:
            warnings.warn(message or default_message, DeprecationWarning, stacklevel=2)

            # If both are provided, fail fast to avoid ambiguity
            if kwargs.get('entity_model') is not None:
                raise ValueError(
                    'Cannot specify both `entity_model` and `entity_slug`. '
                    'entity_slug is deprecated; pass only entity_model.'
                )

            # Maintain legacy behavior when enabled by settings toggle
            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                kwargs['entity_model'] = kwargs.pop('entity_slug')
            else:
                # If deprecated behavior is disabled, drop the deprecated param
                # and rely on the method's own validation (likely to fail fast).
                kwargs.pop('entity_slug', None)

        return func(*args, **kwargs)

    return wrapper
