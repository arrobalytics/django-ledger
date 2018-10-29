from .core import IOCore
from .generic import IOGenericMixIn
from .preproc import IOPreProcMixIn


class IOBase(IOCore,
             IOPreProcMixIn,
             IOGenericMixIn):
    pass
