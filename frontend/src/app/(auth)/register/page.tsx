import type { Metadata } from "next";

import { RegisterForm } from "@/features/auth/components/register-form";

export const metadata: Metadata = {
  title: "Create your organization",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
