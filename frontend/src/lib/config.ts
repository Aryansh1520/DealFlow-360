export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "DealFlow360";

/** Must equal the version at the top of `context/API_CONTRACT.md`. Asserted
 * against `GET /meta/enums`'s `contract_version` on boot — see `useEnums()`. */
export const EXPECTED_CONTRACT_VERSION = "v1.1.0";

/**
 * `FRONTEND_PHASE_1.md` Task 4's mock layer. Backend Phase 2 (the quotation
 * engine, state machine, approvals) is still `501` stubs, so the quotations
 * and approvals features return fixtures typed against the generated schema
 * instead of calling Axios — this is what lets the Phase 2 UI be built and
 * demoed before the backend lands. Defaults **on** for exactly that reason;
 * set `NEXT_PUBLIC_USE_MOCKS=0` the moment the real endpoints ship, delete the
 * mock modules, and this flag goes away entirely (G3 checklist item).
 */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "0";
