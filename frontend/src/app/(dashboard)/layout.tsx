import { AuthGuard } from "@/features/auth/components/auth-guard";
import { InternalGuard } from "@/features/auth/components/internal-guard";
import { ContractVersionBanner } from "@/components/layout/contract-version-banner";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <InternalGuard>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <ContractVersionBanner />
            <Header />
            <main className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-8">
              <div className="mx-auto w-full max-w-6xl">{children}</div>
            </main>
          </div>
        </div>
      </InternalGuard>
    </AuthGuard>
  );
}
