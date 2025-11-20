import ProductDetail from "@/components/ProductDetail/ProductDetail";
import RecentlyViewedTracker from "@/components/RecentlyViewedTracker/RecentlyViewedTracker";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://space4u.in";

export async function generateMetadata({ params }) {
  const resolvedParams = await params;
  const { sku } = resolvedParams;
  const decodedSku = decodeURIComponent(sku);

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    
    try {
      const response = await fetch(`${API_BASE_URL}/products/?sku=${encodeURIComponent(decodedSku)}`, {
    cache: "no-store",
        signal: controller.signal,
  });
      
      clearTimeout(timeoutId);

  if (!response.ok) {
        return {
          title: "Product Not Found",
        };
      }
      const data = await response.json();
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      const product = results[0];

      if (!product) {
        return {
          title: "Product Not Found",
        };
      }

      const price = product.discount_price || product.price || product.variants?.[0]?.price || 0;
      const image = product.image || product.images?.[0]?.image || "/home/hero.jpg";
      const description = product.description || `Buy ${product.name} - Premium ${product.category?.name || "merchandise"} at SPACE4U. ${product.tags?.join(", ") || ""}`;

      return {
        title: `${product.name} | SPACE4U`,
        description: description.substring(0, 160),
        keywords: [
          product.name,
          product.category?.name,
          ...(product.tags || []),
          "anime merchandise",
          "collectibles",
        ],
        openGraph: {
          title: `${product.name} | SPACE4U`,
          description: description.substring(0, 160),
          url: `${siteUrl}/shop/${sku}`,
          siteName: "SPACE4U",
          images: [
            {
              url: image.startsWith("http") ? image : `${siteUrl}${image}`,
              width: 1200,
              height: 630,
              alt: product.name,
            },
          ],
          type: "website",
        },
        twitter: {
          card: "summary_large_image",
          title: `${product.name} | SPACE4U`,
          description: description.substring(0, 160),
          images: [image.startsWith("http") ? image : `${siteUrl}${image}`],
        },
        alternates: {
          canonical: `${siteUrl}/shop/${sku}`,
        },
      };
    } finally {
      clearTimeout(timeoutId);
    }
  } catch (error) {
    // Handle timeout or other errors gracefully
    if (error.name === 'AbortError' || error.message?.includes('timeout')) {
      console.warn("Metadata fetch timeout, using default metadata");
    } else {
      console.warn("Metadata generation error:", error);
    }
    return {
      title: "Product | SPACE4U",
    };
  }
}

async function fetchJSON(path, timeout = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }

  return response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout for ${path}`);
    }
    throw error;
  }
}

async function fetchProduct(sku) {
  const data = await fetchJSON(`/products/?sku=${encodeURIComponent(sku)}`);
  const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  return results[0] || null;
}

async function fetchRelated(product) {
  if (!product?.category?.slug) {
    return [];
  }

  try {
    const data = await fetchJSON(
      `/products/?category=${encodeURIComponent(product.category.slug)}&page_size=12`
    );
    const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    return results.filter((item) => item.sku !== product.sku).slice(0, 10);
  } catch (error) {
    console.warn("Unable to load related products", error);
    return [];
  }
}

async function fetchReviews(productId) {
  try {
    const data = await fetchJSON(`/products/${productId}/reviews/`);
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.warn("Reviews unavailable", error);
    return [];
  }
}

async function fetchLoyaltyConfig() {
  try {
    const data = await fetchJSON(`/auth/loyalty-config/`);
    return data;
  } catch (error) {
    console.warn("Loyalty config unavailable", error);
    return { enabled: false, points_per_currency: 0 };
  }
}

export default async function ProductPage({ params }) {
  const resolvedParams = await params;
  const { sku } = resolvedParams;
  const decodedSku = decodeURIComponent(sku);

  let product = null;
  try {
    product = await fetchProduct(decodedSku);
  } catch (error) {
    console.error("Failed to fetch product", error);
  }

  if (!product) {
    notFound();
  }

  const [related, loyaltyConfig, reviews] = await Promise.all([
    fetchRelated(product),
    fetchLoyaltyConfig(),
    fetchReviews(product.id),
  ]);

  return (
    <>
      <RecentlyViewedTracker sku={decodedSku} />
      <div className="page shop-detail">
        <ProductDetail
          product={product}
          related={related}
          loyaltyConfig={loyaltyConfig}
          reviews={reviews}
        />
      </div>
    </>
  );
}
