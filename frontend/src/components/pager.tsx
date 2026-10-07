import { Button } from "@/components/ui/button";

/** Previous/Next for a DRF page-number list; renders nothing when there's only one page. */
export function Pager({
  previous,
  next,
  onPrevious,
  onNext,
}: {
  previous: string | null;
  next: string | null;
  onPrevious: () => void;
  onNext: () => void;
}) {
  if (!previous && !next) return null;
  return (
    <div className="flex items-center justify-between">
      <Button variant="secondary" disabled={!previous} onClick={onPrevious}>
        Previous
      </Button>
      <Button variant="secondary" disabled={!next} onClick={onNext}>
        Next
      </Button>
    </div>
  );
}
