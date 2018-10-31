from .generic import IOGenericMixIn
from .preproc import IOPreProcMixIn


class IOBase(IOPreProcMixIn,
             IOGenericMixIn):
    """
    IO Base
    """
