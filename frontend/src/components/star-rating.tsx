type StarRatingProps = {
  rating: number | null;
  reviewCount: number;
};

export function StarRating({ rating, reviewCount }: StarRatingProps) {
  if (rating === null) {
    return <span className="text-sm text-text-muted">No reviews yet</span>;
  }

  const rounded = Math.round(rating);

  return (
    <span className="inline-flex items-center gap-1 text-sm">
      <span aria-hidden="true" className="text-yellow-500">
        {[1, 2, 3, 4, 5].map((star) => (star <= rounded ? "★" : "☆")).join("")}
      </span>
      <span className="text-text-muted">
        {rating.toFixed(1)} ({reviewCount} review{reviewCount === 1 ? "" : "s"})
      </span>
    </span>
  );
}
