"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import fetchApi from "@/lib/api";

const WishlistContext = createContext(null);

const normalizeWishlist = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  return [];
};

export const WishlistProvider = ({ children }) => {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState(null);

  const fetchWishlist = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchApi("/commerce/wishlist/");
      setItems(normalizeWishlist(data));
    } catch (err) {
      console.error("[Wishlist] fetch failed", err);
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWishlist();
  }, [fetchWishlist]);

  const mutateWishlist = useCallback(async (mutation) => {
    setIsMutating(true);
    setError(null);
    try {
      const data = await mutation();
      const list = normalizeWishlist(data);
      if (list.length || data?.items?.length === 0) {
        setItems(list);
      }
      return list;
    } catch (err) {
      console.error("[Wishlist] mutation failed", err);
      setError(err);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, []);

  const addItem = useCallback(
    async (variantId) => {
      if (!variantId) return [];
      return mutateWishlist(() =>
        fetchApi("/commerce/wishlist/", {
          method: "POST",
          body: JSON.stringify({ variant_id: variantId }),
        })
      );
    },
    [mutateWishlist]
  );

  const removeItem = useCallback(
    async (variantId) => {
      if (!variantId) return [];
      return mutateWishlist(() =>
        fetchApi("/commerce/wishlist/", {
          method: "DELETE",
          body: JSON.stringify({ variant_id: variantId }),
        })
      );
    },
    [mutateWishlist]
  );

  const isWishlisted = useCallback(
    (variantId) => items.some((entry) => entry?.variant?.id === variantId),
    [items]
  );

  const toggleWishlist = useCallback(
    async (variantId) => {
      if (!variantId) return;
      if (isWishlisted(variantId)) {
        await removeItem(variantId);
      } else {
        await addItem(variantId);
      }
    },
    [addItem, removeItem, isWishlisted]
  );

  const value = useMemo(
    () => ({
      items,
      isLoading,
      isMutating,
      error,
      refresh: fetchWishlist,
      addItem,
      removeItem,
      toggleWishlist,
      isWishlisted,
    }),
    [
      items,
      isLoading,
      isMutating,
      error,
      fetchWishlist,
      addItem,
      removeItem,
      toggleWishlist,
      isWishlisted,
    ]
  );

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
};

export const useWishlistContext = () => {
  const context = useContext(WishlistContext);
  if (!context) {
    throw new Error("useWishlistContext must be used within a WishlistProvider");
  }
  return context;
};

export default WishlistContext;
