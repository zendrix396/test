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

const CartContext = createContext(null);

const normalizeCartResponse = (payload) => {
  if (!payload) return null;
  if (payload.cart) return payload.cart;
  return payload;
};

export const CartProvider = ({ children }) => {
  const [cart, setCart] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState(null);

  const fetchCart = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchApi("/commerce/cart/");
      setCart(normalizeCartResponse(data));
    } catch (err) {
      console.error("[Cart] fetch failed", err);
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  const updateCartState = useCallback((payload) => {
    const normalized = normalizeCartResponse(payload);
    if (normalized) {
      setCart(normalized);
    }
  }, []);

  const runCartMutation = useCallback(async (mutation) => {
    setIsMutating(true);
    setError(null);
    try {
      const response = await mutation();
      updateCartState(response);
      return response;
    } catch (err) {
      console.error("[Cart] mutation failed", err);
      setError(err);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [updateCartState]);

  const openCart = useCallback(() => setIsOpen(true), []);
  const closeCart = useCallback(() => setIsOpen(false), []);
  const toggleCart = useCallback(() => setIsOpen((prev) => !prev), []);

  const addItem = useCallback(
    async (variantId, quantity = 1) => {
      if (!variantId) return;
      const response = await runCartMutation(() =>
        fetchApi("/commerce/cart/", {
          method: "POST",
          body: JSON.stringify({ variant_id: variantId, quantity }),
        })
      );
      openCart();
      return response;
    },
    [runCartMutation, openCart]
  );

  const updateQuantity = useCallback(
    async (variantId, quantity) => {
      if (!variantId) return;
      return runCartMutation(() =>
        fetchApi("/commerce/cart/", {
          method: "PATCH",
          body: JSON.stringify({ variant_id: variantId, quantity }),
        })
      );
    },
    [runCartMutation]
  );

  const removeItem = useCallback(
    async (variantId) => {
      if (!variantId) return;
      return runCartMutation(() =>
        fetchApi("/commerce/cart/", {
          method: "DELETE",
          body: JSON.stringify({ variant_id: variantId }),
        })
      );
    },
    [runCartMutation]
  );

  const setGiftWrap = useCallback(
    async (enabled) => {
      return runCartMutation(() =>
        fetchApi("/commerce/cart/gift-wrap/", {
          method: "PATCH",
          body: JSON.stringify({ gift_wrap: Boolean(enabled) }),
        })
      );
    },
    [runCartMutation]
  );

  const applyCoupon = useCallback(
    async (code) => {
      if (!code) return;
      return runCartMutation(() =>
        fetchApi("/commerce/cart/apply-coupon/", {
          method: "POST",
          body: JSON.stringify({ coupon_code: code }),
        })
      );
    },
    [runCartMutation]
  );

  const removeCoupon = useCallback(async () => {
    return runCartMutation(() =>
      fetchApi("/commerce/cart/apply-coupon/", {
        method: "DELETE",
      })
    );
  }, [runCartMutation]);

  const value = useMemo(
    () => ({
      cart,
      isOpen,
      isLoading,
      isMutating,
      error,
      refresh: fetchCart,
      openCart,
      closeCart,
      toggleCart,
      addItem,
      updateQuantity,
      removeItem,
      setGiftWrap,
      applyCoupon,
      removeCoupon,
    }),
    [
      cart,
      isOpen,
      isLoading,
      isMutating,
      error,
      fetchCart,
      openCart,
      closeCart,
      toggleCart,
      addItem,
      updateQuantity,
      removeItem,
      setGiftWrap,
      applyCoupon,
      removeCoupon,
    ]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCartContext = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCartContext must be used within a CartProvider");
  }
  return context;
};

export default CartContext;

