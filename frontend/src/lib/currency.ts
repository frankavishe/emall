export function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const amount = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-TZ", {
    style: "currency",
    currency: "TZS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}
