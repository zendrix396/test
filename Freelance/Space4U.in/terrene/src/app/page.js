"use client";
import "./index.css";
import "./preloader.css";
import { useRef, useState, useEffect } from "react";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import CustomEase from "gsap/CustomEase";
import { useGSAP } from "@gsap/react";
import { useLenis } from "lenis/react";

import Nav from "@/components/Nav/Nav";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";
import FeaturedProducts from "@/components/FeaturedProjects/FeaturedProducts";
import ClientReviews from "@/components/ClientReviews/ClientReviews";
import CTAWindow from "@/components/CTAWindow/CTAWindow";
import Copy from "@/components/Copy/Copy";
import fetchApi from "@/lib/api";
import { useViewTransition } from "@/hooks/useViewTransition";
import ScrollHero from "@/components/ScrollHero/ScrollHero";
import SakuraPetals from "@/components/SakuraPetals/SakuraPetals";

const categoryItems = [
  "Figures & Statues", // Warriors
  "Keychains & Charms", // Talismans
  "Bobbleheads", // Effigies
  "Apparel & Cosplay", // Armor
  "Replica Weapons", // Blades
  "Posters & Scrolls", // Scrolls & Seals
  "Lighters & Accessories", // Fire Starters
  "Clothing", // Robes
];

const slugifyCategory = (label) =>
  label
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");

let isInitialLoad = true;
gsap.registerPlugin(ScrollTrigger, CustomEase);
CustomEase.create("hop", "0.9, 0, 0.1, 1");

