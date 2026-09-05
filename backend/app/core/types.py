"""Shared annotated primitives so money/percentage validation is uniform everywhere.

Every field holding money is a `MoneyMinor` (integer minor units, e.g. paise); every
field holding a percentage is a `Bps` (integer basis points, 0..10000). Never `Float`.
"""

from typing import Annotated

from pydantic import Field

MoneyMinor = Annotated[int, Field(ge=0)]
Bps = Annotated[int, Field(ge=0, le=10000)]
