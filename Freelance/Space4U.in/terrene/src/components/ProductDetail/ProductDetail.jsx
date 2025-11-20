"use client";

import "./ProductDetail.css";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { FiHeart } from "react-icons/fi";
import { IoIosArrowBack } from "react-icons/io";

import { useCartContext } from "@/context/CartContext";
import { useWishlistContext } from "@/context/WishlistContext";
import { useCurrencyContext } from "@/context/CurrencyContext";
import { useUser } from "@/lib/hooks";
import fetchApi from "@/lib/api";

const clampRating = (rating) => {
  const value = Number(rating);
  if (Number.isNaN(value)) return 0;
  return Math.min(5, Math.max(0, value));
};

const renderStars = (value) => {
  const rounded = Math.round(clampRating(value));
  return Array.from({ length: 5 }).map((_, index) => (
    <span key={index} className={index < rounded ? "is-filled" : ""}>
      ★
    </span>
  ));
};

const formatDate = (value) => {
  if (!value) return "";
  try {
    const date = new Date(value);
    return date.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch (error) {
    return value;
  }
};

const ProductDetail = ({ product, related = [], loyaltyConfig = null, reviews: initialReviews = [] }) => {
  const router = useRouter();
  const { user } = useUser();
  const { addItem, openCart } = useCartContext();
  const { isWishlisted, toggleWishlist } = useWishlistContext();
  const { formatCurrency, currencySymbol, updateCurrencyFromProduct } = useCurrencyContext();

  const [reviews, setReviews] = useState(initialReviews);
  const [showAllReviews, setShowAllReviews] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);

  const defaultVariantId = useMemo(() => {
    const variants = product?.variants || [];
    if (!variants.length) return null;
    return variants.find((variant) => variant.is_default)?.id || variants[0].id;
  }, [product]);

  const [selectedVariantId, setSelectedVariantId] = useState(defaultVariantId);
  const [quantity, setQuantity] = useState(1);
  const [activeImage, setActiveImage] = useState(0);
  const [statusMessage, setStatusMessage] = useState(null);
  const [carouselIndex, setCarouselIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(true);

  const variants = product?.variants || [];
  const selectedVariant = useMemo(
    () => variants.find((variant) => variant.id === selectedVariantId) || null,
    [variants, selectedVariantId]
  );

  useEffect(() => {
    setSelectedVariantId(defaultVariantId);
  }, [defaultVariantId]);

  useEffect(() => {
    setActiveImage(0);
    setQuantity(1);
  }, [selectedVariantId]);

  // Update currency when product loads
  useEffect(() => {
    if (product) {
      updateCurrencyFromProduct(product);
    }
  }, [product, updateCurrencyFromProduct]);

  const galleryImages = useMemo(() => {
    const images = [];
    const seen = new Set();
    
    if (product?.image && !seen.has(product.image)) {
      images.push(product.image);
      seen.add(product.image);
    }
    
    (product?.images || []).forEach((img) => {
      if (img?.image && !seen.has(img.image)) {
        images.push(img.image);
        seen.add(img.image);
      }
    });
    
    if (!images.length) {
      images.push(null);
    }
    return images;
  }, [product]);

  const reviewList = useMemo(() => (Array.isArray(reviews) ? reviews : []), [reviews]);
  const reviewCount = reviewList.length;
  const averageRating = useMemo(() => {
    if (reviewCount === 0) {
      return clampRating(product?.average_rating);
    }
    const total = reviewList.reduce((acc, review) => acc + clampRating(review.rating), 0);
    return clampRating(total / reviewCount);
  }, [reviewList, reviewCount, product]);
  
  const displayedReviews = useMemo(() => {
    return showAllReviews ? reviewList : reviewList.slice(0, 4);
  }, [reviewList, showAllReviews]);

  // Detect screen size for responsive carousel
  const [maxVisible, setMaxVisible] = useState(4);
  
  useEffect(() => {
    const updateMaxVisible = () => {
      if (window.innerWidth <= 768) {
        setMaxVisible(1);
      } else if (window.innerWidth <= 1024) {
        setMaxVisible(3);
      } else {
        setMaxVisible(4);
      }
    };
    
    updateMaxVisible();
    window.addEventListener('resize', updateMaxVisible);
    return () => window.removeEventListener('resize', updateMaxVisible);
  }, []);
  
  const canSlide = related && related.length > maxVisible;
  const extendedRelated = useMemo(() => {
    if (!related?.length) return [];
    if (!canSlide) return related;
    return [...related, ...related.slice(0, maxVisible)];
  }, [related, canSlide, maxVisible]);

  useEffect(() => {
    setCarouselIndex(0);
    setIsTransitioning(true);
  }, [related, maxVisible, canSlide]);

  useEffect(() => {
    if (!canSlide) return undefined;
    const timer = setInterval(() => {
      setCarouselIndex((prev) => prev + 1);
    }, 5000);
    return () => clearInterval(timer);
  }, [canSlide]);

  useEffect(() => {
    if (!isTransitioning) {
      requestAnimationFrame(() => setIsTransitioning(true));
    }
  }, [isTransitioning]);

  const handleCarouselTransitionEnd = () => {
    if (!canSlide) return;
    if (carouselIndex >= related.length) {
      setIsTransitioning(false);
      setCarouselIndex(0);
    }
  };

  const trackStyle = useMemo(() => {
    const visible = Math.max(1, maxVisible);
    if (!extendedRelated.length) {
      return {
        "--visible-count": visible,
      };
    }

    // Calculate card width including gap
    const cardWidthPercent = 100 / visible;
    // Calculate translate amount - move by one card width at a time
    const translatePercent = carouselIndex * cardWidthPercent;

    return {
      "--visible-count": visible,
      transform: `translateX(-${translatePercent}%)`,
      transition: isTransitioning ? "transform 0.8s cubic-bezier(0.83, 0, 0.17, 1)" : "none",
    };
  }, [extendedRelated.length, carouselIndex, maxVisible, isTransitioning]);

  const isWishlistedVariant = selectedVariant ? isWishlisted(selectedVariant.id) : false;
  const isOutOfStock = (selectedVariant?.stock ?? 0) <= 0;

  const loyaltyPoints = useMemo(() => {
    if (!loyaltyConfig?.enabled || !selectedVariant) return 0;
    // Use converted price if available, otherwise regular price
    const amount = Number(
      selectedVariant.converted_deal_price || 
      selectedVariant.converted_discount_price || 
      selectedVariant.converted_price ||
      selectedVariant.deal_price || 
      selectedVariant.discount_price || 
      selectedVariant.price || 0
    );
    return Math.round(amount * (loyaltyConfig.points_per_currency || 0));
  }, [selectedVariant, loyaltyConfig]);

  const handleVariantSelect = useCallback((variantId) => {
    setSelectedVariantId(variantId);
  }, []);

  const incrementQuantity = useCallback(() => {
    setQuantity((prev) => Math.min(10, prev + 1));
  }, []);

  const decrementQuantity = useCallback(() => {
    setQuantity((prev) => Math.max(1, prev - 1));
  }, []);

  const handleAddToCart = useCallback(
    async (navigateAfter = false) => {
      if (!selectedVariant || isOutOfStock) {
        setStatusMessage({ type: "error", message: "This variant is currently unavailable." });
        return;
      }

      try {
        await addItem(selectedVariant.id, quantity);
        if (navigateAfter) {
          setStatusMessage(null);
          router.push("/checkout");
          return;
        }
        openCart();
        setStatusMessage({ type: "success", message: "Added to cart." });
      } catch (error) {
        setStatusMessage({
          type: "error",
          message: error?.message || "Unable to add this item to cart.",
        });
      }
    },
    [addItem, selectedVariant, isOutOfStock, quantity, openCart, router]
  );

  const handleWishlistToggle = useCallback(() => {
    if (!selectedVariant) return;
    toggleWishlist(selectedVariant.id);
  }, [selectedVariant, toggleWishlist]);

  const handleBack = useCallback(() => {
    router.back();
  }, [router]);

  const offers = useMemo(() => {
    if (product?.tags?.length) {
      return product.tags.slice(0, 4).map((tag) => `Exclusive: ${tag}`);
    }
    return [
      "Snapmint instalments available on checkout.",
      "Free collectible stickers on orders over ₹999.",
      "Flat ₹100 off on prepaid orders above ₹1500.",
    ];
  }, [product]);

  const shippingInfo = useMemo(
    () => [
      "Dispatched in 2-4 business days.",
      "Express shipping upgrades available at checkout.",
      "Hassle-free returns within 7 days of delivery.",
    ],
    []
  );

  const additionalInfo = useMemo(() => {
    const data = [];
    if (selectedVariant?.sku) {
      data.push({ label: "Variant SKU", value: selectedVariant.sku });
    }
    if (product?.sku) {
      data.push({ label: "Product SKU", value: product.sku });
    }
    if (product?.category?.name) {
      data.push({ label: "Category", value: product.category.name });
    }
    if (product?.tags?.length) {
      data.push({ label: "Tags", value: product.tags.join(", ") });
    }
    return data;
  }, [selectedVariant, product]);

  // Use converted prices if available, otherwise fall back to regular prices
  const currentPrice = selectedVariant?.converted_deal_price || 
    selectedVariant?.converted_discount_price || 
    selectedVariant?.converted_price ||
    selectedVariant?.deal_price || 
    selectedVariant?.discount_price || 
    selectedVariant?.price || 
    product?.converted_deal_price ||
    product?.converted_discount_price ||
    product?.converted_price ||
    product?.deal_price ||
    product?.discount_price || 
    product?.price;
  const comparePrice = (selectedVariant?.converted_deal_price || selectedVariant?.converted_discount_price || selectedVariant?.deal_price || selectedVariant?.discount_price) 
    ? (selectedVariant?.converted_price || selectedVariant?.price)
    : (product?.converted_deal_price || product?.converted_discount_price || product?.deal_price || product?.discount_price) 
    ? (product?.converted_price || product?.price)
    : null;
  const cashbackAmount = selectedVariant?.cashback_amount || product?.cashback_amount || null;

  const handleReviewSubmitted = useCallback(async () => {
    // Refresh reviews by fetching them again
    try {
      const data = await fetchApi(`/products/${product.id}/reviews/`);
      setReviews(Array.isArray(data) ? data : []);
      setShowReviewForm(false);
    } catch (error) {
      console.error("Failed to refresh reviews:", error);
    }
  }, [product]);

  return (
    <div className="product-detail">
      <div className="product-detail-header">
        <button type="button" className="product-detail-back" onClick={handleBack}>
          <IoIosArrowBack />
          Back to shop
        </button>
        {product?.category?.name && <span className="product-detail-category">{product.category.name}</span>}
      </div>

      <div className="product-detail-grid">
        <div className="product-detail-gallery">
          <div className="product-detail-gallery-main">
            {galleryImages[activeImage] ? (
              <img src={galleryImages[activeImage]} alt={product?.name || "Product image"} />
            ) : (
              <div className="product-detail-gallery-placeholder">Image coming soon</div>
            )}
          </div>
          <div className="product-detail-thumbs">
            {galleryImages.map((src, index) => (
              <button
                key={`${src}-${index}`}
                type="button"
                className={`product-detail-thumb ${index === activeImage ? "is-active" : ""}`}
                onClick={() => setActiveImage(index)}
              >
                {src ? (
                  <img src={src} alt={`${product?.name || "Product"} view ${index + 1}`} />
                ) : (
                  <span>No image</span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="product-detail-info">
          <div className="product-detail-title-row">
            <h1>{product?.name}</h1>
            <button
              type="button"
              className={`product-detail-wishlist ${isWishlistedVariant ? "is-active" : ""}`}
              onClick={handleWishlistToggle}
              aria-label={isWishlistedVariant ? "Remove from wishlist" : "Add to wishlist"}
            >
              <FiHeart />
            </button>
          </div>

          {averageRating > 0 && (
            <p className="product-detail-rating">
              <span className="product-detail-rating-stars">{renderStars(averageRating)}</span>
              <span>
                {averageRating.toFixed(1)} · {reviewCount || 0} review{reviewCount === 1 ? "" : "s"}
              </span>
            </p>
          )}

          <div className="product-detail-pricing">
            <span className="product-detail-price">{formatCurrency(currentPrice)}</span>
            {comparePrice && (selectedVariant?.deal_price || selectedVariant?.discount_price || product?.deal_price || product?.discount_price) && (
              <span className="product-detail-compare">{formatCurrency(comparePrice)}</span>
            )}
            {cashbackAmount && parseFloat(cashbackAmount) > 0 && (
              <span className="product-detail-cashback">
                {currencySymbol}{parseFloat(cashbackAmount).toFixed(0)} Cashback
              </span>
            )}
          </div>

          {loyaltyPoints > 0 && (
            <p className="product-detail-loyalty">Earn up to {loyaltyPoints} loyalty points on this drop.</p>
          )}

          {variants.length > 1 && (
            <div className="product-detail-variants">
              <p>Choose a variant</p>
              <div className="product-detail-variant-grid">
                {variants.map((variant) => (
                  <button
                    key={variant.id}
                    type="button"
                    className={`product-detail-variant ${variant.id === selectedVariantId ? "is-active" : ""}`}
                    onClick={() => handleVariantSelect(variant.id)}
                  >
                    <span>{variant.name}</span>
                    <small>{formatCurrency(variant.converted_deal_price || variant.converted_discount_price || variant.converted_price || variant.deal_price || variant.discount_price || variant.price)}</small>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="product-detail-quantity">
            <p>Quantity</p>
            <div className="product-detail-qty-control">
              <button type="button" onClick={decrementQuantity} disabled={quantity <= 1}>
                −
              </button>
              <span>{quantity}</span>
              <button type="button" onClick={incrementQuantity}>
                +
              </button>
            </div>
          </div>

          <div className="product-detail-actions">
            <button
              type="button"
              className="product-detail-add"
              onClick={() => handleAddToCart(false)}
              disabled={isOutOfStock}
            >
              {isOutOfStock ? "Out of stock" : "Add to cart"}
            </button>
            <button
              type="button"
              className="product-detail-buy"
              onClick={() => handleAddToCart(true)}
              disabled={isOutOfStock}
            >
              Buy it now
            </button>
          </div>

          {statusMessage && (
            <p className={`product-detail-status is-${statusMessage.type}`}>{statusMessage.message}</p>
          )}

          <div className="product-detail-accordion">
            <details open>
              <summary>Description</summary>
              <p>
                {product?.description ||
                  "This collectible is crafted for fans and curators alike. Expect premium build quality and carefully curated finishes."}
              </p>
            </details>
            <details>
              <summary>Offers</summary>
              <ul>
                {offers.map((offer, idx) => (
                  <li key={idx}>{offer}</li>
                ))}
              </ul>
            </details>
            <details>
              <summary>Shipping & return</summary>
              <ul>
                {shippingInfo.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </details>
            <details>
              <summary>Additional info</summary>
              <ul>
                {additionalInfo.length ? (
                  additionalInfo.map((entry) => (
                    <li key={entry.label}>
                      <strong>{entry.label}:</strong> {entry.value}
                    </li>
                  ))
                ) : (
                  <li>Ready to ship from our Lucknow studio.</li>
                )}
              </ul>
            </details>
          </div>
        </div>
      </div>

      <section className="product-detail-related">
        <div className="product-detail-related-header">
          <h2>Related products</h2>
        </div>
        {!related?.length ? (
          <p className="product-detail-related-empty">More drops incoming soon.</p>
        ) : canSlide ? (
          <div className="product-detail-related-window">
            <div
              className="product-detail-related-track"
              style={trackStyle}
              onTransitionEnd={handleCarouselTransitionEnd}
            >
              {extendedRelated.map((item, index) => {
                const image =
                  item.image || (Array.isArray(item.images) && item.images[0]?.image) || null;
                const tags = Array.isArray(item.tags)
                  ? item.tags
                  : typeof item.tags === "string"
                  ? item.tags.split(",").map((tag) => tag.trim())
                  : [];
                return (
                  <button
                    key={`${item.sku || item.id}-${index}`}
                    type="button"
                    className="product-detail-related-card"
                    onClick={() => router.push(`/shop/${item.sku}`)}
                  >
                    {image ? (
                      <img src={image} alt={item.name} loading="lazy" />
                    ) : (
                      <span className="product-detail-related-placeholder">No image</span>
                    )}
                    <div className="product-detail-related-body">
                      <div className="product-detail-related-top">
                        <p>{item.name}</p>
                        <span>{formatCurrency(item.variants?.[0]?.converted_deal_price || item.variants?.[0]?.converted_discount_price || item.variants?.[0]?.converted_price || item.deal_price || item.discount_price || item.price || 0)}</span>
                      </div>
                      {tags.length > 0 && (
                        <div className="product-detail-related-tags">
                          {tags.slice(0, 3).map((tag) => (
                            <span key={`${tag}-${index}`}>#{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="product-detail-related-grid">
            {related.map((item) => {
              const image = item.image || (Array.isArray(item.images) && item.images[0]?.image) || null;
              const tags = Array.isArray(item.tags)
                ? item.tags
                : typeof item.tags === "string"
                ? item.tags.split(",").map((tag) => tag.trim())
                : [];
              return (
                <button
                  key={item.id || item.sku}
                  type="button"
                  className="product-detail-related-card"
                  onClick={() => router.push(`/shop/${item.sku}`)}
                >
                  {image ? (
                    <img src={image} alt={item.name} loading="lazy" />
                  ) : (
                    <span className="product-detail-related-placeholder">No image</span>
                  )}
                  <div className="product-detail-related-body">
                    <div className="product-detail-related-top">
                      <p>{item.name}</p>
                      <span>{formatCurrency(item.variants?.[0]?.converted_discount_price || item.variants?.[0]?.converted_price || item.discount_price || item.price || 0)}</span>
                    </div>
                    {tags.length > 0 && (
                      <div className="product-detail-related-tags">
                        {tags.slice(0, 3).map((tag) => (
                          <span key={tag}>#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <section className="product-detail-reviews">
        <ReviewsSection 
            reviews={reviews} 
            averageRating={averageRating}
            reviewCount={reviewCount}
            product={product}
            onReviewSubmitted={handleReviewSubmitted}
        />
      </section>
    </div>
  );
};

const ReviewsSection = ({ reviews, averageRating, reviewCount, product, onReviewSubmitted }) => {
    const { user } = useUser();
    const [showReviewForm, setShowReviewForm] = useState(false);

    const handleReviewSubmittedWithClose = useCallback(async () => {
        if (onReviewSubmitted) {
            await onReviewSubmitted();
        }
        setShowReviewForm(false);
    }, [onReviewSubmitted]);

    const ratingsBreakdown = useMemo(() => {
        const breakdown = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
        reviews.forEach(review => {
            const rating = Math.round(clampRating(review.rating));
            if (breakdown[rating] !== undefined) {
                breakdown[rating]++;
            }
        });
        return Object.entries(breakdown).map(([stars, count]) => ({
            stars: parseInt(stars),
            count,
            percentage: reviewCount > 0 ? (count / reviewCount) * 100 : 0,
        })).reverse();
    }, [reviews, reviewCount]);

    return (
        <>
            <div className="product-detail-reviews-header">
              <h2>Reviews</h2>
              <div className="product-detail-reviews-summary">
                <div className="product-detail-reviews-score">{averageRating.toFixed(1)}</div>
                <div className="product-detail-reviews-stars">{renderStars(averageRating)}</div>
                <p>{reviewCount || 0} review{reviewCount === 1 ? "" : "s"}</p>
              </div>
            </div>

            <div className="reviews-layout">
                <div className="reviews-summary-bars">
                    {ratingsBreakdown.map(item => (
                        <div key={item.stars} className="reviews-bar-row">
                            <span>{item.stars} star{item.stars > 1 && 's'}</span>
                            <div className="reviews-bar-container">
                                <div className="reviews-bar" style={{ width: `${item.percentage}%` }}></div>
                            </div>
                            <span>{item.percentage.toFixed(0)}%</span>
                        </div>
                    ))}
                </div>
                <div className="reviews-main-content">
                    {user && (
                        <div className="product-detail-reviews-actions">
                            <button type="button" onClick={() => setShowReviewForm(!showReviewForm)}>
                                {showReviewForm ? "Cancel" : "Write a review"}
                            </button>
                        </div>
                    )}

                    {showReviewForm && user && <ReviewForm product={product} onReviewSubmitted={handleReviewSubmittedWithClose} />}

                    {reviews.length > 0 ? (
                      <div className="product-detail-reviews-grid">
                        {reviews.map((review) => (
                          <article key={review.id} className="product-detail-review-card">
                            <div className="product-detail-review-card-header">
                                <span className="product-detail-review-author">{review.user_name || "Anonymous"}</span>
                                <div className="product-detail-review-stars">{renderStars(review.rating)}</div>
                            </div>
                            {review.image && <img src={review.image} alt="Review" className="product-detail-review-image" />}
                            {review.title && <h3>{review.title}</h3>}
                            {review.body && <p>{review.body}</p>}
                            <div className="product-detail-review-meta">
                              {review.created_at && <span>{formatDate(review.created_at)}</span>}
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                        !showReviewForm && (
                            !user 
                                ? <GuestReviewPrompt />
                                : <p className="product-detail-reviews-empty">No reviews yet. Be the first to drop your thoughts.</p>
                        )
                    )}
                </div>
            </div>
        </>
    );
}

const GuestReviewPrompt = () => {
    const router = useRouter();

    return (
        <div className="guest-review-prompt">
            <input type="text" placeholder="Be the first to drop your thoughts." readOnly />
            <button type="button" onClick={() => router.push('/login')}>
                Log in to review
            </button>
        </div>
    );
};

const ReviewForm = ({ product, onReviewSubmitted }) => {
    const [rating, setRating] = useState(5);
    const [title, setTitle] = useState("");
    const [body, setBody] = useState("");
    const [image, setImage] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError(null);

        if (!body.trim()) {
            setError("Please write a review before submitting.");
            setIsSubmitting(false);
            return;
        }

        const formData = new FormData();
        formData.append("product", String(product.id));
        formData.append("rating", String(rating));
        if (title.trim()) {
            formData.append("title", title.trim());
        }
        if (body.trim()) {
            formData.append("body", body.trim());
        }
        if (image) {
            formData.append("image", image);
        }

        try {
            await fetchApi(`/products/${product.id}/add_review/`, {
                method: "POST",
                body: formData,
            });
            // Refresh reviews by calling the callback
            if (onReviewSubmitted) {
                onReviewSubmitted();
            }
            // Reset form
            setRating(5);
            setTitle("");
            setBody("");
            setImage(null);
        } catch (err) {
            console.error("Review submission error:", err);
            let errorMessage = err.message || "Failed to submit review.";
            // Extract validation errors from error data
            if (err.status === 400 && err.data) {
                const errors = [];
                if (err.data.rating) errors.push(...(Array.isArray(err.data.rating) ? err.data.rating : [err.data.rating]));
                if (err.data.title) errors.push(...(Array.isArray(err.data.title) ? err.data.title : [err.data.title]));
                if (err.data.body) errors.push(...(Array.isArray(err.data.body) ? err.data.body : [err.data.body]));
                if (errors.length > 0) {
                    errorMessage = errors.join(" ");
                }
            }
            setError(errorMessage);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="product-detail-review-form">
            <h3>Your review</h3>
            <div className="review-form-rating">
                <span>Rating:</span>
                <div className="review-form-stars">
                    {[1, 2, 3, 4, 5].map((star) => (
                        <button
                            key={star}
                            type="button"
                            className={star <= rating ? "is-filled" : ""}
                            onClick={() => setRating(star)}
                        >
                            ★
                        </button>
                    ))}
                </div>
            </div>
            <input
                type="text"
                placeholder="Review title (optional)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
            />
            <textarea
                placeholder="Write your review here..."
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
            />
            <div className="review-form-image">
                <label htmlFor="review-image">Add an image (optional)</label>
                <input
                    type="file"
                    id="review-image"
                    accept="image/*"
                    onChange={(e) => setImage(e.target.files[0])}
                />
            </div>
            {error && <p className="review-form-error">{error}</p>}
            <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Submit Review"}
            </button>
        </form>
    );
};

export default ProductDetail;