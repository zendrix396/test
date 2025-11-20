"use client";
import "./CategoryPreview.css";
import { useState, useEffect } from "react";
import fetchApi from "@/lib/api";
import { useRouter } from "next/navigation";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";
import { useViewTransition } from "@/hooks/useViewTransition";

const ProductCard = ({ product, onSelect }) => {
  const price = product.discount_price || product.price;
  const originalPrice = product.discount_price ? product.price : null;
  const image = product.image || (product.images && product.images[0]?.image);

  return (
    <div className="category-preview-product-card" onClick={() => onSelect(product)}>
      {image && (
        <div className="category-preview-product-image">
          <img src={image} alt={product.name} />
        </div>
      )}
      <div className="category-preview-product-info">
        <h4>{product.name}</h4>
        <div className="category-preview-product-price">
          {originalPrice ? (
            <>
              <span className="discount-price">₹{price}</span>
              <span className="original-price">₹{originalPrice}</span>
            </>
          ) : (
            <span>₹{price}</span>
          )}
        </div>
      </div>
    </div>
  );
};

const CategoryPreview = ({ category, slug }) => {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { navigateWithTransition } = useViewTransition();

  useEffect(() => {
    const fetchProducts = async () => {
      setIsLoading(true);
      try {
        const data = await fetchApi(`/products/?category=${slug}&page_size=4`);
        const productsList = data.results || data || [];
        setProducts(productsList);
      } catch (error) {
        console.error(`Failed to fetch products for ${category}:`, error);
        setProducts([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, [category, slug]);

  const handleProductSelect = (product) => {
    if (product?.sku) {
      navigateWithTransition(`/shop/${product.sku}`);
    }
  };

  const handleMoreClick = () => {
    navigateWithTransition(`/shop?category=${encodeURIComponent(slug)}`);
  };

  if (isLoading) {
    return (
      <div className="category-preview">
        <div className="category-preview-header">
          <h3>{category}</h3>
        </div>
        <div className="category-preview-products">
          {Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="category-preview-product-card skeleton" />
          ))}
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return null;
  }

  return (
    <div className="category-preview">
      <div className="category-preview-header">
        <h3>{category}</h3>
      </div>
      <div className="category-preview-products">
        {products.slice(0, 4).map((product) => (
          <ProductCard key={product.id || product.sku} product={product} onSelect={handleProductSelect} />
        ))}
      </div>
      <div className="category-preview-actions">
        <AnimatedButton
          label="More"
          onClick={handleMoreClick}
          animate={false}
        />
      </div>
    </div>
  );
};

export default CategoryPreview;

