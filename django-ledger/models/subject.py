from .mixins import BaseSubjectModel, LedgerMixIn


class SubjectModel(BaseSubjectModel,
                   LedgerMixIn):

    class Meta:
        abstract = True
