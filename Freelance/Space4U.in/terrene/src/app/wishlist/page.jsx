"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useWishlistContext } from "@/context/WishlistContext";
import { useCurrencyContext } from "@/context/CurrencyContext";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { FiHeart, FiTrash2 } from "react-icons/fi";
import "./wishlist.css";

const WishlistPage = () => {
  const router = useRouter();
  const { items, isLoading, removeItem } = useWishlistContext();
  const { formatCurrency } = useCurrencyContext();
  const heroRef = useRef(null);
  const gridRef = useRef(null);

  useGSAP(
    () => {
      if (heroRef.current) {
        gsap.fromTo(
          heroRef.current.querySelectorAll(".wishlist-reveal"),
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 1, stagger: 0.12, ease: "power3.out" }
        );
      }
      if (gridRef.current) {
        gsap.fromTo(
          gridRef.current.querySelectorAll(".wishlist-item"),
          { y: 35, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.9, stagger: 0.08, ease: "power3.out", delay: 0.2 }
        );
      }
    },
    { scope: heroRef }
  );

  const handleRemove = async (variantId) => {
    try {
      await removeItem(variantId);
    } catch (error) {
      console.error("Failed to remove from wishlist", error);
    }
  };

  const handleProductClick = (product) => {
    if (product?.sku) {
      router.push(`/shop/${product.sku}`);
    }
  };

  return (
    <>
      <div className="page wishlist-page">
        <div className="container wishlist-wrapper" ref={heroRef}>
          <section className="wishlist-hero">
            <h1 className="wishlist-reveal">Your Wishlist</h1>
            <p className="wishlist-reveal lead">
              Keep track of your grail hunts. When you're ready, move them to cart or remove them forever.
            </p>
          </section>

          {isLoading && (
            <div className="wishlist-empty">
              <p>Loading your wishlist…</p>
            </div>
          )}

          {!isLoading && items.length === 0 && (
            <div className="wishlist-empty">
              <FiHeart size={48} style={{ opacity: 0.4, marginBottom: "1rem" }} />
              <p>Your wishlist is empty.</p>
              <p style={{ fontSize: "0.95rem", opacity: 0.7 }}>
                Start adding items from the shop to build your collection wishlist.
              </p>
            </div>
          )}

          {!isLoading && items.length > 0 && (
            <section className="wishlist-grid" ref={gridRef}>
              {items.map((item) => {
                const product = item?.variant?.product || item?.product;
                const variant = item?.variant;
                const image =
                  product?.image ||
                  (Array.isArray(product?.images) && product?.images[0]?.image) ||
                  variant?.image ||
                  null;

                return (
                  <article key={item.id} className="wishlist-item">
                    <div
                      className="wishlist-item-media"
                      onClick={() => handleProductClick(product)}
                      role="button"
                      tabIndex={0}
                    >
                      {image ? (
                        <img src={image} alt={product?.name || "Product"} />
                      ) : (
                        <div className="wishlist-item-placeholder">No image</div>
                      )}
                      <button
                        className="wishlist-item-remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(variant?.id);
                        }}
                        aria-label="Remove from wishlist"
                      >
                        <FiTrash2 />
                      </button>
                    </div>
                    <div className="wishlist-item-body">
                      <h3 onClick={() => handleProductClick(product)}>{product?.name || "Unknown Product"}</h3>
                      {variant?.name && <p className="wishlist-item-variant">{variant.name}</p>}
                      {product?.tags && product.tags.length > 0 && (
                        <div className="wishlist-item-tags">
                          {product.tags.slice(0, 3).map((tag, idx) => (
                            <span key={idx} className="wishlist-item-tag">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="wishlist-item-pricing">
                        <span className="wishlist-item-price">
                          {formatCurrency(
                            variant?.converted_discount_price || 
                            variant?.converted_price ||
                            variant?.discount_price || 
                            variant?.price || 
                            product?.discount_price || 
                            product?.price
                          )}
                        </span>
                        {(variant?.converted_discount_price || variant?.discount_price) && (variant?.converted_price || variant?.price) && (
                          <span className="wishlist-item-compare">
                            {formatCurrency(variant?.converted_price || variant?.price)}
                          </span>
                        )}
                      </div>
                      <button
                        className="wishlist-item-action"
                        onClick={() => handleProductClick(product)}
                      >
                        View product
                      </button>
                    </div>
                  </article>
                );
              })}
            </section>
          )}
        </div>
      </div>
    </>
  );
};

export default WishlistPage;