export default function Home() {
  const tagsRef = useRef(null);
  const dealsRef = useRef(null);
  const [showPreloader, setShowPreloader] = useState(isInitialLoad);
  const [loaderAnimating, setLoaderAnimating] = useState(false);
  const [heroDeals, setHeroDeals] = useState([]);
  const lenis = useLenis();
  const { navigateWithTransition } = useViewTransition();

  useEffect(() => {
    return () => {
      isInitialLoad = false;
    };
  }, []);

  useEffect(() => {
    if (lenis) {
      if (loaderAnimating) {
        lenis.stop();
      } else {
        lenis.start();
      }
    }
  }, [lenis, loaderAnimating]);

  useEffect(() => {
    const fetchDeals = async () => {
      try {
        const deals = await fetchApi("/products/trending-deals/");
        if (deals && Array.isArray(deals)) {
          // Deduplicate by ID to prevent duplicates
          const uniqueDeals = deals.filter((deal, index, self) =>
            index === self.findIndex(d => d.id === deal.id)
          );
          setHeroDeals(uniqueDeals);
        }
      } catch (error) {
        console.error("Failed to fetch trending deals:", error);
        // Fallback to empty array or default deals
        setHeroDeals([]);
      }
    };
    fetchDeals();
  }, []);

  // Continuous horizontal scroll animation for deals
  useEffect(() => {
    if (!dealsRef.current || heroDeals.length === 0) return;

    const track = dealsRef.current;
    const firstSet = track.children;
    
    // Wait for elements to render
    setTimeout(() => {
      if (firstSet.length === 0) return;
      
      // Calculate the width of one complete set (half the children since we duplicate)
      const halfLength = Math.floor(firstSet.length / 2);
      let totalWidth = 0;
      
      for (let i = 0; i < halfLength; i++) {
        const child = firstSet[i];
        if (child) {
          totalWidth += child.offsetWidth;
          // Add gap width (0.75rem = 12px approximately)
          const computedStyle = window.getComputedStyle(track);
          const gap = parseFloat(computedStyle.gap) || 12;
          totalWidth += gap;
        }
      }

      // Create infinite scroll animation
      const animation = gsap.to(track, {
        x: -totalWidth,
        duration: totalWidth / 30, // Adjust speed: lower number = faster
        ease: "none",
        repeat: -1,
        onRepeat: () => {
          // Seamlessly reset without transition
          gsap.set(track, { x: 0 });
        },
      });

      return () => {
        animation.kill();
      };
    }, 100);
  }, [heroDeals]);

  useGSAP(() => {
    const tl = gsap.timeline({
      delay: 0.3,
      defaults: {
        ease: "hop",
      },
    });

    if (showPreloader) {
      setLoaderAnimating(true);
      const counts = document.querySelectorAll(".count");

      counts.forEach((count, index) => {
        const digits = count.querySelectorAll(".digit h1");

        tl.to(
          digits,
          {
            y: "0%",
            duration: 0.15,
            stagger: 0.02,
            ease: "power2.out",
          },
          index * 0.15
        );

        if (index < counts.length) {
          tl.to(
            digits,
            {
              y: "-100%",
              duration: 0.15,
              stagger: 0.02,
              ease: "power2.in",
            },
            index * 0.15 + 0.15
          );
        }
      });

      tl.to(".spinner", {
        opacity: 0,
        duration: 0.2,
      });

      tl.to(
        ".word h1",
        {
          y: "0%",
          duration: 0.8,
          ease: "power3.out",
        },
        "<"
      );

      tl.to(".divider", {
        scaleY: "100%",
        duration: 0.6,
        ease: "power2.inOut",
        onComplete: () =>
          gsap.to(".divider", { opacity: 0, duration: 0.3, delay: 0.2 }),
      });

      tl.to("#word-1 h1", {
        y: "100%",
        duration: 0.6,
        delay: 0.3,
        ease: "power3.in",
      });

      tl.to(
        "#word-2 h1",
        {
          y: "-100%",
          duration: 0.6,
          ease: "power3.in",
        },
        "<"
      );

      tl.to(
        ".block",
        {
          clipPath: "polygon(0% 0%, 100% 0%, 100% 0%, 0% 0%)",
          duration: 0.5,
          stagger: 0.1,
          delay: 0.2,
          ease: "power3.inOut",
          onStart: () => {
            gsap.to(".hero-img", { scale: 1, duration: 1.2, ease: "power3.out" });
          },
          onComplete: () => {
            gsap.set(".loader", { pointerEvents: "none" });
            setLoaderAnimating(false);
          },
        },
        "<"
      );
    }
  }, [showPreloader]);

  useGSAP(
    () => {
      if (!tagsRef.current) return;

      const tags = tagsRef.current.querySelectorAll(".what-we-do-tag");
      gsap.set(tags, { opacity: 0, x: -40 });

      ScrollTrigger.create({
        trigger: tagsRef.current,
        start: "top 90%",
        once: true,
        animation: gsap.to(tags, {
          opacity: 1,
          x: 0,
          duration: 0.8,
          stagger: 0.1,
          ease: "power3.out",
        }),
      });
    },
    { scope: tagsRef }
  );

  useGSAP(() => {
    if (!dealsRef.current) return;
    if (typeof window === "undefined") return;
    if (heroDeals.length === 0) return; // Don't animate if no deals

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReducedMotion) {
      gsap.set(dealsRef.current, { x: 0 });
      return;
    }

    const track = dealsRef.current;
    let marqueeAnimation = null;
    
    const startAnimation = () => {
      // Use setTimeout to ensure DOM is fully rendered
      setTimeout(() => {
        // Get all chips
        const allChips = track.querySelectorAll('.hero-offer-chip');
        if (allChips.length === 0) return;

        // Calculate width of first set (non-duplicated chips)
        const firstSetCount = heroDeals.length;
        let totalWidth = 0;
        
        for (let i = 0; i < firstSetCount && i < allChips.length; i++) {
          const chip = allChips[i];
          const rect = chip.getBoundingClientRect();
          totalWidth += rect.width + 12; // width + gap (0.75rem = 12px)
        }
        
        if (!totalWidth || totalWidth <= 0) {
          // Retry after a short delay if calculation failed
          setTimeout(startAnimation, 200);
          return;
        }

        // Speed: pixels per second (adjust for desired speed - slower = smoother)
        const pixelsPerSecond = 60; // Smooth, headline-like speed
        const duration = totalWidth / pixelsPerSecond;

        // Kill existing animation
        if (marqueeAnimation) {
          marqueeAnimation.kill();
        }

        // Reset position to 0
        gsap.set(track, { x: 0 });

        // Create seamless infinite loop animation
        marqueeAnimation = gsap.to(track, {
          x: -totalWidth,
          duration: duration,
          ease: "none",
          repeat: -1,
        });
      }, 150);
    };

    // Initial animation start
    startAnimation();

    // Recalculate on window resize
    const handleResize = () => {
      if (marqueeAnimation) {
        marqueeAnimation.kill();
      }
      if (track) {
      gsap.set(track, { x: 0 });
      }
      startAnimation();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (marqueeAnimation) {
        marqueeAnimation.kill();
      }
    };
  }, { scope: dealsRef, dependencies: [heroDeals] });

  return (
    <>
      {showPreloader && (
        <div className="loader">
          <div className="overlay">
            <div className="block"></div>
            <div className="block"></div>
          </div>
          <div className="intro-logo">
            <div className="word" id="word-1">
              <h1>
                <span>SPACE4U</span>
              </h1>
            </div>
            <div className="word" id="word-2">
              <h1>The Warrior's Path</h1>
            </div>
          </div>
          <div className="divider"></div>
          <div className="spinner-container">
            <div className="spinner"></div>
          </div>
          <div className="counter">
            <div className="count">
              <div className="digit">
                <h1>0</h1>
              </div>
              <div className="digit">
                <h1>0</h1>
              </div>
            </div>
            <div className="count">
              <div className="digit">
                <h1>2</h1>
              </div>
              <div className="digit">
                <h1>7</h1>
              </div>
            </div>
            <div className="count">
              <div className="digit">
                <h1>6</h1>
              </div>
              <div className="digit">
                <h1>5</h1>
              </div>
            </div>
            <div className="count">
              <div className="digit">
                <h1>9</h1>
              </div>
              <div className="digit">
                <h1>8</h1>
              </div>
            </div>
            <div className="count">
              <div className="digit">
                <h1>9</h1>
              </div>
              <div className="digit">
                <h1>9</h1>
              </div>
            </div>
          </div>
        </div>
      )}
      <SakuraPetals />
      <ScrollHero 
        heroTitle="Uncover Legendary Artifacts for the True Warrior"
        heroTagline="Welcome to SPACE4U — your gateway to the realm of legends. From the heroes of old to the villains of lore, each artifact is forged for those who honor the warrior's spirit."
      />
      <section className="hero">
        <div className="hero-bg">
          <img src="/home/hero.jpg" alt="" />
        </div>
        <div className="hero-gradient"></div>
        {heroDeals.length > 0 && (
        <div className="hero-offers" aria-label="Active deals">
          <div className="hero-offers-strip">
            <div className="hero-offers-track" ref={dealsRef}>
              {/* Duplicate deals for seamless infinite scroll - this creates the circular effect */}
              {[...heroDeals, ...heroDeals].map((deal, index) => {
                const isDuplicate = index >= heroDeals.length;
                return (
                <span
                    key={`${deal.id}-${index}`}
                  className="hero-offer-chip"
                    style={{ 
                      zIndex: isDuplicate ? 2 : 1,
                      cursor: deal.target_url ? 'pointer' : 'default',
                      pointerEvents: 'auto',
                      background: 'rgba(245, 230, 211, 0.9)',
                      color: '#1a1a1a',
                      border: '1px solid #8b0000',
                      fontFamily: '"Cinzel Decorative", serif',
                      backdropFilter: 'none'
                    }}
                    aria-hidden={isDuplicate}
                    onClick={() => {
                      if (deal.target_url) {
                        navigateWithTransition(deal.target_url);
                      }
                    }}
                >
                    {deal.label}
                </span>
                );
              })}
            </div>
          </div>
        </div>
        )}
        <div className="container">
          <div className="hero-content content-panel content-panel--hero">
            <div className="hero-header">
              <Copy 
                animateOnScroll={false} 
                delay={showPreloader ? 3 : 0.85}
                stagger={0.05}
                startY="120%"
              >
                <h1>Uncover Legendary Artifacts for the True Warrior</h1>
              </Copy>
            </div>
            <div className="hero-tagline">
              <Copy 
                animateOnScroll={false} 
                delay={showPreloader ? 3.3 : 1}
                stagger={0.05}
                startY="120%"
              >
                <p style={{ textShadow: '0 2px 4px rgba(0,0,0,0.8)', fontWeight: 600 }}>
                  Welcome to SPACE4U — your gateway to the realm of legends. From the heroes of old to the villains of lore, 
                  each artifact is forged for those who honor the warrior's spirit.
                </p>
              </Copy>
            </div>
            <AnimatedButton
              label="Enter the Armory"
              route="/shop"
              animateOnScroll={false}
              delay={showPreloader ? 3.5 : 1.15}
            />
          </div>
        </div>
        <div className="hero-stats">
          <div className="container">
            <div className="stat">
              <div className="stat-count">
                <Copy delay={0.1}>
                  <h2>500+</h2>
                </Copy>
              </div>
              <div className="stat-divider"></div>
              <div className="stat-info">
                <Copy delay={0.15}>
                  <p>Legendary Relics</p>
                </Copy>
              </div>
            </div>
            <div className="stat">
              <div className="stat-count">
                <Copy delay={0.2}>
                  <h2>50+</h2>
                </Copy>
              </div>
              <div className="stat-divider"></div>
              <div className="stat-info">
                <Copy delay={0.25}>
                  <p>Ancient Tales</p>
                </Copy>
              </div>
            </div>
            <div className="stat">
              <div className="stat-count">
                <Copy delay={0.3}>
                  <h2>10K+</h2>
                </Copy>
              </div>
              <div className="stat-divider"></div>
              <div className="stat-info">
                <Copy delay={0.35}>
                  <p>Honored Allies</p>
                </Copy>
              </div>
            </div>
            <div className="stat">
              <div className="stat-count">
                <Copy delay={0.4}>
                  <h2>98%</h2>
                </Copy>
              </div>
              <div className="stat-divider"></div>
              <div className="stat-info">
                <Copy delay={0.45}>
                  <p>Warrior's Honor</p>
                </Copy>
              </div>
            </div>
          </div>
        </div>
      </section>
      {/* Welcome headline with SplitText reveal on scroll */}
      <section className="welcome-section">
        <div className="container">
          <div className="welcome-header">
            <Copy delay={0.1}>
              <h1>
                <span className="spacer">&nbsp;</span>
                Welcome to SPACE4U — the only merchandise store, home for anime, 
                superheroes and supervillains. With our unique selection, you can 
                unleash your love!
              </h1>
            </Copy>
          </div>
        </div>
      </section>
      <section id="categories" className="categories">
        <div className="container">
          <div
            className="featured-projects-header is-clickable"
            role="link"
            tabIndex={0}
            onClick={() => navigateWithTransition("/shop")}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                navigateWithTransition("/shop");
              }
            }}
            aria-label="View products filtered by category"
          >
            <div
              className="featured-projects-header-callout"
              onClick={(e) => {
                e.stopPropagation();
                navigateWithTransition("/shop");
              }}
            >
              <Copy delay={0.1}>
                <p>Browse by category</p>
              </Copy>
            </div>
            <Copy delay={0.15}>
              <h2>Find what you love across expansive collections</h2>
            </Copy>
          </div>
          <div className="categories-scroll">
          <div className="categories-grid">
            {categoryItems.map((category) => {
              const slug = slugifyCategory(category);
                const handleNavigate = () =>
                  navigateWithTransition(
                    `/shop?category=${encodeURIComponent(slug)}`
                  );

              return (
                <button
                  key={category}
                  className="category-card"
                  type="button"
                    onClick={handleNavigate}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        handleNavigate();
                      }
                    }}
                    aria-label={`Browse ${category} collectibles`}
                >
                  {category}
                </button>
              );
            })}
          </div>
          </div>
          <AnimatedButton
            label="View All Categories"
            route="/shop"
            extraClasses="view-all-btn"
          />
        </div>
      </section>
      <section className="featured-projects-container">
        <div className="container">
          <div
            className="featured-projects-header-callout is-clickable"
            role="link"
            tabIndex={0}
            onClick={() => navigateWithTransition("/shop?sort=newest")}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                navigateWithTransition("/shop?sort=newest");
              }
            }}
            aria-label="See what's new in the shop"
          >
            <Copy delay={0.1}>
              <p>New Arrivals</p>
            </Copy>
          </div>
          <div
            className="featured-projects-header is-clickable"
            role="link"
            tabIndex={0}
            onClick={() => navigateWithTransition("/shop?sort=newest")}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                navigateWithTransition("/shop?sort=newest");
              }
            }}
            aria-label="Discover exclusive anime merchandise and collectibles"
          >
            <Copy delay={0.15}>
              <h2>Discover exclusive anime merchandise and collectibles</h2>
            </Copy>
          </div>
        </div>
        <FeaturedProducts />
      </section>
      <section className="client-reviews-container">
        <div className="container">
          <ClientReviews />
        </div>
      </section>
      <section className="gallery-callout">
        <div className="container">
          <div className="gallery-callout-col">
            <div className="gallery-callout-row">
              <div className="gallery-callout-img gallery-callout-img-1">
                <img src="/gallery-callout/gallery-callout-1.jpg" alt="" />
              </div>
              <div className="gallery-callout-img gallery-callout-img-2">
                <img src="/gallery-callout/gallery-callout-2.jpg" alt="" />
                <div className="gallery-callout-img-content">
                  <h3>500+</h3>
                  <p>Premium Products</p>
                </div>
              </div>
            </div>
            <div className="gallery-callout-row">
              <div className="gallery-callout-img gallery-callout-img-3">
                <img src="/gallery-callout/gallery-callout-3.jpg" alt="" />
              </div>
              <div className="gallery-callout-img gallery-callout-img-4">
                <img src="/gallery-callout/gallery-callout-4.jpg" alt="" />
              </div>
            </div>
          </div>
          <div className="gallery-callout-col">
            <div className="gallery-callout-copy">
              <Copy delay={0.1}>
                <h3>
                  Browse our expansive collection of anime merchandise, superhero collectibles, 
                  and premium figures. From iconic characters to limited editions, each piece 
                  celebrates legendary tales and brings your favorite stories to life.
                </h3>
              </Copy>
              <AnimatedButton label="Shop Collection" route="/shop" />
            </div>
          </div>
        </div>
      </section>
      <CTAWindow
        img="/home/home-cta-window.jpg"
        header="SPACE4U"
        callout="Your Otaku Haven"
        description="Be it anime, superheroes and supervillains — everything is here. Join our community of passionate fans and elevate your collection with high-quality products today!"
      />
    </>
  );
}
