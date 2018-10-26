from books.models.mixins import LedgerMixIn


class SubjectModel(LedgerMixIn):
    class Meta:
        abstract = True
