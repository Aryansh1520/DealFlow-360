"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

export default function PortalHomePage() {
  const router = useRouter();
  React.useEffect(() => {
    router.replace("/portal/quotations");
  }, [router]);
  return null;
}
