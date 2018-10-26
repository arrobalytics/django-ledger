from .apreciation import IOApprMixIn
from .core import IOCore
from .depreciation import IODeprMixIn
from .generic import IOGenericMixIn
from .preproc import IOPreProcMixIn


class IOBase(IOCore,
             IOPreProcMixIn,
             IOGenericMixIn,
             IODeprMixIn,
             IOApprMixIn):
    pass
