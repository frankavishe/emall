import Image from "next/image";
import { cn } from "@/lib/cn";

// Intrinsic size of the cropped assets in public/brand.
const WIDTH = 428;
const HEIGHT = 106;

type BrandLogoProps = {
  /** `auto` follows the site theme; `light` (white wordmark) is for always-dark surfaces. */
  variant?: "auto" | "light";
  /** Size via height, e.g. `h-7` — width follows the aspect ratio. */
  className?: string;
  /** Above-the-fold logo. Uses `fetchPriority` rather than `preload` so the hidden theme variant isn't fetched too. */
  important?: boolean;
};

/** The MangiMall wordmark (bag-on-truck mark + "MANGIMALL"). */
export function BrandLogo({ variant = "auto", className, important }: BrandLogoProps) {
  const fetchPriority = important ? "high" : undefined;
  const light = (
    <Image
      src="/brand/mangimall-logo-light.png"
      alt="MangiMall"
      width={WIDTH}
      height={HEIGHT}
      fetchPriority={fetchPriority}
      className={cn("w-auto", variant === "auto" && "hidden dark:block", className)}
    />
  );
  if (variant === "light") return light;
  return (
    <>
      <Image
        src="/brand/mangimall-logo.png"
        alt="MangiMall"
        width={WIDTH}
        height={HEIGHT}
        fetchPriority={fetchPriority}
        className={cn("w-auto dark:hidden", className)}
      />
      {light}
    </>
  );
}
