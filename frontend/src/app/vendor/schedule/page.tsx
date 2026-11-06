"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  addShopClosure,
  errorMessage,
  getShopSchedule,
  listShopClosures,
  removeShopClosure,
  saveShopSchedule,
  type OpeningPeriod,
  type ShopSchedule,
} from "@/lib/api-client";
import { formatMarketDate, MARKET_TIME_LABEL, marketToday } from "@/lib/market-time";
import { useApi, useRequireRole } from "@/lib/use-api";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function HoursEditor({
  shopId,
  initial,
  onSaved,
}: {
  shopId: string;
  initial: ShopSchedule;
  onSaved: () => void;
}) {
  const [hours, setHours] = useState<OpeningPeriod[]>(initial.hours);
  const [capacity, setCapacity] = useState(String(initial.booking_capacity));
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function change(target: OpeningPeriod, patch: Partial<OpeningPeriod>) {
    setHours((current) =>
      current.map((period) => (period === target ? { ...period, ...patch } : period)),
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setIsSaving(true);
    try {
      await saveShopSchedule(shopId, { booking_capacity: Number(capacity), hours });
      setNotice("Saved. Existing bookings aren't affected.");
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card as="form" onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Weekly hours</h2>
        <p className="text-sm text-text-muted">
          In {MARKET_TIME_LABEL}. Add a second period to leave room for a lunch break.
        </p>
      </div>

      <ul className="flex flex-col gap-4">
        {WEEKDAYS.map((label, weekday) => {
          const periods = hours.filter((period) => period.weekday === weekday);
          return (
            <li key={label} className="flex flex-col gap-2 border-b border-border pb-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary">{label}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    setHours((current) => [
                      ...current,
                      { weekday, opens_at: "09:00", closes_at: "17:00" },
                    ])
                  }
                >
                  Add period
                </Button>
              </div>
              {periods.length === 0 && <p className="text-sm text-text-muted">Closed</p>}
              {periods.map((period, index) => (
                <div key={index} className="flex flex-wrap items-center gap-2">
                  <input
                    type="time"
                    required
                    aria-label={`${label} opens at`}
                    value={period.opens_at}
                    onChange={(e) => change(period, { opens_at: e.target.value })}
                    className={`${inputClassName} w-auto`}
                  />
                  <span className="text-sm text-text-muted">to</span>
                  <input
                    type="time"
                    required
                    aria-label={`${label} closes at`}
                    value={period.closes_at}
                    onChange={(e) => change(period, { closes_at: e.target.value })}
                    className={`${inputClassName} w-auto`}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setHours((current) => current.filter((item) => item !== period))}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </li>
          );
        })}
      </ul>

      <FormField label="Customers served at the same time">
        <input
          type="number"
          required
          min="1"
          step="1"
          value={capacity}
          onChange={(e) => setCapacity(e.target.value)}
          className={`${inputClassName} w-32`}
        />
      </FormField>

      {error && <ErrorText>{error}</ErrorText>}
      {notice && <p className="text-sm font-medium text-status-delivered">{notice}</p>}
      <Button type="submit" disabled={isSaving} className="self-start">
        {isSaving ? "Saving…" : "Save hours"}
      </Button>
    </Card>
  );
}

function Closures({ shopId }: { shopId: string }) {
  const [page, setPage] = useState(1);
  const closures = useApi(() => listShopClosures(shopId, page), `${shopId}|${page}`, true);
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function run(action: () => Promise<unknown>) {
    setIsPending(true);
    setError(null);
    try {
      await action();
      closures.reload();
      return true;
    } catch (err) {
      setError(errorMessage(err));
      return false;
    } finally {
      setIsPending(false);
    }
  }

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    if (await run(() => addShopClosure(shopId, { date, note }))) {
      setDate("");
      setNote("");
    }
  }

  const results = closures.data?.results ?? [];

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Closed days</h2>
        <p className="text-sm text-text-muted">No times are offered on these dates.</p>
      </div>

      <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3">
        <FormField label="Date">
          <input
            type="date"
            required
            min={marketToday()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <div className="min-w-0 flex-1">
          <FormField label="Note (optional)">
            <input
              type="text"
              maxLength={255}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className={inputClassName}
            />
          </FormField>
        </div>
        <Button type="submit" disabled={isPending}>
          Add
        </Button>
      </form>

      {error && <ErrorText>{error}</ErrorText>}
      {closures.error && <ErrorText>{closures.error}</ErrorText>}

      {closures.isLoading && !closures.data ? (
        <LoadingText>Loading closed days…</LoadingText>
      ) : results.length === 0 ? (
        closures.error ? null : (
          <EmptyText>No closed days coming up.</EmptyText>
        )
      ) : (
        <ul className="flex flex-col gap-2">
          {results.map((closure) => (
            <li key={closure.id} className="flex items-center justify-between gap-3">
              <span className="min-w-0 text-sm text-text-primary">
                {formatMarketDate(closure.date)}
                {closure.note && <span className="text-text-muted"> &middot; {closure.note}</span>}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={isPending}
                onClick={() => run(() => removeShopClosure(shopId, closure.id))}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Pager
        previous={closures.data?.previous ?? null}
        next={closures.data?.next ?? null}
        onPrevious={() => setPage((current) => current - 1)}
        onNext={() => setPage((current) => current + 1)}
      />
    </Card>
  );
}

export default function VendorSchedulePage() {
  const allowed = useRequireRole("VENDOR");
  const { user } = useAuth();
  const shops = (user?.shops ?? []).filter(
    (shop) => shop.status === "APPROVED" && shop.business_type === "SERVICES",
  );
  const [selectedId, setSelectedId] = useState("");
  const shopId = selectedId || (shops[0] ? String(shops[0].id) : "");
  const schedule = useApi(() => getShopSchedule(shopId), shopId, allowed && !!shopId);
  // Bumped after a save, so the editor restarts from what the server actually stored.
  const [savedVersion, setSavedVersion] = useState(0);

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (!shopId) {
    return (
      <PageShell size="sm" className="min-h-screen justify-center">
        <Card>
          <h1 className="mb-4 text-2xl font-semibold text-text-primary">Hours</h1>
          <p className="text-sm text-text-muted">
            You need an approved services shop before you can set its hours. You can request one
            from your account page.
          </p>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Hours" description="Set when customers can book your services.">
      {shops.length > 1 && (
        <FormField label="Shop">
          <select
            value={shopId}
            onChange={(e) => setSelectedId(e.target.value)}
            className={inputClassName}
          >
            {shops.map((shop) => (
              <option key={shop.id} value={shop.id}>
                {shop.name}
              </option>
            ))}
          </select>
        </FormField>
      )}

      {schedule.error && <ErrorText>{schedule.error}</ErrorText>}
      {schedule.isLoading && !schedule.data ? (
        <LoadingText>Loading hours…</LoadingText>
      ) : (
        schedule.data &&
        !schedule.isLoading && (
          <HoursEditor
            key={`${shopId}|${savedVersion}`}
            shopId={shopId}
            initial={schedule.data}
            onSaved={() => {
              schedule.reload();
              setSavedVersion((version) => version + 1);
            }}
          />
        )
      )}

      <Closures key={shopId} shopId={shopId} />
    </PageShell>
  );
}
