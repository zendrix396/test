"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const CurrencyContext = createContext(null);

export const CurrencyProvider = ({ children }) => {
  const [currency, setCurrency] = useState("INR");
  const [currencySymbol, setCurrencySymbol] = useState("₹");

  // Currency symbol mapping
  const currencySymbols = {
    INR: "₹",
    USD: "$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    CAD: "C$",
    AUD: "A$",
    CHF: "CHF",
    CNY: "¥",
    KRW: "₩",
    SGD: "S$",
    HKD: "HK$",
    AED: "د.إ",
    SAR: "﷼",
    BRL: "R$",
    MXN: "$",
    ARS: "$",
    ZAR: "R",
    NZD: "NZ$",
    SEK: "kr",
    NOK: "kr",
    DKK: "kr",
    PLN: "zł",
  };

  // Update currency from product data
  const updateCurrencyFromProduct = useCallback((product) => {
    if (!product) return;

    // Check if product has currency info (from variant or product level)
    const detectedCurrency =
      product.variants?.[0]?.currency ||
      product.currency ||
      product.variant?.currency;

    const detectedSymbol =
      product.variants?.[0]?.currency_symbol ||
      product.currency_symbol ||
      product.variant?.currency_symbol;

    if (detectedCurrency && detectedCurrency !== currency) {
      setCurrency(detectedCurrency);
      setCurrencySymbol(
        detectedSymbol || currencySymbols[detectedCurrency] || detectedCurrency
      );
    }
  }, [currency, currencySymbols]);

  // Format currency based on detected currency
  const formatCurrency = useCallback(
    (value) => {
      if (value === null || value === undefined) return "";
      const num = Number(value);
      if (Number.isNaN(num)) return String(value);

      // Use Intl.NumberFormat with detected currency
      const locale = currency === "INR" ? "en-IN" : "en-US";
      const formatter = new Intl.NumberFormat(locale, {
        style: "currency",
        currency: currency,
        maximumFractionDigits: currency === "JPY" ? 0 : 2,
      });

      return formatter.format(num);
    },
    [currency]
  );

  const value = useMemo(
    () => ({
      currency,
      currencySymbol,
      formatCurrency,
      updateCurrencyFromProduct,
    }),
    [currency, currencySymbol, formatCurrency, updateCurrencyFromProduct]
  );

  return (
    <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>
  );
};

export const useCurrencyContext = () => {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error("useCurrencyContext must be used within a CurrencyProvider");
  }
  return context;
};

export default CurrencyContext;

