"use client";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Nav from "@/components/Nav/Nav";
import ConditionalFooter from "@/components/ConditionalFooter/ConditionalFooter";
import Copy from "@/components/Copy/Copy";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";
import { useWishlistContext } from "@/context/WishlistContext";
import { useCurrencyContext } from "@/context/CurrencyContext";
import { useRouter, useSearchParams } from "next/navigation";
import { FiHeart } from "react-icons/fi";
import "./shop.css";

import SakuraPetals from "@/components/SakuraPetals/SakuraPetals";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

const PAGE_SIZE = 12;

const sortOptionMap = {
  featured: "-created_at",
  priceLowHigh: "price",
  priceHighLow: "-price",
  newest: "-created_at",
  nameAZ: "name",
};

const safeNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const getPriceMeta = (product) => {
  const candidateBase = [];
  const candidateDiscounts = [];
  const candidateDeals = [];

  // Use converted prices if available, otherwise fall back to regular prices
  const basePrice = safeNumber(
    product?.converted_price || product?.variants?.[0]?.converted_price || product?.price
  );
  const discountPrice = safeNumber(
    product?.converted_discount_price || product?.variants?.[0]?.converted_discount_price || product?.discount_price
  );
  const dealPrice = safeNumber(
    product?.converted_deal_price || product?.variants?.[0]?.converted_deal_price || product?.deal_price
  );

  if (basePrice > 0) candidateBase.push(basePrice);
  if (discountPrice > 0) candidateDiscounts.push(discountPrice);
  if (dealPrice > 0) candidateDeals.push(dealPrice);

  if (Array.isArray(product?.variants)) {
    product.variants.forEach((variant) => {
      const variantBase = safeNumber(
        variant?.converted_price || variant?.price
      );
      const variantDiscount = safeNumber(
        variant?.converted_discount_price || variant?.discount_price
      );
      const variantDealPrice = safeNumber(
        variant?.converted_deal_price || variant?.deal_price
      );

      if (variantBase > 0) candidateBase.push(variantBase);
      if (variantDiscount > 0) candidateDiscounts.push(variantDiscount);
      if (variantDealPrice > 0) candidateDeals.push(variantDealPrice);
    });
  }

  // Priority: deal_price > discount_price > base_price
  const display = candidateDeals.length
    ? Math.min(...candidateDeals)
    : candidateDiscounts.length
    ? Math.min(...candidateDiscounts)
    : candidateBase.length
    ? Math.min(...candidateBase)
    : 0;

  const compare = candidateBase.length ? Math.min(...candidateBase) : display;

  return { display, compare, hasDeal: candidateDeals.length > 0, cashback: product?.cashback_amount || (product?.variants?.[0]?.cashback_amount) || null };
};

const deriveCategories = (items = []) => {
  const map = new Map();
  items.forEach((product) => {
    if (product?.category?.slug) {
      map.set(product.category.slug, {
        slug: product.category.slug,
        name: product.category.name,
      });
    }
  });
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
};

const deriveTags = (items = []) => {
  const tagSet = new Set();
  items.forEach((product) => {
    (product?.tags || []).forEach((tag) => {
      if (typeof tag === "string" && tag.trim()) {
        tagSet.add(tag.trim());
      }
    });
  });
  return Array.from(tagSet).sort((a, b) => a.localeCompare(b));
};

