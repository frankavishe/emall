"use client";

import { useState } from "react";
import { errorMessage } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

/** Builds a PDF report on the server and opens it in a new tab, ready to print or save. Falls
 * back to downloading it as `filename` when the browser blocks the new tab. */
export function ReportButton({
  fetchReport,
  filename,
  label = "Print report",
}: {
  fetchReport: () => Promise<Blob>;
  filename: string;
  label?: string;
}) {
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function open() {
    // Opened before the request so it counts as part of the click, not a blocked popup.
    const tab = window.open("", "_blank");
    tab?.document.write("<p style='font-family:sans-serif'>Preparing report…</p>");
    setIsBusy(true);
    setError(null);
    try {
      const url = URL.createObjectURL(await fetchReport());
      if (tab) {
        tab.location.href = url;
      } else {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
      }
      // The tab has loaded it by then; free the memory.
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      tab?.close();
      setError(errorMessage(err));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Button variant="secondary" size="sm" disabled={isBusy} onClick={open}>
        {isBusy ? "Preparing…" : label}
      </Button>
      {error && <span className="text-sm text-status-cancelled">{error}</span>}
    </span>
  );
}
