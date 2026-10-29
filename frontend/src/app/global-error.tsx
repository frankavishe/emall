"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { themeInitScript } from "@/lib/theme-script";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

/** Replaces the root layout when it fails, so it brings its own document, styles and theme. */
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <title>Something went wrong · MangiMall</title>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="flex min-h-full flex-col bg-canvas">
        <ErrorState
          code="500"
          title="Something went wrong"
          description="We couldn't load MangiMall right now. Please try again in a moment."
          actions={
            <>
              <Button onClick={() => retry()}>Try again</Button>
              <Button asChild variant="secondary">
                {/* Plain anchor: a full reload is the safest way out of a broken root layout. */}
                {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
                <a href="/">Go home</a>
              </Button>
            </>
          }
        >
          {error.digest && (
            <p className="font-mono text-xs text-text-muted">Reference: {error.digest}</p>
          )}
        </ErrorState>
      </body>
    </html>
  );
}
