export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "DealFlow360";

/** Must equal the version at the top of `context/API_CONTRACT.md`. Asserted
 * against `GET /meta/enums`'s `contract_version` on boot — see `useEnums()`. */
export const EXPECTED_CONTRACT_VERSION = "v1.1.0";
