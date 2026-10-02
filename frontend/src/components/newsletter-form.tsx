"use client";

/** Newsletter signup. Not wired to a backend yet — submit is a no-op. */
export function NewsletterForm() {
  return (
    <form className="flex" onSubmit={(event) => event.preventDefault()}>
      <label htmlFor="newsletter-email" className="sr-only">
        Email address
      </label>
      <input
        id="newsletter-email"
        type="email"
        required
        placeholder="Enter email..."
        className="w-full min-w-0 rounded-l-control border-0 bg-white/10 px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-400"
      />
      <button
        type="submit"
        className="whitespace-nowrap rounded-r-control bg-teal-400 px-4 py-2 text-xs font-semibold text-navy-900 transition-colors hover:bg-teal-300"
      >
        Join
      </button>
    </form>
  );
}
