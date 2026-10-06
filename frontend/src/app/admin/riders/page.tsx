"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import {
  ApiError,
  VEHICLE_TYPES,
  createRider,
  errorMessage,
  listAdminRiders,
  updateRider,
  type AdminRider,
  type NewRider,
} from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { Avatar } from "@/components/ui/avatar";

type ActiveFilter = "active" | "inactive" | "all";

const EMPTY_FORM: NewRider = {
  name: "",
  email: "",
  password: "",
  phone: "",
  vehicle_type: "MOTORCYCLE",
  plate_number: "",
};

function vehicleLabel(value: string): string {
  return VEHICLE_TYPES.find((v) => v.value === value)?.label ?? value;
}

function filterToParam(filter: ActiveFilter): boolean | undefined {
  return filter === "all" ? undefined : filter === "active";
}

function RegisterRiderForm({ onCreated }: { onCreated: (rider: AdminRider) => void }) {
  const [form, setForm] = useState<NewRider>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update<K extends keyof NewRider>(key: K, value: NewRider[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const rider = await createRider(form);
      setForm(EMPTY_FORM);
      onCreated(rider);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-1 text-lg font-semibold text-text-primary">Register a rider</h2>
      <p className="mb-4 text-sm text-text-muted">
        Give the rider their email and temporary password. They can change it later with
        &ldquo;Forgot your password?&rdquo; on the login page.
      </p>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="Full name">
          <input
            required
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Email">
          <input
            type="email"
            required
            autoComplete="off"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Temporary password">
          <input
            type="text"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Phone">
          <input
            type="tel"
            required
            value={form.phone}
            onChange={(e) => update("phone", e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Vehicle type">
          <select
            value={form.vehicle_type}
            onChange={(e) => update("vehicle_type", e.target.value as NewRider["vehicle_type"])}
            className={inputClassName}
          >
            {VEHICLE_TYPES.map((v) => (
              <option key={v.value} value={v.value}>
                {v.label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Plate number">
          <input
            value={form.plate_number}
            onChange={(e) => update("plate_number", e.target.value)}
            className={inputClassName}
          />
        </FormField>
        {error && (
          <div className="sm:col-span-2">
            <ErrorText>{error}</ErrorText>
          </div>
        )}
        <div className="sm:col-span-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Registering…" : "Register rider"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default function AdminRidersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [filter, setFilter] = useState<ActiveFilter>("active");
  const [riders, setRiders] = useState<AdminRider[]>([]);
  const [isLoadingRiders, setIsLoadingRiders] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "ADMINISTRATOR"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const loadRiders = useCallback(async (current: ActiveFilter) => {
    setIsLoadingRiders(true);
    setError(null);
    try {
      const response = await listAdminRiders({ isActive: filterToParam(current) });
      setRiders(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoadingRiders(false);
    }
  }, []);

  useEffect(() => {
    if (!hasRole(user, "ADMINISTRATOR")) return;
    let cancelled = false;

    async function run() {
      setIsLoadingRiders(true);
      setError(null);
      try {
        const response = await listAdminRiders({ isActive: filterToParam(filter) });
        if (!cancelled) setRiders(response.results);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingRiders(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, filter]);

  async function handleCreated(rider: AdminRider) {
    setNotice(`${rider.name} is registered and can now log in with ${rider.email}.`);
    await loadRiders(filter);
  }

  async function handleToggleActive(rider: AdminRider) {
    setPendingActionId(rider.id);
    setError(null);
    setNotice(null);
    try {
      await updateRider(rider.id, { is_active: !rider.is_active });
      await loadRiders(filter);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingActionId(null);
    }
  }

  if (isLoading || !user || !hasRole(user, "ADMINISTRATOR")) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Riders">
      <RegisterRiderForm onCreated={handleCreated} />

      {notice && <p className="text-sm font-medium text-status-delivered">{notice}</p>}

      <SegmentedToggle
        options={[
          { value: "active", label: "ACTIVE" },
          { value: "inactive", label: "INACTIVE" },
          { value: "all", label: "ALL" },
        ]}
        value={filter}
        onChange={setFilter}
        className="self-start"
      />

      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingRiders ? (
        <LoadingText>Loading riders…</LoadingText>
      ) : riders.length === 0 ? (
        <EmptyText>No riders match this filter.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {riders.map((rider) => (
            <Card as="li" key={rider.id} padding="sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <Avatar name={rider.name} size="sm" />
                  <div>
                    <p className="font-medium text-text-primary">{rider.name}</p>
                    <p className="text-sm text-text-muted">
                      {rider.email} &middot;{" "}
                      <a href={`tel:${rider.phone}`} className="underline">
                        {rider.phone}
                      </a>
                    </p>
                    <p className="text-sm text-text-muted">
                      {vehicleLabel(rider.vehicle_type)}
                      {rider.plate_number && <> &middot; {rider.plate_number}</>} &middot;{" "}
                      {rider.active_delivery_count} active{" "}
                      {rider.active_delivery_count === 1 ? "delivery" : "deliveries"}
                    </p>
                    <div className="mt-1">
                      <Pill tone={rider.is_active ? "approved" : "cancelled"}>
                        {rider.is_active ? "ACTIVE" : "INACTIVE"}
                      </Pill>
                    </div>
                  </div>
                </div>

                <Button
                  variant={rider.is_active ? "danger" : "secondary"}
                  size="sm"
                  disabled={pendingActionId === rider.id}
                  onClick={() => handleToggleActive(rider)}
                >
                  {rider.is_active ? "Deactivate" : "Reactivate"}
                </Button>
              </div>
            </Card>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
