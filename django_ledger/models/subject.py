from .mixins import CreateUpdateMixIn, SlugNameMixIn, LedgerMixIn


class SubjectModelAbstract(SlugNameMixIn,
                           CreateUpdateMixIn,
                           LedgerMixIn):

    # entitifk

    class Meta:
        abstract = True
