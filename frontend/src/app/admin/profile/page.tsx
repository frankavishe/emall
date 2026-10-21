"use client";

import { useAuth, type AdminPermission } from "@/lib/auth-context";
import { useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { AvatarPicker } from "@/components/account/avatar-picker";
import { Detail, PersonalInfoForm } from "@/components/account/personal-info-form";

// Display names for the `<area>` prefix of permission codes such as `orders.manage`.
const AREA_LABELS: Record<string, string> = {
  shops: "Shops",
  catalog: "Catalog",
  customers: "Customers",
  orders: "Orders",
  riders: "Riders",
  finance: "Finance",
  reviews: "Reviews",
  audit: "Audit log",
};

function formatDate(value: string | null, withTime = false): string {
  if (!value) return "—";
  const date = new Date(value);
  return withTime ? date.toLocaleString() : date.toLocaleDateString();
}

function groupByArea(permissions: AdminPermission[]): [string, AdminPermission[]][] {
  const groups = new Map<string, AdminPermission[]>();
  for (const permission of permissions) {
    const area = permission.code.split(".")[0]!;
    groups.set(area, [...(groups.get(area) ?? []), permission]);
  }
  return [...groups.entries()];
}

export default function AdminProfilePage() {
  const { user } = useAuth();
  const allowed = useRequireRole("ADMINISTRATOR");

  if (!allowed || !user) {
    return (
      <PageShell size="md">
        <LoadingText />
      </PageShell>
    );
  }

  const permissionGroups = groupByArea(user.permissions);

  return (
    <PageShell size="md" title="My profile" description="Your details and what your role can do.">
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <AvatarPicker user={user} />
        <div className="flex flex-col gap-1 sm:items-end">
          <p className="text-lg font-semibold text-text-primary">{user.name}</p>
          <Pill tone="approved">{user.admin_role_label ?? "No admin role"}</Pill>
        </div>
      </Card>

      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">Personal information</h2>
        <PersonalInfoForm key={user.id} user={user} />
      </Card>

      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">Account</h2>
        <dl className="flex flex-col gap-3 text-sm">
          <Detail label="Role">{user.admin_role_label ?? "None assigned"}</Detail>
          <Detail label="Date joined">{formatDate(user.date_joined)}</Detail>
          <Detail label="Last login">{formatDate(user.last_login, true)}</Detail>
        </dl>
      </Card>

      <Card className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-text-primary">Role permissions</h2>
          <p className="text-sm text-text-muted">
            What a {user.admin_role_label ?? "administrator without a role"} can do. Roles are
            assigned by a Super Admin.
          </p>
        </div>
        {permissionGroups.length === 0 ? (
          <ErrorText>
            Your account has no admin role yet, so every admin area is closed to you.
          </ErrorText>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {permissionGroups.map(([area, permissions]) => (
              <section key={area} className="flex flex-col gap-2">
                <h3 className="text-sm font-semibold text-text-primary">
                  {AREA_LABELS[area] ?? area}
                </h3>
                <ul className="flex flex-col gap-2">
                  {permissions.map((permission) => (
                    <li key={permission.code} className="text-sm">
                      <span className="font-medium text-text-primary">{permission.label}</span>
                      <span className="block text-text-muted">{permission.description}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </Card>
    </PageShell>
  );
}
