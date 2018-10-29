from .mixins import CreateUpdateMixIn, SlugNameMixIn, LedgerMixIn


class SubjectModelAbstract(SlugNameMixIn,
                           CreateUpdateMixIn,
                           LedgerMixIn):

    class Meta:
        abstract = True
