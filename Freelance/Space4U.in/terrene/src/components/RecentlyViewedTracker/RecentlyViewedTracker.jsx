"use client";

import { useEffect, useRef } from "react";
import fetchApi from "@/lib/api";
import { useUser } from "@/lib/hooks";

/**
 * Component to track when a product is viewed.
 * Works for both anonymous and logged-in users.
 */
export default function RecentlyViewedTracker({ sku, variantId }) {
  const { user } = useUser();
  const hasTracked = useRef(false);

  useEffect(() => {
    if (!sku && !variantId) return;
    if (hasTracked.current) return;

    const trackView = async () => {
      try {
        const payload = variantId 
          ? { variant_id: variantId }
          : { product_sku: sku };

        // 204 No Content response is expected, so we handle it gracefully
        const result = await fetchApi("/commerce/recently-viewed/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        
        // Result may be null for 204 responses, which is fine
        hasTracked.current = true;
      } catch (error) {
        // Silently handle errors - don't want to spam console for tracking
        if (error.status !== 204) {
          console.error("Failed to track recently viewed:", error);
        }
      }
    };

    trackView();
  }, [sku, variantId]);

  return null; // This component doesn't render anything
}