const ProductCard = ({ product, onSelect, isNavigating = false }) => {
  const { display, compare, hasDeal, cashback } = getPriceMeta(product);
  const hasDiscount = compare > display;
  const { isWishlisted, toggleWishlist } = useWishlistContext();
  const { formatCurrency, currencySymbol } = useCurrencyContext();

  const imageSources = useMemo(() => {
    const sources = [];

    if (product?.image) {
      sources.push(product.image);
    }

    if (Array.isArray(product?.images)) {
      product.images.forEach((item) => {
        if (item?.image && !sources.includes(item.image)) {
          sources.push(item.image);
        }
      });
    }

    return sources;
  }, [product]);

  const primaryImage = imageSources[0];
  const secondaryImage = imageSources[1];

  const defaultVariant = useMemo(() => {
    if (!Array.isArray(product?.variants) || product.variants.length === 0) {
      return null;
    }
    return (
      product.variants.find((variant) => variant.is_default) || product.variants[0]
    );
  }, [product]);

  const isWishlistedVariant = defaultVariant ? isWishlisted(defaultVariant.id) : false;

  const handleWishlistToggle = useCallback(
    (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!defaultVariant) return;
      toggleWishlist(defaultVariant.id);
    },
    [defaultVariant, toggleWishlist]
  );

  const handleSelect = useCallback(() => {
    if (typeof onSelect === "function") {
      onSelect(product);
    }
  }, [onSelect, product]);

  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        handleSelect();
    }
    },
    [handleSelect]
  );

  return (
    <article
      className={`shop-product-card ${isNavigating ? "is-navigating" : ""}`}
      role="button"
      tabIndex={0}
      onClick={handleSelect}
      onKeyDown={handleKeyDown}
    >
      <button
        type="button"
        className={`shop-product-card-wishlist ${isWishlistedVariant ? "is-active" : ""}`}
        aria-label={isWishlistedVariant ? "Remove from wishlist" : "Add to wishlist"}
        onClick={handleWishlistToggle}
      >
        <FiHeart />
      </button>
      <div
        className={`shop-product-card-media ${
          secondaryImage ? "has-secondary" : ""
        }`}
    >
        {primaryImage ? (
          <>
            <img
              className="shop-product-card-image is-primary"
              src={primaryImage}
              alt={product?.name || "Product image"}
              loading="lazy"
            />
            {secondaryImage && (
              <img
                className="shop-product-card-image is-secondary"
                src={secondaryImage}
                alt={product?.name || "Product alternate view"}
                loading="lazy"
              />
            )}
          </>
        ) : (
          <div className="shop-product-card-placeholder">Image coming soon</div>
        )}
      </div>
      <div className="shop-product-card-body">
        <div className="shop-product-card-header">
          {product?.category?.name && (
            <span className="shop-product-card-category">{product.category.name}</span>
          )}
          <h3>{product?.name}</h3>
        </div>
        {product?.tags && product.tags.length > 0 && (
          <div className="shop-product-card-tags">
            {product.tags.slice(0, 3).map((tag, idx) => (
              <span key={idx} className="shop-product-card-tag">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="shop-product-card-pricing">
          <span
            className={`shop-product-card-price ${
              hasDiscount ? "has-discount" : ""
            }`}
          >
            {formatCurrency(display)}
          </span>
          {hasDiscount && (
            <span className="shop-product-card-price-compare">
              {formatCurrency(compare)}
            </span>
          )}
          {cashback && parseFloat(cashback) > 0 && (
            <span className="shop-product-card-cashback">
              {currencySymbol}{parseFloat(cashback).toFixed(0)} Cashback
            </span>
          )}
        </div>
      </div>
    </article>
  );
};

const ShopPage = () => {
  const searchParams = useSearchParams();
  const { updateCurrencyFromProduct } = useCurrencyContext();
  const [products, setProducts] = useState([]);
  const [availableCategories, setAvailableCategories] = useState([]);
  const [availableTags, setAvailableTags] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState(() => {
    const categoryFromUrl = searchParams?.get("category");
    return categoryFromUrl || "all";
  });
  const [selectedTags, setSelectedTags] = useState([]);
  const [sortBy, setSortBy] = useState(() => {
    const sortFromUrl = searchParams?.get("sort");
    if (sortFromUrl && sortOptionMap[sortFromUrl]) {
      return sortFromUrl;
    }
    return "featured";
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [navigatingProduct, setNavigatingProduct] = useState(null);
  const router = useRouter();
  const handleProductSelect = useCallback(
    (product) => {
      if (!product?.sku) return;
      setNavigatingProduct(product.sku);
      router.push(`/shop/${product.sku}`);
      // Reset after navigation completes or fails
      setTimeout(() => setNavigatingProduct(null), 3000);
    },
    [router]
  );

  const hasBootstrapped = useRef(false);
  const productsTopRef = useRef(null);

  const fetchProducts = useCallback(async ({ category, tags, search, ordering } = {}) => {
    const params = new URLSearchParams();
    params.set("page_size", "200");

    if (category) params.set("category", category);
    if (tags && tags.length) params.set("tags", tags.join(","));
    if (search) params.set("search", search);
    if (ordering) params.set("ordering", ordering);

    const query = params.toString();
    const url = `${API_BASE_URL}/products/${query ? `?${query}` : ""}`;

    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const message = `Failed to load products (${response.status})`;
      throw new Error(message);
    }

    const data = await response.json();
    return data.results || data;
  }, []);

  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
    }, 300);

    return () => clearTimeout(handle);
  }, [searchQuery]);

  useEffect(() => {
    const categoryFromUrl = searchParams?.get("category");
    if (categoryFromUrl) {
      setActiveCategory(categoryFromUrl);
    } else if (!categoryFromUrl && activeCategory !== "all") {
      setActiveCategory("all");
    }

    const sortFromUrl = searchParams?.get("sort");
    if (sortFromUrl && sortOptionMap[sortFromUrl]) {
      setSortBy(sortFromUrl);
    }
  }, [searchParams]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeCategory, selectedTags, debouncedSearch, sortBy]);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      setIsLoading(true);
      setIsError(false);
      try {
        // Apply category filter from URL if present
        const categoryFilter = activeCategory === "all" ? undefined : activeCategory;
        const items = await fetchProducts({ category: categoryFilter });
        if (cancelled) return;
        setProducts(items);
        setAvailableCategories(deriveCategories(items));
        setAvailableTags(deriveTags(items));
        // Update currency from first product if available
        if (items && items.length > 0) {
          updateCurrencyFromProduct(items[0]);
        }
        hasBootstrapped.current = true;
        setCurrentPage(1);
      } catch (error) {
        if (!cancelled) setIsError(true);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [fetchProducts, activeCategory]);

  useEffect(() => {
    if (!hasBootstrapped.current) return;

    let cancelled = false;

    const applyFilters = async () => {
      setIsLoading(true);
      setIsError(false);
      try {
        const ordering = sortOptionMap[sortBy];
        const categoryFilter = activeCategory === "all" ? undefined : activeCategory;
        const items = await fetchProducts({
          category: categoryFilter,
          tags: selectedTags,
          search: debouncedSearch || undefined,
          ordering,
        });
        if (!cancelled) {
          setProducts(items);
          // Update currency from first product if available
          if (items && items.length > 0) {
            updateCurrencyFromProduct(items[0]);
          }
        }
      } catch (error) {
        if (!cancelled) setIsError(true);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    applyFilters();

    return () => {
      cancelled = true;
    };
  }, [activeCategory, selectedTags, debouncedSearch, sortBy, fetchProducts]);

  useEffect(() => {
    setCurrentPage((prev) => {
      const maxPage = Math.max(1, Math.ceil((products?.length || 0) / PAGE_SIZE));
      return Math.min(prev, maxPage);
    });
  }, [products]);

  const categories = useMemo(() => {
    if (availableCategories.length) return availableCategories;
    return deriveCategories(products);
  }, [availableCategories, products]);

  const tags = useMemo(() => {
    if (availableTags.length) return availableTags;
    return deriveTags(products);
  }, [availableTags, products]);

  const handleCategoryClick = useCallback((slug) => {
    if (!slug || slug === "all") {
      setActiveCategory("all");
      return;
    }
    setActiveCategory((previous) => (previous === slug ? "all" : slug));
  }, []);

  const handleTagToggle = useCallback((tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag)
        ? prev.filter((existing) => existing !== tag)
        : [...prev, tag]
    );
  }, []);

  const handleClearTags = useCallback(() => {
    setSelectedTags([]);
  }, []);

  const totalProducts = products.length;
  const totalPages = Math.max(1, Math.ceil(totalProducts / PAGE_SIZE));
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const paginatedProducts = products.slice(startIndex, startIndex + PAGE_SIZE);

  const handlePageChange = useCallback((page) => {
    setCurrentPage(page);
    if (productsTopRef.current) {
      productsTopRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  return (
    <>
      <SakuraPetals />
      <div className="page shop">
        <section className="shop-hero">
          <div className="container">
            <div className="shop-hero-header">
              <Copy delay={0.1}>
                <h1>Shop the Space4U Collection</h1>
              </Copy>
            </div>

            {categories.length > 0 && (
              <div className="shop-category-scroll">
                <div className="shop-category-grid" role="list">
                  <button
                    type="button"
                    className={`shop-category-card ${
                      activeCategory === "all" ? "is-active" : ""
                    }`}
                    onClick={() => handleCategoryClick("all")}
                  >
                    All Collections
                  </button>
                  {categories.map((category) => (
                    <button
                      key={category.slug}
                      type="button"
                      className={`shop-category-card ${
                        activeCategory === category.slug ? "is-active" : ""
                      }`}
                      onClick={() => handleCategoryClick(category.slug)}
                    >
                      {category.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="shop-controls">
              <div className="shop-controls-bar">
                <label className="shop-search">
                  <span className="shop-search-label">Search</span>
                  <input
                    type="search"
                    placeholder="Search by name, franchise, or keyword"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                  />
                </label>
                <label className="shop-sort">
                  <span className="shop-sort-label">Sort by</span>
                  <select
                    value={sortBy}
                    onChange={(event) => setSortBy(event.target.value)}
                  >
                    <option value="featured">Featured</option>
                    <option value="priceLowHigh">Price: Low to High</option>
                    <option value="priceHighLow">Price: High to Low</option>
                    <option value="newest">Newest Arrivals</option>
                    <option value="nameAZ">Name: A to Z</option>
                  </select>
                </label>
              </div>
            </div>

            {tags.length > 0 && (
              <div className="shop-tag-chips" role="list">
                {tags.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    className={`shop-tag ${
                      selectedTags.includes(tag) ? "is-active" : ""
                    }`}
                    onClick={() => handleTagToggle(tag)}
                  >
                    #{tag}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
        <section className="shop-products" ref={productsTopRef}>
          <div className="container">
            <div className="shop-results-meta">
              <span>
                {isLoading
                  ? "Loading merchandise…"
                  : `${totalProducts} item${totalProducts === 1 ? "" : "s"} available`}
              </span>
              {selectedTags.length > 0 && (
                <button
                  type="button"
                  className="shop-clear-tags"
                  onClick={handleClearTags}
                >
                  Clear tags
                </button>
              )}
            </div>

            {isError && !isLoading && (
              <div className="shop-products-empty">
                <p>We couldn’t load the catalogue right now. Please try again shortly.</p>
              </div>
            )}

            {!isError && (
              <>
                {isLoading ? (
                  <div className="shop-products-grid is-loading">
                    {Array.from({ length: 6 }).map((_, index) => (
                      <div key={index} className="shop-product-card skeleton"></div>
                    ))}
                  </div>
                ) : paginatedProducts.length > 0 ? (
                  <div className="shop-products-grid">
                    {paginatedProducts.map((product) => (
                      <ProductCard
                        key={product?.id || product?.sku || product?.name}
                        product={product}
                        onSelect={handleProductSelect}
                        isNavigating={navigatingProduct === product.sku}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="shop-products-empty">
                    <p>
                      Nothing matches your filters just yet. Try changing your category or tags to explore more drops.
                    </p>
                  </div>
                )}
              </>
            )}
            {!isLoading && !isError && totalPages > 1 && (
              <div className="shop-pagination" role="navigation" aria-label="Product pagination">
                <button
                  type="button"
                  className="shop-pagination-btn"
                  onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Prev
                </button>
                <div className="shop-pagination-pages">
                  {Array.from({ length: totalPages }).map((_, index) => {
                    const page = index + 1;
                    return (
                      <button
                        key={page}
                        type="button"
                        className={`shop-pagination-page ${
                          currentPage === page ? "is-active" : ""
                        }`}
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </button>
                    );
                  })}
                </div>
                <button
                  type="button"
                  className="shop-pagination-btn"
                  onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </section>

        <section className="shop-cta">
          <div className="container">
            <Copy delay={0.1}>
              <h2>Hunting for something ultra-rare?</h2>
            </Copy>
            <Copy delay={0.15}>
              <p>
                Tell us what you're after and our team will source exclusive drops, special editions, and custom builds just for you.
              </p>
            </Copy>
            <AnimatedButton
              label="Talk to us"
              route="/connect"
              animateOnScroll={false}
            />
          </div>
        </section>
      </div>
    </>
  );
};

export default ShopPage;

